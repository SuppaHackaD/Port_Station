# Novidades

## 0.4.0-preview.3

O preparo LÖVE agora faz parte do empacotador: a DLL x64 11.4 verificada recebe
a integração com `paenv.dll` na cópia da build. O executável verificado de
Intravenous recebe também a correção do controle. O launcher atualiza esses
arquivos no prefixo em cache antes de iniciar o jogo, sem substituir saves.

As builds anteriores do teste tinham esses ajustes aplicados separadamente.
Nesta revisão, a interface e a CLI geram o mesmo preparo e registram seus
hashes em `love-compatibility.json`. Use o perfil `opengl-xinput` e recompile
o projeto. A resolução 1920×1080 continua sendo uma seleção válida.

## 0.4.0-preview.2

- Resolução do desktop virtual em `auto` ou configurável até 3840×2160, pela
  interface e por `display_resolution` nos projetos JSON. Projetos antigos usam
  `auto`; `display.desktop` em Avançado continua tendo prioridade.
- Perfil `opengl-xinput` para OpenGL/Mesa-Zink com XInput.
- Correção no Zink para liberar a referência de apresentação ao destruir um
  contexto. O port de teste x64 do Intravenous confirmou mudanças entre 4K,
  1080p e 720p e seleção do mesmo adaptador sem a tela preta anterior.

A detecção consulta o tamanho informado pelo console na abertura do título,
com fallback para 1920×1080. O jogo controla sua resolução de renderização
dentro do desktop escolhido. O tamanho físico da saída e a frequência de
atualização continuam sob as configurações do console e do backend gráfico.
Veja [resolução e tela](NEW_GAME.md#resolução-e-tela).

As builds existentes mantêm seu launcher e runtime. Para incorporar estas
alterações a um port, recompile o projeto com o kit atualizado e instale a
nova pasta do título. Os ajustes específicos e a compatibilidade de cada jogo
continuam sendo validados separadamente.
