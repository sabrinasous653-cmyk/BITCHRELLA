# BitchRella

نسخة عملية أولى من تطبيق الدردشة على Windows:
- Python + Tkinter للواجهة
- FastAPI + WebSocket للسيرفر
- SQLite لقاعدة البيانات
- JWT للمصادقة
- bcrypt عبر passlib لكلمات المرور
- إرسال/استقبال رسائل مباشرة
- حفظ الرسائل عند عدم اتصال المستلم
- Contacts/search/private conversations/groups API

## التشغيل على Windows

1. افتحي مجلد `bitchrella` في VS Code.
2. شغّلي `run_server.bat` واتركي النافذة مفتوحة.
3. شغّلي `run_app.bat` في نافذة ثانية.
4. أنشئي حسابين من `Créer un compte` للتجربة.
5. افتحي محادثة جديدة وابحثي عن الحساب الثاني.

قاعدة البيانات تُنشأ تلقائياً في `server/database/bitchrella.db`.

> للتجربة على جهازين في نفس الشبكة، غيّري عنوان السيرفر في `network_client.py` إلى IP الجهاز الذي يشغّل FastAPI، واسمحّي للمنفذ 8000 في Windows Firewall. عند النشر على الإنترنت استخدمي HTTPS/WSS ومفتاح JWT سري من متغير بيئة.
