# Compilar o Port Station

Este guia é para desenvolvimento do projeto. Para gerar uma homebrew com o kit pronto, use [Guia rápido](QUICKSTART.md) ou [Novo jogo](NEW_GAME.md).

## Ambiente de desenvolvimento

O frontend usa Python 3.13/Tk e Pillow 13.0.0. A base de compilação Windows inclui Clang/LLD 18.1.8, SDK público v0.44, CMake, Ninja e Zig nas versões verificadas pelo kit. Node.js executa os testes JavaScript. O .NET SDK 10 recompila as ferramentas gerenciadas: preparador de Breath, ponte Unity Mono e scanner do extrator.

Clone o repositório e instale as dependências Python:

```powershell
python -m pip install -r requirements.txt
```

Para compilar títulos, use os diretórios `build/` e `tools/` do Windows kit da mesma versão. Eles contêm os binários públicos e o prefixo limpo, que não fazem parte do download source-only. Depois:

```powershell
python -m port_station doctor
python -m port_station verify-runtime
python -m unittest discover -s port_station/tests -v
node port_station/tests/test_nw_bridge.js
python release_support/test-prepare-game.py
dotnet run --project release_support/managed/VerifierTests -c Release
```

Sem FFmpeg, os testes de conversão de áudio são pulados. Instale-o com `python release_support/install-ffmpeg.py` para executar esses testes também.

## Estrutura do código

- `port_station/`: interface, CLI, projetos, geradores e testes.
- `sdk/prospero-achievements/`: SDK e pontes de eventos.
- `src/prospero_achievements/`: servidor C e interface web embutida.
- `sdk/ps5-game-port/`: integração do toolchain para os títulos.
- `build/prospero-evaluation/source-v020/`: fontes do runtime consumidos pela build.
- `release_support/`: preparação de exemplos e ferramentas de empacotamento do kit.

O frontend está em `port_station`; o pacote `achievement_extractor` fornece a análise integrada e a interface independente. Os caminhos de dados do runtime e IDs de jogos são independentes desse nome.

## Backend e SDK

```powershell
python scripts/build-prospero-achievements.py --ps5
python scripts/test-prospero-achievements.py
```

O build embute os arquivos de `src/prospero_achievements/web/` e compila o servidor host, probes, payloads PS5 e a biblioteca estática. As saídas ficam em `build/prospero-achievements/{host,ps5}`. Header e `.a` devem ser da mesma revisão.

## Ferramentas de recursos e título

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build-native-tools.ps1
python -c "from port_station.builder import build_profile_checker; build_profile_checker()"
python release_support/build-assets.py
python scripts/build-port-studio-audio.py
```

Esses comandos recompilam, respectivamente, o conversor nativo/libc pública, o validador de perfis, o encoder BC7 e o encoder ATRAC9. O script de áudio usa FFmpeg instalado para atualizar seu recibo completo.

A build de um jogo gera C/CMake específicos do título e recompila launcher e helper. `python -m port_station build <projeto> --output <pasta-nova>` usa o mesmo caminho da interface.

Os helpers de perfil e eventos para a versão LÖVE suportada são recompilados com
`python -m port_station.love`. O comando usa o Zig do kit e gera
`build/port-studio/compat/pe64/{paenv.dll,paevents.dll,helper.json}`. Os fontes estão em
`port_station/native_compat/paenv.c` e
`sdk/prospero-achievements/bridge/pa_windows_events.c`; o manifesto relaciona
cada fonte à sua DLL. Os
arquivos comerciais são preparados localmente durante a build do port.

Os testes `port_station.tests.test_love_achievements` usam somente fixtures
próprias. Com o kit Windows, verificam também a DLL real e a gravação por usuário.
Defina `PORT_STATION_LUAJIT_DLL` para uma biblioteca LuaJIT 2.x local para rodar
os testes opcionais de argumentos/retornos, repetição, erros e encaminhamento FFI;
eles executam apenas os scripts de teste do projeto.

## Preparador gerenciado do exemplo Breath

```powershell
dotnet build release_support/managed/Bridge/Bridge.csproj -c Release -o build/release-managed
dotnet publish release_support/managed/Patcher/Patcher.csproj -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -p:DebugType=None -o build/release-managed
```

O restore usa Microsoft.NETFramework.ReferenceAssemblies 1.0.3 e Mono.Cecil 0.11.6. Os fontes da ponte e patcher estão em `src/breath/wine_title/`. O resultado modificado do jogo é produzido localmente pelo usuário, não pelo build do projeto.

## Scanner integrado e ponte genérica

```powershell
dotnet publish achievement_extractor/managed/Scanner.csproj -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -p:DebugType=None -o achievement_extractor/bin
python achievement_extractor/build-package.py --seal-helper
python sdk/prospero-achievements/managed/build.py
python -m unittest discover -s achievement_extractor/tests -v
python -m unittest port_station.tests.test_extractor_gui -v
```

O kit inclui os binários próprios e os hashes dos helpers. Os leitores de ZIP/LuaJIT são Python puro; não exigem Lua instalado nem executam o jogo. Veja o [SDK gerenciado](../sdk/prospero-achievements/managed/README.md) para os testes da ponte.

## Runtime e dependências upstream

As revisões estão em `SOURCES.json` e `port_station/runtime.lock.json`; os snapshots principais acompanham o asset `upstream-sources.zip`. O snapshot de prospero-win inclui os patches Wine e scripts como `tools/build_wine_ps5.sh` e `tools/build_tls_ps5.sh`.

Reconstruir toda a pilha Wine/Mesa/SDK exige o ambiente POSIX e os toolchains indicados pelos projetos upstream. O frontend recompila títulos e componentes próprios no Windows usando a pilha fixada. Não há promessa de reprodução byte a byte de toda a pilha em qualquer máquina.

A reconstrução do WGL/Zink com a correção de liberação de `needs_present` está em
[release_support/mesa-wgl](../release_support/mesa-wgl/README.md). O script verifica
o snapshot Mesa e o compilador por SHA-256, aceita `--arch x86_64` ou `--arch i686`
e gera os binários junto dos manifests e fontes modificados. O runtime do kit
usa a variante `--release-pending-present --clean`, sem rastreamento por quadro.

Após uma alteração intencional e testada nas ferramentas ou runtime, a baseline pode ser atualizada com:

```powershell
python -m port_station lock --accept-current
```

O comando preserva o lock anterior. Uma divergência inesperada deve ser investigada antes de aceitar outra baseline. Licenças, créditos e revisões por componente estão em [THIRD_PARTY](../THIRD_PARTY.md).
