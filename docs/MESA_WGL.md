# Compilações fixadas do provedor Mesa WGL

[Documentação](INDEX.md) · [Início](../README.pt-BR.md)

O helper compila de forma cruzada o provedor Windows WGL/Zink x86/x64 fixado
em três variantes. Elas não mudam as regras de propriedade do display Vulkan
nem concedem conquistas.

| Opções | Resultado |
|---|---|
| Sem opções adicionais | Apenas logs de ciclo de vida; referências originais. |
| `--release-pending-present` | Logs e limpeza do recurso pertencente ao contexto. |
| `--release-pending-present --clean` | Somente a limpeza, sem logs adicionais. |

Depois das esperas existentes de filas e da limpeza de batches, a correção
libera a referência restante do contexto em `needs_present`. Desvincular pode
já ter limpado o framebuffer e deixado essa referência independente. A correção
usa o helper normal de referência e nunca força contadores. A variante limpa
altera apenas `zink_context.c`; seu manifesto registra `behavior_patch: true`
e `lifetime_logging: false`.

A variante instrumentada passou no teste separado no console: janelas em
1280×720 e 1920×1080 renderizaram 30 quadros cada, sem erro OpenGL, com destruição
dos alvos entre elas. A variante x64 limpa passou nas trocas 4K → 1080p → 720p
→ 4K e na seleção do mesmo adaptador no port configurado de Intravenous 2:
Mercenarism no firmware 13.60. A x86 usa a mesma correção; a validação de
gameplay é separada. O workflow atual compila ambas sem logs de ciclo de vida.

Os logs instrumentados registram destruição de contexto/framebuffer e operações
de referência dos alvos, incluindo chamador, posição de destino e contadores.
Use essas variantes em testes curtos, pois jogos reais podem gerar logs grandes.

Compile no Linux com Python 3.12, Ninja e as ferramentas Python fixadas no workflow:

```sh
python release_support/mesa-wgl/build.py --work /tmp/station-mesa-new --jobs 2
```

Para o runtime limpo, use `--release-pending-present --clean --arch x86_64`.
Use outra pasta nova e `--arch i686` para o provedor de 32 bits.

A pasta de trabalho deve ser nova. Os arquivos Mesa e llvm-mingw são baixados
dos projetos públicos e verificados por SHA-256. O artefato inclui hashes das
DLLs, fonte dos logs adicionados, arquivos Mesa modificados com avisos originais
e textos de licença. O arquivo Mesa original e seu hash constam no manifesto e
em `SOURCES.json`, permitindo reconstruir a build completa. Não requer arquivos
de jogos nem SDK proprietário do console.

A configuração segue a [receita Mesa do prospero-win](https://github.com/mpereiraesaa/prospero-win/blob/main/tools/build_mesa_zink.sh).
WGL/Zink pertencem aos [contribuidores Mesa](https://www.mesa3d.org/) e ao fork
[PS5_Mesa](https://github.com/mpereiraesaa/PS5_Mesa) fixado. O compilador cruzado
é [llvm-mingw](https://github.com/mstorsjo/llvm-mingw). As licenças e os avisos
originais continuam aplicáveis; o diagnóstico adicionado pelo Port Station é MIT.

Use variantes de diagnóstico em testes controlados. Registre e restaure o
provedor anterior e o prefixo preparado antes de retornar à build normal do jogo.
