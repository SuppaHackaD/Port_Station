# Port Station 0.2.2

Frontend Python para criar uma homebrew de um jogo Windows com Wine, usando o runtime exercitado com Breath e TCOAL. Inclui interface Tk, CLI equivalente, editor de conquistas próprias e preparação da apresentação do título.

## Abrir nesta máquina

Execute **Port_Station.cmd**, na raiz deste workspace. Não precisa instalar Qt, abrir Unity ou recompilar o payload de conquistas. Use **Abrir** para carregar `port_studio/examples/breath.ps5port.json` ou `tcoal.ps5port.json`, ou **Novo** para começar outro jogo.

1. Escolha a pasta do jogo e seu `.exe`. O programa identifica PE x86/x64.
2. Informe título, Title ID exclusivo e game_id estável. Os exemplos usam **PPSA99410** e **PPSA99411**, separados dos jogos atuais do console.
3. Escolha o perfil e os argumentos. Use o ícone original ou uma imagem escolhida por você. Na aba **Áudio**, escolha a música, o início e a duração do trecho.
4. Em **Conquistas**, selecione o adaptador, importe/edite o catálogo e marque a platina se desejado. A descrição e o ícone de cada item são editáveis; a platina também tem nome, descrição e ícone próprios.
5. Em **Build e diagnóstico**, valide, prepare as fontes para revisão ou compile e empacote. Escolha uma pasta pai: será criada uma subpasta nova. A interface mostra o log e permite cancelar.

Uma build completa produz `native/dist/PPSAxxxxx/`, ZIP, `manifest.json`, `project.json`, `game.profile`, `build.log`, catálogo/PNGs e fontes geradas. Os binários nativos são realmente recompilados com a identidade do novo título, incluindo seu helper. O programa não renomeia simplesmente um executável de outro jogo.

O programa não instala nem inicia nada no console. Copiar a pasta completa para `/data/homebrew` e validar pelo ShadowMount+ é uma etapa posterior. Os primeiros exemplos compilados pelo Studio ainda precisam dessa validação; a validação anterior dos jogos não cobre automaticamente esta nova geração de launcher/prefixo.

## Perfis e adaptadores

| Perfil | Configuração inicial |
| --- | --- |
| `dxvk-xinput` | DXVK, controle XInput, janela 1280×720 |
| `nwjs-canvas` | Canvas como primeiro argumento, flags exercitadas com NW.js, teclado mapeado ao controle, diretório Chromium gravável |
| `gdi-keyboard` | GDI e teclado mapeado ao controle |

**Um perfil não garante que outro jogo Windows será compatível.** Jogos que dependem de outra versão da engine, driver, API ou middleware podem precisar de um perfil/adaptação adicional. A ferramenta empacota o jogo com a camada Wine; não recompila sua engine como código nativo PS5.

No perfil NW.js, o Studio lê fontes TTF/OTF referidas pelas folhas CSS, instala-as no prefixo Wine próprio e acrescenta fontes locais como primeira opção no CSS da cópia empacotada. Isso inclui a correção de Faustina necessária ao TCOAL: o original do PC podia ficar aguardando o carregamento pela URL mesmo com Canvas funcionando. O relatório `nwjs-compatibility.json` registra os arquivos ajustados; a pasta original permanece intacta. Prefixos antigos já preparados não recebem mudanças genéricas nos arquivos do jogo: no teste PPSA99411, a correção da fonte foi aplicada separadamente com backup.

| Adaptador | Fonte dos eventos |
| --- | --- |
| `none` | Sem catálogo/eventos |
| `file-v1` | O desenvolvedor integra o SDK/file bridge no próprio jogo e publica os eventos reais |
| `nwjs-steam` | Envolve `Steam.awardAchievement` e `Steam.API.activateAchievement`, quando essas funções existem, preservando argumentos/this/retorno/exceções; recebe mapa explícito de IDs |
| `breath` | Mantém a ponte Unity e as 11 condições originais já implementadas; exige o jogo preparado com a DLL da ponte |

Criar uma lista no editor **não cria condições de gameplay**. Jogos com outras APIs precisam de outro adaptador. A lista é do **Prospero Achievements**, acessível na web, com popups próprios após confirmação do backend. Não é uma lista do serviço de troféus Sony.

O SDK central continua em `sdk/prospero-achievements`. A nova ferramenta usa a versão 0.1.2 e a API1 existente. O payload `prospero_achievements.elf` deve estar ativo no console; quando estiver indisponível, os clientes mantêm a fila em disco. Nenhuma chamada a serviço Sony foi acrescentada.

IDs canônicas são sensíveis à caixa. O campo **ID emitida pelo jogo** permite mapear, por exemplo, `warden_wins` para `WARDEN_WINS`, preservando o argumento original enviado à Steam. IDs de origem conflitantes são rejeitadas. A platina é calculada pelo backend quando todas as conquistas regulares são obtidas; não é enviada como unlock pelo jogo.

Para o pacote identificado como **The Coffin of Andy and Leyley**, os aliases minúsculos das 20 IDs originais são acrescentados automaticamente. Outros jogos mantêm suas regras exatas. Ao importar um catálogo existente pela interface, o Studio começa uma revisão maior; aumente novamente a versão ao alterar uma lista já publicada.

Ao editar um catálogo já instalado, aumente `catalog_version` e preserve IDs/condições. Remoções ou mudanças de condições exigem migração explícita no backend; a ferramenta não apaga progresso para aceitar uma edição. Os exemplos aumentam a versão porque a normalização das imagens altera seus hashes. Eles mantêm os game_ids existentes; portanto compartilham logicamente o progresso já obtido quando sincronizados no mesmo usuário.

## Apresentação

- Ícone obrigatório, sem placeholder automático: corte central e PNG real 512×512.
- Fundo de seleção e de início: imagens comuns ou DDS BC7 DX10 pronto, 3840×2160, sem mipmaps. Indicando só um fundo, ele é usado nos dois lugares.
- Som: conversão local automática de MP3, WAV, OGG, FLAC, M4A/AAC e formatos aceitos pelo FFmpeg embutido. O encoder aberto gera ATRAC9 48 kHz estéreo a 192 kb/s, normaliza o volume para aproximadamente -28 LUFS, limita picos e cria pequenos fades e loop. Padrão: 15 segundos; máximo: 87,3 segundos, respeitando 2 MiB.
- `.at9` pronto continua aceito: é validado e copiado sem mudanças. Início/duração não são aplicados a ele.
- Arquivos do shell: `sce_sys/icon0.png`, `pic0.dds`, `pic1.dds`, `snd0.at9` e `param.json`.

O conversor BC7 usa o código host GPL-3.0-or-later do [ps5-forwarder-manager](https://github.com/heydemoura/ps5-forwarder-manager/tree/4c463596e5eaf42648200117cb6c67c0769b01f8), com cópia de fonte, licença e avisos em `port_studio/vendor/forwarder`. O código é compilado localmente com Zig. A interface utiliza o conceito de arte editável, mas não precisa do aplicativo Forwarder Manager instalado no PS5.

### Conversão de áudio embutida

Salve seu projeto, feche a janela antiga e reabra `Port_Station.cmd`. A aba **Áudio** permite escolher a música, início (segundos) e duração. A build converte automaticamente; **Converter para .at9…** também gera um arquivo separado sem precisar compilar o jogo. Campos da interface aceitam ponto ou vírgula decimal.

```powershell
python -m port_station transcode-audio "C:\musicas\tema.mp3" --output "C:\musicas\tema-ps5.at9" --start 30 --duration 15
```

A conversão funciona offline. O FFmpeg embutido decodifica/recorta/reamostra; o encoder C do [Art Swap](https://github.com/griches/PS5_ArtSwap/blob/03a5c40b9b34bba20deaae46aa0de272f21065cf/helper/src/at9.c) gera o bitstream ATRAC9. O código GPL-3.0-or-later e as tabelas/avisos MIT de LibAtrac9 estão em `port_studio/vendor/artswap_at9`; os executáveis, licença e versões estão em `tools/port-studio-audio`. Não é usado at9tool proprietário nem um serviço de upload.

O trecho pode ser menor que a duração escolhida quando a música termina antes. Início além do fim é erro, sem arquivo final. A origem e saídas preexistentes são preservadas. `audio-report.json` na pasta da build registra tamanho, número de amostras, volume medido e hashes; o volume também é registrado em `pubtools.loudnessSnd0` no pacote, quando mensurável. Silêncio é permitido e tem volume não mensurável.

Projetos 0.1.0 carregam com início zero/duração 15. Para recompilar o encoder a partir das fontes locais: `python scripts/build-port-studio-audio.py`. Essa etapa usa o Zig do kit; o uso normal já leva o encoder compilado. Nesta release pública, FFmpeg é opcional e obtido diretamente com `python release_support/install-ffmpeg.py`; o executável não acompanha o kit. O FFmpeg foi fixado a `2026-10-22-git-bf0e831606-essentials_build`, com SHA-256 e links de fonte/build registrados no recibo; não é baixado durante uma build.

## Estado, updates e isolamento

Cada título do Studio usa `/data/port-studio/ppsaXXXXX` (a ID em minúsculas). O pacote imutável contém o seed; a primeira abertura cria seu prefixo gravável, conferindo tamanhos e CRCs. As aberturas posteriores preservam o jogo/prefixo e os saves. O marcador vincula o prefixo à Title ID e ao game_id.

Os perfis de lançamento e os dois scripts de conquistas criados pelo Studio são sincronizados do pacote a cada abertura; editar argumentos ou a configuração desses scripts não exige recopiá-los manualmente. Isso não substitui o `index.html`, o registry, os arquivos originais do jogo ou os saves existentes. Atualizações dos arquivos do jogo ou overlays em um prefixo já preparado **não são aplicadas automaticamente**: exigem um plano de migração específico, preservando saves, ou uma Title ID nova para teste. Esta versão não pretende realizar essa migração silenciosamente.

O seed usa um template Wine limpo: Windows e registry do prefixo de teste, sem pastas Games/users, saves importados, logs de conquista ou filas de outro jogo. Os arquivos fornecidos dentro da própria pasta selecionada do jogo são copiados como entradas do projeto; revise essa pasta se ela já contiver saves pessoais. Não há coleta automática por FTP ou importação de saves do console.

Fechamento herdado: **Options + clique do touchpad por um segundo**, Alt+F4 e fallback para a tela inicial; o tratamento do botão PS é preservado. O modelo de runtime foi exercitado nos jogos anteriores, mas o comportamento de um novo jogo ainda precisa de teste.

## CLI e reprodução

Na raiz do workspace:

```powershell
python -m port_station doctor
python -m port_station verify-runtime
python -m port_station validate port_studio/examples/tcoal.ps5port.json
python -m port_station prepare port_studio/examples/tcoal.ps5port.json --output build/port-studio/minha-preparacao
python -m port_station build port_studio/examples/tcoal.ps5port.json --output build/port-studio/minha-build
```

`prepare` valida dependências, gera fontes/catálogo/arte/perfil, usa o parser real do runtime para validar o perfil e para antes da compilação. `build --no-zip` produz a pasta completa sem comprimi-la. Todas as saídas precisam ser novas; falhas/cancelamentos preservam os arquivos parciais e `result.json` identifica a situação. Não use uma saída parcial como pacote.

Projetos `.ps5port.json` são UTF-8. Caminhos relativos resolvem contra a pasta do projeto. `${workspace}` resolve contra a pasta que contém este código. O projeto aceita `overlays` explícitos sem modificar os arquivos originais: cada entrada fornece `source` e `destination` relativa ao jogo. O TCOAL usa isso para a correção da tradução já confirmada.

`runtime.lock.json` congela os arquivos reais do runtime, template de prefixo, SDK, ferramentas e fontes compartilhadas com SHA-256. A build verifica esse lock antes de gerar o pacote. O recibo registra os arquivos do jogo, overlays, fontes do Studio, projeto e saída; se o jogo mudar durante o processo, a build falha.

O objetivo é repetir o procedimento com entradas verificáveis. **Não há promessa de binários nativos byte a byte idênticos entre caminhos de build/máquinas**: mapas, caminhos e ferramentas podem influenciar o linker. O ZIP usa datas fixas, e seu hash final fica no recibo.

Após uma atualização intencional do SDK/runtime, execute primeiro seus testes. Só então aceite uma nova baseline:

```powershell
python -m port_station lock --accept-current
```

Esse comando recompila o validador host, recalcula os hashes e preserva o lock anterior em `build/port-studio/locks`. Não use isso para esconder uma divergência inesperada.

## Toolkit para outra máquina

```powershell
python -m port_station export-toolkit handoff/Port_Station_0.1.0/toolkit.zip
```

O comando cria um toolkit local com frontend, Wine/runtime, template limpo, ferramentas públicas, conversor/validador, SDK/fontes/licenças e manifesto de hashes. Não inclui as pastas de jogos/handoff/analysis, saves nem estado de conquistas. O arquivo pode ser grande porque inclui o compilador e o prefixo Windows.

Na outra máquina Windows x64, instale **Python 3.13 x64 com Tcl/Tk**, extraia a pasta, execute `Port_Station.cmd` e rode o diagnóstico. O Pillow compatível está no toolkit; FFmpeg é opcional e instalado separadamente pelo script da release. Crie um novo projeto e selecione seus arquivos locais. As receitas Breath/TCOAL do workspace referenciam assets/jogos preparados localmente e precisam ser religadas; elas não incluem os jogos no toolkit.

`setup` é a inicialização de desenvolvimento desta máquina a partir dos artefatos já exercitados, não um downloader universal. O toolkit exportado já leva o kit pronto, portanto não precisa desse comando. Não substitua um runtime ausente por um download de versão diferente sem revisar o lock e a compatibilidade.

## Verificação e limites atuais

```powershell
python -m unittest discover -s port_studio/tests -v
node port_studio/tests/test_nw_bridge.js
```

Os testes cobrem caminhos/colisões, IDs/aliases, configuração, PE real, UTF-8, platina, recursos PNG, ligação do worker, preservação de fontes e comportamento dos wrappers NW.js. O áudio tem conversões reais e decodificação independente pelo FFmpeg, canais/frequências, duração, volume, silêncio, loops e formatos de entrada. Há builds locais reais das duas receitas com FSELF íntegro na versão 0.1.0. Artes e música personalizadas do Studio foram validadas no PS5 com TCOAL. Esta distribuição usa placeholders próprios e não inclui música ou arquivos comerciais.

Licença do frontend/integradores desta pasta: GPL-3.0-or-later; consulte `port_studio/LICENSE`. Wine/runtime, SDK, bibliotecas e imagens mantêm suas próprias licenças/atribuições. O empacotador não altera a titularidade dos arquivos do jogo.
