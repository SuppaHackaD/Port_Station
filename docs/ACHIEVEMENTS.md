# Prospero Achievements

O pacote separado contém o payload compilado, SDK0.1.2, fontes C do servidor/cliente, ponte por arquivo e a web. Para recompilar, use as ferramentas públicas do kit Port Station e os comandos em BUILDING.md; compiladores não são duplicados no pacote menor.

1. Copie `build/prospero-achievements/ps5/prospero_achievements.elf` para o diretório de payloads aceito pelo seu loader e carregue-o uma vez.
2. Abra `http://IP_DO_CONSOLE:38765/` no navegador da mesma LAN. O serviço permanece independente do jogo.
3. Abra um título integrado. O cliente registra imagens e catálogo e envia eventos reais quando as condições do jogo ocorrem. Escolha o usuário local na web.
4. Para manutenção, feche os jogos clientes antes de carregar `pa_stop.elf`. Reiniciar o serviço conserva os journals em `/data/prospero-achievements`.

Não execute duas instâncias sobre a mesma pasta. Não compartilhe uma outbox entre processos concorrentes. A UI é de consulta; nenhuma tela web concede conquistas ou apaga progresso. A persistência/deduplicação é local, não é autenticação de uma conta de plataforma.

`pa_sdk_probe.elf` é somente um teste de transporte com catálogo próprio, não concede itens dos jogos. Logs essenciais persistem em disco. Nunca publique journals reais ou saves em um relatório de bug.

O payload não instala troféus Sony, não sincroniza com PSN e não altera o serviço de troféus do sistema. Os ícones dos exemplos públicos são placeholders. O título é responsável por fornecer dados, condições e a apresentação do popup após confirmação.
