/* A retained byte pool in MIDI lock fields 30/31 of the current-bank
 * CS1 mirror. Never put pool bytes in native DRAM or project files.
 * Native copies preserve the pool on write and synthesize unlocked (255)
 * on read. Direct MIDI clear/paste loops are bounded to 30 in manifest.py.
 */
typedef unsigned char u8;
typedef unsigned int u32;
#define BASE 0x1001614eu
#define PATTERN 0x8ed8u
#define END (BASE + 16u * PATTERN)
#define TRACK 0x8b0u
#define CAPACITY 16384u

static volatile u8 *address(u32 index)
{
    return (volatile u8 *)(BASE + (index / 1024u) * PATTERN + 0x4900u
        + ((index % 1024u) / 128u) * TRACK + ((index % 128u) / 2u) * 32u
        + 30u + (index & 1u));
}

int rp_write(const u8 *src, u32 offset, u32 length)
{
    if (offset > CAPACITY || length > CAPACITY - offset) return 0;
    while (length--) *address(offset++) = *src++;
    return 1;
}

int rp_read(u8 *dst, u32 offset, u32 length)
{
    if (offset > CAPACITY || length > CAPACITY - offset) return 0;
    while (length--) *dst++ = *address(offset++);
    return 1;
}

/* Length to the next pool/non-pool boundary. No per-byte division. */
static u32 span(u32 at, u32 limit, int *pool)
{
    u32 p, t, slot, n;
    *pool = 0;
    if (at >= END) return limit;
    if (at < BASE) { n = BASE - at; return n < limit ? n : limit; }
    p = (at - BASE) % PATTERN;
    if (p < 0x4900u) n = 0x4900u - p;
    else if (p >= 0x48d0u + 8u * TRACK) n = PATTERN - p;
    else {
        t = (p - 0x48d0u) % TRACK;
        if (t < 0x30u) n = 0x30u - t;
        else if (t >= 0x830u) n = TRACK - t;
        else {
            slot = (t - 0x30u) % 32u;
            *pool = slot >= 30u;
            n = (*pool ? 32u : 30u) - slot;
        }
    }
    return n < limit ? n : limit;
}

/* Native callers use forward memcpy; protect each source/destination span. */
void *rp_native_copy(void *dest, const void *source, u32 length)
{
    volatile u8 *dst = dest;
    const volatile u8 *src = source;
    while (length) {
        int dp, sp;
        u32 n = span((u32)dst, length, &dp);
        u32 s = span((u32)src, n, &sp);
        n = s;
        length -= n;
        if (dp) { dst += n; src += n; }
        else if (sp) { while (n--) { *dst++ = 255; ++src; } }
        else {
            while (n && (((u32)dst | (u32)src) & 3u)) {
                *dst++ = *src++; --n;
            }
            while (n >= 4u) {
                *(volatile u32 *)dst = *(const volatile u32 *)src;
                dst += 4; src += 4; n -= 4;
            }
            while (n--) *dst++ = *src++;
        }
    }
    return dest;
}
