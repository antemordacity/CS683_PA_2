#include "cache.h"
#include <iostream>
#include <unordered_set>

class PrefetchAccuracyTracker {
public:
    void on_fill(uint64_t v_addr, bool is_prefetch, uint64_t v_evicted_addr)
    {
        const uint64_t evicted_line = v_evicted_addr >> LOG2_BLOCK_SIZE;

        if (v_evicted_addr != 0 && prefetched_lines.erase(evicted_line) != 0) {
            ++useless;
        }

        if (is_prefetch) {
            prefetched_lines.insert(v_addr >> LOG2_BLOCK_SIZE);
            ++fills;
        }
    }

    void on_demand_hit(uint64_t addr)
    {
        const uint64_t line = addr >> LOG2_BLOCK_SIZE;

        if (prefetched_lines.erase(line) != 0) {
            ++useful;
        }
    }

    void print() const
    {
        const uint64_t resolved = useful + useless;
        const double accuracy = resolved == 0
            ? 0.0
            : 100.0 * useful / resolved;

        std::cout << "Prefetch fills: " << fills
                  << " useful: " << useful
                  << " useless: " << useless
                  << " resolved accuracy: " << accuracy << "%\n";
    }

private:
    std::unordered_set<uint64_t> prefetched_lines;
    uint64_t fills = 0;
    uint64_t useful = 0;
    uint64_t useless = 0;
};

static PrefetchAccuracyTracker accuracy_tracker;

#define IP_TRACKER_COUNT 24
#define PREFETCH_DEGREE 3
#define MASK_IP 0xFF
#define UNI_THRESHOLD 2
#define DUMMY_PREFETCH 1000 //garbage value
#define HISTORY_LENGTH 4
#define SPP_TABLE_SIZE 32
#define NON_UNI_PREFETCH_THRESH 2
#define CONFIDENCE_COUNTER_MAX 6

void updateCounter(uint8_t &counter, bool increment) {
    if (increment) {
        if (counter < CONFIDENCE_COUNTER_MAX) counter++;
    } else {
        if (counter > 0) counter--;
    }
}

class switcher {
    public : 
    uint8_t counter;
    int predictedStride;
    bool uniformMode;

    switcher(){
        counter = UNI_THRESHOLD+1;
        uniformMode = true;
        predictedStride = DUMMY_PREFETCH;
    }

    void updateSwitcher(int stride){
        if(predictedStride != DUMMY_PREFETCH){
            updateCounter(counter , stride == predictedStride); 
        }

        if(counter >= UNI_THRESHOLD) uniformMode = true;
        else uniformMode = false;
    }

    void updatePrediction(int pred){
        predictedStride = pred == 0 ? DUMMY_PREFETCH : pred;
    }
};

class SPPTable{
    public:
    int predStrides[SPP_TABLE_SIZE];
    uint8_t confidenceCounter[SPP_TABLE_SIZE];

    SPPTable(){
        for(int i = 0 ; i < SPP_TABLE_SIZE ; i++){
            confidenceCounter[i] = 0;
            predStrides[i] = 0;
        }
    }

    int hash(const int history[HISTORY_LENGTH]){
        unsigned int h = 0;

        if(history[HISTORY_LENGTH-1] == DUMMY_PREFETCH)
            return SPP_TABLE_SIZE;

        for (int i = 0; i < HISTORY_LENGTH; i++) {
            h = h * 31 + (history[i] + 31);
        }

        h ^= h >> 16;
        h *= 0x45d9f3b;
        h ^= h >> 16;

        return h % SPP_TABLE_SIZE;
    }

    void updateSPPTable(int observedStride, const int history[HISTORY_LENGTH]) {
        int idx = hash(history);
        if(idx == SPP_TABLE_SIZE)
            return;
        if (observedStride != predStrides[idx] && confidenceCounter[idx] == 0){
            predStrides[idx] = observedStride;
            return;
        }

        updateCounter(confidenceCounter[idx], observedStride == predStrides[idx]);
    }

    
};


class IPTracker{
    public:
    uint64_t ip;
    uint64_t lastCacheLine;
    switcher mode;
    int strideHistory[HISTORY_LENGTH];
    int predictedStrides[PREFETCH_DEGREE];
    int lru;
    int time;
    int uniformStride;
    
    IPTracker(){
        ip = 0;
        lastCacheLine = 0;
        mode = switcher();
        for(int i = 0 ; i < HISTORY_LENGTH ; i++){
            strideHistory[i] = DUMMY_PREFETCH;
        }
        for(int i = 0 ; i < PREFETCH_DEGREE ; i++){
            predictedStrides[i] = 0;
        }
        lru = 0;
        time = 0;
        uniformStride = DUMMY_PREFETCH;
    }

    void updateLRU(){
        for(int i = 0; i <IP_TRACKER_COUNT; i++){
            if(ipTrackers[i].lru < lru)
                ipTrackers[i].lru++;
        }
        lru = 0;
    }


    void reset(uint64_t ipNew, uint64_t cacheLineAddress, int lruValue){
        ip = ipNew;
        lastCacheLine = cacheLineAddress;
        mode = switcher();
        for(int i = 0 ; i < HISTORY_LENGTH ; i++){
            strideHistory[i] = DUMMY_PREFETCH;
        }
        for(int i = 0 ; i < PREFETCH_DEGREE ; i++){
            predictedStrides[i] = 0;
        }
        lru = lruValue;
        time = 0;
        uniformStride = DUMMY_PREFETCH;
    }

    void updateHistory(int stride){
        for(int i = HISTORY_LENGTH - 1 ; i > 0 ; i -- ){
            strideHistory[i] = strideHistory[i-1];
        }
        strideHistory[0] = stride;
    }
};

IPTracker ipTrackers[IP_TRACKER_COUNT];
SPPTable spptable;

void updateHistory(int stride , int* strideHistory){
    for(int i = HISTORY_LENGTH - 1 ; i > 0 ; i -- ){
        strideHistory[i] = strideHistory[i-1];
    }
    strideHistory[0] = stride;
}

bool calculateStride(uint64_t newCacheLine, uint64_t oldCacheLine, int& stride) {
    if (newCacheLine >= oldCacheLine) {
        uint64_t delta = newCacheLine - oldCacheLine;
        if (delta > 63)
            return false;
        stride = static_cast<int>(delta);
    } else {
        uint64_t delta = oldCacheLine - newCacheLine;
        if (delta > 63)
            return false;
        stride = -static_cast<int>(delta);
    }
    return true;
}



void CACHE::l1d_prefetcher_initialize() 
{
    //initialize lru
    for(int i = 0; i < IP_TRACKER_COUNT; i++)
        ipTrackers[i].lru = i;
    //initialize degree
}

void CACHE::l1d_prefetcher_operate(uint64_t addr, uint64_t ip, uint8_t cache_hit, uint8_t type, uint8_t critical_ip_flag)
{
    if (cache_hit)
        accuracy_tracker.on_demand_hit(addr);

    uint64_t cacheLineAddress = addr >> LOG2_BLOCK_SIZE;
    bool entryFound = false;
    int index = 0;

    for(int i = 0 ; i < IP_TRACKER_COUNT ; i++){
        if(ipTrackers[i].ip == ip){
            entryFound = true;
            index = i;
            break;
        }
    }
  
    if(!entryFound){
        for(int i = 0 ; i < IP_TRACKER_COUNT ; i ++ ){
            if(ipTrackers[i].lru == IP_TRACKER_COUNT - 1){
                ipTrackers[i].reset(ip,cacheLineAddress,0);
            }
            else{
                ipTrackers[i].lru++;
            }
        }
        return;
    }
    
    ipTrackers[index].updateLRU();

    int stride;
    // ignore stride if we are crossing a page boundary
    ipTrackers[index].lastCacheLine = cacheLineAddress;
    if (!calculateStride(cacheLineAddress, ipTrackers[index].lastCacheLine, stride)) {
        return;
    }

    // one phase that updates previous tracker
    bool uniformMode = ipTrackers[index].mode.uniformMode;
    if(!uniformMode){
        spptable.updateSPPTable(stride,ipTrackers[index].strideHistory);
    }
    //state transition + confidence update
    ipTrackers[index].mode.updateSwitcher(stride);
    if(ipTrackers[index].mode.uniformMode != uniformMode) ipTrackers[index].uniformStride = DUMMY_PREFETCH;
    ipTrackers[index].updateHistory(stride);
    
    if(!ipTrackers[index].mode.uniformMode){
        int history[HISTORY_LENGTH];
        for(int i = 0 ; i < HISTORY_LENGTH ; i++){
            history[i] = ipTrackers[index].strideHistory[i];
        }
        int i = 0;
        for( ; i < PREFETCH_DEGREE ; i ++ ){
            int table_index = spptable.hash(history);
            if(table_index == SPP_TABLE_SIZE)
                break;
            int predStride = spptable.predStrides[table_index];
            int conf = spptable.confidenceCounter[table_index];
            if(conf >= NON_UNI_PREFETCH_THRESH){ 
                updateHistory(predStride,history);
                ipTrackers[index].predictedStrides[i] = predStride;
            }
            else{
                break;
            }
        }
        for( ; i < PREFETCH_DEGREE ; i ++ ){
            ipTrackers[index].predictedStrides[i] = 0;
        }
    }
    else{
        if(ipTrackers[index].uniformStride == DUMMY_PREFETCH && stride != 0){
            ipTrackers[index].uniformStride = stride;
            for(int i = 0 ; i < PREFETCH_DEGREE ; i ++ ){
                ipTrackers[index].predictedStrides[i] = ipTrackers[index].uniformStride;
            }
        }
    }
    ipTrackers[index].mode.updatePrediction(ipTrackers[index].predictedStrides[0]);
    stride = 0;
    //prefetching
    for (int i=0; i<PREFETCH_DEGREE; i++) {
        if(ipTrackers[index].predictedStrides[i] == 0)
            continue;
        stride+=ipTrackers[index].predictedStrides[i];
        uint64_t pf_address = (cacheLineAddress + stride) << LOG2_BLOCK_SIZE;

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

void CACHE::l1d_prefetcher_cache_fill(uint64_t v_addr, uint64_t addr, uint32_t set, uint32_t way, uint8_t prefetch, uint64_t v_evicted_addr, uint64_t evicted_addr, uint32_t metadata_in)
{
    accuracy_tracker.on_fill(v_addr, prefetch != 0, v_evicted_addr);
}

void CACHE::l1d_prefetcher_final_stats()
{
    accuracy_tracker.print();
}
