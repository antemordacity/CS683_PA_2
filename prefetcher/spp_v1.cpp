#include "cache.h"


#define IP_TRACKER_COUNT 24
#define PREFETCH_DEGREE 3
#define HISTORY_LENGTH 3
#define UNI_THRESH 2
#define NON_UNI_THRESH 2
#define SPT_SIZE 64
#define MASK_IP 0xFF

typedef enum { NON_UNIFORM, UNIFORM } state_t;

class SPT { //Stride Prediction Table
    public: //I've no clue how to implement this properly
        typedef struct {
            int64_t index;
            int64_t next_stride;
            int8_t conf;
        } SPT_entry;

        SPT_entry signature(IP_TRACKER *); //signature for hashing into SPT
        int64_t next_stride(IP_TRACKER *);
        int8_t* next_conf(IP_TRACKER *);
        void update_stride(IP_TRACKER *, int64_t);
        SPT (){

        };
};

SPT spt;

class IP_TRACKER {
  public:
    uint64_t ip;
    uint64_t last_cl_addr;
    int64_t last_stride;
    int64_t stride_history[HISTORY_LENGTH]; //last 3 strides 
    uint32_t lru;
    uint8_t uni_conf; //confidence counter for uniform stride
    state_t state;
    IP_TRACKER () {
        ip = 0;
        last_cl_addr = 0;
        last_stride = 0;
        lru = 0;
        uni_conf = UNI_THRESH;
        state = UNIFORM;
        for (int i=0; i<HISTORY_LENGTH; i++)
            stride_history[i] = 0;
    };
};

IP_TRACKER trackers[IP_TRACKER_COUNT];

void push_history(IP_TRACKER *tracker, int64_t stride) {
    for (int i = 1; i<HISTORY_LENGTH; i++)
        tracker->stride_history[i-1] = tracker->stride_history[i];
    tracker->stride_history[HISTORY_LENGTH-1] = stride;
}

void update_LRU(IP_TRACKER *tracker) {
    for (int i=0; i<IP_TRACKER_COUNT; i++) {
        if (trackers[i].lru < tracker->lru)
            trackers[i].lru++;
    }
    tracker->lru = 0;
}

void CACHE::l1d_prefetcher_initialize() {
    cout << "CPU " << cpu << " L1D SPP" << endl;
    for (int i=0; i<IP_TRACKER_COUNT; i++)
        trackers[i].lru = i;
}

void CACHE::l1d_prefetcher_operate(uint64_t addr, uint64_t ip, uint8_t cache_hit, uint8_t type, uint8_t critical_ip_flag){
    uint64_t cl_addr = addr >> LOG2_BLOCK_SIZE;
    ip = ip & MASK_IP; //use tag bits from the start of the IP to prevent 0 getting false positives?

    int index = -1;
    for (index=0; index<IP_TRACKER_COUNT; index++) {
        if (trackers[index].ip == ip)
            break;
    }

    if (index == IP_TRACKER_COUNT) { //if new IP replace LRU tracker
        for (int i =0; i<IP_TRACKER_COUNT; i++) {
            if (trackers[i].lru == (IP_TRACKER_COUNT-1))
                index = i;
            else
                trackers[i].lru++; //update LRU of all other trackers
        }

        trackers[index].ip = ip;
        trackers[index].last_cl_addr = cl_addr;
        trackers[index].last_stride = 0;
        trackers[index].uni_conf = UNI_THRESH;
        memset(trackers[index].stride_history, 0, sizeof(uint64_t)*HISTORY_LENGTH);
        
        trackers[index].lru = 0; //reset LRU of replaced tracker

        return; //metadata_in;
    }

	// sanity check
    // at this point we should know a matching tracker index
    if (index == -1)
        assert(0);
    
    update_LRU(&trackers[index]);
    
    int64_t stride = 0;
    if (cl_addr > trackers[index].last_cl_addr)
        stride = cl_addr - trackers[index].last_cl_addr;
    else {
        stride = trackers[index].last_cl_addr - cl_addr;
        stride *= -1;
    }

    if(stride == 0) {
        return; //metadata_in;
    }

    if (stride > 63 || stride < -63) { //try to think of a way to handle this better
        return; //metadata_in;
    }

    trackers[index].last_cl_addr = cl_addr;

    switch (trackers[index].state) {
        case UNIFORM:
            if (stride == trackers[index].last_stride) {
                if (trackers[index].uni_conf < 3) //update confidence counter
                    trackers[index].uni_conf++;
                //uniform prefetch here
            }
            else {
                trackers[index].uni_conf--; //update confidence counter
                //update SPT 
            }
            push_history(&trackers[index], stride);
            //state transition logic
            if (trackers[index].uni_conf < UNI_THRESH) {
                trackers[index].state = NON_UNIFORM;
            }
            break;
        case NON_UNIFORM:
            //updating confidence counters
            int8_t *non_uni_conf = spt.next_conf(&trackers[index]);
            if(stride == trackers[index].last_stride){
                trackers[index].uni_conf++;
            }
            else{
                if(trackers[index].uni_conf > 0)
                    trackers[index].uni_conf--;
                else
                    trackers[index].last_stride = stride; //updating last stride if conf = 0
            }
            if(spt.next_stride(&trackers[index]) == stride){
                if(*non_uni_conf < 3)
                    (*non_uni_conf)++;
            }
            else{
                if(*non_uni_conf > 0)
                    (*non_uni_conf)--;
                else
                    spt.update_stride(&trackers[index], stride);
            }
            //prefetching
            push_history(&trackers[index], stride);
            if(*spt.next_conf(&trackers[index]) >= NON_UNI_THRESH){
                //prefetch logic
            }
            //state transition logic
            if (trackers[index].uni_conf >= UNI_THRESH) {
                trackers[index].state = UNIFORM;
            }
            break;
    }
    
    return; //metadata_in;

}


void CACHE::l1d_prefetcher_cache_fill(uint64_t v_addr, uint64_t addr, uint32_t set, uint32_t way, uint8_t prefetch, uint64_t v_evicted_addr, uint64_t evicted_addr, uint32_t metadata_in)
{


}

void CACHE::l1d_prefetcher_final_stats()
{

}

