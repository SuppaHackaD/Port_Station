# Conquistas e interface web

Prospero Achievements é um payload independente que recebe catálogos e eventos dos jogos. Ele mantém o progresso por usuário e oferece uma interface web para consultar as listas. O jogo integrado apresenta um popup após a confirmação de um desbloqueio.

## Ativar o backend

1. Copie `build/prospero-achievements/ps5/prospero_achievements.elf` do kit para o local de payloads do seu loader.
2. Carregue o payload uma vez.
3. Abra `http://IP_DO_CONSOLE:38765/` em um navegador da mesma rede.
4. Inicie um jogo integrado e selecione o usuário na página.

O serviço continua independente do jogo. Se estiver indisponível, o cliente guarda eventos pendentes e tenta enviá-los depois. `pa_stop.elf` é usado para encerrar o serviço quando necessário; não é uma dependência a carregar junto dele.

## Extrair conquistas do jogo

Na aba **Conquistas**, clique em **Extrair do jogo…**. A janela usa a pasta e o executável configurados no projeto. Clique em **Analisar arquivos**, informe o AppID correto e use **Buscar textos oficiais**. Revise os itens e clique em **Aplicar ao projeto**; a lista e o relatório também ficam na pasta de saída escolhida.

**Somente oficiais** exige igualdade exata entre uma ID local e uma ID retornada pela Steam. A consulta malsucedida bloqueia a exportação nesse modo. Você pode editar/traduzir nomes e descrições sem alterar as IDs. A platina continua sendo uma opção separada no projeto.

O leitor suporta catálogos JSON/VDF, chamadas JavaScript conhecidas, metadados Unity Mono e constantes LuaJIT em pacotes LÖVE/ZIP, incluindo ZIP anexado ao executável. Constantes LuaJIT são evidências de presença da ID, não prova de que uma chamada de desbloqueio execute. O leitor não inicia o jogo nem executa o bytecode.

A extração é integrada à interface, mas o adaptador de eventos continua sendo escolhido separadamente. LÖVE/LuaJIT ainda requer uma ponte própria; `unity-mono-steam` atende somente à família Unity Mono compatível.

## Configurar o catálogo

Na aba **Conquistas**, adicione nome, descrição, ícone e uma ID para cada item. A ID canônica identifica a conquista no backend. **ID emitida pelo jogo** permite associar um nome diferente vindo da engine, por exemplo `first_win` a `FIRST_WIN`.

Marque a opção de platina para acrescentar um item calculado quando todas as conquistas regulares forem obtidas. O adaptador não deve tentar desbloquear a platina diretamente.

Uma lista extraída pode não ter descrições. Na conversão para o backend, esses campos recebem o texto de exibição “Descrição não fornecida”, pois o protocolo exige uma descrição não vazia. O projeto e o relatório da extração mantêm a ausência do texto original; você pode preencher os campos depois, sem inventar condições de desbloqueio.

Se você editar um catálogo já usado, aumente sua versão. Preserve as IDs das conquistas que devem conservar progresso. Importar um catálogo pela interface inicia uma revisão maior.

## Escolher o adaptador

| Adaptador | Uso |
|---|---|
| `none` | Jogar sem catálogo ou eventos de conquistas. |
| `nwjs-steam` | Jogos NW.js que usem `Steam.awardAchievement` ou `Steam.API.activateAchievement`. A ponte associa as IDs e conserva a chamada original. |
| `unity-mono-steam` | DLL genérica experimental para Unity Mono, com integrador conservador de wrappers Steamworks.NET. Veja [SDK gerenciado](../sdk/prospero-achievements/managed/README.md). |
| `file-v1` | Integração própria: o jogo publica eventos pelo protocolo da ponte de arquivos. |
| `breath` | Integração específica da receita de Breath. |

Uma lista pronta no editor não identifica sozinha quando o jogador cumpriu uma condição. Se o jogo não usa uma das APIs suportadas, ele precisa de integração. Isso também vale para jogos de outras engines que ofereçam conquistas em outra plataforma.

Com `file-v1`, o launcher envia o catálogo, mas espera que uma ponte própria do jogo produza os arquivos de eventos. O extrator integrado gera definições; ele não instala uma ponte arbitrária na engine. Se a lista aparece com todos os itens bloqueados, confirme primeiro se o jogo possui o produtor de eventos antes de repetir condições de conquista.

O caminho para adicionar um adaptador está em [Integração](INTEGRATION.md), com um exemplo do SDK. As receitas de Breath e TCOAAL já fornecem suas integrações.

## Testar um desbloqueio

Confirme primeiro que o catálogo aparece na web. Obtenha uma conquista durante a partida, confira o popup e atualize a página. Feche e reabra o jogo para verificar a persistência sem repetir o aviso.

Usar a mesma ID estável do jogo mantém a mesma entrada no backend entre builds. Usuários diferentes têm progresso separado.

Estas são conquistas próprias do Port Station/Prospero Achievements; não aparecem na lista oficial de troféus Sony e não sincronizam com PSN. A interface web é de consulta e deve ser usada na rede local.
