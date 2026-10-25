$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$zig = Join-Path $projectRoot 'tools\zig-python\ziglang\zig.exe'
$native = Join-Path $projectRoot 'tools\PS5_Vulkan\tooling\native'
$zlib = Join-Path $projectRoot 'tools\zlib-1.3.2'
$hostDir = Join-Path $projectRoot 'build\host'
$zobj = Join-Path $hostDir 'zlib'
New-Item -ItemType Directory -Path $zobj -Force | Out-Null
Push-Location $zobj
try {
    $sources = 'adler32','compress','crc32','deflate','gzclose','gzlib','gzread','gzwrite','inflate','infback','inftrees','inffast','trees','uncompr','zutil'
    $files = $sources | ForEach-Object { Join-Path $zlib "$_.c" }
    foreach ($source in $files) {
        & $zig cc -target x86_64-windows-gnu -O2 -I $zlib -c $source -o "$([IO.Path]::GetFileNameWithoutExtension($source)).o"
        if ($LASTEXITCODE) { throw 'Host zlib compilation failed' }
    }
    $objects = Get-ChildItem -File -Filter '*.o' | ForEach-Object FullName
    & $zig ar rcs libz.a @objects
    if ($LASTEXITCODE) { throw 'Host zlib archive failed' }
} finally { Pop-Location }
& $zig c++ -target x86_64-windows-gnu -std=c++20 -O2 -I $zlib "$native\native_app_builder.cpp" "$native\self_container.cpp" "$native\elf_object.cpp" "$native\sce_module_writer.cpp" "$zobj\libz.a" -o "$hostDir\ps5-native-tool.exe"
if ($LASTEXITCODE) { throw 'Native converter compilation failed' }
& $zig c++ -target x86_64-windows-gnu -std=c++20 -O2 "$native\libc_builder.cpp" -o "$hostDir\libc-builder.exe"
if ($LASTEXITCODE) { throw 'Runtime generator compilation failed' }
foreach ($copy in @('a','b')) {
    & "$hostDir\libc-builder.exe" "$native\runtime\api-surface.txt" "$native\runtime\imports.txt" "$hostDir\libc-$copy.raw.elf"
    if ($LASTEXITCODE) { throw 'Runtime generation failed' }
    if ((Get-FileHash "$hostDir\libc-$copy.raw.elf").Hash.ToLower() -ne '8ee6e124993e1af26420cb455890fd002f5d6c7e78883c860ce45734e7d002bb') { throw 'Raw runtime digest differs from upstream' }
    & "$hostDir\ps5-native-tool.exe" self --sign --in "$hostDir\libc-$copy.raw.elf" --out "$hostDir\libc-$copy.prx"
    if ($LASTEXITCODE) { throw 'Runtime wrapping failed' }
    if ((Get-FileHash "$hostDir\libc-$copy.prx").Hash.ToLower() -ne 'e6ff45d16adf687855cc3b33b0c8a4132b6504360b221e0a34c7e99fb3ba0036') { throw 'Signed runtime digest differs from upstream' }
}
Copy-Item "$hostDir\libc-a.prx" "$hostDir\libc.prx"
