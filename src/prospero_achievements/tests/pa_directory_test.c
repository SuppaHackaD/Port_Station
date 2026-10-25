#include "pa_common.h"
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Exercise the decoder used by PS5 getdents, including filesystem-sized blocks. */
static size_t record(unsigned char *b,const char *name,unsigned type){
    size_t n=strlen(name),len=(8+n+1+3)&~(size_t)3;
    memset(b,0,len);b[0]=1;b[4]=(unsigned char)len;b[5]=(unsigned char)(len>>8);
    b[6]=(unsigned char)type;b[7]=(unsigned char)n;memcpy(b+8,name,n);return len;
}
int main(void){
    unsigned char *b=malloc(65536);assert(b);PA_Names names={0};size_t n=0;
    n+=record(b+n,".",4);n+=record(b+n,"..",4);n+=record(b+n,".temporary",8);
    n+=record(b+n,"folder",4);n+=record(b+n,"event.json",8);n+=record(b+n,"unknown.json",0);
    assert(!pa_names_dirents(b,n,&names)&&names.count==2);
    assert(!strcmp(names.name[0],"event.json")&&!strcmp(names.name[1],"unknown.json"));pa_names_free(&names);
    assert(!pa_names_dirents(b,0,&names)&&!names.count);
    n=record(b,"event.json",8);
    assert(pa_names_dirents(b,n-1,&names)==-1&&errno==EINVAL);
    assert(pa_names_dirents(b,7,&names)==-1&&errno==EINVAL);
    b[4]=0;assert(pa_names_dirents(b,n,&names)==-1&&errno==EINVAL);
    n=record(b,"event.json",8);b[7]=255;assert(pa_names_dirents(b,n,&names)==-1&&errno==EINVAL);
    n=record(b,"event.json",8);b[8+strlen("event.json")]='x';assert(pa_names_dirents(b,n,&names)==-1&&errno==EINVAL);
    n=record(b,"event.json",8);b[10]=0;assert(pa_names_dirents(b,n,&names)==-1&&errno==EINVAL);
    char longname[81];memset(longname,'a',80);longname[80]=0;n=record(b,longname,8);
    assert(!pa_names_dirents(b,n,&names)&&!names.count);
    /* Multiple batches exceed one 64 KiB block while preserving the snapshot. */
    for(unsigned batch=0;batch<3;batch++){
        n=0;for(unsigned i=0;i<2000;i++)n+=record(b+n,"01234567890123456789",8);
        assert(n<=65536&&!pa_names_dirents(b,n,&names));
    }
    assert(names.count==6000);pa_names_free(&names);
    n=record(b,"event.json",8);
    for(unsigned i=0;i<8192;i++)assert(!pa_names_dirents(b,n,&names));
    assert(pa_names_dirents(b,n,&names)==-1&&errno==EOVERFLOW&&names.count==8192);
    pa_names_free(&names);assert(!names.name&&!names.count&&!names.capacity);free(b);
    puts("PS5 directory record decoder: valid, malformed, large batches and capacity OK");return 0;
}
