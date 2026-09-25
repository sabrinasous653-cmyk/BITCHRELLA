"""BitchRella - functional chat UI connected to FastAPI/WebSocket."""
import tkinter as tk
from tkinter import messagebox
from datetime import datetime

PINK='#E85DA8'; PURPLE='#9B6FD6'; DARK='#6B4C7A'; LIGHT='#9A8AA8'; WHITE='#FFFFFF'; BG='#F3E6F5'; ROW='#FBEAF5'

class ChatWindow(tk.Tk):
    def __init__(self,client):
        super().__init__(); self.client=client; self.title('BitchRella'); self.geometry('1250x760'); self.minsize(950,600); self.configure(bg=BG)
        self.conversations=[]; self.active=None; self.msg_widgets=[]; self.last_message_id=None; self._build(); self.client.start(); self.after(100,self.check_queue); self.load_conversations()
        self.protocol('WM_DELETE_WINDOW',self.close)

    def _build(self):
        top=tk.Frame(self,bg=WHITE,height=62); top.pack(fill='x'); top.pack_propagate(False)
        tk.Label(top,text='BITCHRELLA',font=('Segoe UI',19,'bold'),fg=PINK,bg=WHITE).pack(side='left',padx=22)
        tk.Label(top,text=f'@{self.client.username}',font=('Segoe UI',10),fg=LIGHT,bg=WHITE).pack(side='left')
        self.status=tk.Label(top,text='● Offline',font=('Segoe UI',10,'bold'),fg='#999',bg=WHITE); self.status.pack(side='right',padx=22)
        body=tk.Frame(self,bg=BG); body.pack(fill='both',expand=True,padx=12,pady=12)
        left=tk.Frame(body,bg=WHITE,width=300); left.pack(side='left',fill='y'); left.pack_propagate(False)
        tk.Label(left,text='Discussions ♡',font=('Segoe UI',17,'bold'),fg=PURPLE,bg=WHITE).pack(anchor='w',padx=18,pady=(18,10))
        search=tk.Entry(left,bd=0,highlightbackground='#E6D4EC',highlightthickness=1,font=('Segoe UI',10)); search.pack(fill='x',padx=15,pady=(0,12),ipady=8); search.insert(0,'Rechercher...'); search.bind('<Return>',lambda e:self.search(search.get()))
        self.conv_list=tk.Frame(left,bg=WHITE); self.conv_list.pack(fill='both',expand=True)
        tk.Button(left,text='＋ Nouvelle conversation',command=self.new_chat,bg=PINK,fg=WHITE,relief='flat',font=('Segoe UI',10,'bold')).pack(fill='x',padx=15,pady=15,ipady=8)
        right=tk.Frame(body,bg='#FCF8FD'); right.pack(side='left',fill='both',expand=True,padx=(10,0))
        self.header=tk.Frame(right,bg=WHITE,height=70); self.header.pack(fill='x'); self.header.pack_propagate(False)
        self.chat_title=tk.Label(self.header,text='Choisis une conversation',font=('Segoe UI',15,'bold'),fg=DARK,bg=WHITE); self.chat_title.pack(anchor='w',padx=20,pady=(13,0))
        self.chat_status=tk.Label(self.header,text='',font=('Segoe UI',9),fg='#5FBF6B',bg=WHITE); self.chat_status.pack(anchor='w',padx=20)
        area=tk.Frame(right,bg='#FCF8FD'); area.pack(fill='both',expand=True)
        self.canvas=tk.Canvas(area,bg='#FCF8FD',highlightthickness=0); scroll=tk.Scrollbar(area,command=self.canvas.yview); self.canvas.configure(yscrollcommand=scroll.set); self.canvas.pack(side='left',fill='both',expand=True); scroll.pack(side='right',fill='y')
        self.messages_frame=tk.Frame(self.canvas,bg='#FCF8FD'); self.win=self.canvas.create_window((0,0),window=self.messages_frame,anchor='nw'); self.messages_frame.bind('<Configure>',lambda e:self.canvas.configure(scrollregion=self.canvas.bbox('all'))); self.canvas.bind('<Configure>',lambda e:self.canvas.itemconfigure(self.win,width=e.width))
        bottom=tk.Frame(right,bg=WHITE,height=64); bottom.pack(fill='x'); bottom.pack_propagate(False)
        self.input=tk.Entry(bottom,font=('Segoe UI',11),bd=0,bg='#F8F1FA',fg=DARK); self.input.pack(side='left',fill='both',expand=True,padx=(14,6),pady=12,ipady=8); self.input.bind('<Return>',lambda e:self.send())
        self.input.bind('<KeyRelease>',self.typing)
        tk.Button(bottom,text='➤',command=self.send,bg=PINK,fg=WHITE,relief='flat',font=('Segoe UI',14,'bold')).pack(side='right',padx=12,pady=12,ipadx=12)

    def load_conversations(self):
        try:self.conversations=self.client.get_conversations(); self.render_conversations()
        except Exception as e: self.status.config(text='● Serveur indisponible',fg='#C66')

    def render_conversations(self):
        for w in self.conv_list.winfo_children():w.destroy()
        for c in self.conversations:
            name=c.get('name') or 'Conversation privée'; last=c.get('last_message') or 'Aucun message';
            b=tk.Button(self.conv_list,text=f'{name}\n{last[:35]}',anchor='w',justify='left',command=lambda x=c:self.open_conversation(x),bg=ROW if c['conversation_id']==self.active else WHITE,fg=DARK,relief='flat',font=('Segoe UI',10,'bold'),height=3)
            b.pack(fill='x',padx=8,pady=2)

    def open_conversation(self,c):
        self.active=c['conversation_id']; self.chat_title.config(text=c.get('name') or 'Conversation privée'); self.chat_status.config(text='En ligne' if c.get('type')=='private' else 'Groupe'); self.render_conversations(); self.clear_messages()
        try:
            msgs=self.client.get_messages(self.active); [self.add_message(m) for m in msgs]; self.client.send_read(msgs[-1]['id']) if msgs else None; self.after(50,lambda:self.canvas.yview_moveto(1))
        except Exception as e: messagebox.showerror('Messages',str(e))

    def clear_messages(self):
        for w in self.messages_frame.winfo_children():w.destroy()

    def add_message(self,m):
        mine=m['sender_id']==self.client.user_id
        row=tk.Frame(self.messages_frame,bg='#FCF8FD'); row.pack(fill='x',padx=18,pady=5)
        bubble=tk.Label(row,text=m['content'],font=('Segoe UI',10),bg='#E9D7F1' if not mine else '#F7C9E3',fg=DARK,justify='left',wraplength=520,padx=12,pady=8)
        bubble.pack(side='right' if mine else 'left')
        time_txt=m.get('sent_at','').replace('T',' ')[:16]
        tk.Label(row,text=time_txt,fg=LIGHT,bg='#FCF8FD',font=('Segoe UI',7)).pack(side='right' if mine else 'left',padx=6,anchor='s')
        if mine:
            tk.Label(row,text='✓✓',fg=PURPLE,bg='#FCF8FD',font=('Segoe UI',8,'bold')).pack(side='right')

    def send(self):
        if not self.active:return
        text=self.input.get().strip()
        if not text:return
        self.client.send_message(self.active,text); self.input.delete(0,'end')

    def typing(self,event):
        if self.active:self.client.send_typing(self.active)

    def check_queue(self):
        try:
            while True:
                data=self.client.incoming.get_nowait(); typ=data.get('type'); p=data.get('payload',{})
                if typ=='connection': self.status.config(text='● Online' if p.get('status')=='online' else '● Offline',fg='#5FBF6B' if p.get('status')=='online' else '#999')
                elif typ=='message':
                    m=p
                    if m.get('conversation_id')==self.active:self.add_message(m); self.canvas.update_idletasks(); self.canvas.yview_moveto(1); self.client.send_read(m['id'])
                    self.load_conversations()
                elif typ=='typing' and p.get('conversation_id')==self.active:
                    self.chat_status.config(text='écrit maintenant...'); self.after(1800,lambda:self.chat_status.config(text='En ligne'))
                elif typ=='presence':
                    if self.active:self.chat_status.config(text='En ligne' if p.get('is_online') else 'Hors ligne')
        except Exception: pass
        self.after(100,self.check_queue)

    def new_chat(self):
        w=tk.Toplevel(self); w.title('Nouvelle conversation'); w.geometry('430x260'); w.configure(bg=WHITE); tk.Label(w,text='Rechercher un utilisateur',font=('Segoe UI',13,'bold'),fg=PURPLE,bg=WHITE).pack(pady=18); e=tk.Entry(w,font=('Segoe UI',11)); e.pack(fill='x',padx=35,pady=8,ipady=7); results=tk.Listbox(w,font=('Segoe UI',10)); results.pack(fill='both',expand=True,padx=35,pady=8)
        def go():
            results.delete(0,'end')
            try:
                for u in self.client.search_users(e.get()): results.insert('end',f"{u['id']} | {u['username']}")
            except Exception as ex: messagebox.showerror('بحث',str(ex),parent=w)
        def select(ev):
            if not results.curselection():return
            uid=int(results.get(results.curselection()[0]).split('|')[0].strip())
            try:
                cid=self.client.create_private(uid); w.destroy(); self.load_conversations(); self.after(200,lambda:self.open_by_id(cid))
            except Exception as ex:messagebox.showerror('Conversation',str(ex),parent=w)
        e.bind('<Return>',lambda ev:go()); results.bind('<Double-Button-1>',select); tk.Button(w,text='Rechercher',command=go,bg=PINK,fg=WHITE,relief='flat').pack(pady=8)

    def open_by_id(self,cid):
        for c in self.conversations:
            if c['conversation_id']==cid:self.open_conversation(c);return
        self.load_conversations()

    def search(self,q): pass
    def close(self): self.client.stop(); self.destroy()

if __name__=='__main__':
    messagebox.showinfo('BitchRella','Lance main.py pour تسجيل الدخول.')
