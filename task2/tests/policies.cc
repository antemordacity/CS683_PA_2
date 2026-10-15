#include "cache.h"
#if TEST_POLICY == 0
#include "../../replacement/base_replacement.cc"
#include "../../replacement/lru.l2c_repl"
#elif TEST_POLICY == 1
#include "../../replacement/rrip.l2c_repl"
#elif TEST_POLICY == 2
#include "../../replacement/irrip.l2c_repl"
#else
#include "../../replacement/dyn_irrip.l2c_repl"
#endif
CACHE cache;
void update(int set, int way, bool hit, bool instr, int type=LOAD) {
    cache.l2c_update_replacement_state(0,set,way,0,0,0,type,hit,instr);
}
int victim(int set) { return cache.l2c_find_victim(0,0,set,cache.block[set],0,0,LOAD); }
int main() {
    cache.l2c_initialize_replacement();
#ifdef EQUIVALENCE_MODE
    // Feed the actual static and dynamic implementations the same event stream.
    // Pin the follower decision here to isolate all three policy operations.
#if TEST_POLICY == 3
    dyn[0].use_irrip = EQUIVALENCE_MODE;
#endif
    uint64_t digest = 1469598103934665603ULL;
    uint32_t rng = 917;
    for (int i=0; i<10000; ++i) {
        rng = rng*1664525u+1013904223u;
        bool hit = (rng&8), instruction = (rng&16);
        int way = hit ? rng%L2C_WAY : victim(0);
        update(0,way,hit,instruction);
        if (!hit) cache.block[0][way].instruction = instruction;
        digest = (digest ^ way)*1099511628211ULL;
        for(int w=0;w<L2C_WAY;++w) {
#if TEST_POLICY == 3
            digest = (digest ^ dyn[0].rrpv[0][w])*1099511628211ULL;
#else
            digest = (digest ^ l2_rrpv[0][w])*1099511628211ULL;
#endif
        }
    }
    cout << "DIGEST " << digest << endl;
    return 0;
#endif
    const int f=0, l=16;
    for(int s=0;s<L2C_SET;++s) for(int w=0;w<L2C_WAY;++w) cache.block[s][w].lru=w;
#if TEST_POLICY == 0
    assert(victim(f)==7);
    update(f,7,true,false); assert(cache.block[f][7].lru==0); assert(victim(f)==6);
    update(f,6,true,false,WRITEBACK); assert(victim(f)==6);
    update(f,6,false,false); assert(cache.block[f][6].lru==0);
#elif TEST_POLICY <= 2
    update(f,0,false,true);
#if TEST_POLICY == 1
    assert(l2_rrpv[f][0]==2);
#else
    assert(l2_rrpv[f][0]==0);
#endif
    update(f,1,false,false); assert(l2_rrpv[f][1]==2);
    update(f,1,true,false);
#if TEST_POLICY == 2 && IRRIP_VERSION >= 2
    assert(l2_rrpv[f][1]==1);
#else
    assert(l2_rrpv[f][1]==0);
#endif
    update(f,1,true,false); update(f,1,true,false); assert(l2_rrpv[f][1]==0);
    for(int w=0;w<L2C_WAY;++w) l2_rrpv[f][w]=0;
    cache.block[f][0].instruction=true;
#if TEST_POLICY == 2 && IRRIP_VERSION == 3
    assert(victim(f)==1);
#else
    assert(victim(f)==0);
#endif
    for(int w=0;w<L2C_WAY;++w) { assert(l2_rrpv[f][w]==3); cache.block[f][w].instruction=true; }
    assert(victim(f)==0);
#else
    auto& s=dyn[0];
    int count=0; for(int set=0;set<L2C_SET;++set) count+=leader(set);
    assert(count==32 && leader(16) && leader(1008) && !leader(0));
    assert(metric(s)==0 && !s.use_irrip);
    update(f,0,false,true); assert(s.rrpv[f][0]==2); // empty: RRIP
    for(int i=0;i<20;++i) victim(l);
    assert(s.ia==0 && s.da==0); // retries cannot count accesses
    update(l,0,false,true);
    assert(s.ia==1 && s.im==1 && s.da==0 && s.dm==0 && s.use_irrip);
    assert(s.rrpv[l][0]==2); // RRIP-only leader insertion
    update(l,1,false,false); update(l,1,true,false);
    assert(s.rrpv[l][1]==0); // RRIP-only leader promotion
    update(f,0,false,true); assert(s.rrpv[f][0]==0);
    update(f,1,false,false); update(f,1,true,false); assert(s.rrpv[f][1]==1);
    update(f,1,true,true); assert(s.rrpv[f][1]==0);
    for(int w=0;w<L2C_WAY;++w) { s.rrpv[f][w]=3; s.rrpv[l][w]=3; }
    cache.block[f][0].instruction=cache.block[l][0].instruction=true;
    assert(victim(f)==1); assert(victim(l)==0); // distinct eviction rules
    for(int i=0;i<20;++i) update(l,0,true,false);
    assert(s.ia==1 && s.im==1 && s.da==22 && s.dm==1 && !s.use_irrip);
    assert(s.switches==2 && s.leader_updates==23);
    update(f,0,false,true); assert(s.rrpv[f][0]==2);
    update(f,0,true,false); assert(s.rrpv[f][0]==0);
    // Boundary: metric=1/4 exactly; equality selects I-RRIP.
    s.ia=1; s.im=0; s.da=2; s.dm=0;
    update(l,0,true,false); assert(metric(s)==0.25 && s.use_irrip);
    for(int w=0;w<L2C_WAY;++w) s.rrpv[f][w]=0;
    assert(victim(f)==1); for(int w=0;w<L2C_WAY;++w) assert(s.rrpv[f][w]==3);
    for(int w=0;w<L2C_WAY;++w) cache.block[f][w].instruction=true;
    assert(victim(f)==0);
    // Reinitialize clears cumulative statistics and decisions.
    cache.l2c_initialize_replacement(); assert(s.ia==0 && s.switches==0 && !s.use_irrip);
    update(l,0,false,true,LOAD_TRANSLATION);
    update(l,0,true,false,WRITEBACK);
    assert(s.ia==1 && s.im==1 && s.da==1 && s.dm==0);
    cache.l2c_initialize_replacement();
#endif
    cache.block[f][5].valid=false;
#if TEST_POLICY == 1 || TEST_POLICY == 2
    l2_rrpv[f][5]=0;
#elif TEST_POLICY == 3
    dyn[0].rrpv[f][5]=0;
#endif
    assert(victim(f)==5); // invalid even when another valid line is evictable
    cache.block[f][5].valid=true;
    // Deterministic stress: bound all metadata and returned victim indices.
    uint32_t random=12345;
    for(int i=0;i<10000;++i) {
        random=random*1664525u+1013904223u;
        int set=(random>>16)%L2C_SET, way=random%L2C_WAY;
        update(set,way,random&0x100,random&0x200);
        assert(victim(set)<L2C_WAY);
#if TEST_POLICY == 1 || TEST_POLICY == 2
        for(int w=0;w<L2C_WAY;++w) assert(l2_rrpv[set][w]<=3);
#elif TEST_POLICY == 3
        for(int w=0;w<L2C_WAY;++w) assert(dyn[0].rrpv[set][w]<=3);
#endif
    }
    cache.l2c_replacement_final_stats();
    cout << "PASS policy=" << TEST_POLICY << endl;
}
