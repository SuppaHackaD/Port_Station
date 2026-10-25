# Compilação

## Ambiente e organização

O frontend é Python puro/Tk; não existe um .exe Windows obrigatório. A release leva o código que ele executa, junto dos compiladores e binários públicos. Requisitos externos: Windows x64, Python 3.13 x64/Tk e, para recompilar a ponte gerenciada, .NET SDK 10. Node.js é usado nos testes JavaScript. Pillow está no kit; em checkout sem kit instale Pillow 13.0.0.

Extraia o kit da release em uma pasta nova. Para trabalhar num clone do Git, copie o conteúdo do kit para a raiz do clone e mantenha seus fontes da versão correspondente. `build/` e `tools/` contêm também dependências de desenvolvimento; `.gitignore` distingue essas dependências dos fontes rastreados.

```powershell
python -m port_station doctor
python -m port_station verify-runtime
python -m unittest discover -s port_studio/tests -v
node port_studio/tests/test_nw_bridge.js
```

Os testes não precisam de jogos comerciais: arquitetura PE usa fixture sintética, exemplos são validados sem exigir a cópia local e os testes de fonte usam a fonte aberta do prefixo. O teste de áudio pode ser executado depois de instalar o FFmpeg opcional.

## Frontend e título

```powershell
Port_Station.cmd
python -m port_station validate port_studio/examples/tcoal.ps5port.json
python -m port_station prepare port_studio/examples/tcoal.ps5port.json --output outputs/tcoal-review
python -m port_station build port_studio/examples/tcoal.ps5port.json --output outputs/tcoal-build
```

Esses três últimos comandos exigem preparar a cópia local primeiro. Cada saída precisa ser uma pasta nova. O build gera C/CMake do título, compila o launcher e helper com Clang/SDK público, produz FSELF e `param.json`, copia Wine/prefixo limpo, aplica fontes/ponte na cópia e calcula manifestos. `--no-zip` dispensa o ZIP final, não a compilação.

No console, segure **Options + clique do touchpad** por um segundo para encerrar pelo runtime. O fechamento pelo botão PS foi exercitado na base atual. Não usar o antigo atalho Create.

## Backend e SDK de conquistas

```powershell
python scripts/build-prospero-achievements.py --ps5
python scripts/test-prospero-achievements.py
```

O script embute `src/prospero_achievements/web/{index.html,app.css,app.js}` a partir dos fontes. Compila o servidor host real, probes de teste e os payloads PS5. Saídas: `build/prospero-achievements/host`, `build/prospero-achievements/ps5/prospero_achievements.elf`, `pa_stop.elf`, `pa_sdk_probe.elf` e `libprospero_achievements.a`. A API continua v1, servidor0.1.0 e SDK0.1.2.

`pa_stop.elf` encerra o serviço para manutenção; não carregue junto como se fosse dependência obrigatória. Nunca teste o servidor host sobre uma pasta de dados real: os testes criam fixtures isoladas. A biblioteca estática e o header precisam ser da mesma revisão. O worker não deve executar rede no loop de renderização.

## Ferramentas host

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build-native-tools.ps1
python -c "from port_studio.builder import build_profile_checker; build_profile_checker()"
python release_support/build-assets.py
python scripts/build-port-studio-audio.py
```

O primeiro comando compila a ferramenta nativa e gera `libc.prx` a partir dos manifestos públicos de `tools/PS5_Vulkan/tooling/native/runtime`; verifica os hashes esperados. O segundo recompila o validador de perfis. O terceiro recompila o encoder de imagens BC7. O quarto recompila o encoder ATRAC9 do Art Swap; instale o FFmpeg opcional antes caso queira atualizar o recibo completo das ferramentas de áudio.

Uma recompilação intencional pode alterar hashes de binários por caminhos/toolchain. Preserve o lock anterior e revise as diferenças. Somente depois de testar, aceite a nova baseline explicitamente:

```powershell
python -m port_station lock --accept-current
```

Não aceite divergências desconhecidas para contornar a verificação.

## Ponte Breath, sem Unity

```powershell
dotnet build release_support/managed/Bridge/Bridge.csproj -c Release -o build/release-managed
dotnet publish release_support/managed/Patcher/Patcher.csproj -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -p:DebugType=None -o build/release-managed
```

O restore busca `Microsoft.NETFramework.ReferenceAssemblies`1.0.3 e Mono.Cecil0.11.6 do NuGet. O primeiro projeto gera nossa DLL compatível com .NET Framework4, sem referências a Unity/Steam. O segundo é um patcher próprio, self-contained Windows. Os fontes estão em `src/breath/wine_title`; só o patcher lê o assembly privado fornecido pelo comprador. Ele exige o hash conhecido e verifica que apenas `SteamAchievments.Start` e `Conquista` foram alterados. Não publica o resultado.

## Recompilar Wine, Mesa e o SDK público

O kit usa os binários fixados e já exercitados do prospero-win0.2.0. A release `upstream-sources.zip` inclui os arquivos-fonte dos componentes principais nas revisões de `SOURCES.json`, além das fontes/patches locais ao lado do código. As ferramentas de build upstream estão no tar de prospero-win: `tools/build_wine_ps5.sh`, `tools/build_tls_ps5.sh` e scripts Mesa relacionados. O SDK público inclui os próprios scripts e patches.

Esses builds completos exigem ambiente POSIX/WSL ou Linux e os toolchains indicados pelos respectivos projetos. Extraia as fontes, preserve os commits/versões do manifesto e siga os READMEs upstream; o rebuild completo de Wine/Mesa **não é uma etapa Windows de um clique deste frontend**. O kit Windows recompila títulos, backend e nossas ferramentas sem reconstruir toda essa pilha. Não foi demonstrada equivalência byte a byte para uma reconstrução integral de todas as dependências.

FFmpeg é uma dependência opcional obtida diretamente pelo usuário; seu script de instalação, hash, URL, licença e configuração estão documentados. Não apresentamos o binário de terceiros como compilação própria. As ferramentas de desenvolvimento (.NET, LLVM, Zig, CMake) mantêm seus projetos, licenças e instruções de build upstream.
