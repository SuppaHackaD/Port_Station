# Créditos e licenças

Os projetos abaixo tornam esta ferramenta possível. A autoria upstream permanece indicada nos fontes e avisos originais. O projeto não reivindica a criação de Wine, drivers, SDK público ou codecs.

| Componente | Autores/projeto e licença | Origem usada |
|---|---|---|
| Runtime principal | [mpereiraesaa/prospero-win](https://github.com/mpereiraesaa/prospero-win), LGPL-2.1-or-later |0.2.0; commit644e32e400c555e340d507383398c5d21b39b0b0; fontes consumidos em build/prospero-evaluation/source-v020 |
| Wine | [Wine contributors](https://gitlab.winehq.org/wine/wine), LGPL-2.1-or-later e avisos dos componentes internos |490f6d5dcbb2a5047345b8af88d114bbcaad69a8 + patches do prospero-win |
| Título, FSELF, libc própria | [BlackBearReloaded / PS5 Native App Boilerplate](https://github.com/mpereiraesaa/ps5-native-app-boilerplate), GPL-3.0-or-later; ferramentas obtidas de PS5_Vulkan | título9c0b994a048521af6fb84c73ded364504fe250e9; módulo30597512539e7edfde079cbcaf4a626bc0a948c5; fontes locais completos em tools/PS5_Vulkan/tooling/native |
| SDK público | [ps5-payload-dev](https://github.com/ps5-payload-dev/sdk), GPL-3.0-or-later e licenças das bibliotecas empacotadas |v0.44; não é SDK oficial Sony |
| Helper de privilégio próprio por título | [Arksama / Team PHU — Lapy JB Daemon](https://github.com/mpereiraesaa/PS5-Lapy-JB-Daemon), MIT |base local b48b7d7236eca25c7b9dfd6c040c763ae05dde80 + fontes/alterações em tools/Lapy-breath-reference/source; recompilado por Title ID |
| Driver RADV/Mesa, WGL/Zink | [mpereiraesaa/PS5_Mesa](https://github.com/mpereiraesaa/PS5_Mesa), Mesa contributors, licenças permissivas por arquivo; ligação PS5 GPL |RADV01d70579b8d410d6a482e36c6f184798ae4c83ad; Zinke4607ef697fe3df8d1ebc329bf1917d041843306 |
| Plataforma Vulkan | [PS5_Vulkan](https://github.com/mpereiraesaa/PS5_Vulkan) e [mihawk-99/PS5_PayloadSDK](https://github.com/mihawk-99/PS5_PayloadSDK), GPL-3.0-or-later |8aee3afb37bcfad06f0c7d263b901040f08ebbd0 /95c08f27386fc698f6bbe21dde3030140a41d10b |
| DXVK | [doitsujin e contribuidores](https://github.com/doitsujin/dxvk), zlib |2.6.2; DLLs públicas do perfil D3D11 |
| Apresentação BC7 | [heydemoura/ps5-forwarder-manager](https://github.com/heydemoura/ps5-forwarder-manager), GPL-3.0-or-later; stb sob suas licenças |4c463596e5eaf42648200117cb6c67c0769b01f8; port_studio/vendor/forwarder |
| Encoder ATRAC9 | [griches/PS5_ArtSwap](https://github.com/griches/PS5_ArtSwap), GPL-3.0-or-later; tabelas LibAtrac9 MIT |03a5c40b9b34bba20deaae46aa0de272f21065cf; adapter/driver host locais; fontes em port_studio/vendor/artswap_at9 |
| FFmpeg opcional | [FFmpeg contributors](https://ffmpeg.org/) / build de [Gyan Doshi](https://www.gyan.dev/ffmpeg/builds/), GPLv3 no build selecionado |bf0e831606938f530326c9679591109407fa8d0d; executável não acompanha a release, download direto verificado pelo usuário |
| JSON/hash do backend | [Dave Gamble/cJSON](https://github.com/DaveGamble/cJSON), MIT; [Brad Conte](https://github.com/B-Con/crypto-algorithms), domínio público |cJSON1.7.19; SHA-256cfbde48414baacf51fc7c74f275190881f037d32; alterações de namespace documentadas em src/prospero_achievements/vendor |
| Patcher gerenciado | [Jb Evain/Mono.Cecil](https://github.com/jbevain/cecil), MIT |0.11.6; não inclui assembly do jogo |
| Renderização de fontes | FreeType2.13.3, FreeType License; DejaVu, Noto, Faustina e fontes Wine sob seus avisos específicos |licenças do runtime e OFL da Faustina incluídas |
| TLS | GnuTLS3.8.13, Nettle3.10.2 e dependências; LGPL/GPL/permissivas conforme componente |licenças e AUTHORS em LICENSES/gnutls, nettle do runtime |
| Ferramentas host | LLVM18.1.8 (Apache2/LLVM exception), Zig (MIT e componentes), CMake (BSD), Ninja (Apache2), Pillow13.0.0 (HPND), .NET (MIT e componentes), zlib1.3.2 (zlib) |toolchains fixados no runtime.lock, avisos distribuídos nos diretórios correspondentes |

A permutação de tiles do backend VideoOut deriva do código SDL/PS5 de John Törnblom, sob zlib; o aviso está em `native/pw_videoout_ps5.c` do runtime. Não depende de SDL instalado separadamente para essa rotina.

O inventário do runtime original acompanha o kit em `build/prospero-evaluation/staged/PPSA99995/{THIRD_PARTY.md,SOURCES.txt,LICENSES/}`. Leia também os avisos nos fontes vendorizados e os manifests de áudio. As licenças da raiz não substituem os avisos individuais.

Créditos dos jogos: Breath é de Herbherth; The Coffin of Andy and Leyley é de Kit9 Studio. Os arquivos comerciais devem ser adquiridos de seus titulares. Nenhum vínculo, aprovação ou autorização dos criadores é alegado.
