#define sha256_init pa_sha256_init
#define sha256_update pa_sha256_update
#define sha256_final pa_sha256_final
#define sha256_transform pa_sha256_transform
#define SHA256_CTX PA_SHA256_CTX
/*********************************************************************
* Filename:   sha256.h
* Author:     Brad Conte (brad AT bradconte.com)
* Copyright:
* Disclaimer: This code is presented "as is" without any guarantees.
* Details:    Defines the API for the corresponding SHA1 implementation.
*********************************************************************/

#ifndef SHA256_H
#define SHA256_H

/*************************** HEADER FILES ***************************/
#include <stddef.h>

/****************************** MACROS ******************************/
#define SHA256_BLOCK_SIZE 32            // SHA256 outputs a 32 byte digest

/**************************** DATA TYPES ****************************/
typedef unsigned char PA_SHA256_BYTE;             // 8-bit byte
typedef unsigned int  PA_SHA256_WORD;             // 32-bit word, change to "long" for 16-bit machines

typedef struct {
	PA_SHA256_BYTE data[64];
	PA_SHA256_WORD datalen;
	unsigned long long bitlen;
	PA_SHA256_WORD state[8];
} SHA256_CTX;

/*********************** FUNCTION DECLARATIONS **********************/
void sha256_init(SHA256_CTX *ctx);
void sha256_update(SHA256_CTX *ctx, const PA_SHA256_BYTE data[], size_t len);
void sha256_final(SHA256_CTX *ctx, PA_SHA256_BYTE hash[]);

#endif   // SHA256_H
