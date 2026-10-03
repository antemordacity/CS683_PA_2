#include "cache.h"
#include<cstring>

#define PREFETCH_DEGREE 1
#define MASK_IP 0xFF
#define IP_TRACKER_COUNT 24
#define PATTERN_WIDTH 2
#define UNI_CONF_THRESH 1
#define NON_UNI_CONF_THRESH 2

template <typename T, std::size_t MaxLen, typename Container = std::deque<T>>
class FixedQueue : public Container {
public:
    void push(const T& value) {
        if (this->size() == MaxLen) {
            this->pop_front();
        }
        Container::push_back(value);
    }
};

inline void reset(FixedQueue<int64_t, PATTERN_WIDTH> &q) {
    while (!q.empty())
        q.pop_back();
}

typedef enum {
    STATE_INIT,
    STATE_UNI,
    STATE_NON_UNI
} PF_STATE;

class IP_TRACKER{
    public:
        uint64_t ip; 
        FixedQueue<int64_t, PATTERN_WIDTH> strides; //observed stride pattern
        //uint64_t stride_offset;
        uint64_t last_cl_addr; //last address accessed
        uint32_t lru;
        uint32_t conf_counter;
        uint32_t uni_conf_counter;
        PF_STATE state;
        IP_TRACKER () {
            //stride_offset = 0;
            conf_counter = 0;
            uni_conf_counter = 0;
            state = STATE_INIT;
            ip = 0;
            last_cl_addr = 0;
            reset(strides); 
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
        trackers[index].state = STATE_INIT;

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
        case STATE_INIT: 
            //resets table entry
            trackers[index].conf_counter = 0;
            trackers[index].uni_conf_counter = 0;
            reset(trackers[index].strides);
            //new stride observed, move to uniform access state
            trackers[index].state = STATE_UNI;
            trackers[index].strides.push(stride);
            trackers[index].last_cl_addr = cl_addr;
            break;
        case STATE_UNI:
            if (stride == trackers[index].strides.back()) {
                trackers[index].conf_counter = 0;
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
                trackers[index].strides.push(stride);
                if(trackers[index].conf_counter++ > NON_UNI_CONF_THRESH)
                    trackers[index].state = STATE_NON_UNI;
            }
            trackers[index].last_cl_addr = cl_addr;
            break;
        case STATE_NON_UNI:
            trackers[index].last_cl_addr = cl_addr;
            if(stride == trackers[index].strides.front()){
                if(trackers[index].uni_conf_counter++ > UNI_CONF_THRESH)
                    trackers[index].state = STATE_INIT;
            }
            else{
                trackers[index].uni_conf_counter = 0;
                trackers[index].state = STATE_INIT;
                if(trackers[index].strides.front() == stride){
                    uint64_t address = cl_addr;
                    for (int i=0; i<PREFETCH_DEGREE; i++) {
                        address += trackers[index].strides[i];
                        uint64_t pf_address = address << LOG2_BLOCK_SIZE;

                        // only issue a prefetch if the prefetch address is in the same 4 KB page
                        // as the current demand access address
                        if ((pf_address >> LOG2_PAGE_SIZE) != (addr >> LOG2_PAGE_SIZE))
                            break;

                        // check the MSHR occupancy to decide if we're going to prefetch to the L1 or L2
                        if (MSHR.occupancy < (MSHR.SIZE>>1))
                            prefetch_line(ip, addr, pf_address, FILL_L1, 0);
                        else
                            prefetch_line(ip, addr, pf_address, FILL_L2, 0);
                    } // prefetch the thing(s) after front
                }
                else{
                    trackers[index].strides.push(stride);
                }
            }
            break;
    }

}

void CACHE::l1d_prefetcher_cache_fill(uint64_t v_addr, uint64_t addr, uint32_t set, uint32_t way, uint8_t prefetch, uint64_t v_evicted_addr, uint64_t evicted_addr, uint32_t metadata_in)
{
	return; //metadata_in;
}

void CACHE::l1d_prefetcher_final_stats()
{
    cout << "CPU " << cpu << " L1D PC-based stride prefetcher final stats" << endl;
	cout << "Degree: " << PREFETCH_DEGREE << endl;
}