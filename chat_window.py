"""BitchRella - functional chat UI connected to FastAPI/WebSocket."""
import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
from PIL import Image, ImageTk
import os, json, webbrowser, io, requests

PINK='#E85DA8'
PURPLE='#9B6FD6'
DARK='#6B4C7A'
LIGHT='#9A8AA8'
WHITE='#FFFFFF'
BG='#F3E6F5'
ROW='#FBEAF5'


class ChatWindow(tk.Tk):
    def __init__(self, client):
        super().__init__()
        self.client = client
        self.title('BitchRella')
        self.geometry('1250x760')
        self.minsize(950, 600)
        self.configure(bg=BG)

        self.conversations = []
        self.active = None
        self.last_message_id = None
        self.reply_to = None
        self.favorite_ids = set()
        self.dark_mode = False
        self.profile_data = {}
        self.profile_local_path = os.path.join(os.path.dirname(__file__), "profile.json")

        try:
            with open(self.profile_local_path, encoding="utf8") as f: self.profile_data=json.load(f)
        except Exception: self.profile_data={}
        self._build()
        self.client.start()
        self.after(100, self.check_queue)
        self.load_conversations()
        self.protocol('WM_DELETE_WINDOW', self.close)

    def _build(self):
        top = tk.Frame(self, bg=WHITE, height=62)
        top.pack(fill='x')
        top.pack_propagate(False)

        tk.Label(
            top, text='BITCHRELLA',
            font=('Segoe UI', 19, 'bold'),
            fg=PINK, bg=WHITE
        ).pack(side='left', padx=22)

        tk.Label(
            top, text=f'@{self.client.username}',
            font=('Segoe UI', 10),
            fg=LIGHT, bg=WHITE
        ).pack(side='left')

        self.profile_button = tk.Button(top, text='👤 Profile', command=self.open_profile,
                  bg=WHITE, fg=PURPLE, relief='flat',
                  font=('Segoe UI', 9, 'bold'))
        self.profile_button.pack(side='right', padx=(4, 4))

        tk.Button(top, text='⚙ Settings', command=self.open_settings,
                  bg=WHITE, fg=PURPLE, relief='flat',
                  font=('Segoe UI', 9, 'bold')).pack(side='right', padx=(4,10))
        self.status = tk.Label(
            top, text='● Offline',
            font=('Segoe UI', 10, 'bold'),
            fg='#999', bg=WHITE
        )
        self.status.pack(side='right', padx=8)

        body = tk.Frame(self, bg=BG)
        body.pack(fill='both', expand=True, padx=12, pady=12)

        left = tk.Frame(body, bg=WHITE, width=300)
        left.pack(side='left', fill='y')
        left.pack_propagate(False)

        tk.Label(
            left, text='Discussions ♡',
            font=('Segoe UI', 17, 'bold'),
            fg=PURPLE, bg=WHITE
        ).pack(anchor='w', padx=18, pady=(18, 10))

        self.search_entry = tk.Entry(
            left,
            bd=0,
            highlightbackground='#E6D4EC',
            highlightthickness=1,
            font=('Segoe UI', 10),
            fg=DARK
        )
        self.search_entry.pack(fill='x', padx=15, pady=(0, 12), ipady=8)
        self.search_entry.insert(0, 'Rechercher...')
        self.search_entry.bind('<FocusIn>', self._clear_search_placeholder)
        self.search_entry.bind('<Return>', lambda e: self.search(self.search_entry.get()))

        self.conv_list = tk.Frame(left, bg=WHITE)
        self.conv_list.pack(fill='both', expand=True)

        tk.Button(
            left,
            text='⭐ Favorites',
            command=self.show_favorites,
            bg='#FFF4C9', fg=DARK,
            relief='flat',
            font=('Segoe UI', 10, 'bold')
        ).pack(fill='x', padx=15, pady=(5, 5), ipady=7)

        tk.Button(
            left,
            text='👥 Contacts',
            command=self.open_contacts,
            bg='#F1E6F7', fg=PURPLE,
            relief='flat',
            font=('Segoe UI', 10, 'bold')
        ).pack(fill='x', padx=15, pady=(8, 5), ipady=7)

        tk.Button(
            left,
            text='＋ Nouvelle conversation',
            command=self.new_chat,
            bg=PINK, fg=WHITE,
            relief='flat',
            font=('Segoe UI', 10, 'bold')
        ).pack(fill='x', padx=15, pady=(5, 15), ipady=8)

        right = tk.Frame(body, bg='#FCF8FD')
        right.pack(side='left', fill='both', expand=True, padx=(10, 0))

        self.header = tk.Frame(right, bg=WHITE, height=70)
        self.header.pack(fill='x')
        self.header.pack_propagate(False)

        self.favorite_button = tk.Button(self.header, text='☆', command=self.toggle_favorite,
                  bg=WHITE, fg='#E3B400', relief='flat', font=('Segoe UI', 18, 'bold'))
        self.favorite_button.pack(side='right', padx=14)

        self.chat_title = tk.Label(
            self.header,
            text='Choisis une conversation',
            font=('Segoe UI', 15, 'bold'),
            fg=DARK, bg=WHITE
        )
        self.chat_title.pack(anchor='w', padx=20, pady=(13, 0))

        self.chat_status = tk.Label(
            self.header,
            text='',
            font=('Segoe UI', 9),
            fg='#5FBF6B', bg=WHITE
        )
        self.chat_status.pack(anchor='w', padx=20)

        area = tk.Frame(right, bg='#FCF8FD')
        area.pack(fill='both', expand=True)

        self.canvas = tk.Canvas(
            area, bg='#FCF8FD', highlightthickness=0
        )
        scroll = tk.Scrollbar(area, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scroll.set)
        self.canvas.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')

        # Keep the original wallpaper/design.
        wallpaper_path = os.path.join(
            os.path.dirname(__file__),
            'assets',
            'chat_wallpaper.png'
        )
        self.wallpaper_original = Image.open(wallpaper_path).convert('RGB')
        self.wallpaper_photo = None
        self.wallpaper_item = self.canvas.create_image(
            0, 0, anchor='nw'
        )
        self.message_y = 24
        self.canvas.bind('<Configure>', self._resize_wallpaper)

        bottom = tk.Frame(right, bg=WHITE, height=64)
        bottom.pack(fill='x')
        bottom.pack_propagate(False)

        self.input = tk.Entry(
            bottom,
            font=('Segoe UI', 11),
            bd=0,
            bg='#F8F1FA',
            fg=DARK
        )
        self.input.pack(
            side='left', fill='both', expand=True,
            padx=(14, 6), pady=12, ipady=8
        )
        self.input.bind('<Return>', lambda e: self.send())
        self.input.bind('<KeyRelease>', self.typing)

        tk.Button(bottom, text='😀', command=self.insert_emoji,
                  bg=WHITE, fg=PURPLE, relief='flat',
                  font=('Segoe UI', 12, 'bold')).pack(side='right', padx=2)
        tk.Button(bottom, text='📎', command=self.attach_file,
                  bg=WHITE, fg=PURPLE, relief='flat',
                  font=('Segoe UI', 12, 'bold')).pack(side='right', padx=2)

        tk.Button(
            bottom, text='➤',
            command=self.send,
            bg=PINK, fg=WHITE,
            relief='flat',
            font=('Segoe UI', 14, 'bold')
        ).pack(side='right', padx=12, pady=12, ipadx=12)

    def _clear_search_placeholder(self, event=None):
        if self.search_entry.get() == 'Rechercher...':
            self.search_entry.delete(0, 'end')

    def load_conversations(self):
        try:
            self.conversations = self.client.get_conversations()
            self.render_conversations()
        except Exception:
            self.status.config(
                text='● Serveur indisponible',
                fg='#C66'
            )

    def render_conversations(self, conversations=None):
        if conversations is None:
            conversations = self.conversations

        for w in self.conv_list.winfo_children():
            w.destroy()

        for c in conversations:
            name = c.get('name') or 'Conversation privée'
            last = c.get('last_message') or 'Aucun message'

            b = tk.Button(
                self.conv_list,
                text=f'{name}\n{last[:35]}',
                anchor='w',
                justify='left',
                command=lambda x=c: self.open_conversation(x),
                bg=ROW if c['conversation_id'] == self.active else WHITE,
                fg=DARK,
                relief='flat',
                font=('Segoe UI', 10, 'bold'),
                height=3
            )
            b.pack(fill='x', padx=8, pady=2)

    def open_conversation(self, c):
        self.active = c['conversation_id']
        self.chat_title.config(
            text=c.get('name') or 'Conversation privée'
        )
        self.chat_status.config(
            text='En ligne' if c.get('type') == 'private' else 'Groupe'
        )
        try:
            self.favorite_ids = set(self.client.get_favorite_ids())
            self.favorite_button.config(text='★' if self.active in self.favorite_ids else '☆')
        except Exception:
            self.favorite_button.config(text='☆')
        self.render_conversations()
        self.clear_messages()

        try:
            msgs = self.client.get_messages(self.active)
            for m in msgs:
                self.add_message(m)

            if msgs:
                self.client.send_read(msgs[-1]['id'])

            self.after(50, lambda: self.canvas.yview_moveto(1))
        except Exception as e:
            messagebox.showerror('Messages', str(e))

    def _resize_wallpaper(self, event=None):
        w = max(1, self.canvas.winfo_width())
        h = max(1, self.canvas.winfo_height())

        img = self.wallpaper_original.resize(
            (w, h), Image.Resampling.LANCZOS
        )
        self.wallpaper_photo = ImageTk.PhotoImage(img)
        self.canvas.itemconfigure(
            self.wallpaper_item,
            image=self.wallpaper_photo
        )
        self.canvas.tag_lower(self.wallpaper_item)

    def clear_messages(self):
        self.canvas.delete('message_item')
        self.message_y = 24
        self.canvas.configure(
            scrollregion=(
                0, 0,
                max(1, self.canvas.winfo_width()),
                max(1, self.canvas.winfo_height())
            )
        )

    def add_message(self, m):
        mine = m['sender_id'] == self.client.user_id

        display = m.get('content','')
        image_obj = None
        if m.get('type') == 'image':
            display = '🖼️  ' + (display.split('/')[-1] or 'Image')
            try:
                url = self.client.base_url + display.replace('🖼️  ', '', 1)
                r = requests.get(url, timeout=5)
                r.raise_for_status()
                im = Image.open(io.BytesIO(r.content)).convert('RGB')
                im.thumbnail((260, 190), Image.Resampling.LANCZOS)
                image_obj = ImageTk.PhotoImage(im)
            except Exception:
                image_obj = None
        elif m.get('type') == 'file':
            display = '📎  ' + (display.split('/')[-1] or 'Fichier')
        if m.get('edited_at'):
            display += '  (modifiée)'
        if m.get('reply_to'):
            display = '↪ Réponse à un message\n' + display

        bubble = tk.Label(
            self.canvas,
            text=display,
            image=image_obj if image_obj else None,
            compound='top',
            font=('Segoe UI', 10),
            bg='#E9D7F1' if not mine else '#F7C9E3',
            fg=DARK,
            justify='left',
            wraplength=520,
            padx=12,
            pady=8,
            cursor='hand2'
        )
        if image_obj:
            bubble.image = image_obj
        bubble.bind('<Button-3>', lambda e, msg=dict(m): self.message_menu(e, msg))

        width = max(1, self.canvas.winfo_width())
        x = width - 30 if mine else 30
        anchor = 'ne' if mine else 'nw'

        self.canvas.create_window(
            x, self.message_y,
            window=bubble,
            anchor=anchor,
            tags='message_item'
        )

        time_txt = m.get('sent_at', '').replace('T', ' ')[:16]
        tx = width - 30 if mine else 30

        self.canvas.create_text(
            tx,
            self.message_y + 38,
            text=time_txt,
            anchor='e' if mine else 'w',
            fill=LIGHT,
            font=('Segoe UI', 7),
            tags='message_item'
        )

        if mine:
            self.canvas.create_text(
                width - 8,
                self.message_y + 38,
                text='✓✓',
                anchor='e',
                fill=PURPLE,
                font=('Segoe UI', 8, 'bold'),
                tags='message_item'
            )

        self.message_y += max(
            72,
            bubble.winfo_reqheight() + 34
        )

        self.canvas.configure(
            scrollregion=(
                0, 0, width,
                max(self.message_y + 20, self.canvas.winfo_height())
            )
        )

    def send(self):
        if not self.active:
            return

        text = self.input.get().strip()
        if not text:
            return

        try:
            self.client.send_message(self.active, text, reply_to=self.reply_to)
            self.input.delete(0, 'end')
            self.reply_to = None
        except Exception as e:
            messagebox.showerror('Message', str(e))

    def message_menu(self, event, m):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label='↩ Répondre', command=lambda: self.start_reply(m))
        if m.get('type') in ('image', 'file'):
            menu.add_command(label='📂 Ouvrir le fichier', command=lambda: self.open_attachment(m))
        if m.get('sender_id') == self.client.user_id and not m.get('deleted'):
            menu.add_command(label='✏ Modifier', command=lambda: self.edit_existing(m))
            menu.add_command(label='🗑 Supprimer', command=lambda: self.delete_existing(m))
        menu.tk_popup(event.x_root, event.y_root)

    def start_reply(self, m):
        self.reply_to = int(m['id'])
        self.input.delete(0,'end')
        self.input.insert(0, '↩ ')
        self.input.focus_set()

    def edit_existing(self, m):
        value=simpledialog.askstring('Modifier', 'Nouveau texte :', initialvalue=m.get('content',''), parent=self)
        if value is None or not value.strip(): return
        try:
            self.client.edit_message(m['id'], value.strip())
            self.open_by_id(self.active)
        except Exception as ex:
            messagebox.showerror('Modifier', str(ex), parent=self)

    def delete_existing(self, m):
        if not messagebox.askyesno('Supprimer', 'Supprimer cette message ?', parent=self): return
        try:
            self.client.delete_message(m['id'])
            self.open_by_id(self.active)
        except Exception as ex:
            messagebox.showerror('Supprimer', str(ex), parent=self)

    def insert_emoji(self):
        w=tk.Toplevel(self); w.title('Emoji'); w.geometry('360x220'); w.configure(bg=WHITE); w.transient(self)
        emojis=['😀','😂','🥰','😍','😘','😊','😭','😡','😎','🤍','💗','💜','❤️','✨','🔥','🎀','🌸','👑','👍','👏','🙏','🥹','😴','🙈','💕','🫶']
        for i,e in enumerate(emojis):
            tk.Button(w,text=e,font=('Segoe UI Emoji',16),command=lambda x=e:self._put_emoji(x,w),
                      bg=WHITE,relief='flat').grid(row=i//6,column=i%6,padx=4,pady=4)
    def _put_emoji(self,e,w):
        self.input.insert('insert',e); self.input.focus_set(); w.destroy()

        def attach_file(self):
        if not self.active:
            return

        path = filedialog.askopenfilename(
            parent=self,
            title='Choisir une image ou un fichier',
            filetypes=[
                (
                    'Images',
                    '*.png *.jpg *.jpeg *.webp *.gif *.bmp *.avif'
                ),
                (
                    'Tous les fichiers',
                    '*.*'
                )
            ]
        )

        if not path:
            return

        try:
            ext = os.path.splitext(path)[1].lower()

            if ext in ('.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp', '.avif'):
                try:
                    with Image.open(path) as img:
                        img.verify()
                except Exception:
                    messagebox.showerror(
                        'Image',
                        'Cette image ne peut pas être ouverte par Pillow.',
                        parent=self
                    )
                    return

            info = self.client.upload_file(path)
            self.client.send_message(
                self.active,
                info['path'],
                msg_type=info['type']
            )

        except Exception as ex:
            messagebox.showerror(
                'Fichier',
                "Impossible d'envoyer le fichier.\n" + str(ex),
                parent=self
            )

    def show_favorites(self):
        try:
            self.favorite_ids=set(self.client.get_favorite_ids())
            fav=[c for c in self.conversations if c['conversation_id'] in self.favorite_ids]
            self.render_conversations(fav)
        except Exception as ex:
            messagebox.showerror('Favorites', str(ex), parent=self)

    def toggle_favorite(self):
        if not self.active: return
        try:
            state=self.client.toggle_favorite(self.active)
            if state: self.favorite_ids.add(self.active)
            else: self.favorite_ids.discard(self.active)
            self.favorite_button.config(text='★' if state else '☆')
            messagebox.showinfo('Favorites', 'Ajoutée ⭐' if state else 'Retirée des favoris', parent=self)
        except Exception as ex:
            messagebox.showerror('Favorites', str(ex), parent=self)

    def open_settings(self):
        w=tk.Toplevel(self); w.title('Settings'); w.geometry('460x500'); w.configure(bg=WHITE); w.transient(self)
        tk.Label(w,text='⚙ Settings',font=('Segoe UI',20,'bold'),fg=PURPLE,bg=WHITE).pack(pady=18)
        tk.Label(w,text=f'Connecté en tant que @{self.client.username}',fg=DARK,bg=WHITE,font=('Segoe UI',11)).pack(pady=4)
        dark=tk.BooleanVar(value=self.dark_mode)
        tk.Checkbutton(w,text='🌙 Dark Mode',variable=dark,command=lambda:self.set_dark(dark.get()),
                       bg=WHITE,fg=DARK,selectcolor='#E9D7F1',font=('Segoe UI',11)).pack(pady=12)
        tk.Button(w,text='👤 Mon profil',command=lambda:(w.destroy(),self.open_profile()),
                  bg='#F1E6F7',fg=PURPLE,relief='flat',font=('Segoe UI',10,'bold')).pack(fill='x',padx=55,pady=6,ipady=7)
        tk.Button(w,text='⭐ Voir mes favoris',command=lambda:(w.destroy(),self.show_favorites()),
                  bg='#FFF4C9',fg=DARK,relief='flat').pack(fill='x',padx=55,pady=6,ipady=7)
        tk.Button(w,text='➕ Ajouter un compte',command=lambda:(w.destroy(),self.add_account()),
                  bg='#F7C9E3',fg=DARK,relief='flat',font=('Segoe UI',10,'bold')).pack(fill='x',padx=55,pady=6,ipady=7)
        tk.Button(w,text='🚪 Se déconnecter',command=lambda:(w.destroy(),self.logout()),
                  bg=WHITE,fg='#C44',relief='flat',font=('Segoe UI',10,'bold')).pack(fill='x',padx=55,pady=6,ipady=7)
        tk.Button(w,text='Fermer',command=w.destroy,bg=PINK,fg=WHITE,relief='flat').pack(pady=20,ipadx=25,ipady=6)

    def open_profile(self):
        w=tk.Toplevel(self); w.title('Mon profil'); w.geometry('480x520'); w.configure(bg=WHITE); w.transient(self)
        tk.Label(w,text='👤 Mon profil',font=('Segoe UI',20,'bold'),fg=PURPLE,bg=WHITE).pack(pady=18)
        avatar_label=tk.Label(w,text='👤',font=('Segoe UI Emoji',50),bg=WHITE,fg=PURPLE); avatar_label.pack(pady=8)
        info=tk.Label(w,text=f'@{self.client.username}',font=('Segoe UI',13,'bold'),fg=DARK,bg=WHITE); info.pack()
        tk.Label(w,text='Photo de profil',font=('Segoe UI',10,'bold'),fg=DARK,bg=WHITE).pack(pady=(18,4))
        path_var=tk.StringVar(value='')
        current_avatar = None

        def show_avatar(path):
            try:
                if not path:
                    return
                if path.startswith('/uploads/'):
                    url = self.client.base_url + path
                    r = requests.get(url, timeout=8)
                    r.raise_for_status()
                    im = Image.open(io.BytesIO(r.content)).convert('RGB')
                elif os.path.isfile(path):
                    im = Image.open(path).convert('RGB')
                else:
                    return
                im.thumbnail((110,110))
                avatar_label.image = ImageTk.PhotoImage(im)
                avatar_label.config(image=avatar_label.image, text='')
            except Exception:
                pass

        try:
            prof = self.client.get_profile()
            self.profile_data = prof or {}
            current_avatar = self.profile_data.get('avatar_path') or ''
            path_var.set(current_avatar)
            show_avatar(current_avatar)
        except Exception:
            pass

        def choose():
            path=filedialog.askopenfilename(parent=w,title='Choisir une photo',filetypes=[('Images','*.png *.jpg *.jpeg *.gif *.webp *.bmp')])
            if path:
                path_var.set(path)
                show_avatar(path)
        tk.Button(w,text='📷 Choisir une photo',command=choose,bg='#F1E6F7',fg=PURPLE,relief='flat').pack(pady=6,ipadx=15,ipady=5)
        tk.Label(w,text='Bio',font=('Segoe UI',10,'bold'),fg=DARK,bg=WHITE).pack(pady=(15,4))
        bio=tk.Entry(w,font=('Segoe UI',11),bd=0,highlightbackground='#D9B8E8',highlightthickness=1); bio.pack(fill='x',padx=45,ipady=8)
        try:
            prof=self.client.get_profile()
            if prof and not bio.get():
                bio.insert(0,prof.get('bio','') or '')
        except Exception: pass

        def save():
            try:
                avatar=path_var.get().strip()
                remote=avatar

                if avatar and os.path.isfile(avatar):
                    uploaded = self.client.upload_file(avatar)
                    remote = uploaded.get('path') or uploaded.get('url')
                    if not remote:
                        raise ValueError("Le serveur n'a pas retourné le chemin de la photo.")

                if not remote:
                    remote = current_avatar or None

                self.client.update_profile(avatar_path=remote, bio=bio.get().strip())

                self.profile_data = {
                    'avatar_path': remote or '',
                    'bio': bio.get().strip()
                }
                with open(self.profile_local_path,'w',encoding='utf-8') as f:
                    json.dump(self.profile_data,f,ensure_ascii=False)

                messagebox.showinfo('Profil','Profil enregistré ✓',parent=w)
                w.destroy()
            except Exception as ex:
                messagebox.showerror('Profil',str(ex),parent=w)
        tk.Button(w,text='Enregistrer',command=save,bg=PINK,fg=WHITE,relief='flat',font=('Segoe UI',10,'bold')).pack(fill='x',padx=45,pady=20,ipady=8)
        tk.Button(w,text='Fermer',command=w.destroy,bg=WHITE,fg=PURPLE,relief='flat').pack()

    def add_account(self):
        self.client.stop()
        self.destroy()
        from main import Login
        Login().mainloop()

    def logout(self):
        self.client.stop()
        self.destroy()
        from main import Login
        Login().mainloop()

    def set_dark(self, enabled):
        self.dark_mode=enabled
        bg='#211B27' if enabled else BG
        fg='#F7EAF4' if enabled else DARK
        card='#2D2433' if enabled else WHITE
        def walk(widget):
            try:
                if isinstance(widget,(tk.Frame,tk.Label,tk.Button,tk.Checkbutton,tk.Entry)):
                    widget.configure(bg=card)
                    if 'fg' in widget.keys(): widget.configure(fg=fg)
            except Exception: pass
            for ch in widget.winfo_children(): walk(ch)
        self.configure(bg=bg); walk(self)
        self.canvas.configure(bg=bg)

    def typing(self, event):
        if self.active:
            self.client.send_typing(self.active)

    def check_queue(self):
        try:
            while True:
                data = self.client.incoming.get_nowait()
                typ = data.get('type')
                p = data.get('payload', {})

                if typ == 'connection':
                    online = p.get('status') == 'online'
                    self.status.config(
                        text='● Online' if online else '● Offline',
                        fg='#5FBF6B' if online else '#999'
                    )

                elif typ == 'message':
                    m = p
                    if m.get('conversation_id') == self.active:
                        self.add_message(m)
                        self.canvas.update_idletasks()
                        self.canvas.yview_moveto(1)
                        self.client.send_read(m['id'])
                    else:
                        sender = m.get('sender_username') or 'Nouveau message'
                        self.bell = True
                        self.status.config(text='● Nouveau message', fg='#E85DA8')
                        self.after(2500, lambda: self.status.config(text='● Online' if self.client.connected else '● Offline', fg='#5FBF6B' if self.client.connected else '#999'))
                    self.load_conversations()

                elif typ == 'typing' and p.get('conversation_id') == self.active:
                    self.chat_status.config(text='écrit maintenant...')
                    self.after(
                        1800,
                        lambda: self.chat_status.config(text='En ligne')
                    )

                elif typ == 'presence':
                    if self.active:
                        self.chat_status.config(
                            text='En ligne'
                            if p.get('is_online')
                            else 'Hors ligne'
                        )
        except Exception:
            pass

        self.after(100, self.check_queue)

    def open_contacts(self):
        w = tk.Toplevel(self)
        w.title('Contacts')
        w.geometry('520x620')
        w.minsize(460, 520)
        w.configure(bg=WHITE)

        tk.Label(w, text='Mes contacts', font=('Segoe UI', 18, 'bold'),
                 fg=PURPLE, bg=WHITE).pack(pady=(18, 8))

        tabs = tk.Frame(w, bg=WHITE)
        tabs.pack(fill='x', padx=22)
        body = tk.Frame(w, bg=WHITE)
        body.pack(fill='both', expand=True, padx=22, pady=10)

        def clear_body():
            for child in body.winfo_children(): child.destroy()

        def show_contacts():
            clear_body()
            try: contacts = self.client.get_contacts()
            except Exception as ex:
                messagebox.showerror('Contacts', str(ex), parent=w); return
            if not contacts:
                tk.Label(body, text='Aucun contact pour le moment.', fg=LIGHT, bg=WHITE,
                         font=('Segoe UI', 10)).pack(pady=25)
                return
            for c in contacts:
                row = tk.Frame(body, bg='#FCF8FD', bd=0)
                row.pack(fill='x', pady=4)
                state = '● En ligne' if c.get('is_online') else '○ Hors ligne'
                tk.Label(row, text=f"@{c['username']}", font=('Segoe UI', 11, 'bold'),
                         fg=DARK, bg='#FCF8FD').pack(side='left', padx=12, pady=10)
                tk.Label(row, text=state, font=('Segoe UI', 8),
                         fg='#5FBF6B' if c.get('is_online') else LIGHT,
                         bg='#FCF8FD').pack(side='left')
                tk.Button(row, text='Ouvrir', command=lambda uid=c['id']: open_chat(uid),
                          bg=PINK, fg=WHITE, relief='flat', font=('Segoe UI', 9, 'bold')).pack(side='right', padx=8, pady=7)

        def open_chat(uid):
            try:
                cid = self.client.create_private(int(uid)); w.destroy()
                self.load_conversations(); self.after(150, lambda: self.open_by_id(cid))
            except Exception as ex: messagebox.showerror('Conversation', str(ex), parent=w)

        def show_requests():
            clear_body()
            try: requests_ = self.client.get_pending_contacts()
            except Exception as ex:
                messagebox.showerror('Demandes', str(ex), parent=w); return
            if not requests_:
                tk.Label(body, text='Aucune demande en attente.', fg=LIGHT, bg=WHITE,
                         font=('Segoe UI', 10)).pack(pady=25); return
            for r in requests_:
                row = tk.Frame(body, bg='#FCF8FD'); row.pack(fill='x', pady=4)
                tk.Label(row, text=f"@{r['username']}", font=('Segoe UI', 11, 'bold'),
                         fg=DARK, bg='#FCF8FD').pack(side='left', padx=12, pady=10)
                tk.Button(row, text='✓ Accepter',
                          command=lambda uid=r['id']: respond(uid, True), bg=PINK, fg=WHITE,
                          relief='flat', font=('Segoe UI', 9, 'bold')).pack(side='right', padx=(3,8), pady=7)
                tk.Button(row, text='Refuser',
                          command=lambda uid=r['id']: respond(uid, False), bg='#EEE6F1', fg=DARK,
                          relief='flat', font=('Segoe UI', 9)).pack(side='right', padx=3, pady=7)

        def respond(uid, accept):
            try:
                self.client.respond_contact_request(uid, accept)
                show_requests()
            except Exception as ex: messagebox.showerror('Demande', str(ex), parent=w)

        def add_contact():
            q = add_entry.get().strip()
            if not q: return
            try: users = self.client.search_users(q)
            except Exception as ex:
                messagebox.showerror('Ajouter', str(ex), parent=w); return
            clear_body()
            for u in users:
                row=tk.Frame(body,bg='#FCF8FD'); row.pack(fill='x',pady=4)
                tk.Label(row,text=f"@{u['username']}",font=('Segoe UI',10,'bold'),fg=DARK,bg='#FCF8FD').pack(side='left',padx=12,pady=10)
                tk.Button(row,text='＋ Ajouter',command=lambda uid=u['id']: send_request(uid),bg=PINK,fg=WHITE,relief='flat',font=('Segoe UI',9,'bold')).pack(side='right',padx=8,pady=7)
            if not users: tk.Label(body,text='Aucun utilisateur trouvé.',fg=LIGHT,bg=WHITE).pack(pady=20)

        def send_request(uid):
            try:
                self.client.send_contact_request(uid)
                messagebox.showinfo('Contacts', 'Demande envoyée ✓', parent=w)
            except Exception as ex: messagebox.showerror('Ajouter', str(ex), parent=w)

        search_box=tk.Frame(w,bg=WHITE); search_box.pack(fill='x',padx=22,pady=5)
        add_entry=tk.Entry(search_box,font=('Segoe UI',10),bd=0,highlightbackground='#E6D4EC',highlightthickness=1)
        add_entry.pack(side='left',fill='x',expand=True,ipady=7)
        tk.Button(search_box,text='Ajouter',command=add_contact,bg=PINK,fg=WHITE,relief='flat',font=('Segoe UI',9,'bold')).pack(side='right',padx=(7,0),ipadx=8,ipady=4)
        tk.Button(tabs,text='Contacts',command=show_contacts,bg=WHITE,fg=PURPLE,relief='flat',font=('Segoe UI',10,'bold')).pack(side='left',padx=4)
        tk.Button(tabs,text='Demandes',command=show_requests,bg=WHITE,fg=PURPLE,relief='flat',font=('Segoe UI',10,'bold')).pack(side='left',padx=4)
        show_contacts()

    def new_chat(self):
        w = tk.Toplevel(self)
        w.title('Nouvelle conversation')
        w.geometry('470x560')
        w.minsize(430, 500)
        w.configure(bg=WHITE)

        tk.Label(
            w, text='Nouvelle conversation',
            font=('Segoe UI', 16, 'bold'),
            fg=PURPLE, bg=WHITE
        ).pack(pady=(18, 10))

        mode = tk.StringVar(value='private')
        mode_frame = tk.Frame(w, bg=WHITE)
        mode_frame.pack(fill='x', padx=28)

        tk.Radiobutton(
            mode_frame, text='Conversation privée', variable=mode, value='private',
            bg=WHITE, fg=DARK, selectcolor='#F7C9E3',
            font=('Segoe UI', 10, 'bold'), command=lambda: refresh_mode()
        ).pack(side='left', padx=4)
        tk.Radiobutton(
            mode_frame, text='Créer un groupe', variable=mode, value='group',
            bg=WHITE, fg=DARK, selectcolor='#E9D7F1',
            font=('Segoe UI', 10, 'bold'), command=lambda: refresh_mode()
        ).pack(side='left', padx=4)

        group_name = tk.Entry(w, font=('Segoe UI', 11), bd=0,
                              highlightbackground='#E6D4EC', highlightthickness=1)
        group_name.insert(0, 'Nom du groupe')

        search_frame = tk.Frame(w, bg=WHITE)
        search_entry = tk.Entry(search_frame, font=('Segoe UI', 11), bd=0,
                                highlightbackground='#E6D4EC', highlightthickness=1)
        search_entry.pack(side='left', fill='x', expand=True, ipady=7)
        results = tk.Frame(w, bg=WHITE)
        results.pack(fill='both', expand=True, padx=28, pady=8)

        found_users = []
        selected = {}

        def refresh_mode():
            is_group = mode.get() == 'group'
            if is_group:
                group_name.pack(fill='x', padx=28, pady=(14, 8), ipady=7)
                search_frame.pack(fill='x', padx=28, pady=4)
                title.config(text='Rechercher et sélectionner les membres')
                action.config(text='Créer le groupe', command=create_group)
                go()
            else:
                group_name.pack_forget()
                search_frame.pack(fill='x', padx=28, pady=8)
                title.config(text='Rechercher un utilisateur')
                action.config(text='Ouvrir la conversation', command=select_private)
                go()

        title = tk.Label(w, text='Rechercher un utilisateur',
                         font=('Segoe UI', 10, 'bold'), fg=DARK, bg=WHITE)
        title.pack(pady=(8, 0))

        def clear_results():
            for child in results.winfo_children():
                child.destroy()

        def go(event=None):
            clear_results()
            found_users.clear()
            q = search_entry.get().strip()
            if not q:
                return
            try:
                found_users.extend(self.client.search_users(q))
                if not found_users:
                    tk.Label(results, text='Aucun utilisateur trouvé.', bg=WHITE, fg=LIGHT).pack(pady=15)
                    return
                for u in found_users:
                    if mode.get() == 'group':
                        var = tk.BooleanVar(value=selected.get(u['id'], False))
                        selected[u['id']] = var.get()
                        cb = tk.Checkbutton(
                            results, text=f"@{u['username']}", variable=var,
                            command=lambda uid=u['id'], v=var: selected.__setitem__(uid, v.get()),
                            anchor='w', bg=WHITE, fg=DARK, selectcolor='#F7C9E3',
                            font=('Segoe UI', 10), relief='flat'
                        )
                        cb.pack(fill='x', pady=2)
                    else:
                        tk.Button(
                            results, text=f"@{u['username']}", anchor='w',
                            command=lambda uid=u['id']: select_private(uid),
                            bg=WHITE, fg=DARK, relief='flat',
                            font=('Segoe UI', 10, 'bold')
                        ).pack(fill='x', pady=2)
            except Exception as ex:
                messagebox.showerror('Recherche', str(ex), parent=w)

        def select_private(uid=None):
            if uid is None:
                if not found_users:
                    messagebox.showwarning('Conversation', 'Recherche un utilisateur d’abord.', parent=w)
                    return
                uid = found_users[0]['id']
            try:
                cid = self.client.create_private(int(uid))
                w.destroy()
                self.load_conversations()
                self.after(200, lambda: self.open_by_id(cid))
            except Exception as ex:
                messagebox.showerror('Conversation', str(ex), parent=w)

        def create_group():
            name = group_name.get().strip()
            if name == 'Nom du groupe':
                name = ''
            members = [int(uid) for uid, checked in selected.items() if checked]
            if not name:
                messagebox.showwarning('Groupe', 'Donne un nom au groupe.', parent=w)
                return
            if not members:
                messagebox.showwarning('Groupe', 'Sélectionne au moins un membre.', parent=w)
                return
            try:
                cid = self.client.create_group(name, members)
                w.destroy()
                self.load_conversations()
                self.after(200, lambda: self.open_by_id(cid))
            except Exception as ex:
                messagebox.showerror('Groupe', str(ex), parent=w)

        search_entry.bind('<Return>', go)
        tk.Button(
            search_frame, text='Rechercher', command=go,
            bg=PINK, fg=WHITE, relief='flat',
            font=('Segoe UI', 9, 'bold')
        ).pack(side='right', padx=(7, 0), ipadx=8, ipady=4)

        action = tk.Button(
            w, text='Ouvrir la conversation', command=select_private,
            bg=PINK, fg=WHITE, relief='flat',
            font=('Segoe UI', 10, 'bold')
        )
        action.pack(fill='x', padx=28, pady=(6, 10), ipady=8)

        refresh_mode()

    def open_by_id(self, cid):
        for c in self.conversations:
            if c['conversation_id'] == cid:
                self.open_conversation(c)
                return

        self.load_conversations()

        for c in self.conversations:
            if c['conversation_id'] == cid:
                self.open_conversation(c)
                return

    def search(self, q):
        q = q.strip()

        if not q or q == 'Rechercher...':
            return

        # Search users from the upper search bar.
        try:
            users = self.client.search_users(q)
        except Exception as ex:
            messagebox.showerror(
                'Recherche',
                str(ex),
                parent=self
            )
            return

        w = tk.Toplevel(self)
        w.title('Résultats de recherche')
        w.geometry('430x320')
        w.configure(bg=WHITE)

        tk.Label(
            w,
            text=f'Recherche : {q}',
            font=('Segoe UI', 13, 'bold'),
            fg=PURPLE, bg=WHITE
        ).pack(pady=15)

        results = tk.Listbox(
            w,
            font=('Segoe UI', 10),
            bg=WHITE,
            fg=DARK,
            relief='flat'
        )
        results.pack(
            fill='both', expand=True,
            padx=25, pady=10
        )

        if not users:
            results.insert('end', 'Aucun utilisateur trouvé.')

        for u in users:
            results.insert(
                'end',
                f"{u.get('id')} | @{u.get('username', 'Utilisateur')}"
            )

        def select(ev=None):
            if not results.curselection() or not users:
                return

            index = results.curselection()[0]
            if index >= len(users):
                return

            uid = int(users[index]['id'])

            try:
                cid = self.client.create_private(uid)
                w.destroy()
                self.load_conversations()
                self.after(
                    200,
                    lambda: self.open_by_id(cid)
                )
            except Exception as ex:
                messagebox.showerror(
                    'Conversation', str(ex), parent=w
                )

        results.bind('<Double-Button-1>', select)

        tk.Button(
            w,
            text='Fermer',
            command=w.destroy,
            bg=PINK, fg=WHITE,
            relief='flat',
            font=('Segoe UI', 10, 'bold')
        ).pack(pady=12, ipadx=15)

    def close(self):
        self.client.stop()
        self.destroy()


if __name__ == '__main__':
    messagebox.showinfo(
        'BitchRella',
        'Lance main.py pour تسجيل الدخول.'
    )
