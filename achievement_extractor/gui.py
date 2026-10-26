"""Independent Tk frontend. No imports from Port Station or game libraries."""
from datetime import datetime
import json
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from . import __version__
from .core import scan,export,save_report
from .official import fetch,enrich,detect_app_id,select_confirmed


class App:
    def __init__(self,root):
        self.root=root;self.result=None;self.events=queue.Queue();self.cancel=threading.Event();self.lookup_busy=False
        root.title('Achievement Extractor '+__version__+' · Port Station');root.geometry('1120x740');root.minsize(920,600)
        style=ttk.Style(root);style.theme_use('clam')
        style.configure('TFrame',background='#17212d');style.configure('TLabel',background='#17212d',foreground='#ecf0f5');style.configure('Title.TLabel',font=('Segoe UI',18,'bold'))
        frame=ttk.Frame(root,padding=20);frame.pack(fill='both',expand=True);frame.columnconfigure(1,weight=1);frame.rowconfigure(9,weight=1)
        ttk.Label(frame,text='Achievement Extractor',style='Title.TLabel').grid(row=0,column=0,columnspan=3,sticky='w')
        ttk.Label(frame,text='Catálogos locais + textos oficiais → JSON para importar no Port Station',padding=(0,6)).grid(row=1,column=0,columnspan=3,sticky='w')
        self.folder=tk.StringVar();self.exe=tk.StringVar();self.metadata=tk.StringVar();self.output=tk.StringVar();self.language=tk.StringVar(value='brazilian')
        for row,label,var,command in [(2,'Pasta do jogo',self.folder,self.choose_folder),(3,'Executável .exe',self.exe,self.choose_exe),(4,'Metadados extras (opcional)',self.metadata,self.choose_metadata),(5,'Nova pasta de saída',self.output,self.choose_output)]:
            ttk.Label(frame,text=label).grid(row=row,column=0,sticky='w',pady=5)
            ttk.Entry(frame,textvariable=var).grid(row=row,column=1,sticky='ew',padx=10)
            ttk.Button(frame,text='Escolher…',command=command).grid(row=row,column=2)
        bar=ttk.Frame(frame);bar.grid(row=6,column=0,columnspan=3,sticky='ew',pady=10)
        ttk.Label(bar,text='Idioma preferido:').pack(side='left')
        ttk.Combobox(bar,textvariable=self.language,values=('brazilian','portuguese','english','spanish','french','german','japanese'),width=15).pack(side='left',padx=8)
        self.scan_button=ttk.Button(bar,text='Analisar arquivos',command=self.start);self.scan_button.pack(side='left',padx=8)
        ttk.Button(bar,text='Cancelar análise',command=self.cancel.set).pack(side='left')
        official=ttk.Frame(frame);official.grid(row=7,column=0,columnspan=3,sticky='ew',pady=(0,10))
        self.appid=tk.StringVar()
        ttk.Label(official,text='AppID Steam:').pack(side='left')
        ttk.Entry(official,textvariable=self.appid,width=14).pack(side='left',padx=8)
        self.lookup_button=ttk.Button(official,text='Buscar textos oficiais no idioma escolhido',command=self.lookup)
        self.lookup_button.pack(side='left')
        ttk.Label(official,text='  Sem texto: Descrição não fornecida').pack(side='left')
        ttk.Label(frame,text='IDs extraídas podem precisar de nomes, descrições e ícones. A lista não cria os eventos de desbloqueio.',wraplength=1000).grid(row=8,column=0,columnspan=3,sticky='w',pady=(0,10))
        columns=('selected','id','title','description','review')
        self.table=ttk.Treeview(frame,columns=columns,show='headings',selectmode='browse')
        for col,title,width in [('selected','Usar',48),('id','ID emitida pelo jogo',205),('title','Nome',235),('description','Descrição',290),('review','Revisar',180)]:
            self.table.heading(col,text=title);self.table.column(col,width=width)
        self.table.grid(row=9,column=0,columnspan=3,sticky='nsew');self.table.bind('<Double-1>',lambda _:self.edit())
        actions=ttk.Frame(frame);actions.grid(row=10,column=0,columnspan=3,sticky='w',pady=10)
        for label,command in [('Incluir / excluir',self.toggle),('Editar item / ver origem',self.edit),('Só IDs oficiais',self.confirmed),('Exportar JSON',self.save),('Salvar só relatório',self.report),('Abrir saída',self.open_output)]:ttk.Button(actions,text=label,command=command).pack(side='left',padx=(0,8))
        self.status=tk.StringVar(value='Selecione a pasta e o executável.');ttk.Label(frame,textvariable=self.status,wraplength=1000).grid(row=11,column=0,columnspan=3,sticky='w')
        self.log=tk.Text(frame,height=5,font=('Consolas',9),state='disabled');self.log.grid(row=12,column=0,columnspan=3,sticky='ew',pady=(10,0))
        root.after(100,self.poll)
    def choose_folder(self):
        path=filedialog.askdirectory(parent=self.root)
        if path:
            self.folder.set(path)
            self.appid.set(detect_app_id(path))
            self.output.set(str(Path.home()/'Desktop'/(Path(path).name+'-achievements-'+datetime.now().strftime('%Y%m%d-%H%M%S'))))
    def choose_exe(self):
        path=filedialog.askopenfilename(parent=self.root,initialdir=self.folder.get() or None,filetypes=[('Executável Windows','*.exe')])
        if path:self.exe.set(path)
    def choose_metadata(self):
        path=filedialog.askopenfilename(parent=self.root,filetypes=[('Metadados locais','*.json *.vdf *.bin'),('Todos','*')])
        if path:self.metadata.set(path)
    def choose_output(self):
        parent=filedialog.askdirectory(parent=self.root)
        if parent:self.output.set(str(Path(parent)/('achievements-'+datetime.now().strftime('%Y%m%d-%H%M%S'))))
    def start(self):
        if self.scan_button['state']=='disabled' or self.lookup_busy:return
        folder,exe,language,metadata=self.folder.get(),self.exe.get(),self.language.get(),self.metadata.get() or None
        self.cancel.clear();self.scan_button.configure(state='disabled');self.status.set('Analisando…')
        def work():
            try:self.events.put(('result',scan(folder,exe,language,metadata,lambda s:self.events.put(('log',s)),self.cancel)))
            except Exception as e:self.events.put(('error',str(e)))
        threading.Thread(target=work,daemon=True).start()
    def lookup(self):
        if not self.result or self.lookup_busy or self.scan_button['state']=='disabled':return
        ident,language=self.appid.get(),self.language.get()
        import copy
        snapshot=copy.deepcopy(self.result)
        self.lookup_busy=True;self.lookup_button.configure(state='disabled');self.status.set('Consultando textos oficiais da Steam…')
        def work():
            try:self.events.put(('official',enrich(snapshot,fetch(ident,language))))
            except Exception as e:self.events.put(('lookup_error',str(e)))
        threading.Thread(target=work,daemon=True).start()
    def poll(self):
        while True:
            try:kind,value=self.events.get_nowait()
            except queue.Empty:break
            if kind=='log':
                self.log.configure(state='normal');self.log.insert('end',value+'\n');self.log.see('end');self.log.configure(state='disabled')
            elif kind in ('official','lookup_error'):
                self.lookup_busy=False;self.lookup_button.configure(state='normal')
                if kind=='official':
                    self.result=value;self.refresh();self.status.set(value['warnings'][-1])
                else:
                    self.status.set(value);messagebox.showwarning('Textos oficiais',value,parent=self.root)
            elif kind=='result':
                self.result=value;self.refresh();self.scan_button.configure(state='normal')
                if not value['entries']:self.status.set('Nenhuma definição recuperada. Tente fornecer um schema local no campo de metadados extras.')
            else:self.scan_button.configure(state='normal');self.status.set(value);messagebox.showerror('Extração',value,parent=self.root)
        self.root.after(100,self.poll)
    def refresh(self):
        self.table.delete(*self.table.get_children())
        labels={'title':'nome','description':'descrição','hidden':'secreta','icon':'ícone'}
        for i,row in enumerate(self.result['entries']):self.table.insert('','end',iid=str(i),values=('✓' if row['selected'] else '',row['source_id'],row['title'],row['description'],', '.join(labels.get(x,x.replace('conflict:','conflito: ')) for x in row['review'])))
        self.status.set(f'{len(self.result["entries"])} IDs · {sum(r["selected"] for r in self.result["entries"])} selecionadas · {len(self.result["warnings"])} avisos. Candidatos de strings nativas exigem seleção manual.')
    def selected(self):
        values=self.table.selection()
        return self.result['entries'][int(values[0])] if values and self.result else None
    def confirmed(self):
        if not self.result or self.lookup_busy:return
        try:select_confirmed(self.result);self.refresh()
        except ValueError as e:messagebox.showinfo('IDs oficiais',str(e),parent=self.root)
    def toggle(self):
        if self.lookup_busy:return
        row=self.selected()
        if row:row['selected']=not row['selected'];self.refresh()
    def edit(self):
        if self.lookup_busy:return
        row=self.selected()
        if not row:return
        dialog=tk.Toplevel(self.root);dialog.title(row['source_id']);dialog.geometry('760x540');dialog.transient(self.root);dialog.grab_set()
        frame=ttk.Frame(dialog,padding=16);frame.pack(fill='both',expand=True);frame.columnconfigure(1,weight=1)
        variables={key:tk.StringVar(value=row[key]) for key in ('title','description','icon')}
        for i,key in enumerate(variables):
            ttk.Label(frame,text={'title':'Nome','description':'Descrição','icon':'Ícone local'}[key]).grid(row=i,column=0,sticky='w',pady=8)
            ttk.Entry(frame,textvariable=variables[key]).grid(row=i,column=1,sticky='ew')
        hidden=tk.BooleanVar(value=row['hidden']);ttk.Checkbutton(frame,text='Secreta',variable=hidden).grid(row=3,column=1,sticky='w')
        def icon():
            path=filedialog.askopenfilename(parent=dialog,filetypes=[('Imagem local','*.png *.jpg *.jpeg')])
            if path:variables['icon'].set(path)
        ttk.Button(frame,text='Escolher ícone…',command=icon).grid(row=3,column=0,sticky='w')
        info=tk.Text(frame,height=13,wrap='word');info.grid(row=4,column=0,columnspan=2,sticky='nsew',pady=10);info.insert('1.0',json.dumps({'origens':row['evidence'],'revisar':row['review'],'textos_oficiais':row.get('official_texts',{})},ensure_ascii=False,indent=2));info.configure(state='disabled')
        def save():
            changed={k for k,v in variables.items() if v.get()!=row[k]}
            if hidden.get()!=row['hidden']:changed.add('hidden')
            row['manual_fields']=sorted(set(row.get('manual_fields',[]))|changed)
            row.update({k:v.get() for k,v in variables.items()});row['hidden']=hidden.get();row['selected']=True;row['user_reviewed']=True;row['review']=[];self.refresh();dialog.destroy()
        ttk.Button(frame,text='Salvar revisão e incluir',command=save).grid(row=5,column=1,sticky='e')
    def save(self):
        try:
            if self.lookup_busy:raise ValueError('Aguarde a consulta oficial antes de exportar.')
            if not self.result:raise ValueError('Faça uma análise primeiro.')
            path=export(self.result,self.output.get());self.status.set('Exportado: '+str(path));messagebox.showinfo('JSON pronto','No Port Station: Conquistas → Importar catálogo JSON → achievements.json.\n\nA platina pode ser acrescentada no Port Station.',parent=self.root)
        except Exception as e:messagebox.showerror('Exportação',str(e),parent=self.root)
    def open_output(self):
        import os
        path=Path(self.output.get())
        if path.is_dir():os.startfile(path)
    def report(self):
        try:
            if not self.result:raise ValueError('Faça uma análise primeiro.')
            path=save_report(self.result,self.output.get());self.status.set('Relatório salvo: '+str(path))
        except Exception as e:messagebox.showerror('Relatório',str(e),parent=self.root)

def main():
    root=tk.Tk();App(root);root.mainloop()
