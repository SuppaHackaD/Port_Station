/* Windows host driver for Art Swap's open ATRAC9 encoder. GPL-3.0-or-later. */
#include "at9.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <wchar.h>

bool buf_reserve(buf_t *b,size_t n){
    if(n<=b->cap)return true;
    void *p=realloc(b->data,n);if(!p)return false;
    b->data=p;b->cap=n;return true;
}
static void number(FILE *f,double value){if(isfinite(value))fprintf(f,"%.8f",value);else fputs("null",f);}
int wmain(int argc,wchar_t **argv){
    if(argc!=4){fputs("Usage: port-at9-encode INPUT.f64 OUTPUT.at9 REPORT.json\n",stderr);return 2;}
    FILE *in=_wfopen(argv[1],L"rb");if(!in){perror("PCM input");return 3;}
    if(_fseeki64(in,0,SEEK_END)){fclose(in);return 3;}
    long long bytes=_ftelli64(in);rewind(in);
    if(bytes<=0||bytes%16||bytes/16>(long long)at9_max_samples(192)){fclose(in);fputs("PCM input empty, incomplete or longer than ATRAC9 size limit\n",stderr);return 4;}
    size_t n=(size_t)(bytes/16);double *l=malloc(n*sizeof(double)),*r=malloc(n*sizeof(double));
    if(!l||!r){free(l);free(r);fclose(in);return 5;}
    for(size_t i=0;i<n;i++){
        double frame[2];
        if(fread(frame,sizeof(double),2,in)!=2||!isfinite(frame[0])||!isfinite(frame[1])){free(l);free(r);fclose(in);return 6;}
        l[i]=frame[0];r[i]=frame[1];
    }
    fclose(in);double before,after;
    fputs("ATRAC9: normalizing loudness, limiting peaks and preparing loop...\n",stderr);
    if(!at9_prepare(l,r,n,-28.0,-2.0,0.01,0.01,&before,&after)){free(l);free(r);return 7;}
    buf_t out={0};char error[512]={0};
    fprintf(stderr,"ATRAC9: encoding %.3f seconds, stereo 48 kHz, 192 kb/s...\n",(double)n/48000);
    bool ok=at9_encode(l,r,n,192,&out,error,sizeof(error));free(l);free(r);
    if(!ok){fprintf(stderr,"ATRAC9: %s\n",error);free(out.data);return 8;}
    FILE *file=_wfopen(argv[2],L"wb");if(!file){free(out.data);return 9;}
    ok=fwrite(out.data,1,out.len,file)==out.len;int closed=fclose(file);free(out.data);if(!ok||closed)return 9;
    FILE *report=_wfopen(argv[3],L"wb");if(!report)return 10;
    fprintf(report,"{\"sample_rate\":48000,\"channels\":2,\"samples\":%zu,\"duration\":%.8f,\"bitrate_kbps\":192,\"bytes\":%zu,\"loop\":true,\"source_lufs\":",n,(double)n/48000,out.len);
    number(report,before);fputs(",\"final_lufs\":",report);number(report,after);fputs(",\"true_peak_ceiling_dbtp\":-2,\"fade_seconds\":0.01}\n",report);
    if(fclose(report))return 10;fputs("ATRAC9: done.\n",stderr);return 0;
}
