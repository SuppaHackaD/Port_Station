"""Build only owned bridge/tool; no game input is read or bundled."""
import argparse,hashlib,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dotnet',default='dotnet');parser.add_argument('--output',type=Path,default=ROOT/'build/port-studio/managed')
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    subprocess.run([args.dotnet,'build',str(HERE/'Bridge/Bridge.csproj'),'-c','Release','--nologo'],check=True)
    subprocess.run([args.dotnet,'publish',str(HERE/'Integrator/Integrator.csproj'),'-c','Release','-r','win-x64',
        '--self-contained','true','-p:PublishSingleFile=true','-p:DebugType=None','-p:EnableCompressionInSingleFile=true','-o',str(out),'--nologo'],check=True)
    (out/'ProsperoAchievements.dll').write_bytes((HERE/'Bridge/bin/Release/net40/ProsperoAchievements.dll').read_bytes())
    files={n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in ('ProsperoManagedIntegrator.exe','ProsperoAchievements.dll')}
    (out/'managed.lock.json').write_text(json.dumps({'version':'0.1.0','files':files},indent=2)+'\n',encoding='utf-8')
    print(out)

if __name__=='__main__':main()
