# Ponte gerenciada genérica · experimental 0.1.0

`ProsperoAchievements.dll` é uma biblioteca .NET Framework 4.0 sem dependências da Unity ou da Steam. O mesmo binário pode acompanhar diferentes ports; um arquivo de configuração associa as IDs emitidas pelo jogo às IDs do catálogo.

```text
Condição original do jogo
  → método de concessão adaptado
  → ProsperoAchievements.dll
  → arquivo de eventos no prefixo Wine
  → ponte nativa + outbox do SDK
  → prospero_achievements.elf → interface web
```

O payload e o SDK nativo continuam responsáveis por persistência, tentativas de envio, notificações, separação de usuários e platina automática. A DLL publica solicitações de desbloqueio somente quando o jogo chama seu ponto de concessão. Ela não verifica condições de gameplay nem cria desbloqueios ao iniciar.

## Usar no Port Station

1. Importe/revise o catálogo e mantenha cada `source_id` exatamente igual à ID emitida pelo jogo. Nomes e descrições podem ser traduzidos; IDs não devem ser traduzidas.
2. Selecione **`unity-mono-steam`** como adaptador. O kit deve conter `build/port-studio/managed/` com a DLL, o integrador e `managed.lock.json`.
3. Gere uma nova build. O integrador lê `*_Data/Managed/Assembly-CSharp.dll` sem executar o jogo e aceita apenas um padrão restrito de método estático `void(string)` dedicado à concessão de conquistas. O relatório fica em `managed/compatibility.json` na saída.
4. A build recebe uma cópia da assembly adaptada, a DLL genérica e `ProsperoAchievements.config.tsv`. A origem permanece intacta. Na abertura, o launcher também sincroniza esses três arquivos em um prefixo já preparado, verificando tamanho e CRC antes de substituir cada arquivo.
5. Com o payload ativo, valide primeiro a abertura do jogo e o catálogo. Depois obtenha uma conquista legítima, confira o popup e a web, feche/reabra e confira a persistência.

**Estado:** compilação e testes em Windows passaram, incluindo execução de um fixture próprio pela DLL compilada e sincronização nativa de arquivos grandes. A análise estática reconhece o wrapper da cópia de Kindergarten utilizada no desenvolvimento. A integração foi validada em uma build de Kindergarten no PS5, com desbloqueio legítimo de Best Boyfriend Ever, popup e persistência no backend. Outros jogos/wrappers precisam de validação própria. A receita específica de Breath permanece disponível e validada separadamente.

### Limites do integrador automático

O padrão inicial corresponde a um wrapper que verifica `SteamManager.Initialized`, consulta se a conquista já foi obtida e então chama `SteamUserStats.SetAchievement(id)` e `StoreStats()`. O integrador verifica assinatura, sequência de instruções e destinos dos saltos. Ele acrescenta uma rota local na entrada desse wrapper; preserva o corpo original para execução fora do contexto do port.

Métodos com condições adicionais de gameplay, rotinas por enum, outras APIs/assinaturas, assemblies com assinatura forte, IL2CPP e binários nativos são recusados. Não há substituição global de SteamManager ou DLL nativa `steam_api64.dll`. Um jogo fora desse padrão precisa de um adaptador revisado; **usar o mesmo SDK/DLL não torna os pontos de integração iguais em todos os jogos**. Breath continua com sua receita específica, e NW.js com a ponte JavaScript.

Estatísticas e conquistas calculadas por limites de estatísticas não são convertidas nesta versão. O catálogo pode conter IDs de caminhos/edições não alcançáveis na versão ativa do jogo; revise a lista e não interprete extração estática como prova de cobertura de gameplay.

## Compilar

Na raiz das fontes, com Python 3.13 e .NET SDK 10:

```powershell
python sdk/prospero-achievements/managed/build.py
dotnet run --project sdk/prospero-achievements/managed/Tests -c Release -- build/port-studio/managed/ProsperoManagedIntegrator.exe build/port-studio/managed/ProsperoAchievements.dll
```

O build produz a DLL `net40` e um integrador Windows x64 independente da instalação de .NET no computador de uso. A restauração baixa Mono.Cecil 0.11.6 e as referências .NET Framework 4.0; não utiliza fontes ou arquivos de jogos. Os avisos de .NET/Mono.Cecil do kit também se aplicam ao integrador.

Para uma inspeção sem escrita:

```powershell
build/port-studio/managed/ProsperoManagedIntegrator.exe "D:/MeuJogo/Game_Data/Managed/Assembly-CSharp.dll"
```

## Integração manual com fontes próprias

Adicione uma referência à DLL e chame o SDK no ponto em que seu jogo já concede a conquista:

```csharp
if (ProsperoAchievements.Bridge.TryUnlock(originalAchievementId)) return;
// Caminho original da plataforma, quando não houver contexto local do port.
```

O retorno indica que o contexto local assumiu a solicitação, inclusive se houver falha de escrita. Isso evita entrar na API Steam ausente após reconhecer um contexto válido. Uma falha anterior a qualquer gravação não é persistida pela DLL; nesse caso será preciso repetir a condição no jogo. O transporte HTTP e suas tentativas são executados pelo worker nativo, após ele ler um registro completo e colocá-lo no outbox.

`ProsperoAchievements.config.tsv`, junto da DLL, usa UTF-8 sem BOM:

```text
PA_MANAGED_CONFIG_V1	meu.jogo
MAP	RklSU1Q=	FIRST
```

Os separadores são TABs reais; `RklSU1Q=` é a ID de origem `FIRST` codificada em base64 UTF-8. A configuração inclui apenas conquistas regulares. O launcher fornece `C:\ProsperoAchievements\meu.jogo-context-v1.txt`, contendo o jogo/usuário ativos. Sem contexto correspondente, a DLL mantém o caminho original. Registros usam o protocolo [file bridge](../bridge/README.md), sem acesso direto à API HTTP do backend e sem dependência do sistema de troféus da Sony.

Não distribua assemblies modificadas de jogos comerciais junto das fontes ou ferramentas. A ferramenta prepara a cópia local fornecida por cada usuário.
