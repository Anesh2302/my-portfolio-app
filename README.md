# ANESH DEV — Portfolio App

About me + all projects with live URLs + how-each-was-made, reminders with sound, tasks, login/logout + admin, security, themes that update everywhere.

Same Iron-Man HUD style as your latest portfolio site.

## Run
```
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

Login: `admin / Admin123!` — change after first login (register new users, promote in /admin).

## Features
- **About me** (`/`) + Featured projects
- **Projects** (`/projects`) filter web/ai/tool, each has LIVE DEMO + GitHub + dedicated page `/projects/<slug>` with **Explain / How it was made**
- **Reminders** (`/reminders`) datetime picker, alarm **sound** (Web Audio beeps x4), browser Notification, toast, polling `/api/reminders/due` every 10s
- **Tasks** (`/tasks`) add / done / delete, priority, due date
- **Auth**: register / login / logout (Flask-Login + Bcrypt hash), first user = admin
- **Security**: bcrypt, CSRF (Flask-WTF), rate-limit login (Flask-Limiter), secure HttpOnly cookies, Talisman headers, admin-only 403, parameterized ORM queries, password 8+ rule
- **Themes**: iron / gold / crimson / ghost — per-user saved + localStorage, applied on every page via `data-theme`
- **Sync with latest website**: Admin → “SYNC FROM LATEST WEBSITE” reads `../portfolio/index.html`, pulls titles/descs/live URLs/GitHub/tech into DB. Any add/edit in admin or sync shows instantly with current theme.

## Structure
```
myapp/
 app.py  templates/  static/css/style.css  static/js/app.js
 instance/app.db (auto-created)
```
