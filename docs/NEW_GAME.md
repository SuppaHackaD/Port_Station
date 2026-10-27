# Configurar um novo jogo

Este guia parte de um projeto novo e não depende das receitas de Breath ou TCOAAL. Os perfis são configurações iniciais: encontrar uma combinação funcional pode exigir testar o executável, o renderer, os argumentos e os controles separadamente.

## 1. Escolher os arquivos de entrada

Selecione a **pasta completa** do jogo Windows. Ela deve conter os dados, DLLs e subpastas usados pelo executável. Selecione o `.exe` principal, em vez de um atalho ou instalador.

O campo **Executável** é relativo à pasta escolhida. Por exemplo:

```text
Pasta do jogo: D:/Jogos/MeuJogo
Executável: bin/MeuJogo.exe
```

O programa identifica x86 ou x64 pelo executável. O diretório de trabalho é ajustado para sua subpasta. Os arquivos de entrada são copiados para o pacote; a build não edita sua instalação original.

## 2. Definir a identidade

| Campo | Como escolher |
|---|---|
| Título exibido | Nome que aparecerá no console. |
| Title ID | `PPSA` + cinco números, diferente dos títulos que você já usa. Exemplo de formato: `PPSA99510`. |
| ID estável das conquistas | Nome curto, minúsculo, com letras, números, `.`, `_` ou `-`, até 32 caracteres. Exemplo: `meu.jogo`. Mantenha essa ID nas próximas builds para continuar usando a mesma entrada no backend. |
| Versão da aplicação | Formato `01.000.001`. Incremente quando gerar uma atualização do título. |

O Title ID identifica a aplicação no console. A ID das conquistas identifica o jogo no backend; ela não é um nome de usuário e não precisa corresponder a uma conta de plataforma.

## 3. Escolher o perfil

| Perfil | Quando começar por ele | Controles iniciais |
|---|---|---|
| `dxvk-xinput` | Jogos que usam Direct3D e oferecem controle XInput. | XInput. |
| `opengl-xinput` | Jogos OpenGL, pela camada Mesa/Zink sobre Vulkan. | XInput. |
| `nwjs-canvas` | Jogos NW.js/RPG Maker que tenham modo Canvas. | Botões convertidos em teclas. |
| `gdi-keyboard` | Aplicações 2D/GDI ou jogos que dependem de teclado. | Botões convertidos em teclas. |

O perfil `nwjs-canvas` acrescenta `canvas` como primeiro argumento e configura uma pasta gravável para o NW.js. Não é preciso repetir `canvas` no campo de argumentos. Jogos que dependam exclusivamente de WebGL podem precisar de outra configuração.

A correção de fontes NW.js instala as TTF/OTF locais referidas pelo CSS no prefixo e dá preferência ao carregamento local. Ela é aplicada automaticamente durante a build desse perfil.

### LÖVE

Use `opengl-xinput`. O Port Station reconhece por SHA-256 a DLL x64 LÖVE 11.4
validada e prepara, na cópia da build, um helper para consultar o diretório do
usuário no Wine. Na versão verificada de Intravenous 2: Mercenarism, também
corrige o descritor de controle usado pelas opções do jogo. Os arquivos de
origem são preservados; outras versões de DLL ou executável continuam exigindo
validação própria.

Para conquistas nessa revisão, importe o catálogo oficial e escolha `file-v1`.
A build integra um publicador local das chamadas originais de desbloqueio;
o relatório deve incluir `achievement_producer` com o tipo
`love-platform-setachievement-v1`. Outros executáveis LÖVE não recebem essa
ponte automaticamente. Veja [Conquistas](ACHIEVEMENTS.md).

O relatório `love-compatibility.json` informa os arquivos preparados e seus
hashes. A build inclui a atualização desses arquivos no prefixo em cache antes
de iniciar o jogo, mantendo saves e outros recursos. Isso permite reinstalar
uma build corrigida com o mesmo Title ID, usando a pasta completa gerada.

Se um jogo falhar, altere uma configuração por vez. Trocar renderer, argumentos e controles ao mesmo tempo dificulta saber qual mudança resolveu o problema. Um perfil não supre automaticamente APIs ou componentes ausentes do runtime.

## 4. Argumentos de lançamento

### Resolução e tela

Em **Jogo → Resolução do desktop virtual**, `auto` consulta a resolução informada
pelo VideoOut ao iniciar o título. Se a consulta falhar ou retornar dados inválidos,
usa 1920×1080. O limite desta versão é 3840×2160. Você também pode escolher ou
digitar um tamanho, por exemplo `1920x1080` ou `2560x1440`.

Esse valor define o desktop e o teto de modos anunciado ao jogo. O jogo continua
responsável por sua resolução de renderização e pode selecionar modos menores
no próprio menu, quando sua engine oferece essa opção. Uma tela 4K não obriga o
jogo a renderizar em 4K: reduza a resolução no jogo se precisar de desempenho.
O backend gráfico apresenta a imagem na saída suportada pelo console, preservando
a proporção com `scaling=fit`. O apresentador de GDI continua usando saída 1080p.

`display.desktop` nas opções avançadas tem prioridade sobre o campo da interface;
remova esse override para usar `auto`. Argumentos como `-screen-width` e
`-screen-height`, ou configurações salvas pelo próprio jogo, também podem manter
uma resolução específica. A receita de Breath conserva os argumentos 720p já
testados; retire-os ao testar a seleção pelo menu. A detecção ocorre na abertura:
reabra o título depois de trocar a TV ou a configuração de saída do PS5.

Em projetos JSON, o campo é `"display_resolution": "auto"`. Projetos anteriores
sem esse campo também usam `auto`; overrides avançados existentes são preservados.
As trocas de resolução dependem da engine e do renderer e precisam ser validadas
em cada jogo. Isso não adiciona HDR nem altera a frequência de atualização.

A detecção automática e a troca 4K → 1080p → 720p → 4K foram validadas no port
de Intravenous 2: Mercenarism, em OpenGL/Zink x64 no firmware 13.60, incluindo
a seleção do mesmo adaptador. O runtime corrigido libera a referência de
apresentação retida pelo contexto antes de recriar a janela. A compatibilidade
e os ajustes específicos de cada jogo continuam exigindo validação própria.

Use argumentos que o próprio jogo reconheça. Para um jogo Unity que aceite esses parâmetros, por exemplo:

```text
-force-d3d11 -screen-width 1280 -screen-height 720 -screen-fullscreen 0
```

Esse exemplo não deve ser aplicado indiscriminadamente a outras engines. Se não houver um argumento necessário conhecido, comece com o campo vazio.

## 5. Ajustar os controles

O perfil XInput é o primeiro caminho quando o jogo já aceita controle. Nos perfis de teclado, o mapeamento inicial usa X como Enter, Círculo como Escape, Quadrado como Shift, Triângulo como X e direcionais como setas.

Em **Avançado → Opções do perfil**, é possível substituir teclas por botão. Exemplo:

```json
{
  "input": {
    "mode": "keyboard",
    "cross": "enter",
    "circle": "escape",
    "square": "shift",
    "triangle": "x",
    "l1": "pageup",
    "r1": "pagedown"
  }
}
```

Essas opções não mudam o atalho de encerramento **Options + clique do touchpad**. Teste ações no menu e durante o jogo: o mesmo botão pode ter funções diferentes entre essas telas.

As opções avançadas aceitam as seções `display`, `input`, `runtime`, `debug` e `application.dll_overrides`. Os nomes e valores dependem do parser do runtime; prefira os valores já usados pelos perfis até identificar uma necessidade específica.

## 6. Personalizar a apresentação

- **Ícone:** escolha uma imagem; o programa prepara PNG 512×512 com corte central.
- **Fundos:** imagens comuns são convertidas para DDS BC7 3840×2160. Ao selecionar só um fundo, ele é usado nas duas telas.
- **Música de seleção:** escolha um áudio e ajuste início/duração na aba Áudio. Essa música toca na apresentação do título, não substitui a trilha dentro do jogo.

O encoder ATRAC9 acompanha o kit. MP3/WAV/OGG/FLAC/M4A/AAC e outros formatos usam o FFmpeg opcional instalado pelo script indicado no guia rápido. O trecho padrão é de 15 segundos; o máximo é 87,3 segundos. Um `.at9` pronto é copiado integralmente, sem aplicar o recorte.

Você pode deixar fundos e música vazios para simplificar a primeira build.

## 7. Fazer o primeiro teste sem conquistas

Use o adaptador `none`, sem itens na lista. Clique em **Validar projeto** e depois em **Compilar e empacotar**.

Após copiar a pasta completa para o console, confira nesta ordem:

1. A preparação inicial termina e o jogo chega ao menu.
2. Textos e imagens aparecem.
3. Áudio e controle funcionam.
4. Uma partida pode ser iniciada e um save pode ser carregado após reabrir.
5. Encerramento e nova abertura funcionam.

Quando isso estiver estável, configure o catálogo e o adaptador de [conquistas](ACHIEVEMENTS.md). Assim, uma falha de inicialização não fica misturada a uma falha de integração.

## 8. Ajustar e recompilar

Salve o `.ps5port.json` para reutilizar a configuração. O programa gera uma pasta nova para cada build pela interface. Os argumentos e scripts próprios da ponte são sincronizados na abertura do título.

Uma build atualizada não substitui automaticamente todos os dados já preparados no console. Se você trocar os arquivos do jogo, o registry ou overlays, teste com outro Title ID ou planeje a atualização do prefixo. Isso é especialmente relevante ao trocar a versão do jogo; uma alteração só de argumento não exige esse procedimento.

## Problemas comuns

| Sintoma | O que conferir primeiro |
|---|---|
| Build não começa | Caminho da pasta, `.exe` selecionado, ícone e resultado de Diagnóstico. |
| Retorna imediatamente ao loader | Executável principal, DLLs/dados completos e log de inicialização. |
| Fica em loading no NW.js | Se o jogo oferece Canvas, perfil escolhido, fontes e log da engine. |
| Funciona no menu, mas não durante a partida | Mapeamento de teclado/XInput e opções de controle do próprio jogo. |
| Tela preta ou erro de renderer | API gráfica usada pelo jogo e perfil escolhido; nem toda dependência é suportada. |
| Apresentação tem som, jogo não | A música de seleção é independente do áudio da engine; confira o log do runtime. |
| Lista de conquistas aparece, mas não desbloqueia | O catálogo chegou ao backend; falta conferir o evento real e o adaptador. |

O `build.log` registra a compilação. Logs de inicialização, do runtime e da própria engine ajudam a localizar falhas depois do lançamento. Ao comparar testes, anote o perfil, os argumentos e a versão do jogo usados.

## Pela linha de comando

Salve o projeto na interface ou adapte `port_station/examples/windows-game.ps5port.json`. A partir da pasta do kit:

```powershell
python -m port_station doctor
python -m port_station validate "D:/Projetos/MeuJogo.ps5port.json"
python -m port_station prepare "D:/Projetos/MeuJogo.ps5port.json" --output "D:/Builds/MeuJogo-revisao"
python -m port_station build "D:/Projetos/MeuJogo.ps5port.json" --output "D:/Builds/MeuJogo-build"
```

`prepare` gera configurações e recursos para revisão, sem compilar o título. `build` produz a pasta completa e seu ZIP; `--no-zip` mantém só a pasta. Os destinos da CLI precisam ser novos, pois a ferramenta não sobrescreve builds existentes.
