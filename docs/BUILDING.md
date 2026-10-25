# Compilar o Port Station

Este guia é para desenvolvimento do projeto. Para gerar uma homebrew com o kit pronto, use [Guia rápido](QUICKSTART.md) ou [Novo jogo](NEW_GAME.md).

## Ambiente de desenvolvimento

O frontend usa Python 3.13/Tk e Pillow 13.0.0. A base de compilação Windows inclui Clang/LLD 18.1.8, SDK público v0.44, CMake, Ninja e Zig nas versões verificadas pelo kit. Node.js executa os testes JavaScript. O .NET SDK 10 é necessário somente para recompilar o preparador gerenciado de Breath.

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

O projeto usa um único pacote Python, `port_station`. Os caminhos de dados do runtime e IDs de jogos são independentes desse nome.

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

## Preparador gerenciado do exemplo Breath

```powershell
dotnet build release_support/managed/Bridge/Bridge.csproj -c Release -o build/release-managed
dotnet publish release_support/managed/Patcher/Patcher.csproj -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -p:DebugType=None -o build/release-managed
```

O restore usa Microsoft.NETFramework.ReferenceAssemblies 1.0.3 e Mono.Cecil 0.11.6. Os fontes da ponte e patcher estão em `src/breath/wine_title/`. O resultado modificado do jogo é produzido localmente pelo usuário, não pelo build do projeto.

## Runtime e dependências upstream

As revisões estão em `SOURCES.json` e `port_station/runtime.lock.json`; os snapshots principais acompanham o asset `upstream-sources.zip`. O snapshot de prospero-win inclui os patches Wine e scripts como `tools/build_wine_ps5.sh` e `tools/build_tls_ps5.sh`.

Reconstruir toda a pilha Wine/Mesa/SDK exige o ambiente POSIX e os toolchains indicados pelos projetos upstream. O frontend recompila títulos e componentes próprios no Windows usando a pilha fixada. Não há promessa de reprodução byte a byte de toda a pilha em qualquer máquina.

Após uma alteração intencional e testada nas ferramentas ou runtime, a baseline pode ser atualizada com:

```powershell
python -m port_station lock --accept-current
```

O comando preserva o lock anterior. Uma divergência inesperada deve ser investigada antes de aceitar outra baseline. Licenças, créditos e revisões por componente estão em [THIRD_PARTY](../THIRD_PARTY.md).
