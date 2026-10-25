"""Preparation orchestration on owned fixtures; no commercial game is required."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from port_station import breath
from port_station.project import ProjectError


class BreathPreparationTests(unittest.TestCase):
    def setup_tree(self, root, assembly=b'own original fixture'):
        kit = root / 'kit/build/release-managed'
        kit.mkdir(parents=True)
        (kit / 'PatchBreathAchievements.exe').write_bytes(b'own tool fixture, never executed')
        (kit / 'BreathPS5Bridge.dll').write_bytes(b'own bridge fixture')
        game = root / 'game'
        managed = game / breath.MANAGED
        managed.mkdir(parents=True)
        (managed / 'Assembly-CSharp.dll').write_bytes(assembly)
        return game, managed, root / 'kit'

    def test_original_copy_is_patched_verified_and_reopen_does_not_patch_again(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            game, managed, kit = self.setup_tree(root)
            original = (managed / 'Assembly-CSharp.dll').read_bytes()
            calls = []
            def run(args):
                calls.append(args)
                if str(args[1]) != '--verify':
                    Path(args[3]).write_bytes(b'own prepared fixture')
                else:
                    self.assertEqual(Path(args[2]).read_bytes(), b'own prepared fixture')
                    self.assertEqual(Path(args[3]).read_bytes(), b'own bridge fixture')
            with patch.object(breath, 'ORIGINAL_SHA256', hashlib.sha256(original).hexdigest()):
                report = breath.prepare(game, run, kit)
                self.assertEqual(report['input'], 'original')
                self.assertEqual(len(report['changes']), 2)
                self.assertEqual(len(calls), 2)
                self.assertEqual(breath.prepare(game, run, kit)['input'], 'prepared')
                self.assertEqual(len(calls), 3)  # verification only
            self.assertNotEqual(report['assembly_before_sha256'], report['assembly_sha256'])

    def test_unknown_version_and_missing_bridge_fail_before_tool_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            game, _, kit = self.setup_tree(Path(temp), b'own unknown fixture')
            with self.assertRaises(ProjectError):
                breath.inspect(game, lambda _: self.fail('must not run tool'), kit)

    def test_verifier_failure_preserves_prepared_input(self):
        with tempfile.TemporaryDirectory() as temp:
            game, managed, kit = self.setup_tree(Path(temp), b'own invalid prepared fixture')
            bridge = managed / 'BreathPS5Bridge.dll'
            bridge.write_bytes(b'wrong fixture')
            before = {p.name: p.read_bytes() for p in managed.iterdir()}
            def fail(_):
                raise ProjectError('invalid bridge route')
            with self.assertRaisesRegex(ProjectError, 'invalid bridge route'):
                breath.prepare(game, fail, kit)
            self.assertEqual({p.name: p.read_bytes() for p in managed.iterdir()}, before)

    def test_inspection_of_original_never_changes_input(self):
        with tempfile.TemporaryDirectory() as temp:
            game, managed, kit = self.setup_tree(Path(temp))
            assembly = managed / 'Assembly-CSharp.dll'
            before = assembly.read_bytes()
            with patch.object(breath, 'ORIGINAL_SHA256', hashlib.sha256(before).hexdigest()):
                self.assertEqual(breath.inspect(game, lambda _: self.fail('not needed'), kit), 'original')
            self.assertEqual(assembly.read_bytes(), before)
            self.assertEqual(len(list(managed.iterdir())), 1)


if __name__ == '__main__':
    unittest.main()
