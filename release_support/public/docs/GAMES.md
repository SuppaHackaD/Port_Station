# Receitas locais

Compre e instale a versão Windows dos jogos. Nenhuma etapa baixa conteúdo comercial. Mantenha os arquivos originais fora do repositório e use uma pasta nova para cada preparação.

## Breath

Receita exercitada: Breath1.0.3, Unity2019, assembly original SHA-256 `b98be2ab162e9f7f2ff4029b0bf8221db075df052d5782b96c73424c6ee95f18`. Outras versões são rejeitadas pelo patcher para evitar alterações incorretas.

```powershell
python release_support/prepare-game.py breath --source "D:/SteamLibrary/steamapps/common/Breath" --output local-games/breath
```

O script copia o jogo, aplica nossa ponte às duas rotinas de conquistas e acrescenta apenas `BreathPS5Bridge.dll`, que é código próprio. O jogo original não é escrito. O assembly modificado existe somente na cópia local do comprador e não deve ser publicado. A receita usa DXVK/XInput, D3D11 e janela1280×720. A DLL de Steam original, quando fornecida pelo jogo, permanece propriedade de seus titulares; não acompanham o projeto substitutos proprietários.

Abra `port_studio/examples/breath.ps5port.json`. Há11 condições originais e uma platina calculada pelo backend. As imagens são placeholders; você pode substituí-las localmente por imagens que tenha direito de usar.

## The Coffin of Andy and Leyley

Base exercitada: jogo3.0.13, NW.js0.29/RPG Maker. A compatibilidade pode mudar em atualizações posteriores.

```powershell
python release_support/prepare-game.py tcoal --source "D:/SteamLibrary/steamapps/common/The Coffin of Andy and Leyley" --output local-games/tcoal
```

O script copia a instalação e, quando o catálogo nativo conhecido está presente, acrescenta somente escolhas ausentes das traduções locais usando os dados da própria cópia. Para `Call again.` em português, usa `Ligar novamente.`. Não inclui tradução ou diálogo completos na distribuição. Revisa as mudanças no recibo de preparação antes de empacotar outra versão.

Abra `port_studio/examples/tcoal.ps5port.json`. O argumento `canvas` precisa vir primeiro; o perfil já cuida disso. Durante a build, o Studio registra TTF/OTF locais no prefixo Wine e usa fallback CSS local (incluindo Faustina), evitando o loading observado na base original. A ponte envolve as APIs observadas da Steam sem trocar condições de gameplay e associa `warden_wins` a `WARDEN_WINS` e demais IDs conhecidas.20 conquistas originais + platina opcional.

## Dados e atualização

O exemplo usa catálogo10 como revisão inicial desta apresentação pública. Isso evita reutilizar as revisões de desenvolvimento1–3. Se já houver catálogo10 instalado e você mudar textos/imagens, incremente a versão novamente. IDs e condições devem permanecer estáveis. Nunca zerar progresso automaticamente para aceitar uma edição.

Compartilhar `game_id=breath` ou `tcoal` compartilha a entrada e progresso lógico com outros ports que usem o mesmo ID no mesmo usuário. O Title ID controla a identidade do título e a pasta privada do runtime; escolha outro se houver colisão.

Saves não são importados automaticamente pelo Studio. Nenhum reset acompanha as receitas ou scripts de release. Não publique `local-games`, `outputs`, manifests de builds privadas, saves ou logs com caminhos pessoais.
