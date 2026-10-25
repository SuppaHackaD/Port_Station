import argparse
import json
from pathlib import Path
import sys
from .project import read_project, validate, ProjectError
from .builder import Builder, doctor, setup, check_lock, build_profile_checker, refresh_lock

def main():
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf8',line_buffering=True)
    if hasattr(sys.stderr,'reconfigure'):sys.stderr.reconfigure(encoding='utf8',line_buffering=True)
    parser=argparse.ArgumentParser(description='Port Station — Windows/Wine para homebrew PS5')
    sub=parser.add_subparsers(dest='command')
    sub.add_parser('gui');sub.add_parser('doctor');sub.add_parser('setup');sub.add_parser('verify-runtime')
    lock=sub.add_parser('lock');lock.add_argument('--accept-current',action='store_true',required=True)
    export=sub.add_parser('export-toolkit');export.add_argument('destination',type=Path)
    audio=sub.add_parser('transcode-audio');audio.add_argument('source',type=Path);audio.add_argument('--output',required=True,type=Path);audio.add_argument('--start',type=float,default=0);audio.add_argument('--duration',type=float,default=15)
    for command in ['validate','prepare','build']:
        p=sub.add_parser(command);p.add_argument('project',type=Path)
        if command!='validate':p.add_argument('--output',required=True,type=Path)
        if command=='build':p.add_argument('--no-zip',action='store_true')
    args=parser.parse_args()
    try:
        if args.command in (None,'gui'):
            from .gui import launch
            launch();return 0
        if args.command=='doctor':
            result=doctor();print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if all(x['present']for x in result['dependencies'])else 1
        if args.command=='setup':setup();return 0
        if args.command=='lock':build_profile_checker();refresh_lock();return 0
        if args.command=='export-toolkit':
            from .distribution import toolkit
            toolkit(args.destination);return 0
        if args.command=='verify-runtime':check_lock();print('Runtime íntegro.');return 0
        if args.command=='transcode-audio':
            from .audio import transcode
            builder=Builder();report=transcode(args.source,args.output,builder.run,builder.emit,args.start,args.duration)
            print(json.dumps(report,ensure_ascii=False,indent=2));return 0
        path=args.project.resolve();project=read_project(path);validate(project,path.parent)
        if args.command=='validate':print('Projeto válido.');return 0
        Builder().build(project,path.parent,args.output,archive=not getattr(args,'no_zip',False),prepare_only=args.command=='prepare')
        return 0
    except (ProjectError,OSError,ValueError)as e:
        print('ERRO: '+str(e),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
