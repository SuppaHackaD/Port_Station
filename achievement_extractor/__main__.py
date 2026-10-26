import argparse
from .core import scan, export, save_report, ExtractionError

def main():
    parser=argparse.ArgumentParser(description='Extrator local de catálogos para Port Station; não executa o jogo.')
    parser.add_argument('--game-dir');parser.add_argument('--exe');parser.add_argument('--output')
    parser.add_argument('--metadata',help='Schema JSON/VDF/binário local adicional')
    parser.add_argument('--language',default='brazilian')
    parser.add_argument('--include-candidates',action='store_true',help='Inclui strings nativas sem relação de chamada comprovada; revise antes de usar')
    parser.add_argument('--steam-appid',help='Consulta opcional de textos oficiais por AppID; nenhum progresso é consultado')
    parser.add_argument('--official-only',action='store_true',help='Exporta apenas IDs locais confirmadas pela Steam; exige --steam-appid e consulta bem-sucedida')
    args=parser.parse_args()
    if args.official_only and not args.steam_appid:parser.error('--official-only exige --steam-appid.')
    if not any([args.game_dir,args.exe,args.output]):
        from .gui import main as gui_main
        gui_main();return
    if not all([args.game_dir,args.exe,args.output]):parser.error('Informe --game-dir, --exe e --output juntos.')
    try:
        result=scan(args.game_dir,args.exe,args.language,args.metadata,print)
        if args.steam_appid:
            from .official import fetch,enrich,LookupError
            try:result=enrich(result,fetch(args.steam_appid,args.language))
            except LookupError as e:
                if args.official_only:raise
                result['warnings'].append(str(e));print(e)
        if args.include_candidates:
            for row in result['entries']:row['selected']=True
        if not any(row['selected'] for row in result['entries']):
            report=save_report(result,args.output)
            parser.exit(2,'Nenhuma definição selecionada; relatório salvo em '+str(report)+'\n')
        print(export(result,args.output,official_only=args.official_only,steam_app_id=args.steam_appid))
    except (ExtractionError,OSError,ValueError) as e:parser.exit(2,str(e)+'\n')

if __name__=='__main__':main()
