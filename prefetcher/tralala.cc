#include "cache.h"
#include <unordered_set>

#define IP_TRACKER_COUNT 24
#define PREFETCH_DEGREE 3
#define MASK_IP 0xFF

class accuracyTracker{
    int hits, misses; 
    int predictedStride;
    bool pageBoundaryIgnore = true;
    uint64_t lastCacheLine;

    accuracyTracker(){
        hits = 0;
        misses = 0;
        lastCacheLine = 0;
    }

    void updateAccuracy(uint64_t currentCacheLine,int stridePrediction){
        int stride = currentCacheLine - lastCacheLine;
        bool boundaryCheck = ((stride < 63) && (stride > -63)) | (!pageBoundaryIgnore);
        if(lastCacheLine != 0 && boundaryCheck){
            if(predictedStride == stride) hits++;
            else misses++;
        }
        lastCacheLine = currentCacheLine;
        predictedStride = stridePrediction;
    }
};


class PrefetchAccuracyTracker {
public:
    void on_fill(uint64_t addr, bool is_prefetch, uint64_t evicted_addr)
    {
        const uint64_t evicted_line = evicted_addr >> LOG2_BLOCK_SIZE;

        // If the evicted line was prefetched but never used, it was useless.
        if (prefetched_lines.erase(evicted_line) != 0)
            ++useless;

        if (is_prefetch) {
            prefetched_lines.insert(addr >> LOG2_BLOCK_SIZE);
            ++fills;
        }
    }

    void on_demand_hit(uint64_t addr)
    {
        const uint64_t line = addr >> LOG2_BLOCK_SIZE;

        // Erase it so one prefetch can only be counted useful once.
        if (prefetched_lines.erase(line) != 0)
            ++useful;
    }

    void print() const
    {
        const uint64_t resolved = useful + useless;
        const double accuracy = resolved == 0
            ? 0.0
            : 100.0 * useful / resolved;

        cout << "Prefetch fills: " << fills
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

void CACHE::l1d_prefetcher_initialize() 
{
}

void CACHE::l1d_prefetcher_operate(uint64_t addr, uint64_t ip, uint8_t cache_hit, uint8_t type, uint8_t critical_ip_flag)
{
    if (cache_hit)  accuracy_tracker.on_demand_hit(addr);

}

void CACHE::l1d_prefetcher_cache_fill(uint64_t v_addr, uint64_t addr, uint32_t set, uint32_t way, uint8_t prefetch, uint64_t v_evicted_addr, uint64_t evicted_addr, uint32_t metadata_in)
{
    accuracy_tracker.on_fill(addr, prefetch != 0, evicted_addr);
}

void CACHE::l1d_prefetcher_final_stats()
{
    accuracy_tracker.print();
}
