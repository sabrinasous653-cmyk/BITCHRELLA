"""شبكة BitchRella: REST + WebSocket في Thread مستقل عن Tkinter."""
import asyncio, json, queue, threading, time, os
import requests
import websocket

DEFAULT_SERVER = "http://127.0.0.1:8000"


class NetworkClient:
    def __init__(self, base_url=DEFAULT_SERVER):
        self.base_url = base_url.rstrip('/')
        self.ws_url = self.base_url.replace('https://','wss://').replace('http://','ws://')
        self.token = None
        self.user_id = None
        self.username = None
        self.incoming = queue.Queue()
        self.outgoing = queue.Queue()
        self.stop_event = threading.Event()
        self.connected = False
        self._thread = None
        self._ws = None

    def login(self, email, password):
        r = requests.post(self.base_url + '/login', json={'email': email, 'password': password}, timeout=10)
        r.raise_for_status()
        data = r.json()
        self.token, self.user_id, self.username = data['access_token'], data['user_id'], data['username']
        return data

    def register(self, username, email, password):
        r = requests.post(self.base_url + '/register', json={'username': username, 'email': email, 'password': password}, timeout=10)
        r.raise_for_status()
        data = r.json()
        self.token, self.user_id, self.username = data['access_token'], data['user_id'], data['username']
        return data

    def _headers(self):
        return {'Authorization': f'Bearer {self.token}'}

    def get_conversations(self):
        r=requests.get(self.base_url+'/conversations',headers=self._headers(),timeout=10); r.raise_for_status(); return r.json()

    def get_messages(self, conversation_id, before_id=None, limit=50):
        params={'limit':limit}
        if before_id: params['before_id']=before_id
        r=requests.get(f'{self.base_url}/conversations/{conversation_id}/messages',headers=self._headers(),params=params,timeout=10); r.raise_for_status(); return r.json()

    def search_users(self,q):
        r=requests.get(self.base_url+'/users/search',headers=self._headers(),params={'q':q},timeout=10); r.raise_for_status(); return r.json()

    def get_profile(self):
        r=requests.get(self.base_url+'/profile',headers=self._headers(),timeout=10); r.raise_for_status(); return r.json()

    def update_profile(self, avatar_path=None, bio=None):
        body={}
        if avatar_path is not None: body['avatar_path']=avatar_path
        if bio is not None: body['bio']=bio
        r=requests.put(self.base_url+'/profile',headers=self._headers(),json=body,timeout=10); r.raise_for_status(); return r.json()

    def get_contacts(self):
        r=requests.get(self.base_url+'/contacts',headers=self._headers(),timeout=10); r.raise_for_status(); return r.json()

    def get_pending_contacts(self):
        r=requests.get(self.base_url+'/contacts/pending',headers=self._headers(),timeout=10); r.raise_for_status(); return r.json()

    def send_contact_request(self, contact_id):
        r=requests.post(self.base_url+'/contacts/request',headers=self._headers(),json={'contact_id':int(contact_id)},timeout=10); r.raise_for_status(); return r.json()

    def respond_contact_request(self, requester_id, accept=True):
        r=requests.post(self.base_url+'/contacts/respond',headers=self._headers(),json={'requester_id':int(requester_id),'accept':bool(accept)},timeout=10); r.raise_for_status(); return r.json()

    def create_private(self,other_user_id):
        r=requests.post(self.base_url+'/conversations/private',headers=self._headers(),json={'other_user_id':other_user_id},timeout=10); r.raise_for_status(); return r.json()['conversation_id']

    def get_favorite_ids(self):
        r=requests.get(self.base_url+'/favorites',headers=self._headers(),timeout=10); r.raise_for_status(); return r.json()['conversation_ids']

    def toggle_favorite(self, conversation_id):
        r=requests.post(self.base_url+f'/favorites/{int(conversation_id)}',headers=self._headers(),timeout=10); r.raise_for_status(); return r.json()['favorite']

    def edit_message(self, message_id, content):
        r=requests.put(self.base_url+f'/messages/{int(message_id)}',headers=self._headers(),json={'content':content},timeout=10); r.raise_for_status(); return r.json()

    def delete_message(self, message_id):
        r=requests.delete(self.base_url+f'/messages/{int(message_id)}',headers=self._headers(),timeout=10); r.raise_for_status(); return r.json()

    def upload_file(self, path):
        with open(path,'rb') as f:
            r=requests.post(self.base_url+'/upload',headers=self._headers(),files={'file':(os.path.basename(path),f)},timeout=60)
        r.raise_for_status(); return r.json()

    def create_group(self, name, member_ids):
        r=requests.post(
            self.base_url+'/conversations/group',
            headers=self._headers(),
            json={'name': name, 'member_ids': member_ids},
            timeout=10
        )
        r.raise_for_status()
        return r.json()['conversation_id']

    def start(self):
        if self._thread and self._thread.is_alive(): return
        self.stop_event.clear()
        self._thread=threading.Thread(target=self._run_loop,daemon=True)
        self._thread.start()

    def send_message(self, conversation_id, content, msg_type='text', reply_to=None):
        self.outgoing.put({'type':'message','payload':{'conversation_id':conversation_id,'content':content,'msg_type':msg_type,'reply_to':reply_to}})

    def send_typing(self,conversation_id):
        self.outgoing.put({'type':'typing','payload':{'conversation_id':conversation_id}})

    def send_read(self,message_id):
        self.outgoing.put({'type':'read_receipt','payload':{'message_id':message_id}})

    def _run_loop(self):
        delay=1
        while not self.stop_event.is_set():
            try:
                self._ws=websocket.create_connection(self.ws_url+'/ws/'+self.token,timeout=10)
                self.connected=True; delay=1
                self.incoming.put({'type':'connection','payload':{'status':'online'}})
                self._ws.settimeout(0.5)
                while not self.stop_event.is_set():
                    # إرسال الطابور
                    while True:
                        try: item=self.outgoing.get_nowait()
                        except queue.Empty: break
                        self._ws.send(json.dumps(item,ensure_ascii=False))
                    try:
                        raw=self._ws.recv()
                        if raw: self.incoming.put(json.loads(raw))
                    except websocket.WebSocketTimeoutException:
                        continue
                try:self._ws.close()
                except Exception:pass
            except Exception as e:
                self.connected=False
                self.incoming.put({'type':'connection','payload':{'status':'offline','error':str(e)}})
                time.sleep(delay); delay=min(delay*2,15)
            finally:
                self.connected=False

    def stop(self):
        self.stop_event.set()
        try:
            if self._ws:self._ws.close()
        except Exception:pass
