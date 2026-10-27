# Achievement Extractor 0.3.0

Ferramenta disponível na aba **Conquistas → Extrair do jogo…** do Port Station e também como programa independente, para recuperar definições e IDs de conquistas de uma cópia local de um jogo Windows e gerar uma lista importável pelo Port Station. Não é necessário instalar o kit completo do Port Station para usar o extrator.

## Começar

Instale Python 3.13 de 64 bits com Tk e abra `Achievement_Extractor.cmd` na raiz do pacote Windows. No clone de fontes, use `achievement_extractor/Achievement_Extractor.cmd`. Não há dependências Python adicionais.

1. Selecione a pasta do jogo e o executável principal dentro dela.
2. Se tiver um schema de conquistas local separado, selecione-o em **Metadados extras**. O campo é opcional.
3. Escolha o idioma preferido. Quando não existir, o leitor tenta inglês e depois outro texto disponível; o relatório registra o idioma encontrado.
4. Clique em **Analisar arquivos**. Revise os nomes, descrições, ícones e itens marcados para revisão. Dê dois cliques em um item para editar e consultar sua origem.
5. Opcionalmente, confirme o **AppID Steam** e clique em **Buscar textos oficiais no idioma escolhido**. A consulta usa apenas AppID/idioma, sem login ou progresso de jogadores. Somente IDs exatamente iguais são associadas. **Só IDs oficiais** seleciona apenas as correspondências da última consulta, mantendo as demais visíveis para revisão; isso ajuda quando uma assembly contém código de mais de uma edição/jogo.
6. Confirme a nova pasta de saída e clique em **Exportar JSON**.
7. No Port Station, abra **Conquistas → Importar catálogo JSON** e escolha `achievements.json`. Configure o adaptador dos eventos e, se desejar, marque a platina automática.

**Somente oficiais** vem marcado na interface. Com ele ativo, a exportação exige uma consulta Steam bem-sucedida para o AppID atual e aceita apenas `ID extraída localmente ∩ ID retornada pela Steam`, com igualdade exata, incluindo maiúsculas/minúsculas. Nomes iguais não confirmam uma ID. Itens locais sem correspondência continuam no relatório, mas ficam fora do JSON mesmo se forem selecionados novamente. Se a consulta falhar ou o AppID mudar, consulte novamente antes de exportar; para um fluxo manual/offline, desmarque a opção.

A lista estritamente oficial não acrescenta platina. Essa continua sendo uma escolha separada no Port Station; deixe-a desmarcada se desejar somente as conquistas originais.

A saída contém `achievements.json`, `extraction-report.json`, instruções de importação e os ícones locais recuperados. As imagens permanecem relativas à lista, para que a pasta possa ser movida inteira. Uma saída existente não é substituída.

Se nenhuma definição for encontrada, use **Salvar só relatório** para guardar os diagnósticos sem criar um catálogo vazio. Na CLI, esse relatório é salvo automaticamente e o comando retorna código 2 quando não há itens selecionados.

## Fontes suportadas nesta versão

| Fonte | Resultado |
|---|---|
| JSON com `achievements`, schemas Steam e definições locais compatíveis | IDs, nomes/descrições disponíveis, atributo secreto e referência a ícone local. |
| VDF textual e KeyValues binário legado com terminador 8 | Definições explícitas de conquistas; `stats` do tipo 4 com `bits`. Outras variantes binárias são recusadas. |
| Chamadas JavaScript literais conhecidas, como `Steam.awardAchievement("ID")` e `greenworks.activateAchievement("ID", ...)` | IDs e localização no script. Comentários, strings contendo código, regex e argumentos dinâmicos não se tornam IDs confirmadas. |
| Assemblies gerenciados, incluindo scripts de jogos Unity Mono | Strings passadas diretamente a APIs de conquistas e mapas locais de retorno de string usados nessas chamadas. O scanner lê metadados/CIL com Mono.Cecil. |
| Pacotes LÖVE/ZIP, inclusive anexados a um PE, e dumps LuaJIT v1/v2 | Constantes locais com origem/hash do membro, cruzadas por igualdade exata com IDs oficiais. Não interpreta instruções nem prova chamadas de desbloqueio. |
| Strings `ACH_…`, `ACHIEVEMENT_…`, `ACHV_…` e `TROPHY_…` no executável | Candidatos para revisão, desmarcados por padrão. Não há relação de chamada comprovada. |

Não é um extrator universal de engines, contêineres ou criptografia. Expressões dinâmicas, ofuscação, formatos de pacote não suportados, IL2CPP e versões diferentes de schemas podem exigir um leitor futuro. O relatório registra limites, chamadas gerenciadas não resolvidas e falhas de leitura. Não encontrar uma ID não demonstra que o jogo não tenha conquistas.

Nomes e descrições muitas vezes são fornecidos pela plataforma em vez de acompanhar o jogo. Quando não são recuperados, o título provisório é a própria ID e a ausência da descrição permanece indicada no editor/relatório. A exportação usa **“Descrição não fornecida”** para produzir um catálogo aceito pelo backend. A consulta opcional busca a localização oficial da Steam; não gera traduções por IA ou serviços externos. O serviço pode responder em inglês quando não houver o idioma solicitado. Edite nomes e descrições por duplo clique para traduzir manualmente; os campos que você alterar ficam protegidos de consultas posteriores. Os textos oficiais recebidos permanecem no relatório para comparação. Uma falha de rede mantém os textos existentes e permite continuar offline. Imagens remotas não são baixadas; PNG/JPEG locais de até 4 MiB podem acompanhar a exportação.

O catálogo não implementa condições de desbloqueio, não importa progresso de jogadores e não concede conquistas. A conexão dos eventos ao backend continua sendo uma etapa do port. Mantenha `source_id` igual ao valor emitido pelo jogo; uma ID canônica incompatível com o formato do Port Station recebe um nome estável, preservando o valor original em `source_id`.

## Linha de comando

A partir da pasta que contém `achievement_extractor/`:

```powershell
python -m achievement_extractor --game-dir "D:/Jogos/MeuJogo" --exe "Game.exe" --output "D:/Catalogos/MeuJogo" --language brazilian
```

Use `--steam-appid 12345 --official-only` para exigir a interseção oficial também na linha de comando. Nesse modo, uma falha de consulta interrompe a exportação.

Adicione `--steam-appid 12345` para consultar os textos oficiais após analisar os arquivos. Não há pesquisa por nome nem associação por posição: confirme o AppID correto na página Steam do seu jogo. Um `steam_appid.txt` na raiz apenas preenche uma sugestão na interface.

Use `--metadata "D:/Schemas/achievements.json"` para um schema local adicional. `--include-candidates` inclui também as strings nativas não confirmadas: use apenas depois de revisar sua origem. Sem argumentos, abre a interface. No Port Station, **Aplicar ao projeto** usa o mesmo exportador e importador de JSON, preservando as opções do projeto. A lista não escolhe automaticamente um adaptador de eventos.

## Compilar e testar

O scanner é independente dos arquivos dos jogos. Para recompilá-lo, instale .NET SDK 10 e execute, da raiz do repositório:

```powershell
dotnet publish achievement_extractor/managed/Scanner.csproj -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -p:DebugType=None -o achievement_extractor/bin
python achievement_extractor/build-package.py --seal-helper
python -m unittest discover -s achievement_extractor/tests -v
```

O pacote Windows inclui o scanner próprio compilado e seu SHA-256. Um clone só com fontes permite usar os leitores JSON/VDF/JavaScript; sem o scanner, a análise gerenciada é marcada como parcial. O programa nunca inicia o executável selecionado, executa scripts do jogo, carrega suas DLLs no runtime nem modifica a cópia de origem.

## Licenças e referências

Código próprio sob a licença do Port Station, incluída no pacote. Mono.Cecil 0.11.6 é distribuído sob MIT; o runtime .NET tem os avisos e licenças incluídos em `LICENSES/`.

- [API pública de catálogos Steam](https://api.steampowered.com/IPlayerService/GetGameAchievements/v1/): consulta opcional por AppID e idioma; sua disponibilidade depende da Valve.
- [Formato de dumps LuaJIT](https://github.com/LuaJIT/LuaJIT/blob/v2.1/src/lj_bcdump.h) e [leitor upstream](https://github.com/LuaJIT/LuaJIT/blob/v2.0/src/lj_bcread.c): referência para o leitor próprio de constantes; o runtime LuaJIT não é incluído nem executado.
- [Mono.Cecil](https://github.com/jbevain/cecil): leitura estática de metadados e CIL.
- [Documentação Steamworks de conquistas](https://partner.steamgames.com/doc/features/achievements): diferença entre IDs e atributos de exibição.
- [KeyValues da Valve](https://github.com/ValveSoftware/source-sdk-2013/blob/master/src/tier1/KeyValues.cpp): referência de formato; o leitor desta ferramenta é uma implementação própria.
- [Arquivos de fontes upstream usados pelo Port Station 0.3.2](https://github.com/SuppaHackaD/Port_Station/releases/download/v0.3.2/upstream-sources.zip), incluindo Mono.Cecil. O código do runtime .NET 10.0.13 incluído no scanner está em [dotnet/runtime v10.0.13](https://github.com/dotnet/runtime/tree/v10.0.13).

Não há vínculo com desenvolvedores de jogos, Valve ou Sony. O pacote não inclui arquivos, catálogos ou imagens de jogos comerciais. Use sua própria cópia e respeite os direitos dos autores ao compartilhar resultados extraídos.
