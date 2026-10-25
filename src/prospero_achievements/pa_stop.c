#include "pa_common.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(void){
    pa_net_init();pa_socket s=pa_connect(PA_PORT);if(s==PA_INVALID)return 1;
    const char request[]="POST /api/v1/service/stop HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Length: 0\r\nConnection: close\r\n\r\n";
    int rc=pa_send_all(s,request,sizeof(request)-1);char b[1024]={0};int n=rc?-1:(int)recv(s,b,sizeof(b)-1,0);pa_socket_close(s);
    return n>0&&strstr(b,"HTTP/1.1 200 ")?0:2;
}
