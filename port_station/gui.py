"""Tk frontend: the CLI and UI use exactly the same project/build implementation."""
from __future__ import annotations
import copy
from datetime import datetime
import json
import os
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from . import __version__
from .project import WORKSPACE, PROFILES, ADAPTERS, default_project, read_project, write_project, resolve_path, validate
from .builder import Builder, doctor
from .assets import Image, ImageOps

class App:
    def __init__(self,root):
        self.root=root;root.title('Port Station · '+__version__);root.geometry('1120x820');root.minsize(950,700)
        self.path=None;self.base=WORKSPACE;self.project=default_project();self.busy=False;self.messages=queue.Queue();self.cancel=threading.Event();self.last_output=None
        self.vars={};self.preview_images=[]
        style=ttk.Style();style.theme_use('clam')
        style.configure('TFrame',background='#f3f5f8');style.configure('TLabel',background='#f3f5f8',foreground='#1b293a');style.configure('TNotebook',background='#f3f5f8')
        style.configure('TButton',padding=(12,7));style.configure('Title.TLabel',font=('Segoe UI',19,'bold'));style.configure('Sub.TLabel',foreground='#526477')
        top=ttk.Frame(root,padding=18);top.pack(fill='x')
        ttk.Label(top,text='Port Station',style='Title.TLabel').pack(side='left')
        ttk.Label(top,text='Windows + Wine → PS5 homebrew',style='Sub.TLabel').pack(side='left',padx=20)
        self.file_buttons=[]
        for text,command in [('Novo',self.new),('Abrir',self.open),('Salvar',self.save),('Salvar como',lambda:self.save(True))]:
            b=ttk.Button(top,text=text,command=command);b.pack(side='right',padx=3);self.file_buttons.append(b)
        self.project_label=ttk.Label(root,text='Projeto novo · caminhos relativos à pasta do projeto',padding=(20,0,20,12));self.project_label.pack(fill='x')
        self.tabs=ttk.Notebook(root);self.tabs.pack(fill='both',expand=True,padx=18,pady=(0,12))
        self.game_tab=self.tab('Jogo');self.art_tab=self.tab('Apresentação');self.audio_tab=self.tab('Áudio');self.ach_tab=self.tab('Conquistas');self.advanced_tab=self.tab('Avançado');self.build_tab=self.tab('Build e diagnóstico')
        self.make_game();self.make_art();self.make_audio();self.make_achievements();self.make_advanced();self.make_build()
        self.status=tk.StringVar(value='Pronto. Abra uma receita em port_station/examples ou configure um novo jogo.')
        ttk.Label(root,textvariable=self.status,padding=(20,5,20,12),style='Sub.TLabel').pack(fill='x')
        self.populate(self.project);root.after(100,self.poll);root.protocol('WM_DELETE_WINDOW',self.close)

    def tab(self,title):
        f=ttk.Frame(self.tabs,padding=20);self.tabs.add(f,text=title);return f

    def var(self,key):
        if key not in self.vars:self.vars[key]=tk.StringVar()
        return self.vars[key]

    def field(self,parent,row,label,key,browse=None,width=65):
        ttk.Label(parent,text=label).grid(row=row,column=0,sticky='w',pady=7,padx=(0,15))
        entry=ttk.Entry(parent,textvariable=self.var(key),width=width);entry.grid(row=row,column=1,sticky='ew',pady=7)
        if browse:ttk.Button(parent,text='Escolher…',command=browse).grid(row=row,column=2,padx=(8,0))
        parent.columnconfigure(1,weight=1);return entry

    def choose(self,key,directory=False):
        value=filedialog.askdirectory(parent=self.root)if directory else filedialog.askopenfilename(parent=self.root)
        if value:self.var(key).set(value)

    def make_game(self):
        f=self.game_tab
        for row,label,key in [(0,'Título exibido','title'),(1,'Title ID (PPSA + 5 números)','title_id'),(2,'ID estável das conquistas','game_id'),(3,'Versão da aplicação','version')]:self.field(f,row,label,key)
        self.field(f,4,'Pasta completa do jogo','game_dir',lambda:self.choose('game_dir',True))
        self.field(f,5,'Executável (relativo à pasta)','executable',self.choose_exe)
        ttk.Label(f,text='Perfil de compatibilidade').grid(row=6,column=0,sticky='w',pady=7)
        ttk.Combobox(f,textvariable=self.var('profile'),values=PROFILES,state='readonly').grid(row=6,column=1,sticky='ew')
        self.field(f,7,'Argumentos adicionais','arguments')
        ttk.Label(f,text='Os perfis são pontos de partida. DXVK/XInput para jogos 3D; Canvas para NW.js;\nGDI/teclado para aplicações 2D. O executável PE determina x86 ou x64.',wraplength=820,style='Sub.TLabel').grid(row=8,column=0,columnspan=3,sticky='w',pady=20)
        ttk.Label(f,text='Saída: pasta de homebrew completa. Fechamento: Options + clique do touchpad (1 s).\nVerifique também PS → Fechar jogo durante o teste do seu título.',wraplength=820,style='Sub.TLabel').grid(row=9,column=0,columnspan=3,sticky='w')

    def choose_exe(self):
        path=filedialog.askopenfilename(parent=self.root,filetypes=[('Windows executável','*.exe')])
        if not path:return
        try:
            game=resolve_path(self.var('game_dir').get(),self.base);self.var('executable').set(Path(path).resolve().relative_to(game).as_posix())
        except ValueError:messagebox.showerror('Executável','Selecione primeiro a pasta do jogo e um .exe dentro dela.',parent=self.root)

    def make_art(self):
        f=self.art_tab
        for row,label,key in [(0,'Ícone (obrigatório)','icon'),(1,'Fundo ao selecionar','background'),(2,'Fundo ao iniciar','launch_background')]:self.field(f,row,label,key,lambda k=key:self.choose(k))
        ttk.Label(f,text='O ícone vira PNG 512×512. Imagens de fundo viram DDS BC7 3840×2160.\nSe indicar só um fundo, ele será usado nas duas telas. Corte central, preservando proporção.\nEscolha a música e o trecho na aba Áudio.',style='Sub.TLabel').grid(row=4,column=0,columnspan=3,sticky='w',pady=15)
        ttk.Button(f,text='Atualizar prévia',command=self.preview).grid(row=5,column=0,sticky='w')
        self.preview_frame=ttk.Frame(f);self.preview_frame.grid(row=6,column=0,columnspan=3,sticky='nsew',pady=15)

    def make_audio(self):
        f=self.audio_tab
        self.field(f,0,'Música da tela inicial','sound',self.choose_audio)
        self.field(f,1,'Início do trecho (segundos)','audio_start')
        self.field(f,2,'Duração (0,1 a 87,3 segundos)','audio_duration')
        ttk.Label(f,text='Selecione MP3, WAV, OGG, FLAC, M4A, AAC ou outro áudio compatível.\nO trecho será convertido automaticamente durante a build.\n\nVolume normalizado, pequenos fades e repetição contínua. Padrão: 15 segundos.\nAT9 pronto é validado e copiado integralmente; início e duração não são aplicados a ele.\n\nVocê também pode gerar um .at9 separado antes de compilar o jogo.\nA música original continua selecionada no projeto para permitir novos ajustes.',wraplength=850,style='Sub.TLabel').grid(row=3,column=0,columnspan=3,sticky='w',pady=20)
        self.audio_convert_button=ttk.Button(f,text='Converter para .at9…',command=self.convert_audio)
        self.audio_convert_button.grid(row=4,column=1,sticky='w')

    def choose_audio(self):
        value=filedialog.askopenfilename(parent=self.root,filetypes=[('Áudio','*.mp3 *.wav *.ogg *.flac *.m4a *.aac *.aiff *.aif *.opus *.wma *.at9'),('Todos os arquivos','*.*')])
        if value:self.var('sound').set(value)

    def convert_audio(self):
        if self.busy:return
        try:
            from .audio import validate_options
            p=self.snapshot();validate_options(p['audio_start'],p['audio_duration']);source=resolve_path(p['sound'],self.base)
            if not source.is_file():raise ValueError('Selecione uma música existente.')
        except Exception as e:messagebox.showerror('Áudio',str(e),parent=self.root);return
        file=filedialog.asksaveasfilename(parent=self.root,title='Salvar novo ATRAC9',defaultextension='.at9',filetypes=[('ATRAC9','*.at9')])
        if not file:return
        destination=Path(file)
        self.busy=True;self.cancel.clear();self.tabs.select(self.build_tab);self.progress.start(15);self.cancel_button.configure(state='normal');self.last_output=destination.parent
        for b in self.action_buttons+self.file_buttons:b.configure(state='disabled')
        self.status.set('Convertendo áudio…')
        def worker():
            try:
                from .audio import transcode
                builder=Builder(lambda s:self.messages.put(('log',s)),self.cancel)
                report=transcode(source,destination,builder.run,builder.emit,p['audio_start'],p['audio_duration'])
                self.messages.put(('log',json.dumps(report,ensure_ascii=False,indent=2)))
                self.messages.put(('done',str(destination)))
            except Exception as e:self.messages.put(('error',str(e)))
        threading.Thread(target=worker,daemon=True).start()

    def preview(self):
        from PIL import ImageTk
        for child in self.preview_frame.winfo_children():child.destroy()
        self.preview_images=[]
        try:
            for i,(key,size)in enumerate([('icon',(156,156)),('background',(460,259))]):
                value=self.var(key).get()
                if not value:continue
                with Image.open(resolve_path(value,self.base))as im:thumb=ImageOps.fit(ImageOps.exif_transpose(im).convert('RGB'),size,method=Image.Resampling.LANCZOS)
                photo=ImageTk.PhotoImage(thumb);self.preview_images.append(photo)
                ttk.Label(self.preview_frame,image=photo).grid(row=0,column=i,padx=(0,18),sticky='nw')
            ttk.Label(self.preview_frame,text=self.var('title').get(),font=('Segoe UI',12,'bold')).grid(row=1,column=0,columnspan=2,sticky='w',pady=10)
        except Exception as e:messagebox.showerror('Prévia',str(e),parent=self.root)

    def make_achievements(self):
        f=self.ach_tab;f.columnconfigure(1,weight=1)
        ttk.Label(f,text='Adaptador de eventos').grid(row=0,column=0,sticky='w')
        ttk.Combobox(f,textvariable=self.var('adapter'),values=ADAPTERS,state='readonly').grid(row=0,column=1,sticky='ew')
        self.field(f,1,'Versão do catálogo','catalog_version')
        ttk.Label(f,text='Catálogo do Prospero Achievements. A criação da lista não cria condições de desbloqueio.\nnone: sem conquistas · file-v1: ponte própria · unity-mono-steam: ponte experimental para wrappers compatíveis · nwjs-steam: duas APIs Steam conhecidas · breath: receita existente.',wraplength=900,style='Sub.TLabel').grid(row=2,column=0,columnspan=3,sticky='w',pady=10)
        self.ach_tree=ttk.Treeview(f,columns=('id','title','source','hidden'),show='headings',height=9,selectmode='browse')
        for col,label,width in [('id','ID canônica',150),('title','Nome',330),('source','ID emitida pelo jogo',190),('hidden','Secreta',65)]:self.ach_tree.heading(col,text=label);self.ach_tree.column(col,width=width)
        self.ach_tree.grid(row=3,column=0,columnspan=3,sticky='nsew');self.ach_tree.bind('<Double-1>',lambda e:self.edit_achievement())
        f.rowconfigure(3,weight=1)
        bar=ttk.Frame(f);bar.grid(row=4,column=0,columnspan=3,sticky='w',pady=8)
        for label,command in [('Extrair do jogo…',self.extract_achievements),('Adicionar',lambda:self.edit_achievement(True)),('Editar',self.edit_achievement),('Remover',self.remove_achievement),('Importar catálogo JSON',self.import_catalog),('Exportar lista JSON',self.export_catalog)]:ttk.Button(bar,text=label,command=command).pack(side='left',padx=(0,5))
        self.platinum=tk.BooleanVar();ttk.Checkbutton(f,text='Acrescentar platina automática ao obter todas as conquistas regulares',variable=self.platinum).grid(row=5,column=0,columnspan=3,sticky='w',pady=8)
        self.field(f,6,'Nome da platina','platinum_title');self.field(f,7,'Ícone da platina (opcional)','platinum_icon',lambda:self.choose('platinum_icon'))

    def refresh_achievements(self):
        self.ach_tree.delete(*self.ach_tree.get_children())
        for i,a in enumerate(self.project['achievements']):self.ach_tree.insert('',tk.END,iid=str(i),values=(a['id'],a['title'],a.get('source_id',a['id']),'Sim'if a.get('hidden')else'Não'))

    def edit_achievement(self,new=False):
        selected=self.ach_tree.selection()
        if not new and not selected:return
        index=None if new else int(selected[0]);value={}if new else self.project['achievements'][index]
        dialog=tk.Toplevel(self.root);dialog.title('Conquista');dialog.transient(self.root);dialog.grab_set();dialog.geometry('650x430')
        frame=ttk.Frame(dialog,padding=20);frame.pack(fill='both',expand=True)
        fields={}
        for row,(key,label)in enumerate([('id','ID canônica'),('source_id','ID emitida (vazio = canônica)'),('title','Nome'),('description','Descrição'),('icon','Imagem (opcional)')]):
            fields[key]=tk.StringVar(value=value.get(key,''));ttk.Label(frame,text=label).grid(row=row,column=0,sticky='w',pady=8)
            ttk.Entry(frame,textvariable=fields[key],width=48).grid(row=row,column=1,sticky='ew',pady=8)
        def browse():
            p=filedialog.askopenfilename(parent=dialog)
            if p:fields['icon'].set(p)
        ttk.Button(frame,text='Escolher imagem…',command=browse).grid(row=5,column=1,sticky='w')
        hidden=tk.BooleanVar(value=value.get('hidden',False));ttk.Checkbutton(frame,text='Secreta enquanto bloqueada',variable=hidden).grid(row=6,column=1,sticky='w',pady=8)
        def save():
            from .project import valid_id
            a={k:v.get()for k,v in fields.items()};a['source_id']=a['source_id']or a['id'];a['hidden']=hidden.get();a['target']=1
            if not valid_id(a['id'])or not a['title'].strip():messagebox.showerror('Conquista','Informe ID válida e nome.',parent=dialog);return
            if any(x['id']==a['id']for i,x in enumerate(self.project['achievements'])if i!=index):messagebox.showerror('Conquista','ID duplicada.',parent=dialog);return
            if new:self.project['achievements'].append(a)
            else:self.project['achievements'][index]=a
            self.refresh_achievements();dialog.destroy()
        ttk.Button(frame,text='Salvar conquista',command=save).grid(row=7,column=1,sticky='e',pady=12)

    def remove_achievement(self):
        selected=self.ach_tree.selection()
        if selected:del self.project['achievements'][int(selected[0])];self.refresh_achievements()

    def import_catalog(self):
        file=filedialog.askopenfilename(parent=self.root,filetypes=[('Catálogo JSON','*.json')])
        if not file:return
        return self.load_catalog(Path(file))

    def extract_achievements(self):
        if self.busy:return
        try:
            from achievement_extractor.gui import App as Extractor
            from achievement_extractor.official import detect_app_id
            game=resolve_path(self.var('game_dir').get(),self.base)
            window=tk.Toplevel(self.root);window.transient(self.root)
            child=Extractor(window,on_import=self.load_catalog,integrated=True)
            child.folder.set(str(game));child.exe.set(self.var('executable').get())
            child.appid.set(detect_app_id(game))
            child.output.set(str(WORKSPACE/'outputs'/('achievements-'+datetime.now().strftime('%Y%m%d-%H%M%S'))))
            window.grab_set()
            self.extractor=child
        except Exception as e:messagebox.showerror('Extrator',str(e),parent=self.root)

    def load_catalog(self,path):
        try:
            path=Path(path);data=json.loads(path.read_text(encoding='utf-8-sig'));items=data.get('achievements',data.get('items',[]))if isinstance(data,dict)else data
            if not isinstance(items,list):raise ValueError('Lista ausente.')
            regular=[]
            for item in items:
                a=copy.deepcopy(item)
                if 'api_name'in a:a['id']=a['api_name'];a['title']=a['name']
                icon=a.get('icon','')
                if len(icon)==64 and all(c in '0123456789abcdef'for c in icon):icon=str(path.parent/'assets'/(icon+'.png'))
                elif icon:icon=str((path.parent/icon).resolve())
                a['icon']=icon
                if a.get('completion'):
                    self.platinum.set(True)
                    for key,source in [('platinum_id','id'),('platinum_title','title'),('platinum_description','description'),('platinum_icon','icon')]:self.var(key).set(a.get(source,''))
                else:regular.append(a)
            self.project['achievements']=regular;self.refresh_achievements()
            if isinstance(data,dict)and 'catalog_version'in data:self.var('catalog_version').set(max(int(self.var('catalog_version').get()),int(data['catalog_version'])+1))
            self.status.set(f'Importadas {len(regular)} conquistas. Catálogo importado usa uma revisão nova; aumente novamente ao alterar uma lista já publicada.')
            return True
        except Exception as e:messagebox.showerror('Importação',str(e),parent=self.root);return False

    def export_catalog(self):
        path=filedialog.asksaveasfilename(parent=self.root,defaultextension='.json',filetypes=[('Lista editável','*.json')])
        if path:write_project(path,{'schema':1,'achievements':self.project['achievements']})

    def make_advanced(self):
        f=self.advanced_tab
        self.field(f,0,'Classificação etária (0–18)','age');self.field(f,1,'ID da platina','platinum_id');self.field(f,2,'Descrição da platina','platinum_description')
        ttk.Label(f,text='Opções do perfil (JSON por seção: display, input, runtime, debug, application.dll_overrides)',style='Sub.TLabel').grid(row=3,column=0,columnspan=3,sticky='w',pady=(15,5))
        self.options_text=tk.Text(f,height=9,font=('Consolas',10),wrap='none');self.options_text.grid(row=4,column=0,columnspan=3,sticky='nsew')
        ttk.Label(f,text='Overlays explícitos: [{"source": "arquivo local", "destination": "caminho/relativo/no/jogo"}]',style='Sub.TLabel').grid(row=5,column=0,columnspan=3,sticky='w',pady=(15,5))
        self.overlays_text=tk.Text(f,height=6,font=('Consolas',10),wrap='none');self.overlays_text.grid(row=6,column=0,columnspan=3,sticky='nsew')
        f.rowconfigure(4,weight=1);f.rowconfigure(6,weight=1)

    def make_build(self):
        f=self.build_tab
        bar=ttk.Frame(f);bar.pack(fill='x')
        self.action_buttons=[self.audio_convert_button]
        for label,command in [('Diagnóstico',self.diagnose),('Validar projeto',self.validate_project),('Preparar fontes',lambda:self.start_build(True)),('Compilar e empacotar',self.start_build),('Abrir saída',self.open_output)]:
            b=ttk.Button(bar,text=label,command=command);b.pack(side='left',padx=(0,5));self.action_buttons.append(b)
        self.cancel_button=ttk.Button(bar,text='Cancelar',command=lambda:self.cancel.set(),state='disabled');self.cancel_button.pack(side='right')
        self.progress=ttk.Progressbar(f,mode='indeterminate');self.progress.pack(fill='x',pady=12)
        self.log_text=tk.Text(f,font=('Consolas',10),bg='#14202f',fg='#dae9f3',insertbackground='white',wrap='word',state='disabled');self.log_text.pack(fill='both',expand=True)

    def populate(self,p):
        self.project=copy.deepcopy(p)
        for key in self.vars:self.vars[key].set(p.get(key,''))
        self.platinum.set(p['platinum']);self.refresh_achievements()
        for widget,value in [(self.options_text,p['profile_options']),(self.overlays_text,p['overlays'])]:widget.delete('1.0','end');widget.insert('1.0',json.dumps(value,ensure_ascii=False,indent=2))
        self.project_label.configure(text=str(self.path)if self.path else'Projeto novo · salve antes de compilar')

    def snapshot(self):
        p=copy.deepcopy(self.project)
        for key,var in self.vars.items():p[key]=var.get()
        p['age']=int(p['age']);p['catalog_version']=int(p['catalog_version']);p['platinum']=self.platinum.get()
        p['audio_start']=float(p['audio_start'].replace(',','.'));p['audio_duration']=float(p['audio_duration'].replace(',','.'))
        p['profile_options']=json.loads(self.options_text.get('1.0','end'));p['overlays']=json.loads(self.overlays_text.get('1.0','end'))
        return p

    def new(self):
        if self.discard():self.path=None;self.base=WORKSPACE;self.populate(default_project())

    def discard(self):
        try:changed=self.snapshot()!=self.project
        except Exception:changed=True
        return not changed or messagebox.askyesno('Alterações não salvas','Descartar as alterações não salvas?',parent=self.root)

    def open(self):
        if not self.discard():return
        file=filedialog.askopenfilename(parent=self.root,initialdir=WORKSPACE/'port_station/examples',filetypes=[('Projeto Port Station','*.ps5port.json'),('JSON','*.json')])
        if not file:return
        try:
            p=read_project(file);self.path=Path(file);self.base=self.path.parent;self.populate(p);self.status.set('Projeto carregado.')
        except Exception as e:messagebox.showerror('Projeto',str(e),parent=self.root)

    def save(self,save_as=False):
        try:
            p=self.snapshot();path=self.path
            if save_as or not path:
                file=filedialog.asksaveasfilename(parent=self.root,defaultextension='.ps5port.json',filetypes=[('Projeto Port Station','*.ps5port.json')])
                if not file:return False
                path=Path(file)
                if path.parent!=self.base:
                    for key in ['game_dir','icon','background','launch_background','sound','platinum_icon']:
                        if p[key]and not p[key].startswith('${workspace}'):p[key]=str(resolve_path(p[key],self.base))
                    for a in p['achievements']:
                        if a.get('icon')and not a['icon'].startswith('${workspace}'):a['icon']=str(resolve_path(a['icon'],self.base))
                    for a in p['overlays']:a['source']=str(resolve_path(a['source'],self.base))
            write_project(path,p);self.path=path;self.base=path.parent;self.populate(p);self.status.set('Projeto salvo.');return True
        except Exception as e:messagebox.showerror('Salvar',str(e),parent=self.root);return False

    def validate_project(self):
        try:validate(self.snapshot(),self.base);self.status.set('Projeto válido.');messagebox.showinfo('Validação','Configuração e arquivos de entrada válidos.',parent=self.root)
        except Exception as e:messagebox.showerror('Validação',str(e),parent=self.root)

    def diagnose(self):
        self.tabs.select(self.build_tab);self.messages.put(('log',json.dumps(doctor(),ensure_ascii=False,indent=2)))

    def start_build(self,prepare=False):
        if self.busy:return
        try:p=self.snapshot();validate(p,self.base)
        except Exception as e:messagebox.showerror('Build',str(e),parent=self.root);return
        if not self.path:
            if not self.save():return
            p=self.snapshot()
        parent=filedialog.askdirectory(parent=self.root,title='Pasta onde criar uma NOVA build',initialdir=WORKSPACE/'build')
        if not parent:return
        output=Path(parent)/(p['title_id']+'-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
        self.last_output=output;self.busy=True;self.cancel.clear();self.tabs.select(self.build_tab);self.progress.start(15);self.cancel_button.configure(state='normal')
        for b in self.action_buttons+self.file_buttons:b.configure(state='disabled')
        self.status.set('Preparando…'if prepare else'Compilando…')
        base=self.base
        def worker():
            try:
                result=Builder(lambda s:self.messages.put(('log',s)),self.cancel).build(p,base,output,prepare_only=prepare)
                self.messages.put(('done',str(result)))
            except Exception as e:self.messages.put(('error',str(e)))
        threading.Thread(target=worker,daemon=True).start()

    def poll(self):
        try:
            while True:
                kind,value=self.messages.get_nowait()
                self.log_text.configure(state='normal');self.log_text.insert('end',value+'\n');self.log_text.see('end');self.log_text.configure(state='disabled')
                if kind in ('done','error'):
                    self.busy=False;self.progress.stop();self.cancel_button.configure(state='disabled')
                    for b in self.action_buttons+self.file_buttons:b.configure(state='normal')
                    self.status.set('Concluído: '+value if kind=='done'else'Falha/cancelamento: '+value)
        except queue.Empty:pass
        self.root.after(100,self.poll)

    def open_output(self):
        if self.last_output and self.last_output.exists():os.startfile(self.last_output)

    def close(self):
        if self.busy:
            messagebox.showinfo('Build em andamento','Cancele a build e aguarde o encerramento antes de fechar.',parent=self.root);return
        if self.discard():self.root.destroy()

def launch():
    root=tk.Tk();App(root);root.mainloop()
