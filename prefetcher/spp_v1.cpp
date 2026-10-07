#include "cache.h"


#define IP_TRACKER_COUNT 24
#define PREFETCH_DEGREE 3
#define HISTORY_LENGTH 3
#define MASK_IP 0xFF

typedef enum { NON_UNIFORM, UNIFORM } state_t;

class SPT { //Stride Prediction Table

};

class IP_TRACKER {
  public:
    uint64_t ip;
    uint64_t last_cl_addr;
    //int64_t last_stride;
    int64_t stride_history[HISTORY_LENGTH]; //last 3 strides 
    uint32_t lru;
    uint8_t uni_conf; //confidence counter for uniform stride
    state_t state;
    IP_TRACKER () {
        ip = 0;
        last_cl_addr = 0;
        //last_stride = 0;
        lru = 0;
        uni_conf = 0;
        state = UNIFORM;
        for (int i=0; i<HISTORY_LENGTH; i++)
            stride_history[i] = 0;
    };
};

IP_TRACKER trackers[IP_TRACKER_COUNT];

void CACHE::l1d_prefetcher_initialize() {
    cout << "CPU " << cpu << " L1D SPP" << endl;
    for (int i=0; i<IP_TRACKER_COUNT; i++)
        trackers[i].lru = i;
}

void CACHE::l1d_prefetcher_operate(uint64_t addr, uint64_t ip, uint8_t cache_hit, uint8_t type, uint8_t critical_ip_flag){
    uint64_t cl_addr = addr >> LOG2_BLOCK_SIZE;
    ip = ip & MASK_IP;

    int index = -1;
    for (index=0; index<IP_TRACKER_COUNT; index++) {
        if (trackers[index].ip == ip)
            break;
    }

    if (index == IP_TRACKER_COUNT) { //if new IP replace LRU tracker
        for (index=0; index<IP_TRACKER_COUNT; index++) {
            if (trackers[index].lru == (IP_TRACKER_COUNT-1))
                break;
            else
                trackers[index].lru++; //update LRU of all other trackers
        }

        trackers[index].ip = ip;
        trackers[index].last_cl_addr = cl_addr;
        memset(trackers[index].stride_history, 0, sizeof(uint64_t)*HISTORY_LENGTH);
        //trackers[index].last_stride = 0;
        
        trackers[index].lru = 0; //reset LRU of replaced tracker

        return; //metadata_in;
    }

	// sanity check
    // at this point we should know a matching tracker index
    if (index == -1)
        assert(0);
    
    switch (trackers[index].state) {
        case UNIFORM:
            break;
        case NON_UNIFORM:
            break;
    }

}


void CACHE::l1d_prefetcher_cache_fill(uint64_t v_addr, uint64_t addr, uint32_t set, uint32_t way, uint8_t prefetch, uint64_t v_evicted_addr, uint64_t evicted_addr, uint32_t metadata_in)
{


}

void CACHE::l1d_prefetcher_final_stats()
{

}

