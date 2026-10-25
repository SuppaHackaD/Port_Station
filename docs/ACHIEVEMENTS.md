# Conquistas e interface web

Prospero Achievements é um payload independente que recebe catálogos e eventos dos jogos. Ele mantém o progresso por usuário e oferece uma interface web para consultar as listas. O jogo integrado apresenta um popup após a confirmação de um desbloqueio.

## Ativar o backend

1. Copie `build/prospero-achievements/ps5/prospero_achievements.elf` do kit para o local de payloads do seu loader.
2. Carregue o payload uma vez.
3. Abra `http://IP_DO_CONSOLE:38765/` em um navegador da mesma rede.
4. Inicie um jogo integrado e selecione o usuário na página.

O serviço continua independente do jogo. Se estiver indisponível, o cliente guarda eventos pendentes e tenta enviá-los depois. `pa_stop.elf` é usado para encerrar o serviço quando necessário; não é uma dependência a carregar junto dele.

## Configurar o catálogo

Na aba **Conquistas**, adicione nome, descrição, ícone e uma ID para cada item. A ID canônica identifica a conquista no backend. **ID emitida pelo jogo** permite associar um nome diferente vindo da engine, por exemplo `first_win` a `FIRST_WIN`.

Marque a opção de platina para acrescentar um item calculado quando todas as conquistas regulares forem obtidas. O adaptador não deve tentar desbloquear a platina diretamente.

Uma lista extraída pode não ter descrições. Na conversão para o backend, esses campos recebem o texto de exibição “Descrição não informada.”, pois o protocolo exige uma descrição não vazia. O projeto e o relatório da extração mantêm a ausência do texto original; você pode preencher os campos depois, sem inventar condições de desbloqueio.

Se você editar um catálogo já usado, aumente sua versão. Preserve as IDs das conquistas que devem conservar progresso. Importar um catálogo pela interface inicia uma revisão maior.

## Escolher o adaptador

| Adaptador | Uso |
|---|---|
| `none` | Jogar sem catálogo ou eventos de conquistas. |
| `nwjs-steam` | Jogos NW.js que usem `Steam.awardAchievement` ou `Steam.API.activateAchievement`. A ponte associa as IDs e conserva a chamada original. |
| `file-v1` | Integração própria: o jogo publica eventos pelo protocolo da ponte de arquivos. |
| `breath` | Integração específica da receita de Breath. |

Uma lista pronta no editor não identifica sozinha quando o jogador cumpriu uma condição. Se o jogo não usa uma das APIs suportadas, ele precisa de integração. Isso também vale para jogos de outras engines que ofereçam conquistas em outra plataforma.

Com `file-v1`, o launcher envia o catálogo, mas espera que uma ponte própria do jogo produza os arquivos de eventos. O extrator separado gera definições; ele não instala essa ponte. Se a lista aparece com todos os itens bloqueados, confirme primeiro se o jogo possui o produtor de eventos antes de repetir condições de conquista.

O caminho para adicionar um adaptador está em [Integração](INTEGRATION.md), com um exemplo do SDK. As receitas de Breath e TCOAAL já fornecem suas integrações.

## Testar um desbloqueio

Confirme primeiro que o catálogo aparece na web. Obtenha uma conquista durante a partida, confira o popup e atualize a página. Feche e reabra o jogo para verificar a persistência sem repetir o aviso.

Usar a mesma ID estável do jogo mantém a mesma entrada no backend entre builds. Usuários diferentes têm progresso separado.

Estas são conquistas próprias do Port Station/Prospero Achievements; não aparecem na lista oficial de troféus Sony e não sincronizam com PSN. A interface web é de consulta e deve ser usada na rede local.
