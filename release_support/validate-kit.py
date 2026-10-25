"""Compile a diagnostic package using own fixtures; does not launch or deploy it."""
from pathlib import Path
import argparse,json,struct,sys,tempfile
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R))
from port_studio.project import read_project
from port_studio.builder import Builder

def validate(output):
    output=output.resolve()
    if output.exists():raise ValueError('Validation output must be a new directory.')
    with tempfile.TemporaryDirectory(prefix='port-studio-owned-fixture-')as temp:
        game=Path(temp);www=game/'www';www.mkdir()
        (www/'index.html').write_text('<!doctype html><body>Port Station own fixture only.</body>\n',encoding='utf8')
        (game/'package.json').write_text(json.dumps({'name':'Port Station own diagnostic fixture','main':'www/index.html'}),encoding='utf8')
        data=bytearray(134);data[:2]=b'MZ';struct.pack_into('<I',data,60,128);data[128:132]=b'PE\0\0';struct.pack_into('<H',data,132,0x14c)
        (game/'Fixture.exe').write_bytes(data) # Header fixture, deliberately never executed.
        base=R/'port_studio/examples';p=read_project(base/'tcoal.ps5port.json')
        p.update(title='Port Station Build Diagnostic',title_id='PPSA99500',game_id='studio.diagnostic',game_dir=str(game),executable='Fixture.exe',sound='',platinum=False,achievements=[{'id':'FIRST','title':'First diagnostic event','description':'Own fixture; no commercial game.','icon':p['icon'],'source_id':'first','target':1,'hidden':False}])
        result=Builder().build(p,base,output,archive=False)
        print('Build-only diagnostic passed:',result,flush=True)
        print('This checks compilation/packaging only; it is not a playable game or a console launch test.',flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True,type=Path);validate(ap.parse_args().output)
