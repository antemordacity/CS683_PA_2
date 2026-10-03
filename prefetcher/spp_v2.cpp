#include "cache.h"
#include<cstring>

#define PREFETCH_DEGREE 1
#define MASK_IP 0xFF
#define IP_TRACKER_COUNT 24
#define PATTERN_WIDTH 3
#define UNI_THRESH 1
#define NON_UNI_THRESH 2
#define COUNTER_SAT 7
/*
    note to self: 
    non-uniform prediction amended when counter goes to 0
    saturating counters all
*/

typedef struct stride_node {
    int64_t stride;
    struct stride_node *next;
    uint8_t conf; //confidence counter for non-uniform prediction
}stride_node;

class SP_TRACKER{
    public:
        stride_node *head;
        stride_node *tail;
        uint64_t size;
    SP_TRACKER () {
        head = nullptr;
        tail = nullptr;
        size = 0;
    };
    void advance(){
        if(size > 0){
            head = head->next;
            tail = tail->next;
        }
    };
    void push(int64_t stride_val) {
        if(size > PATTERN_WIDTH){
            head = head->next;
            delete tail->next;
            tail->next = head;
            size--;
        }
        if(!head){
            head = new stride_node;
            head->stride = stride_val;
            head->next = head;
            head->conf = 1;
            tail = head;
        }
        else{
            tail->next = new stride_node;
            tail->next->next = head;
            tail->next->stride = stride_val;
            tail->next->conf = 1;
            tail = tail->next;
        }
        size++;
    };
    void destroy(){
        stride_node* node = head->next;
        while(node != head){
            stride_node *temp = node;
            node = node->next;
            delete temp;
        }
        delete head;
        head = nullptr;
        tail = nullptr;
        size = 0;
    }
    uint64_t stride(){
        return tail->stride;
    };
    uint64_t signature(){
        return tail->next->stride;
    };
    uint8_t* confidence(){
        return &tail->conf;
    };
    ~SP_TRACKER () {
        destroy();
    };
};


typedef enum {
    STATE_UNI,
    STATE_TRANS,
    STATE_NON_UNI
} PF_STATE;

class IP_TRACKER{
    public:
        int64_t curr_stride;
        uint64_t ip; 
        SP_TRACKER strides; //observed stride pattern
        uint64_t last_cl_addr; //last address accessed
        uint32_t lru;
        uint8_t uni_conf; //confidence counter for uniform access state
        PF_STATE state;
        IP_TRACKER () {
            uni_conf = UNI_THRESH;
            strides = SP_TRACKER();
            state = STATE_UNI;
            ip = 0;
            last_cl_addr = 0;
            lru = 0;
    };
};

IP_TRACKER trackers[IP_TRACKER_COUNT];


void CACHE::l1d_prefetcher_initialize() 
{
    std::cout << "------------------------------------------------" << std::endl;
    std::cout << "        Stride Pattern Prefetcher (SPP)         " << std::endl;
    std::cout << "------------------------------------------------" << std::endl;
    for (int i=0; i<IP_TRACKER_COUNT; i++)
        	trackers[i].lru = i;
}

void CACHE::l1d_prefetcher_operate(uint64_t addr, uint64_t ip, uint8_t cache_hit, uint8_t type, uint8_t critical_ip_flag)
{
    uint64_t cl_addr = addr >> LOG2_BLOCK_SIZE;
    ip = ip & MASK_IP;
    int index = -1;
    for (index=0; index<IP_TRACKER_COUNT; index++) {
        if (trackers[index].ip == ip)
            break;
    }
    if (index == IP_TRACKER_COUNT) {

        for (index=0; index<IP_TRACKER_COUNT; index++) {
            if (trackers[index].lru == (IP_TRACKER_COUNT-1))
                break;
        }

        //maybe write a function for this?
        trackers[index].ip = ip;
        trackers[index].last_cl_addr = cl_addr;
        trackers[index].state = STATE_UNI;
        trackers[index].uni_conf = UNI_THRESH;
        trackers[index].strides.destroy();

        //cout << "[IP_STRIDE] MISS index: " << index << " lru: " << trackers[index].lru << " ip: " << hex << ip << " cl_addr: " << cl_addr << dec << endl;
	    for (int i=0; i<IP_TRACKER_COUNT; i++) {
            if (trackers[i].lru < trackers[index].lru)
                trackers[i].lru++;
        }
        trackers[index].lru = 0;

        return; //metadata_in;
    }

	// sanity check
    // at this point we should know a matching tracker index
    if (index == -1)
        assert(0);

    //stride calculation
    int64_t stride = 0;
    if (cl_addr > trackers[index].last_cl_addr)
        stride = cl_addr - trackers[index].last_cl_addr;
    else {
        stride = trackers[index].last_cl_addr - cl_addr;
        stride *= -1;
    }

    //cout << "[IP_STRIDE] HIT  index: " << index << " lru: " << trackers[index].lru << " ip: " << hex << ip << " cl_addr: " << cl_addr << dec << " stride: " << stride << endl;
    if (stride == 0)
        return; //metadata_in
    switch(trackers[index].state){
        case STATE_UNI:
            if(trackers[index].curr_stride == stride){ //possible edge case
                trackers[index].uni_conf = std::min(trackers[index].uni_conf + 1, COUNTER_SAT);
                for (int i=0; i<PREFETCH_DEGREE; i++) {
                    uint64_t pf_address = (cl_addr + (stride*(i+1))) << LOG2_BLOCK_SIZE;

                    // only issue a prefetch if the prefetch address is in the same 4 KB page
                    // as the current demand access address
                    if ((pf_address >> LOG2_PAGE_SIZE) != (addr >> LOG2_PAGE_SIZE))
                        break;

                    // check the MSHR occupancy to decide if we're going to prefetch to the L1 or L2
                    if (MSHR.occupancy < (MSHR.SIZE>>1))
                        prefetch_line(ip, addr, pf_address, FILL_L1, 0);
                    else
                        prefetch_line(ip, addr, pf_address, FILL_L2, 0);
                }
            }
            else{
                //trackers[index].strides.push(stride);
                trackers[index].uni_conf--;
            }
            trackers[index].strides.push(stride);
            trackers[index].curr_stride = stride;
            trackers[index].last_cl_addr = cl_addr;
            if(trackers[index].uni_conf <= UNI_THRESH)
                trackers[index].state = STATE_NON_UNI;
            break;
        // case STATE_TRANS:
        //     if (stride == trackers[index].strides.stride()) {
        //         trackers[index].uni_conf++;
        //         //trackers[index].strides.push(stride); -- push only when conf = 0
        //         break;
        //     }
        //     if(stride == trackers[index].strides.signature()){
        //         (*trackers[index].strides.confidence())++;
        //         break;
        //     }
        //  break;
        case STATE_NON_UNI:
            if(stride == trackers[index].strides.signature()){
                *trackers[index].strides.confidence() = std::min((*trackers[index].strides.confidence()) + 1, COUNTER_SAT);
                //trackers[index].strides.push(stride); //this overwrites the confidence counter of the next stride
            }
            else{
                *trackers[index].strides.confidence() = std::max((*trackers[index].strides.confidence()) - 1, 0);
            }
            if(*trackers[index].strides.confidence() > NON_UNI_THRESH){ //prefetch logic
                for (int i=0; i<1; i++) {
                    uint64_t pf_address = (cl_addr + (trackers[index].strides.signature()*(i+1))) << LOG2_BLOCK_SIZE;

                    // only issue a prefetch if the prefetch address is in the same 4 KB page
                    // as the current demand access address
                    if ((pf_address >> LOG2_PAGE_SIZE) != (addr >> LOG2_PAGE_SIZE))
                        break;

                    // check the MSHR occupancy to decide if we're going to prefetch to the L1 or L2
                    if (MSHR.occupancy < (MSHR.SIZE>>1))
                        prefetch_line(ip, addr, pf_address, FILL_L1, 0);
                    else
                        prefetch_line(ip, addr, pf_address, FILL_L2, 0);
                }
            }
            if(*trackers[index].strides.confidence() == 0){
                trackers[index].strides.push(stride); //push new stride when confidence counter is 0 and break
                break;
            }
            trackers[index].strides.advance();
            if(stride == trackers[index].curr_stride){
                trackers[index].uni_conf++;
            }
            else{
                trackers[index].uni_conf = std::max(trackers[index].uni_conf - 1, 0);
            }
            trackers[index].curr_stride = stride;
            if(trackers[index].uni_conf > UNI_THRESH)
                trackers[index].state = STATE_UNI;
            break;
    }

}

void CACHE::l1d_prefetcher_cache_fill(uint64_t v_addr, uint64_t addr, uint32_t set, uint32_t way, uint8_t prefetch, uint64_t v_evicted_addr, uint64_t evicted_addr, uint32_t metadata_in)
{
	return; //metadata_in;
}

void CACHE::l1d_prefetcher_final_stats()
{

}