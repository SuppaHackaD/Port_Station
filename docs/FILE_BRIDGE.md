# Ponte de arquivos — Node/NW.js e Windows/LuaJIT

[Documentação](INDEX.md) · [Início](../README.pt-BR.md)

Complemento do SDK C 0.1.1. Compile `pa_file_bridge.c` no adaptador nativo e
vincule a biblioteca do SDK. Carregue `prospero_file_bridge.js` no Node/NW.js.
O trabalhador C cria um contexto com a ID do jogo e o usuário ativo e consome
o stream de origem por usuário, com acréscimos ao final. Prepare SDK/catálogo
antes de chamar o poll; execute-o apenas no trabalhador.

O jogo fornece uma lista explícita de IDs permitidas. Uma concessão original
chama `publisher.unlock(id)`; não há heurística de save nem necessidade de
login Steam. Esse transporte somente de unlock reserva a própria ID da conquista
como ID estável do evento no namespace jogo/usuário. Não reutilize essas IDs
para outros eventos do SDK. IDs de até 64 caracteres são aceitas. O stream
retido permite recuperar eventos após reiniciar; o outbox do SDK continua
sendo a fila de entrega pela rede.

O publicador sincroniza cada acréscimo de evento, repete gravações malsucedidas
ao chamar `flush` e inicia registros com uma quebra de linha para isolar
escritas incompletas. O consumidor valida registros canônicos, jogo/usuário/ID,
linhas incompletas e longas demais; só avança após a aceitação durável pelo
SDK. Entrada duplicada e reenvio são idempotentes. O loop JavaScript não faz
HTTP; o adaptador nativo executa rede no próprio trabalhador. Cada contexto e
stream tem um único escritor/trabalhador.

Registros ASCII com LF:

```text
PA_FILE_CONTEXT_V1\tgame\tuser
PA_FILE_BRIDGE_V1\tgame\tuser
PA_FILE_UNLOCK_V1\tgame\tuser\tachievement
```

Os separadores são TABs reais. O contexto é `game-context-v1.txt` e o stream é
`game-user.tsv`, em `drive_c/ProsperoAchievements` do prefixo. TCOAAL fornece
o primeiro exemplo completo. O módulo não registra troféus Sony nem importa
históricos de outras contas.

## Publicador Windows

`pa_windows_events.c` gera a DLL própria x64 `paevents.dll`. Exporta funções cdecl:

```c
int pa_event_ready_v1(const char *folder, const char *game);
int pa_event_unlock_v1(const char *folder, const char *game, const char *id);
```

Use `C:/ProsperoAchievements` dentro do Wine, com o mesmo namespace do adaptador
nativo. Ambas vinculam o usuário ativo a partir do contexto canônico. Somente
uma solicitação real de conquista deve chamar unlock; ready não concede nada.

Zero indica que o acréscimo foi sincronizado e o handle fechado com sucesso.
Retornos negativos: argumento inválido (-1), contexto ausente (-2), contexto
malformado (-3), falha de abertura (-4), posicionamento/escrita (-5), sincronização
(-6) ou fechamento (-7). Mantenha eventos malsucedidos pendentes e tente novamente.
O publicador abre com `GENERIC_WRITE` para permitir `FlushFileBuffers`, aceita
leitores nativos e mantém um único escritor Windows. Diagnósticos ficam em
`<game>-bridge.log` na mesma pasta própria. A thread Lua não executa HTTP.

`port_station/templates/love_achievements.lua` oferece mapeamento/lista permitida,
deduplicação no processo e repetição de chamadas reais a `SetAchievement`.
A função original é executada primeiro; argumentos, resultados e erros são
preservados. `port_station/love_achievements.py` aplica o adaptador somente ao
módulo verificado em uma cópia local da build, preservando o original. Não
contém nem distribui scripts comerciais. Um catálogo sozinho não é um produtor universal.
