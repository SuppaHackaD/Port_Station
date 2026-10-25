#include "prospero_achievements.h"
#include "pa_probe_assets.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef PA_PS5
#include <unistd.h>
static void notice(const char *message){
    struct {char reserved[45];char message[3075];} r={0};extern int sceKernelSendNotificationRequest(int,void *,size_t,int);
    snprintf(r.message,sizeof(r.message),"%s",message);sceKernelSendNotificationRequest(0,&r,sizeof(r),0);
}
#else
static void notice(const char *message){puts(message);}
#endif
int main(int argc,char **argv){
    const char *root="/data/prospero-achievements-sdk-test";unsigned port=PA_SDK_DEFAULT_PORT;
#ifdef PA_NATIVE_TITLE
    root="/download0/prospero-achievements-sdk-test";
#endif
#ifndef PA_PS5
    if(argc>1)root=argv[1];if(argc>2)port=(unsigned)strtoul(argv[2],NULL,10);
#else
    (void)argc;(void)argv;
#endif
    PA_SDK sdk;int rc=pa_sdk_init(&sdk,root,"sdk.lifecycle.test","00000001",port);
    if(rc){notice("PA SDK Test: falha ao abrir a fila persistente.");return 1;}
    char hash[65];rc=pa_sdk_asset(&sdk,pa_probe_icon,sizeof(pa_probe_icon),hash);
    char catalog[4096];int n=snprintf(catalog,sizeof(catalog),
        "{\"schema\":1,\"game_id\":\"sdk.lifecycle.test\",\"title\":\"SDK · Teste de continuidade\",\"catalog_version\":1,\"icon\":\"%s\","
        "\"achievements\":[{\"id\":\"HELLO\",\"title\":\"Primeiro contato\",\"description\":\"O cliente enviou um desbloqueio ao payload.\",\"target\":1},"
        "{\"id\":\"PROGRESS\",\"title\":\"Passo a passo\",\"description\":\"Receber tres unidades de progresso.\",\"target\":3},"
        "{\"id\":\"ALL\",\"title\":\"Conjunto completo\",\"description\":\"Obter todas as conquistas deste teste.\",\"target\":1,\"completion\":true}]}",hash);
    if(rc||n<=0||n>=(int)sizeof(catalog)||pa_sdk_catalog(&sdk,catalog,(size_t)n)){notice("PA SDK Test: falha ao preparar o catalogo.");return 2;}
    rc=pa_sdk_unlock(&sdk,"HELLO","probe-hello-v1");
    if(!rc)rc=pa_sdk_progress(&sdk,"PROGRESS",1,"probe-progress1-v1");
    if(rc){
        char msg[256];snprintf(msg,sizeof(msg),"PA SDK %s: evento falhou rc=%d errno=%d etapa=%s dirs=%d.",PA_SDK_VERSION,rc,sdk.last_errno,sdk.last_stage?sdk.last_stage:"?",sdk.directory_method);notice(msg);
#ifdef PA_PS5
        sleep(3);
#endif
        return 3;
    }
    rc=pa_sdk_pump(&sdk);
    char msg[256];snprintf(msg,sizeof(msg),"PA SDK Test: %s; pendentes=%d; HTTP=%d.",rc>=0?"conexao e gravacao OK":"payload indisponivel ou recusou; fila preservada",pa_sdk_pending(&sdk),sdk.last_http_status);notice(msg);
#ifdef PA_PS5
    sleep(3);
#endif
    return rc<0?4:0;
}
