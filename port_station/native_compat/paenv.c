/* SPDX-License-Identifier: GPL-3.0-or-later
 * Own-process profile lookup for PhysFS on Wine hosts without account-name
 * mapping. This module changes no tokens, permissions or system state.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>

static BOOL current_user_token(HANDLE input){
 BYTE target[512],current[512];DWORD n=0;HANDLE own=NULL;BOOL ok;
 if(!input){SetLastError(ERROR_INVALID_HANDLE);return FALSE;}
 if(!GetTokenInformation(input,TokenUser,target,sizeof(target),&n))return FALSE;
 if(!OpenProcessToken(GetCurrentProcess(),TOKEN_QUERY,&own))return FALSE;
 ok=GetTokenInformation(own,TokenUser,current,sizeof(current),&n);
 DWORD error=GetLastError();CloseHandle(own);
 if(!ok){SetLastError(error);return FALSE;}
 if(!EqualSid(((TOKEN_USER*)target)->User.Sid,((TOKEN_USER*)current)->User.Sid)){
  SetLastError(ERROR_NOT_SUPPORTED);return FALSE;
 }
 return TRUE;
}
static DWORD profile_path(WCHAR *path,DWORD capacity){
 DWORD n=GetEnvironmentVariableW(L"USERPROFILE",path,capacity);
 if(!n||n>=capacity){SetLastError(n?ERROR_INSUFFICIENT_BUFFER:ERROR_PATH_NOT_FOUND);return 0;}
 if(n<3||path[1]!=L':'||(path[2]!=L'\\'&&path[2]!=L'/')){SetLastError(ERROR_BAD_PATHNAME);return 0;}
 return n+1;
}
__declspec(dllexport) BOOL WINAPI GetUserProfileDirectoryW(HANDLE token,LPWSTR output,LPDWORD capacity){
 WCHAR path[32768];DWORD required;
 if(!capacity){SetLastError(ERROR_INVALID_PARAMETER);return FALSE;}
 if(!current_user_token(token))return FALSE;
 required=profile_path(path,sizeof(path)/sizeof(path[0]));if(!required)return FALSE;
 DWORD available=*capacity;*capacity=required;
 if(!output||available<required){SetLastError(ERROR_INSUFFICIENT_BUFFER);return FALSE;}
 memcpy(output,path,required*sizeof(WCHAR));SetLastError(ERROR_SUCCESS);return TRUE;
}
__declspec(dllexport) BOOL WINAPI GetUserProfileDirectoryA(HANDLE token,LPSTR output,LPDWORD capacity){
 WCHAR path[32768];int required;
 if(!capacity){SetLastError(ERROR_INVALID_PARAMETER);return FALSE;}
 if(!current_user_token(token))return FALSE;
 if(!profile_path(path,sizeof(path)/sizeof(path[0])))return FALSE;
 required=WideCharToMultiByte(CP_ACP,0,path,-1,NULL,0,NULL,NULL);if(!required)return FALSE;
 DWORD available=*capacity;*capacity=(DWORD)required;
 if(!output||available<(DWORD)required){SetLastError(ERROR_INSUFFICIENT_BUFFER);return FALSE;}
 if(!WideCharToMultiByte(CP_ACP,0,path,-1,output,available,NULL,NULL))return FALSE;
 SetLastError(ERROR_SUCCESS);return TRUE;
}
