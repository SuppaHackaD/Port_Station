"""Prepare the supported local Breath copy; never modify the purchaser's source."""
from pathlib import Path
import hashlib
import shutil
from .project import WORKSPACE, ProjectError

ORIGINAL_SHA256 = 'b98be2ab162e9f7f2ff4029b0bf8221db075df052d5782b96c73424c6ee95f18'
MANAGED = Path('Breath_Data/Managed')


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def tools(workspace=WORKSPACE):
    root = Path(workspace) / 'build/release-managed'
    patcher, bridge = root / 'PatchBreathAchievements.exe', root / 'BreathPS5Bridge.dll'
    if not patcher.is_file() or not bridge.is_file():
        raise ProjectError('Breath: instale o kit Windows completo ou compile as ferramentas gerenciadas de docs/BUILDING.md.')
    return patcher, bridge


def inspect(game, run, workspace=WORKSPACE):
    patcher, _ = tools(workspace)
    managed = Path(game) / MANAGED
    assembly, bridge = managed / 'Assembly-CSharp.dll', managed / 'BreathPS5Bridge.dll'
    if not assembly.is_file():
        raise ProjectError('Breath: Breath_Data/Managed/Assembly-CSharp.dll não encontrado.')
    if sha(assembly) == ORIGINAL_SHA256:
        return 'original'
    if not bridge.is_file():
        raise ProjectError('Breath: versão não reconhecida ou preparação incompleta. Use a cópia original compatível do Breath 1.0.3.')
    # Cecil verifies actual CIL call targets and the conditional return before
    # the original Steam branch. A DLL filename alone is not a prepared copy.
    run([patcher, '--verify', assembly, bridge])
    return 'prepared'


def prepare(game, run, workspace=WORKSPACE):
    """Called only on an owned build copy, after user overlays and before hashes."""
    game = Path(game)
    mode = inspect(game, run, workspace)
    patcher, bridge = tools(workspace)
    assembly = game / MANAGED / 'Assembly-CSharp.dll'
    before = sha(assembly)
    changes = []
    if mode == 'original':
        temporary = assembly.with_name('Assembly-CSharp.port-station-patched.dll')
        if temporary.exists():
            raise ProjectError('Breath: arquivo de preparação temporário já existe na cópia de saída.')
        run([patcher, assembly, bridge, temporary])
        temporary.replace(assembly)
        shutil.copy2(bridge, assembly.parent / bridge.name)
        changes = [(MANAGED / assembly.name).as_posix(), (MANAGED / bridge.name).as_posix()]
        inspect(game, run, workspace)
    return {'input': mode, 'changes': changes, 'assembly_before_sha256': before,
            'assembly_sha256': sha(assembly),
            'bridge_sha256': sha(assembly.parent / 'BreathPS5Bridge.dll')}
