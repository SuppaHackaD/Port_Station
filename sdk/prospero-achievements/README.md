# Prospero Achievements SDK 0.1.2

Cliente C/C++ para o payload `prospero_achievements.elf`, API HTTP v1, sem APIs de troféus Sony. Continuidade no PS5 e integrações Breath/TCOAAL foram confirmadas em testes manuais; ver README raiz para o escopo.

O jogo fornece catálogo, ícones e eventos. O payload persiste progresso por usuário/jogo e serve uma interface web embutida. A biblioteca estática e o header público permitem integrar um port sem incluir o servidor. A homebrew de exemplo vincula exatamente essa biblioteca.

A revisão 0.1.1 mantém o protocolo v1 e funciona com o backend 0.1.0. Adiciona leitura alternativa de diretórios via getdents de 64 KiB no PS5 e diagnóstico da fila em last_stage/last_errno/directory_method (1: readdir; 2: getdents). Estes campos descrevem operações de fila, não todos os erros de rede. Recompile os clientes com o header e o arquivo .a da mesma revisão: o tamanho de PA_SDK mudou. A correção ainda depende de confirmação no console.

A revisão 0.1.2 acrescenta pa_sdk_pump_with_callback sem alterar PA_SDK. O callback recebe somente IDs recém-desbloqueados em uma confirmação aceita com o event_id correto; replay/duplicate não repetem o aviso. Executa no trabalhador do adaptador e não deve reentrar o SDK. O port decide como apresentar o popup. O backend permanece 0.1.0/API1. Se uma resposta se perder, a conquista permanece no backend mesmo que o aviso não seja exibido. A correção de diretórios 0.1.1 já foi confirmada no console.

## Uso

Um trabalhador do port é responsável pelo contexto PA_SDK. Execute suas chamadas nesse trabalhador, fora do loop de renderização: preparação/enqueue fazem I/O durável e pump faz rede. O SDK v0.1 não cria threads implicitamente. Não compartilhe um contexto/outbox entre trabalhadores ou processos concorrentes.

~~~c
#include <prospero_achievements.h>
PA_SDK sdk;
/* Caminho gravável pela homebrew e ID do usuário local ativo. */
pa_sdk_init(&sdk, "/data/meu-port/achievements-outbox",
            "meu.jogo", "0000002a", PA_SDK_DEFAULT_PORT);
char hash[65];
pa_sdk_asset(&sdk, png_bytes, png_size, hash);
pa_sdk_catalog(&sdk, catalog_json, catalog_size);
pa_sdk_unlock(&sdk, "FIRST_CAPTURE", "session001-event0001");
pa_sdk_progress(&sdk, "COLLECT_10", 3, "session001-event0002");
/* Periodicamente, no trabalhador, com intervalo/backoff do port. */
int acknowledged = pa_sdk_pump(&sdk);
~~~

Verifique todos os retornos. Enqueue bem-sucedido significa que o arquivo local foi persistido, não que o servidor o recebeu. Pump só remove o evento depois de accepted/duplicate com o event_id correto. Se o payload estiver ausente, a fila permanece. Um reinício do servidor dispara nova sincronização do catálogo/imagens. A preparação também pode ocorrer offline.

Forneça event_id único por usuário/jogo, estável nos reenvios. Use identidade persistente da instalação/sessão e contador persistente, ou identidade e posição de uma fila de origem. Não gere outro ID a cada tentativa. IDs de jogos/conquistas são independentes do Title ID PS5 e da posição na interface.

## Build e link

~~~powershell
python scripts/build-prospero-achievements.py --ps5
python scripts/test-prospero-achievements.py
~~~

Saídas em build/prospero-achievements/ps5: prospero_achievements.elf e libprospero_achievements.a. Header público: sdk/prospero-achievements/include/prospero_achievements.h.

Vincule com o toolchain PS5 do projeto e as bibliotecas usuais libc/kernel/SceNet. examples/CMakeLists.txt mostra a ligação em homebrew nativa. O SDK público v0.44 é o mesmo utilizado pelos ports.

cJSON 1.7.19 (MIT) e SHA-256 de Brad Conte (domínio público) estão incluídos com símbolos privados renomeados para evitar colisões com os jogos. Fontes, licenças e alterações: src/prospero_achievements/vendor. Contrato: docs/PROTOCOL.md.

## Limites desta versão

- Um escritor por pasta do serviço; um trabalhador por contexto/outbox.
- Até 256 conquistas por catálogo, JSON até 128 KiB.
- PNG até 512 KiB e 1024×1024, identificado por SHA-256.
- Até 4096 eventos por usuário/jogo; ainda sem compactação. Agregue progresso em marcos, nunca por frame.
- Usuário fornecido pelo adaptador. Não consulta contas Sony nem autentica conquistas de jogos de terceiros.
- Escrita por loopback, sem Origin; interface LAN de consulta.
- Adaptadores Breath/TCOAAL e popup de confirmação no port são incluídos. Autoload do payload e migração genérica de condições ainda não são implementados.
- Sincronização depende de operações do filesystem retornarem sucesso. Falha real de energia no PS5 não foi ensaiada.
