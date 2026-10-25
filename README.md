# Port Station

Crie uma homebrew PS5 a partir de um jogo Windows usando Wine/prospero-win. Escolha o executável, configure a compatibilidade e os controles, personalize a apresentação e compile pelo aplicativo ou pela linha de comando.

[Baixar o kit Windows](https://github.com/SuppaHackaD/Port_Station/releases/latest) · [Começar a usar](docs/QUICKSTART.md) · [Configurar outro jogo](docs/NEW_GAME.md)

## Começar

1. Instale **Python 3.13 x64 com Tcl/Tk** no Windows.
2. Baixe e extraia o **Windows kit** da release. Ele inclui o runtime, os compiladores públicos, o SDK e as ferramentas de imagem e ATRAC9.
3. Abra **Port_Station.cmd**, escolha **Novo** e selecione a pasta completa do jogo e seu `.exe` principal.
4. Escolha um perfil de compatibilidade, um ícone e uma pasta de saída. Para o primeiro teste, deixe as conquistas desativadas.
5. Clique em **Compilar e empacotar** e copie a pasta resultante para o console.

O [guia rápido](docs/QUICKSTART.md) acompanha a primeira build. O [guia para novos jogos](docs/NEW_GAME.md) explica cada configuração, como testar perfis e como resolver os problemas mais comuns. Há também um [modelo genérico](port_station/examples/windows-game.ps5port.json) para começar pela CLI.

## O que a ferramenta oferece

- Interface Python/Tk e CLI usando o mesmo processo de build.
- Perfis iniciais para Direct3D/DXVK com XInput, NW.js com Canvas e aplicações GDI com teclado.
- Mapeamento de botões e argumentos de lançamento editáveis.
- Ícone, fundos e música de seleção personalizáveis; conversão local de imagens para PNG/BC7 e de áudio para ATRAC9.
- Catálogos de conquistas, platina opcional e integração com **Prospero Achievements**, um backend independente com interface web.
- Projetos `.ps5port.json` reutilizáveis e logs de compilação.

Port Station empacota o jogo com uma camada de compatibilidade. Não recompila automaticamente a engine para PS5 e não garante que todo jogo Windows funcione. Alguns jogos precisam de ajustes ou componentes que o runtime atual não oferece.

A base foi exercitada em PS5 **13.60**, com Relapse, PLDMGR 0.6.1 e ShadowMount+. O console precisa estar preparado para executar homebrews; o kit não fornece desbloqueio ou SDK proprietário.

## Conquistas

O jogo informa os eventos e o backend mantém o progresso e apresenta a lista na web. A platina pode ser calculada quando todas as conquistas regulares forem obtidas.

O editor cria o catálogo; as condições de desbloqueio precisam chegar por um adaptador compatível ou por integração com o jogo. Comece pelo [guia de conquistas](docs/ACHIEVEMENTS.md). Para desenvolver um adaptador, consulte [Integração](docs/INTEGRATION.md).

São conquistas próprias, sem registro na lista de troféus Sony ou sincronização com PSN.

## Exemplos testados

As receitas de **Breath** e **The Coffin of Andy and Leyley (TCOAAL)** são pontos de partida prontos para essas versões dos jogos. A ferramenta também aceita projetos novos, sem depender delas.

| Exemplo | Configuração incluída |
|---|---|
| [Breath](port_station/examples/breath.ps5port.json) | DXVK/XInput, ponte de conquistas e platina opcional |
| [TCOAAL](port_station/examples/tcoaal.ps5port.json) | NW.js/Canvas, fontes locais, ponte de conquistas e platina opcional |

As receitas usam placeholders próprios e não incluem música. Veja [Exemplos](docs/EXAMPLES.md) para preparar uma cópia local compatível.

## Documentação

- [Guia rápido](docs/QUICKSTART.md)
- [Configurar e testar um novo jogo](docs/NEW_GAME.md)
- [Conquistas e backend](docs/ACHIEVEMENTS.md)
- [Exemplos Breath e TCOAAL](docs/EXAMPLES.md)
- [Compilar o projeto e suas ferramentas](docs/BUILDING.md)
- [Arquitetura e integração de adaptadores](docs/INTEGRATION.md)
- [Contribuir](CONTRIBUTING.md)
- [Créditos e licenças](THIRD_PARTY.md)

## Licença e jogos

Port Station é um projeto independente, sem vínculo com Sony, Valve ou com os desenvolvedores dos jogos utilizados nos exemplos. Não inclui jogos, arte oficial ou trilhas sonoras. Use sua própria cópia e apoie os criadores: [Breath, de Herbherth](https://store.steampowered.com/app/1475350/) e [TCOAAL, de Kit9 Studio](https://store.steampowered.com/app/2378900/).

O código próprio é GPL-3.0-or-later. Wine, runtime, SDK e bibliotecas mantêm suas licenças e créditos em [LICENSE](LICENSE), [NOTICE](NOTICE.md) e [THIRD_PARTY](THIRD_PARTY.md).
