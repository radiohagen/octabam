/* Fixed-size Harmony. No allocation, native writes or persisted history.
 * NAT stays in voicing.s. See README.md for the musical selection contract. */
#include "size.h"

static void sort(int *p, unsigned n) {
    for (unsigned i=1; i<n; ++i) {
        int v=p[i]; unsigned j=i;
        while (j && p[j-1]>v) { p[j]=p[j-1]; --j; }
        p[j]=v;
    }
}
static unsigned contains(const int *p, unsigned n, int value) {
    for (unsigned i=0; i<n; ++i) if (p[i]==value) return 1;
    return 0;
}
static unsigned select_tones(const uint8_t *raw, unsigned quality,
                             unsigned size, unsigned root_mode, int *base) {
    unsigned available=(quality==1 || quality==2 || quality==7)?4:3;
    unsigned altered=raw[2]>raw[0] && (raw[2]-raw[0])%12!=7;
    unsigned colour=available==4?3:(quality==3 || quality==4)?1:altered?2:1;
    unsigned priority[5]={0,colour,altered?2:1,1,2};
    unsigned n=0, used=0;
    for (unsigned i=0; i<5 && n<size; ++i) {
        unsigned k=priority[i];
        if ((root_mode==1 && k==0) || (used&(1u<<k))) continue;
        used|=1u<<k;
        /* The generator pads unavailable upper tones with the root. */
        if (raw[k]>127 || (k && raw[k]<=raw[0])) continue;
        base[n++]=raw[k];
    }
    sort(base,n);
    return n;
}

/* Invert the distinct retained tones, then double upwards. Inversion zero
 * keeps an ADD9's written ninth. Other inversions compact around their bass,
 * matching manual NAT inversions. Doublings never create new inversions. */
static unsigned candidate(const int *base, unsigned n, unsigned target,
                          unsigned inversion, int offset, unsigned spread,
                          unsigned root_mode, int root, int *out) {
    if (!n) return 0;
    if (inversion>=n) inversion=n-1;
    int bass=base[inversion]+offset;
    for (unsigned i=0; i<n; ++i) {
        int v=base[i]+offset;
        if (inversion) {
            while (v<bass) v+=12;
            while (v>=bass+12) v-=12;
        }
        if (v<0 || v>127) return 0;
        out[i]=v;
    }
    sort(out,n);
    unsigned count=n, fill=target;
    /* Place the actual bass before choosing doublings. A dropped root may
     * be doubled above it; there is still only one voice in the bass octave. */
    if (root_mode>=2) {
        unsigned kept=0;
        for (unsigned i=0; i<count; ++i)
            if ((out[i]-root)%12) out[kept++]=out[i];
        int low=root-12*(int)(root_mode-1);
        if (low>=0) out[kept++]=low;
        else --fill; /* Do not hide a missing required bass with another tone. */
        count=kept;
        sort(out,count);
    }
    unsigned originals=count;
    while (count<fill) {
        int next=128;
        for (unsigned i=0; i<originals; ++i) {
            int v=out[i]+12;
            while (contains(out,count,v)) v+=12;
            if (v<next) next=v;
        }
        if (next>127) break;
        out[count++]=next;
    }
    sort(out,count);
    int spaced[4];
    for (unsigned i=0; i<count; ++i) spaced[i]=out[i];
    if (spread==1 && count>1) {
        spaced[1]+=12;
        /* A doubled tone may already occupy the usual OPEN destination. */
        for (;;) {
            unsigned collision=0;
            for (unsigned i=0; i<count; ++i)
                if (i!=1 && spaced[i]==spaced[1]) collision=1;
            if (!collision) break;
            spaced[1]+=12;
        }
    } else if (spread==2) {
        for (unsigned i=1; i<count; ++i) spaced[i]+=12;
    }
    unsigned fits=1;
    for (unsigned i=0; i<count; ++i) if (spaced[i]>127) fits=0;
    if (fits) for (unsigned i=0; i<count; ++i) out[i]=spaced[i];
    /* Overflow keeps CLOSE. */
    sort(out,count);
    return count;
}

/* AUTO clarity guard, before movement scoring. These register thresholds are
 * our conservative realization of wide bass / closer treble spacing, not a
 * rule of jazz theory: a fifth above a low bass, fourths between other voices
 * below MIDI 48, and thirds below MIDI 60. Manual VOIC
 * remains literal. The anchored ROOT never moves to repair another voice. */
static unsigned clarify(int *out, unsigned n, int anchor, int ninth) {
    if (n>1 && ninth>=0 && out[0]%12==ninth) return 0;
    for (unsigned pass=0; pass<12; ++pass) {
        unsigned i;
        for (i=1; i<n; ++i) {
            int gap=out[i-1]<48?(i==1?7:5):out[i-1]<60?3:1;
            if (out[i]-out[i-1]<gap) break;
        }
        if (i==n) return 1;
        if (out[i]==anchor) return 0;
        int v=out[i]+12;
        while (contains(out,n,v)) v+=12;
        if (v>127) return 0;
        out[i]=v;
        sort(out,n);
    }
    return 0;
}

void mh_size_voice_c(uint8_t pool[4], uint8_t history[8], unsigned config,
                     unsigned quality, unsigned source_scale) {
    unsigned size=(config>>7)&3, voic=config&7;
    unsigned spread=(config>>3)&3, root_mode=(config>>5)&3;
    if (!size || size>3) return;
    unsigned target=size+1;
    unsigned token=0x800000u | config | ((source_scale&0x1fffu)<<9);
    unsigned old=((unsigned)history[5]<<16)|((unsigned)history[6]<<8)|history[7];
    int root=pool[0], base[4], best[4], trial[4];
    unsigned n=select_tones(pool,quality,target,root_mode,base);
    unsigned inversion=voic>=2?voic-1:0;
    unsigned count=candidate(base,n,target,inversion,0,spread,root_mode,root,best);
    if (!count) count=candidate(base,n,target,0,0,spread,root_mode,root,best);
    int anchor=root_mode>=2?root-12*(int)(root_mode-1):root;
    int ninth=quality==2 && pool[3]<128 && pool[3]>root?pool[3]%12:-1;
    if (voic==1 && count) clarify(best,count,root_mode==1?-1:anchor,ninth);
    if (voic==1 && old==token && n) {
        int shift=(root-(int)history[4])/12*12;
        int best_cost=0x7fffffff;
        /* Ordered ties: root position, then ascending inversion; 0,-12,+12.
         * At most 12 candidates. Score actual sounding voices after ROOT. */
        for (unsigned inv=0; inv<n; ++inv) for (unsigned oct=0; oct<3; ++oct) {
            int offset=oct==0?0:oct==1?-12:12;
            unsigned got=candidate(base,n,target,inv,offset,spread,root_mode,root,trial);
            if (got!=target) continue;
            if (!clarify(trial,got,root_mode==1?-1:anchor,ninth)) continue;
            int distance=trial[0]-anchor;
            if (distance < -12 || distance > 12) continue;
            if (root_mode!=1 && !contains(trial,got,anchor)) continue;
            int cost=0;
            for (unsigned i=0; i<got; ++i) {
                int d=trial[i]-(int)history[i]-shift;
                cost+=8*(d<0?-d:d)+(d!=0);
            }
            if (cost<best_cost) {
                best_cost=cost; count=got;
                for (unsigned i=0; i<got; ++i) best[i]=trial[i];
            }
        }
    }
    for (unsigned i=0; i<4; ++i) pool[i]=i<count?(uint8_t)best[i]:255;
    for (unsigned i=0; i<4; ++i) history[i]=pool[i];
    if (count!=target || voic!=1) token=0;
    history[4]=(uint8_t)root;
    history[5]=(uint8_t)(token>>16);
    history[6]=(uint8_t)(token>>8);
    history[7]=(uint8_t)token;
}
