# Port Station

Crie pacotes homebrew PS5 a partir dos seus arquivos de jogos Windows usando
Wine e [prospero-win](https://github.com/mpereiraesaa/prospero-win). Configure
gráficos, controles, apresentação e conquistas pela interface Python ou CLI.

**[Baixar o kit Windows](https://github.com/SuppaHackaD/Port_Station/releases/latest)**
· [English](README.md) · [Guia rápido](docs/QUICKSTART.md)
· [Configurar outro jogo](docs/NEW_GAME.md)

A primeira versão pública é a **0.4.0**. Port Station é uma ferramenta de
compatibilidade e empacotamento; não recompila automaticamente a engine para
PS5. O suporte é experimental e depende das APIs e do renderer de cada jogo.

## Começar

1. Instale **Python 3.13 x64 com Tcl/Tk** no Windows.
2. Extraia `Port_Station-0.4.0-windows-kit.zip` da release. Ele inclui runtime,
   compiladores públicos, SDK e ferramentas de recursos. O download de fontes
   sozinho é destinado ao desenvolvimento.
3. Abra **Port_Station.cmd**, crie um projeto e selecione a pasta completa do
   jogo e seu executável principal.
4. Escolha o perfil e um Title ID livre no formato `PPSA` + cinco números.
   Comece com conquistas desativadas para testar a compatibilidade básica.
5. Compile em uma pasta nova e copie a pasta completa
   `<build>/native/dist/<TITLE_ID>/` para `/data/homebrew/` no console.
   Atualize a lista do loader.

A primeira abertura prepara os dados graváveis e pode demorar mais. Segure
**Options + clique do touchpad** por um segundo para sair ou use o menu do
botão PS no ambiente compatível.

O ambiente testado é PS5 **13.60**, Relapse, PLDMGR 0.6.1 e ShadowMount+. O
console precisa estar preparado para executar homebrews. O projeto não fornece
desbloqueio ou SDK proprietário Sony.

## Recursos

- Interface Python/Tk e CLI com o mesmo processo de build.
- Perfis Direct3D/DXVK e OpenGL/Mesa-Zink com XInput, NW.js/Canvas e GDI/teclado.
- Desktop virtual automático ou configurável até 4K, com seleção de modos pelo
  jogo quando suportada.
- Título, ícone, fundos e música opcionais, com conversão local PNG/BC7/ATRAC9.
- Extrator integrado, cruzamento exato de IDs oficiais Steam, consulta de
  textos oficiais localizados e edição manual.
- Platina opcional e **Prospero Achievements**, backend independente e
  persistente com interface web.
- Projetos `.ps5port.json`, logs e hashes de dependências.

Para converter MP3 e outros formatos, instale o FFmpeg opcional na pasta do kit
com `python release_support/install-ffmpeg.py`. Música não é necessária para
gerar uma build.

## Arquitetura e conquistas

O frontend valida o projeto, prepara os arquivos na cópia de saída, compila um
launcher específico e reúne o runtime Wine com os dados fornecidos pelo usuário.
A instalação original do PC é preservada. No console, cada título prepara seus
dados graváveis e saves em um diretório próprio.

O extrator fornece definições. Para obter conquistas, um adaptador precisa
acompanhar as chamadas reais do jogo e entregá-las ao SDK nativo. O SDK mantém
uma fila persistente, envia os eventos ao backend e apresenta o popup após a
confirmação. O backend separa o progresso por jogo e usuário e calcula a platina.
Essas conquistas são locais; não aparecem como troféus Sony nem sincronizam com PSN.

As receitas de [Breath](port_station/examples/breath.ps5port.json) e
[TCOAAL](port_station/examples/tcoaal.ps5port.json) são exemplos, não requisitos
da ferramenta. Kindergarten foi testado com a ponte Unity Mono e Intravenous
2: Mercenarism 1.7.1 com OpenGL/XInput e a ponte LÖVE verificada. Os testes
cobrem trechos e funções específicas, sem garantir campanhas completas ou
outras revisões. As imagens incluídas são placeholders próprios, sem música.

## Guias

- [Instalar e fazer a primeira build](docs/QUICKSTART.md)
- [Configurar e testar um novo jogo](docs/NEW_GAME.md)
- [Conquistas, extrator e backend](docs/ACHIEVEMENTS.md)
- [Versões dos exemplos](docs/EXAMPLES.md)
- [Compilar o projeto](docs/BUILDING.md)
- [Arquitetura e integração](docs/INTEGRATION.md)
- [Contribuir](CONTRIBUTING.md)
- [Novidades](docs/RELEASE_NOTES.md)
- [Créditos e licenças](THIRD_PARTY.md)

A release inclui fontes completos, ferramentas compiladas, backend/SDK e
snapshots upstream fixados. O extrator também pode ser aberto separadamente por
`achievement_extractor/Achievement_Extractor.cmd`.

## Licença e jogos

O projeto usa prospero-win, Wine, SDK ps5-payload-dev, PS5_Mesa/Mesa-Zink,
PS5_Vulkan, DXVK, PS5 Native App Boilerplate, Lapy JB Daemon,
ps5-forwarder-manager, PS5_ArtSwap e os componentes creditados em
[THIRD_PARTY.md](THIRD_PARTY.md). O código próprio é **GPL-3.0-or-later**, salvo
licenças individuais explícitas; os componentes mantêm suas próprias licenças.

Port Station é independente e não tem vínculo com Sony, Valve ou os
desenvolvedores dos jogos. **Não distribuímos jogos, binários comerciais, arte
oficial ou trilhas sonoras.** Use sua própria cópia adquirida e apoie os autores:
[Breath, de Herbherth](https://store.steampowered.com/app/1475350/) e
[TCOAAL, de Kit9 Studio](https://store.steampowered.com/app/2378900/).
