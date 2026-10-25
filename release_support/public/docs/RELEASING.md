# Publicação

Suba somente a pasta `Port_Station/` como conteúdo do repositório GitHub. Ela contém fontes, receitas, placeholders, licenças e documentação. Não suba `_staging/`, `_sources/`, `local-games/` ou builds privadas. O relatório ao lado da pasta de deploy descreve o que foi incluído.

Anexe os arquivos de `releases/0.2.2/` à release GitHub correspondente: kit Windows compilado, payload/SDK, arquivos de fontes upstream e checksums SHA-256. Os binários grandes e compiladores não pertencem ao histórico Git. Publique as fontes e os avisos de licença junto com os binários; preserve também `SOURCES.json` e o manifesto de hashes da release.

O código completo próprio inclui frontend, geradores, bootstrap, pontes, servidor, web, SDK, ferramentas host e projetos do patcher. Fontes vendorizados mantêm seus avisos. `upstream-sources.zip` fornece snapshots dos componentes principais de runtime; `THIRD_PARTY.md` identifica os demais projetos/toolchains e os arquivos de licença presentes no kit.

Para reproduzir o staging a partir de um workspace de desenvolvimento com kit instalado, consulte `release_support/stage-deploy.py`. Ele usa uma allowlist; não copia a raiz inteira. `release_support/fetch-sources.py --lock SOURCES.json <pasta>` verifica downloads pelos hashes fixados. `release_support/archive-release.py <pasta-deploy>` produz os ZIPs/manifesta e verifica CRC/SHA.

Antes de publicar uma atualização: execute testes Python/JS/backend, compile um título de diagnóstico, confira o manifesto contra o arquivo ZIP e procure dados pessoais/arquivos de jogos. Validação host não substitui teste no console. Não marque todas as conquistas/campanha como validadas por causa de uma conquista testada.

Não há upload, criação de repositório, push, login GitHub ou execução de payload disparados por esses scripts. Escolha nome/licença das suas contribuições respeitando as licenças herdadas. A licença raiz GPL-3.0-or-later aplica-se ao código próprio e à combinação distribuída; não substitui licenças permissivas/LGPL dos componentes individuais nem licencia jogos.
