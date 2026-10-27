# Sua primeira build

[Documentação](INDEX.md) · [Início](../README.pt-BR.md)

## Instalar

No Windows x64, instale Python 3.13 com a opção **Tcl/Tk** e extraia o **Windows kit** disponível nas [releases](https://github.com/SuppaHackaD/Port_Station/releases/latest). Abra `Port_Station.cmd`.

Use o Windows kit para compilar jogos. O arquivo de código-fonte do GitHub é destinado a quem vai desenvolver a ferramenta e não leva os binários do runtime.

Para adicionar uma música de seleção, instale o decodificador opcional uma vez, a partir da pasta do kit:

```powershell
python release_support/install-ffmpeg.py
```

Sem música, essa etapa não é necessária.

## Criar o projeto

1. Clique em **Novo**.
2. Em **Jogo**, selecione a pasta completa da instalação e seu executável principal. O `.exe` deve ficar dentro dessa pasta.
3. Preencha o título e escolha um **Title ID** livre no console, no formato `PPSA` seguido de cinco números. Defina também uma ID estável para as conquistas, por exemplo `meu.jogo`.
4. Escolha o perfil inicial: `dxvk-xinput` para jogos Direct3D com controle, `opengl-xinput` para OpenGL/Mesa-Zink, `nwjs-canvas` para jogos NW.js que ofereçam Canvas, ou `gdi-keyboard` para aplicações GDI/teclado.
5. Em **Apresentação**, selecione um ícone. Fundos e música são opcionais.
6. Em **Conquistas**, mantenha o adaptador `none` neste primeiro teste.
7. Salve o projeto como `.ps5port.json`.

Na aba **Jogo**, deixe a resolução em `auto` para usar o tamanho informado pelo
console, ou escolha o teto do desktop virtual. O jogo pode selecionar modos
menores pelo seu próprio menu. Veja [resolução e tela](NEW_GAME.md#resolução-e-tela)
para os limites e a prioridade de argumentos e opções avançadas.

Você também pode abrir `port_station/examples/windows-game.ps5port.json`, que já traz imagens genéricas. Troque a pasta e o executável pelos do seu jogo.

## Compilar

Abra **Build e diagnóstico**. Use **Diagnóstico** para conferir as ferramentas e **Validar projeto** para conferir a configuração. Clique em **Compilar e empacotar** e escolha uma pasta de saída. O programa cria uma subpasta para a build e mostra o andamento no log.

Ao terminar, a pasta de homebrew fica em:

```text
<SUA_BUILD>/native/dist/<TITLE_ID>/
```

Ela contém `eboot.bin`, módulos, runtime e os arquivos necessários para a primeira abertura.

## Executar no console

Copie a pasta completa `<TITLE_ID>` para `/data/homebrew/` e atualize a lista do seu loader. No ambiente testado, o lançamento é feito pelo ShadowMount+.

A primeira abertura prepara os dados graváveis do jogo e pode demorar mais. Aguarde a preparação. As aberturas seguintes aproveitam os dados já preparados.

Teste menu, texto, áudio, controles e save. Segure **Options + clique do touchpad** por um segundo para encerrar pelo runtime. Confira também o fechamento pelo botão PS e uma nova abertura.

Se o jogo não iniciar ou algum recurso falhar, siga [Configurar outro jogo](NEW_GAME.md). Quando o funcionamento básico estiver bom, adicione a integração de [conquistas](ACHIEVEMENTS.md).
