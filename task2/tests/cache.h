#pragma once
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <iomanip>
#include <string>
using namespace std;
#define L2C_SET 1024
#define L2C_WAY 8
#define NUM_CPUS 1
#define LOAD 0
#define RFO 1
#define PREFETCH 2
#define WRITEBACK 3
#define LOAD_TRANSLATION 4
#define PREFETCH_TRANSLATION 5
#define TRANSLATION_FROM_L1D 6
#define DP(x)
struct BLOCK { bool valid = true, instruction = false; uint32_t lru = 0; };
struct CACHE {
    uint32_t cpu = 0, NUM_WAY = L2C_WAY;
    string NAME = "test";
    BLOCK block[L2C_SET][L2C_WAY];
    void l2c_initialize_replacement();
    uint32_t l2c_find_victim(uint32_t,uint64_t,uint32_t,const BLOCK*,uint64_t,uint64_t,uint32_t);
    void l2c_update_replacement_state(uint32_t,uint32_t,uint32_t,uint64_t,uint64_t,uint64_t,uint32_t,uint8_t,uint8_t);
    void l2c_replacement_final_stats();
    void base_initialize_replacement();
    uint32_t base_find_victim(uint32_t,uint64_t,uint32_t,const BLOCK*,uint64_t,uint64_t,uint32_t);
    void base_update_replacement_state(uint32_t,uint32_t,uint32_t,uint64_t,uint64_t,uint64_t,uint32_t,uint8_t,uint8_t);
    void base_replacement_final_stats();
    uint32_t lru_victim(uint32_t,uint64_t,uint32_t,const BLOCK*,uint64_t,uint64_t,uint32_t);
    void lru_update(uint32_t,uint32_t);
};
