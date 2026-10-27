# API v1 — contrato 0.1.0

[Documentação](../../../docs/INDEX.md) · [Início](../../../README.pt-BR.md)

Porta TCP 38765. SDK usa 127.0.0.1; navegador usa IP LAN do console. HTTP/1.1 com Content-Length, uma requisição por conexão e JSON UTF-8. Escritas aceitas somente por loopback sem Origin. Não depende de Trophy2, NPWR ou bancos do sistema PS5.

## Registro

Primeiro envie cada PNG em `PUT /api/v1/assets/<sha256>.png`, corpo binário. Nome e conteúdo devem corresponder. Depois envie `POST /api/v1/catalogs`:

~~~json
{
  "schema": 1,
  "game_id": "meu.jogo",
  "title": "Meu jogo",
  "catalog_version": 1,
  "icon": "<64 caracteres SHA-256>",
  "achievements": [
    {"id":"FIRST","title":"Primeiro passo","description":"Concluir a primeira etapa.","target":1},
    {"id":"COLLECT","title":"Colecionador","description":"Encontrar dez itens.","target":10,"hidden":false},
    {"id":"ALL","title":"Conjunto completo","description":"Obter todas as outras conquistas.","target":1,"completion":true}
  ]
}
~~~

Cada conquista pode fornecer icon com outro SHA-256. Só uma completion é permitida; depende de todas as normais. Conclusão já obtida permanece caso outro catálogo acrescente conquistas.

IDs: ASCII alfanumérico, ponto, hífen e sublinhado, até 64 caracteres, começando por alfanumérico e sem "..". Game_id usa somente letras minúsculas para evitar colisões entre filesystems. Usuários: oito dígitos hexadecimais minúsculos. Títulos: até 256 bytes; descrições: até 2048; metas inteiras de 1 a 1.000.000.000.

Hidden oculta texto na apresentação enquanto bloqueada; não protege a confidencialidade do catálogo. Catálogo semanticamente igual retorna 200 unchanged. Alterações exigem catalog_version crescente. Pode acrescentar conquistas e mudar textos/imagens. Remover IDs, alterar metas ou regras existentes retorna 409 até haver migração explícita. Catálogo ilegível é preservado.

Um catálogo mais antigo, cujos IDs e condições continuam compatíveis, retorna 200 newer_catalog_active. O servidor mantém os metadados novos e aceita eventos do jogo antigo, sem rebaixar o catálogo.

## Eventos

`POST /api/v1/events`:

~~~json
{
  "event_id":"installation001-session003-event0004",
  "game_id":"meu.jogo",
  "user_id":"0000002a",
  "achievement_id":"COLLECT",
  "type":"progress",
  "value":3
}
~~~

Type: progress ou unlock. Progress é um acumulado absoluto, não incremento; nunca regride e é limitado à meta. Unlock marca a meta atingida, sem exigir value. Não envie unlock diretamente para completion.

O backend normaliza campos relevantes, identifica por usuário/jogo/event_id, registra o horário de recebimento e inclui conclusões na mesma transação. Confirma após sincronizar a escrita. Repetição com conteúdo igual retorna duplicate; com conteúdo diferente, 409.

~~~json
{"status":"accepted","event_id":"installation001-session003-event0004","new_unlocks":[]}
~~~

Accepted retorna HTTP 201; duplicate retorna 200 e new_unlocks vazio. SDK verifica status e ID antes de remover o arquivo local. Horário exibido é o recebimento pelo payload, não a data offline do cliente.

## Consultas

- GET /api/v1/info: serviço, versão, api_major/minor, instance_id, uptime e limites.
- GET /api/v1/games: catálogos.
- GET /api/v1/users: usuários com progresso.
- GET /api/v1/state/<user>/<game>: progresso, desbloqueio e horário Unix.
- GET /api/v1/assets/<sha256>.png: imagem imutável.
- /, /app.css, /app.js: interface embutida, sem fontes/CDN externas.

Major define compatibilidade obrigatória; SDK 0.1 recusa outro major. Nova instância requer sincronização dos metadados.

## Persistência

~~~text
/data/prospero-achievements/
  .service.lock
  service.log
  catalogs/<game>.json
  assets/<sha256>.png
  users/<user>/<game>.journal
~~~

Journal v1: [uint32_le tamanho][uint32_le CRC32][JSON UTF-8]. JSON contém evento normalizado, body_sha256, received_at e awards. Limite de 4096 eventos, sem compactação nesta versão. Final fisicamente incompleto é sinalizado nas consultas e truncado até o último registro válido antes da próxima escrita. Registro completo com CRC/estrutura incorreto causa erro e é preservado.

SDK usa pasta própria do port, com identity.txt, catalog.json, assets e pending/<hash-event_id>.json. Não grava diretamente no progresso do servidor.

## Controle e erros

POST /api/v1/service/stop, corpo vazio, Content-Length 0, encerra apenas este serviço. Mesmas restrições de loopback/Origin; utilizado por pa_stop.elf, sem botão de encerramento na web.

400: dados inválidos; 403: escrita não local/Origin; 404: rota/jogo ausente; 409: conflito de ID/versão; 503: armazenamento/estado indisponível; 507: quota. Nunca tratar erros como confirmações de desbloqueio.
