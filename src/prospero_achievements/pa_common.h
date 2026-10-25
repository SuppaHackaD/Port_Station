#ifndef PA_COMMON_H
#define PA_COMMON_H
#include <stddef.h>
#include <stdint.h>
#include "vendor/cJSON.h"
#define PA_VERSION "0.1.0"
#define PA_PORT 38765
#define PA_MAX_BODY (512u*1024u)
#define PA_MAX_CATALOG (128u*1024u)
#define PA_MAX_ACH 256
#define PA_MAX_EVENTS 4096
void pa_hash(const void *,size_t,char out[65]);
uint32_t pa_crc(const void *,size_t);
int pa_id(const char *);
int pa_game_id(const char *);
int pa_user(const char *);
int pa_digest(const char *);
int pa_mkdirs(const char *);
int pa_atomic(const char *,const void *,size_t);
unsigned char *pa_read(const char *,size_t,size_t *);
int pa_write_all(int,const void *,size_t);
int pa_sync(int);
int pa_sync_parent(const char *);
int pa_truncate(int,size_t);
int pa_lock_root(const char *);
uint64_t pa_millis(void);
cJSON *pa_json(const void *,size_t);
const char *pa_string(const cJSON *,const char *);
int pa_integer(const cJSON *,const char *,int,int,int *);
void pa_log(const char *,...);
void pa_log_open(const char *);
#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
typedef SOCKET pa_socket;
#define PA_INVALID INVALID_SOCKET
#define pa_socket_close closesocket
#else
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
typedef int pa_socket;
#define PA_INVALID (-1)
#define pa_socket_close close
#endif
int pa_net_init(void);
typedef struct { char (*name)[80]; size_t count,capacity; int method; } PA_Names;
int pa_names_get(const char *,PA_Names *);
void pa_names_free(PA_Names *);
int pa_names_dirents(const unsigned char *,size_t,PA_Names *);
void pa_net_timeout(pa_socket,unsigned);
pa_socket pa_connect(unsigned);
int pa_send_all(pa_socket,const void *,size_t);
#endif
