// The-Loom solver
// Recurrence: P[n+1] = g(P[n]) ^ P[n-1]
// g(cur)[j] = (cur[j]&cur[j-2]) ^ (cur[j-1]^cur[j+1]) ^ (cur[j-1]&cur[j+1])
//             ^ (cur[j]&cur[j+2]) ^ (cur[j-2]&cur[j+2])   (all mod 256)
// We know P[1000002] = bits(C2), P[1000003] = bits(C1); iterate backward to P[0].
#include <stdio.h>
#include <stdint.h>
#include <string.h>

static const uint8_t C1[32] = {
 0x80,0x96,0xab,0x41,0x0e,0x1e,0x9d,0x3e,0x09,0xec,0xec,0x59,0xba,0x2d,0x5c,0xae,
 0x21,0xa7,0x94,0x64,0x4c,0x57,0xa1,0xc0,0xd2,0x8e,0xee,0x74,0x09,0x9c,0x8c,0x5b};
static const uint8_t C2[32] = {
 0x66,0x2b,0xd9,0x2e,0x71,0x03,0xc8,0x09,0xa6,0xef,0x4e,0x4f,0x80,0x73,0x97,0x2e,
 0x52,0xcb,0xce,0x9f,0xfb,0xd2,0x7f,0x75,0x6c,0x85,0x4d,0x24,0x79,0x4a,0x41,0x6a};

static void expand(const uint8_t in[32], uint8_t out[256]) {
    for (int i = 0; i < 256; i++)
        out[i] = (in[i>>3] >> (i&7)) & 1;
}
static void pack(const uint8_t in[256], uint8_t out[32]) {
    memset(out, 0, 32);
    for (int i = 0; i < 256; i++)
        out[i>>3] |= (uint8_t)((in[i] & 1) << (i&7));
}
static void gfun(const uint8_t B[256], uint8_t out[256]) {
    for (int j = 0; j < 256; j++) {
        uint8_t t = B[j];
        uint8_t p = B[(j-2)&255];
        uint8_t q = B[(j-1)&255];
        uint8_t r = B[(j+1)&255];
        uint8_t s = B[(j+2)&255];
        uint8_t v = (uint8_t)((t&p) ^ (q^r) ^ (q&r) ^ (t&s) ^ (p&s));
        out[j] = v & 1;
    }
}

int main(void) {
    uint8_t nxt[256], cur[256], prev[256];
    expand(C1, nxt);   // P[1000003]
    expand(C2, cur);   // P[1000002]
    for (long k = 0; k < 1000002; k++) {
        gfun(cur, prev);
        for (int j = 0; j < 256; j++) prev[j] ^= nxt[j];
        memcpy(nxt, cur, 256);
        memcpy(cur, prev, 256);
    }
    uint8_t input[32];
    pack(cur, input);
    fwrite(input, 1, 32, stdout);
    fputc('\n', stdout);
    // sanity: forward check
    printf("input = ");
    for (int i = 0; i < 32; i++) printf("%02x", input[i]);
    printf("\n");
    printf("ascii = ");
    for (int i = 0; i < 32; i++) putchar((input[i]>=32&&input[i]<127)?input[i]:'.');
    printf("\n");
    return 0;
}
