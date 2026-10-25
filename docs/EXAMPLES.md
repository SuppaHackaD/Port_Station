# Configurações testadas

Os exemplos mostram duas integrações funcionais com perfis diferentes. Para configurar outro jogo, siga [Novo jogo](NEW_GAME.md); não é necessário adaptar uma dessas receitas.

As imagens incluídas são placeholders próprios. A música de seleção fica desativada por padrão.

## Breath

Receita: `port_station/examples/breath.ps5port.json`.

- Base testada: Breath 1.0.3, Unity 2019.
- Perfil: `dxvk-xinput`, Direct3D 11 e janela 1280×720.
- Conquistas: 11 originais e platina opcional.

Prepare a cópia local com:

```powershell
python release_support/prepare-game.py breath --source "D:/Jogos/Breath" --output "D:/Preparados/Breath"
```

O preparador acrescenta a ponte própria e adapta duas rotinas de conquistas em uma cópia. Ele reconhece o assembly original pelo SHA-256 `b98be2ab162e9f7f2ff4029b0bf8221db075df052d5782b96c73424c6ee95f18`; outra versão é rejeitada em vez de receber uma alteração incorreta.

Abra a receita e selecione a pasta preparada. Ícone, fundos, título e música podem ser personalizados como em qualquer projeto.

Para testar uma instalação separada, escolha outro Title ID. Se quiser também uma lista de conquistas independente no backend, escolha outra ID estável do jogo, por exemplo `breathy`. O adaptador aceita essa personalização e continua usando as 11 IDs originais das conquistas, que correspondem aos eventos emitidos pelo jogo.

## The Coffin of Andy and Leyley — TCOAAL

Receita: `port_station/examples/tcoaal.ps5port.json`.

- Base testada: jogo 3.0.13, NW.js 0.29/RPG Maker.
- Perfil: `nwjs-canvas`.
- Conquistas: 20 originais e platina opcional.

```powershell
python release_support/prepare-game.py tcoaal --source "D:/Jogos/The Coffin of Andy and Leyley" --output "D:/Preparados/TCOAAL"
```

O preparador complementa escolhas ausentes de traduções locais quando encontra o catálogo nativo compatível. Depois, na build, o perfil registra fontes locais e aplica o fallback CSS. A ponte relaciona as APIs de conquistas observadas às IDs do catálogo.

Abra a receita e selecione a pasta preparada. O perfil já acrescenta `canvas` como primeiro argumento.

A chave interna `tcoal` é mantida para que o progresso e os dados de instalações anteriores continuem sendo reconhecidos; o nome do exemplo é TCOAAL.

## Atualizações dos jogos

Essas receitas descrevem as versões acima. Uma atualização de engine, dos arquivos de dados ou das APIs de conquistas pode exigir outra configuração. Você pode salvar uma cópia do projeto para testar ajustes sem alterar sua configuração anterior.

As receitas usam uma revisão de catálogo própria para as imagens incluídas. Ao trocar imagens ou textos depois de já sincronizar a lista, incremente a versão do catálogo.
