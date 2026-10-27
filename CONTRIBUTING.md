# Contribuir

[Documentação](docs/INDEX.md) · [Início](README.pt-BR.md)

Correções, novas configurações testadas e novos adaptadores são bem-vindos. Para começar a usar a ferramenta, consulte o [README em português](README.pt-BR.md); para desenvolver, consulte [Compilação](docs/BUILDING.md).

Ao relatar compatibilidade de um jogo, informe sua versão, perfil, executável, argumentos, mapeamento de controles e até onde o teste chegou. Diferencie o funcionamento do menu de uma partida completa e descreva como reproduzir a falha.

Para um novo adaptador, explique de onde vêm os eventos e teste persistência, reenvio sem duplicação, usuário ativo e retomada após o backend ficar indisponível. O editor de catálogo não substitui a integração das condições reais.

Antes de enviar uma alteração, execute os testes relevantes em `port_station/tests`, a regressão JavaScript e, se alterar o serviço/SDK, os testes host do backend. A CI executa as verificações que não exigem jogos ou o kit de compilação.

Preserve as licenças e créditos dos componentes de terceiros. Exemplos devem funcionar com dados locais fornecidos pelo usuário; relatos e contribuições não devem incluir jogos, saves ou dados pessoais.
