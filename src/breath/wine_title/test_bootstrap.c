#include "breath_bootstrap.h"
#include <stdio.h>
int main(int argc,char**argv){if(argc!=2)return 2;int r=breath_bootstrap(argv[1]);printf("bootstrap result=%d\n",r);return r?1:0;}
