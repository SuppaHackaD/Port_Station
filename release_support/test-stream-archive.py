"""Verify streaming ZIP determinism and extraction using only owned fixture bytes."""
from pathlib import Path
import importlib.util,io,hashlib,tempfile,unittest,zipfile
spec=importlib.util.spec_from_file_location('archives',Path(__file__).with_name('archive-release.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class StreamingArchiveTests(unittest.TestCase):
    def test_two_passes_match_and_all_entries_extract(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);p=root/'own.txt';p.write_bytes(b'owned fixture '*1000);entries={'own.txt':p};hashes={'own.txt':m.sha(p)}
            buffers=[]
            for _ in range(2):
                b=io.BytesIO();sink=m.StreamWriter(b.write);m.write_stream_archive(entries,hashes,sink,'Kit/');data=b.getvalue();self.assertEqual(sink.digest.hexdigest(),hashlib.sha256(data).hexdigest());buffers.append(data)
            self.assertEqual(*buffers)
            with zipfile.ZipFile(io.BytesIO(buffers[0]))as z:
                self.assertIsNone(z.testzip());self.assertEqual(z.read('Kit/own.txt'),p.read_bytes())
    def test_changed_input_is_rejected(self):
        with tempfile.TemporaryDirectory()as td:
            p=Path(td)/'own';p.write_bytes(b'changed')
            with self.assertRaises(ValueError):m.write_stream_archive({'own':p},{'own':'0'*64},m.StreamWriter())
if __name__=='__main__':unittest.main()
