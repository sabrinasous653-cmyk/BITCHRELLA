"""BitchRella Windows client - login/register."""
import os, json, tkinter as tk
from tkinter import messagebox, font as tkfont
from PIL import Image, ImageTk
from network_client import NetworkClient
from chat_window import ChatWindow

BASE_DIR=os.path.dirname(os.path.abspath(__file__)); ASSETS=os.path.join(BASE_DIR,'assets')
PINK='#E85DA8'; PURPLE='#9B6FD6'; DARK='#6B4C7A'; LIGHT='#8B7A99'; WHITE='#FFFFFF'

class Login(tk.Tk):
    def __init__(self):
        super().__init__(); self.title('BitchRella'); self.geometry('1100x700'); self.minsize(900,600); self.configure(bg='#F3E6F5')
        self.client=NetworkClient(); self._remember_path=os.path.join(BASE_DIR,'remember.json'); self._build(); self._load_remembered()

    def _build(self):
        try:
            im=Image.open(os.path.join(ASSETS,'app_background.png')).convert('RGBA')
            im.thumbnail((self.winfo_screenwidth(),self.winfo_screenheight()),Image.LANCZOS)
            self.bg=ImageTk.PhotoImage(im); tk.Label(self,image=self.bg,bg='#F3E6F5').place(relx=.5,rely=.5,anchor='center')
        except Exception: pass
        card=tk.Frame(self,bg=WHITE,bd=0,highlightthickness=0); card.place(relx=.72,rely=.5,anchor='center',relwidth=.38,relheight=.76)
        try:
            logo=Image.open(os.path.join(ASSETS,'logo_transparent.png')).convert('RGBA'); logo.thumbnail((180,100)); self.logo=ImageTk.PhotoImage(logo); tk.Label(card,image=self.logo,bg=WHITE).pack(pady=(20,5))
        except Exception: tk.Label(card,text='BITCHRELLA',font=('Segoe UI',24,'bold'),fg=PINK,bg=WHITE).pack(pady=25)
        tk.Label(card,text='Bienvenue !',font=('Segoe UI',22,'bold'),fg=PURPLE,bg=WHITE).pack()
        tk.Label(card,text='Connecte-toi pour continuer',font=('Segoe UI',11),fg=LIGHT,bg=WHITE).pack(pady=(4,18))
        self.email=self._field(card,'Adresse e-mail'); self.password=self._field(card,'Mot de passe',True)
        self.remember=tk.BooleanVar(value=False)
        tk.Checkbutton(card,text='☑ Remember me',variable=self.remember,bg=WHITE,fg=DARK,
                       selectcolor='#F7C9E3',font=('Segoe UI',9)).pack(anchor='w',padx=45,pady=(0,2))
        tk.Button(card,text='Mot de passe oublié ?',command=self.forgot_password,
                  bg=WHITE,fg=PURPLE,relief='flat',font=('Segoe UI',9)).pack(anchor='e',padx=45)
        self.email.focus_set()
        tk.Button(card,text='Se connecter  →',command=self.login,bg=PINK,fg=WHITE,font=('Segoe UI',12,'bold'),relief='flat',cursor='hand2').pack(fill='x',padx=45,pady=18,ipady=10)
        tk.Label(card,text='— Ou —',fg=LIGHT,bg=WHITE).pack()
        tk.Button(card,text='Créer un compte  ＋',command=self.register,bg=WHITE,fg=PINK,font=('Segoe UI',11,'bold'),relief='flat',cursor='hand2').pack(pady=14)
        tk.Label(card,text='Serveur local : http://127.0.0.1:8000',fg=LIGHT,bg=WHITE,font=('Segoe UI',8)).pack(side='bottom',pady=12)
        self.bind('<Return>',lambda e:self.login())

    def _field(self,parent,label,password=False):
        box=tk.Frame(parent,bg=WHITE,highlightbackground='#D9B8E8',highlightthickness=1); box.pack(fill='x',padx=45,pady=7)
        var=tk.StringVar(); tk.Label(box,text=label,fg='#B9A6C4',bg=WHITE,font=('Segoe UI',9)).pack(anchor='w',padx=10,pady=(5,0))
        ent=tk.Entry(box,textvariable=var,show='•' if password else '',bd=0,relief='flat',font=('Segoe UI',11),bg=WHITE,fg=DARK); ent.pack(fill='x',padx=10,pady=(0,7)); ent.var=var; return ent

    def login(self):
        email=self.email.get().strip(); password=self.password.get()
        if not email or not password: messagebox.showwarning('BitchRella','أدخلي البريد الإلكتروني وكلمة المرور.'); return
        try:
            self.client.login(email,password)
            if self.remember.get():
                with open(self._remember_path,'w',encoding='utf8') as f: json.dump({'email':email,'password':password},f)
            elif os.path.exists(self._remember_path):
                os.remove(self._remember_path)
            self.destroy(); app=ChatWindow(self.client); app.mainloop()
        except Exception as e: messagebox.showerror('تسجيل الدخول',self._error(e))

    def _load_remembered(self):
        try:
            with open(self._remember_path,encoding='utf8') as f: d=json.load(f)
            self.email.insert(0,d.get('email','')); self.password.insert(0,d.get('password','')); self.remember.set(True)
        except Exception: pass

    def forgot_password(self):
        messagebox.showinfo('Mot de passe oublié',
            'إعادة تعيين كلمة السر عبر البريد الإلكتروني نجهزوها في مرحلة Online، لأن الإرسال الحقيقي يحتاج خدمة بريد آمنة.',
            parent=self)

    def register(self):
        w=tk.Toplevel(self); w.title('Créer un compte'); w.geometry('430x500'); w.configure(bg=WHITE); w.transient(self); w.grab_set()
        tk.Label(w,text='Créer un compte',font=('Segoe UI',20,'bold'),fg=PURPLE,bg=WHITE).pack(pady=20)
        def f(label,pwd=False):
            tk.Label(w,text=label,fg=DARK,bg=WHITE).pack(anchor='w',padx=40); e=tk.Entry(w,show='•' if pwd else '',font=('Segoe UI',11),bd=1,relief='solid'); e.pack(fill='x',padx=40,pady=(3,12),ipady=6); return e
        username=f('Nom d’utilisateur'); email=f('Adresse e-mail'); password=f('Mot de passe',True); confirm=f('Confirmer le mot de passe',True)
        def go():
            if password.get()!=confirm.get(): messagebox.showerror('Erreur','Les mots de passe ne correspondent pas.',parent=w); return
            try:
                self.client.register(username.get().strip(),email.get().strip(),password.get()); w.destroy(); self.destroy(); ChatWindow(self.client).mainloop()
            except Exception as e: messagebox.showerror('Créer un compte',self._error(e),parent=w)
        tk.Button(w,text='Créer le compte',command=go,bg=PINK,fg=WHITE,font=('Segoe UI',11,'bold'),relief='flat').pack(fill='x',padx=40,pady=15,ipady=8)

    @staticmethod
    def _error(e):
        try:return e.response.json().get('detail',str(e))
        except Exception:return 'تعذر الاتصال بالسيرفر. تأكدي أن السيرفر يعمل.'

if __name__=='__main__': Login().mainloop()
