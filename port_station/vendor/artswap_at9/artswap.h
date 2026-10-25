/* Port Station host-only buffer adapter. GPL-3.0-or-later. */
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
typedef struct { uint8_t *data; size_t len, cap; } buf_t;
bool buf_reserve(buf_t *buffer, size_t capacity);
