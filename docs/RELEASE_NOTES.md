# Novidades

[Documentação](INDEX.md) · [Início](../README.pt-BR.md)

## 0.4.0 — primeira versão pública

O kit completo inclui frontend Python/Tk e CLI, runtime Wine/prospero-win,
SDK público, compiladores e ferramentas de recursos. Não é necessário instalar
previews ou aplicar uma sequência de updates. Python 3.13 x64 com Tcl/Tk é o
pré-requisito externo; FFmpeg é opcional para decodificar arquivos de áudio.

### Empacotamento e apresentação

- Projetos reutilizáveis com perfis Direct3D/DXVK, OpenGL/Mesa-Zink,
  NW.js/Canvas e GDI.
- Título, ícone, fundos e música opcionais, conversão BC7 e encoder ATRAC9 local.
- Desktop virtual automático ou configurável até 4K. O backend OpenGL libera
  a referência de apresentação ao destruir o contexto, permitindo recriar a
  janela ao trocar a resolução nas configurações do jogo compatível.
- Atalho Options + clique do touchpad e fechamento pelo menu PS no ambiente
  testado; preparação de dados graváveis e atualização de arquivos de
  compatibilidade no prefixo em cache, preservando saves.

### Conquistas

- Extrator integrado com leitores JSON/VDF, JavaScript, Unity Mono e constantes
  LuaJIT em pacotes LÖVE/ZIP, inclusive anexados ao executável.
- Interseção exata com IDs oficiais Steam, consulta de textos oficiais por idioma
  e edição manual, sem tradução automática por serviços externos.
- Backend Prospero Achievements, fila persistente no SDK, popup confirmado,
  progresso por usuário e platina opcional calculada pelo serviço.
- Adaptadores NW.js, Unity Mono, Breath e protocolo de arquivos. A revisão
  LÖVE verificada de Intravenous recebe um produtor de chamadas originais
  `SetAchievement`, com fonte e DLL própria incluídos.

### Compatibilidade e validação

Os testes manuais no PS5 13.60 confirmaram funções de jogo e conquistas em
Breath, TCOAAL, Kindergarten e na revisão x64 de Intravenous 2: Mercenarism 1.7.1.
A ponte LÖVE passou no teste real de desbloqueio relatado pelo usuário. Em
Intravenous, também foram testadas trocas 4K → 1080p → 720p → 4K e a seleção
do mesmo adaptador sem tela preta. A cobertura é por função/trecho; não equivale
a campanhas completas nem garante outras versões.

Os testes locais abrangem build, catálogos, fontes, transporte de eventos,
isolamento por usuário, repetição, falhas de gravação e preservação da API do
jogo. A CI verifica os fontes e o extrator sem depender dos arquivos comerciais.
As receitas, revisões, hashes e instruções de reconstrução acompanham o kit.

### Instalação

Baixe `Port_Station-0.4.0-windows-kit.zip`, extraia em uma pasta nova e abra
`Port_Station.cmd`. Consulte o [guia rápido](QUICKSTART.md). Para projetos
existentes, abra seu `.ps5port.json` no kit novo e gere outra build; o projeto
não substitui automaticamente a instalação do jogo no console.

As configurações de Breath e TCOAAL são exemplos com placeholders próprios.
Nenhum jogo, save, arte oficial ou música comercial é distribuído. Os fontes
completos, backend/SDK compilados e fontes upstream acompanham a release.
