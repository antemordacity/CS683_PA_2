#include "cache.h"
#include <iostream>
#include <unordered_set>

#define IP_TRACKER_COUNT 24
#define MAX_PREFETCH_DEGREE 5
#define INITIAL_PREFETCH_DEGREE 3
#define ACCURACY_EPOCH_CYCLES 1000
#define ACCURACY_REGIME_1_MAX 20.0
#define ACCURACY_REGIME_2_MAX 40.0
#define ACCURACY_REGIME_3_MAX 60.0
#define ACCURACY_REGIME_4_MAX 80.0
#define ACCURACY_REGIME_1_DEGREE 1
#define ACCURACY_REGIME_2_DEGREE 2
#define ACCURACY_REGIME_3_DEGREE 3
#define ACCURACY_REGIME_4_DEGREE 4
#define ACCURACY_REGIME_5_DEGREE 5
#define MASK_IP 0xFFFF
#define MASK_CACHE_LINE 0xFFFF
#define UNI_THRESHOLD 2
#define DUMMY_PREFETCH 1000 // Invalid-stride sentinel
#define HISTORY_LENGTH 4
#define SPP_TABLE_SIZE 32
#define NON_UNI_PREFETCH_THRESH 1
#define CONFIDENCE_COUNTER_MAX 7

static_assert(ACCURACY_EPOCH_CYCLES > 0, "Accuracy epoch must be nonzero");
static_assert(ACCURACY_REGIME_1_MAX < ACCURACY_REGIME_2_MAX &&
              ACCURACY_REGIME_2_MAX < ACCURACY_REGIME_3_MAX &&
              ACCURACY_REGIME_3_MAX < ACCURACY_REGIME_4_MAX &&
              ACCURACY_REGIME_4_MAX <= 100.0,
              "Accuracy regime bounds must be increasing and at most 100");
static_assert(ACCURACY_REGIME_1_DEGREE >= 0 &&
              ACCURACY_REGIME_1_DEGREE <= MAX_PREFETCH_DEGREE &&
              ACCURACY_REGIME_2_DEGREE >= 0 &&
              ACCURACY_REGIME_2_DEGREE <= MAX_PREFETCH_DEGREE &&
              ACCURACY_REGIME_3_DEGREE >= 0 &&
              ACCURACY_REGIME_3_DEGREE <= MAX_PREFETCH_DEGREE &&
              ACCURACY_REGIME_4_DEGREE >= 0 &&
              ACCURACY_REGIME_4_DEGREE <= MAX_PREFETCH_DEGREE &&
              ACCURACY_REGIME_5_DEGREE >= 0 &&
              ACCURACY_REGIME_5_DEGREE <= MAX_PREFETCH_DEGREE,
              "Each accuracy regime degree must fit the prediction array");

class PrefetchAccuracyTracker {
public:
    void reset(uint64_t cycle)
    {
        epoch_end_cycle = cycle + ACCURACY_EPOCH_CYCLES;
        epoch_useful = 0;
        epoch_useless = 0;
        current_degree = INITIAL_PREFETCH_DEGREE;
    }

    void advance_cycle(uint64_t cycle)
    {
        while (cycle >= epoch_end_cycle) {
            const uint64_t resolved = epoch_useful + epoch_useless;
            if (resolved != 0) {
                const double accuracy = 100.0 * epoch_useful / resolved;
                if (accuracy < ACCURACY_REGIME_1_MAX)
                    current_degree = ACCURACY_REGIME_1_DEGREE;
                else if (accuracy < ACCURACY_REGIME_2_MAX)
                    current_degree = ACCURACY_REGIME_2_DEGREE;
                else if (accuracy < ACCURACY_REGIME_3_MAX)
                    current_degree = ACCURACY_REGIME_3_DEGREE;
                else if (accuracy < ACCURACY_REGIME_4_MAX)
                    current_degree = ACCURACY_REGIME_4_DEGREE;
                else
                    current_degree = ACCURACY_REGIME_5_DEGREE;
            }

            epoch_useful = 0;
            epoch_useless = 0;
            epoch_end_cycle += ACCURACY_EPOCH_CYCLES;
        }
    }

    void on_fill(uint64_t v_addr, bool is_prefetch, uint64_t v_evicted_addr)
    {
        const uint64_t evicted_line = v_evicted_addr >> LOG2_BLOCK_SIZE;

        if (v_evicted_addr != 0 && prefetched_lines.erase(evicted_line) != 0) {
            ++useless;
            ++epoch_useless;
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
            ++epoch_useful;
        }
    }

    int degree() const
    {
        return current_degree;
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
    uint64_t epoch_end_cycle = ACCURACY_EPOCH_CYCLES;
    uint64_t epoch_useful = 0;
    uint64_t epoch_useless = 0;
    int current_degree = INITIAL_PREFETCH_DEGREE;
};

static PrefetchAccuracyTracker accuracy_tracker;

void updateCounter(int &counter, bool increment) {
    if (increment) {
        if (counter < CONFIDENCE_COUNTER_MAX) counter++;
    } else {
        if (counter > 0) counter--;
    }
}

class switcher {
public:
    int counter;
    int predictedStride;
    bool uniformMode;

    switcher()
    {
        counter = UNI_THRESHOLD + 1;
        uniformMode = true;
        predictedStride = DUMMY_PREFETCH;
    }

    void updateSwitcher(int stride)
    {
        if (predictedStride != DUMMY_PREFETCH) {
            const bool predictionMatched = stride == predictedStride;
            updateCounter(counter, uniformMode ? predictionMatched : !predictionMatched);
        }

        uniformMode = counter >= UNI_THRESHOLD;
    }

    void updatePrediction(int pred)
    {
        predictedStride = pred == 0 ? DUMMY_PREFETCH : pred;
    }
};

class SPPTable {
public:
    int predStrides[SPP_TABLE_SIZE];
    int confidenceCounter[SPP_TABLE_SIZE];

    SPPTable()
    {
        for (int i = 0; i < SPP_TABLE_SIZE; i++) {
            confidenceCounter[i] = 0;
            predStrides[i] = 0;
        }
    }

    int hash(const int signature, int time)
    {
        uint32_t h = static_cast<uint32_t>(signature) & 0xFFF;
        if (time < HISTORY_LENGTH)
            return SPP_TABLE_SIZE;

        h ^= h >> 16;
        h *= 0x45d9f3bU;
        h ^= h >> 16;

        return static_cast<int>(h % SPP_TABLE_SIZE);
    }

    void updateSPPTable(int observedStride, const int signature, int time)
    {
        const int idx = hash(signature, time);
        if (idx == SPP_TABLE_SIZE)
            return;

        if (observedStride != predStrides[idx] && confidenceCounter[idx] == 0) {
            predStrides[idx] = observedStride;
            return;
        }

        updateCounter(confidenceCounter[idx], observedStride == predStrides[idx]);
    }
};

class IPTracker {
public:
    uint16_t ip;
    uint16_t lastCacheLine;
    switcher mode;
    int64_t signature;
    int predictedStrides[MAX_PREFETCH_DEGREE];
    int lru;
    int time;
    int uniformStride;

    IPTracker()
    {
        ip = 0;
        lastCacheLine = 0;
        mode = switcher();
        signature = 0;
        for (int i = 0; i < MAX_PREFETCH_DEGREE; i++)
            predictedStrides[i] = 0;
        lru = 0;
        time = 0;
        uniformStride = DUMMY_PREFETCH;
    }

    void updateLRU();

    void reset(uint16_t ipNew, uint16_t cacheLineAddress, int lruValue)
    {
        ip = ipNew;
        lastCacheLine = cacheLineAddress;
        mode = switcher();
        signature = 0;
        for (int i = 0; i < MAX_PREFETCH_DEGREE; i++)
            predictedStrides[i] = 0;
        lru = lruValue;
        time = 0;
        uniformStride = DUMMY_PREFETCH;
    }

    void updateHistory(int stride)
    {
        stride = stride & 0x7F;
        signature = (signature << 3) ^ stride;
    }
};

IPTracker ipTrackers[IP_TRACKER_COUNT];
SPPTable spptable;

void IPTracker::updateLRU()
{
    for (int i = 0; i < IP_TRACKER_COUNT; i++) {
        if (ipTrackers[i].lru < lru)
            ipTrackers[i].lru++;
    }
    lru = 0;
}

int64_t updateHistory(int stride, int signature)
{
    signature = (signature << 3) ^ stride;
    return signature;
}

int calculateStride(uint16_t newCacheLine, uint16_t oldCacheLine)
{
    const uint16_t wrapped_delta = static_cast<uint16_t>(newCacheLine - oldCacheLine);
    return wrapped_delta < 0x8000
        ? static_cast<int>(wrapped_delta)
        : static_cast<int>(wrapped_delta) - 0x10000;
}

void CACHE::l1d_prefetcher_initialize()
{
    accuracy_tracker.reset(current_core_cycle[cpu]);
    for (int i = 0; i < IP_TRACKER_COUNT; i++)
        ipTrackers[i].lru = i;
}

void CACHE::l1d_prefetcher_operate(uint64_t addr, uint64_t ip, uint8_t cache_hit, uint8_t type, uint8_t critical_ip_flag)
{
    accuracy_tracker.advance_cycle(current_core_cycle[cpu]);
    if (cache_hit)
        accuracy_tracker.on_demand_hit(addr);

    const uint64_t cacheLineAddress = addr >> LOG2_BLOCK_SIZE;
    const uint16_t maskedIp = static_cast<uint16_t>(ip & MASK_IP);
    const uint16_t maskedCacheLine =
        static_cast<uint16_t>(cacheLineAddress & MASK_CACHE_LINE);
    bool entryFound = false;
    int index = 0;
    for (int i = 0; i < IP_TRACKER_COUNT; i++) {
        if (ipTrackers[i].ip == maskedIp) {
            entryFound = true;
            index = i;
            break;
        }
    }

    if (!entryFound) {
        for (int i = 0; i < IP_TRACKER_COUNT; i++) {
            if (ipTrackers[i].lru == IP_TRACKER_COUNT - 1)
                ipTrackers[i].reset(maskedIp, maskedCacheLine, 0);
            else
                ipTrackers[i].lru++;
        }
        return;
    }

    ipTrackers[index].updateLRU();
    int stride = 0;
    stride = calculateStride(maskedCacheLine, ipTrackers[index].lastCacheLine);
    ipTrackers[index].lastCacheLine = maskedCacheLine;

    if (stride > 63 || stride < -63 || stride == 0)
        return;

    ipTrackers[index].time++;
    const bool uniformMode = ipTrackers[index].mode.uniformMode;
    if (!uniformMode)
        spptable.updateSPPTable(stride, ipTrackers[index].signature, ipTrackers[index].time);

    ipTrackers[index].mode.updateSwitcher(stride);
    if (uniformMode && !ipTrackers[index].mode.uniformMode)
        ipTrackers[index].uniformStride = DUMMY_PREFETCH;
    ipTrackers[index].updateHistory(stride);

    if (!ipTrackers[index].mode.uniformMode) {
        int sig = ipTrackers[index].signature;
        int i = 0;
        for (; i < MAX_PREFETCH_DEGREE; i++) {
            const int table_index = spptable.hash(sig, ipTrackers[index].time);
            if (table_index == SPP_TABLE_SIZE)
                break;

            const int predStride = spptable.predStrides[table_index];
            const int conf = spptable.confidenceCounter[table_index];
            if (conf >= NON_UNI_PREFETCH_THRESH) {
                sig = static_cast<int>(updateHistory(predStride, sig));
                ipTrackers[index].predictedStrides[i] = predStride;
            } else {
                break;
            }
        }
        for (; i < MAX_PREFETCH_DEGREE; i++)
            ipTrackers[index].predictedStrides[i] = 0;
    } else if (ipTrackers[index].uniformStride == DUMMY_PREFETCH) {
        ipTrackers[index].uniformStride = stride;
        for (int i = 0; i < MAX_PREFETCH_DEGREE; i++)
            ipTrackers[index].predictedStrides[i] = ipTrackers[index].uniformStride;
    }

    ipTrackers[index].mode.updatePrediction(ipTrackers[index].predictedStrides[0]);
    stride = 0;
    for (int i = 0; i < accuracy_tracker.degree(); i++) {
        if (ipTrackers[index].predictedStrides[i] == 0)
            continue;

        stride += ipTrackers[index].predictedStrides[i];
        const uint64_t pf_address = (cacheLineAddress + stride) << LOG2_BLOCK_SIZE;
        if ((pf_address >> LOG2_PAGE_SIZE) != (addr >> LOG2_PAGE_SIZE))
            break;

        if (MSHR.occupancy < (MSHR.SIZE >> 1))
            prefetch_line(ip, addr, pf_address, FILL_L1, 0);
        else
            prefetch_line(ip, addr, pf_address, FILL_L2, 0);
    }
}

void CACHE::l1d_prefetcher_cache_fill(uint64_t v_addr, uint64_t addr, uint32_t set, uint32_t way, uint8_t prefetch, uint64_t v_evicted_addr, uint64_t evicted_addr, uint32_t metadata_in)
{
    accuracy_tracker.advance_cycle(current_core_cycle[cpu]);
    accuracy_tracker.on_fill(v_addr, prefetch != 0, v_evicted_addr);
}

void CACHE::l1d_prefetcher_final_stats()
{
    accuracy_tracker.print();
}
