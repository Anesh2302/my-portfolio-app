"""
SIMONPETER PORTFOLIO APP — About + Projects (live URLs + how-made) + Reminders w/ sound + Tasks + Auth/Admin + Themes + Portfolio sync
Run:  pip install -r requirements.txt  ;  python app.py
Login: admin / Admin123!  (change after first login)
"""
import os, re, secrets, tempfile
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf import CSRFProtect
from flask_talisman import Talisman

BASE = os.path.dirname(os.path.abspath(__file__))
if os.environ.get("VERCEL"):
    DB_PATH = os.path.join(tempfile.gettempdir(), "app.db")  # Vercel serverless: only tmp is writable
else:
    DB_PATH = os.path.join(BASE, "instance", "app.db")
    os.makedirs(os.path.join(BASE, "instance"), exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# secure cookies (relaxed for localhost http)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["REMEMBER_COOKIE_HTTPONLY"] = True

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
limiter = Limiter(get_remote_address, app=app, default_limits=["200/hour"])
# CSP relaxed to allow Google fonts; force_https False for local dev
Talisman(app, content_security_policy=None, force_https=False, session_cookie_secure=False)

THEMES = ["iron", "gold", "crimson", "ghost"]

# ── MODELS ──
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(10), default="user")  # admin | user
    theme = db.Column(db.String(20), default="iron")
    created = db.Column(db.DateTime, default=datetime.utcnow)
    def is_admin(self): return self.role == "admin"

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    short_desc = db.Column(db.Text, default="")
    how_made = db.Column(db.Text, default="")  # explain / how built
    tech = db.Column(db.String(300), default="")
    category = db.Column(db.String(30), default="web")
    live_url = db.Column(db.String(300), default="")
    github_url = db.Column(db.String(300), default="")
    updated = db.Column(db.DateTime, default=datetime.utcnow)

class Reminder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    notes = db.Column(db.Text, default="")
    remind_at = db.Column(db.DateTime, nullable=False)
    done = db.Column(db.Boolean, default=False)
    notified = db.Column(db.Boolean, default=False)
    created = db.Column(db.DateTime, default=datetime.utcnow)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    priority = db.Column(db.String(10), default="med")  # low|med|high
    due_date = db.Column(db.String(20), default="")
    done = db.Column(db.Boolean, default=False)
    created = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(uid): return User.query.get(int(uid))

def admin_required(f):
    @wraps(f)
    def w(*a, **kw):
        if not current_user.is_authenticated or not current_user.is_admin():
            abort(403)
        return f(*a, **kw)
    return w

def slugify(t): return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")

# ── SEED ──
SEED_PROJECTS = [
 dict(title="TALENTOS", category="web", tech="Flask, Python, SQLite, OTP, TOTP 2FA",
      live_url="https://anesh2302.github.io/talentos/", github_url="https://github.com/Anesh2302/talentos",
      short_desc="Recruitment & talent management platform — OTP email verification, TOTP 2FA, role-based access, job management, todo system, security dashboard.",
      how_made="HOW IT WAS MADE:\n1. Backend: Flask + SQLite. Users table with bcrypt password hashes.\n2. Email OTP verification with Flask-Mail + expiring tokens.\n3. TOTP 2FA with pyotp + QR codes for authenticator apps.\n4. Role-based access (admin/recruiter/candidate) via decorators.\n5. Jobs CRUD + applications + todo module + security dashboard (failed logins, audit log).\n6. Frontend: Jinja + vanilla JS. Deployed static demo to GitHub Pages, full Flask version runs locally."),
 dict(title="CLASS 11 CHEMISTRY LAB", category="web", tech="HTML, CSS, JavaScript, Node.js",
      live_url="https://anesh2302.github.io/class11-chem/", github_url="https://github.com/Anesh2302/class11-chem",
      short_desc="Interactive offline chemistry learning — periodic table (118 elements), virtual lab, 21 experiments, reaction predictor, quizzes. NCERT Chapters 1-6.",
      how_made="HOW IT WAS MADE:\n1. Pure HTML/CSS/JS, zero backend so it works offline.\n2. Periodic table rendered from a JSON of 118 elements with search + category colours.\n3. Virtual lab: 21 experiments as JS simulations (canvas + step logic).\n4. Reaction predictor: rule-based balancer for common NCERT reactions.\n5. Quiz engine: question bank in JS with localStorage scores.\n6. Node.js only for local dev server. Hosted on GitHub Pages."),
 dict(title="MR ETAMIL BOOKS", category="web", tech="Next.js, Express, MySQL",
      live_url="https://anesh2302.github.io/MR_ETamilBooks/", github_url="https://github.com/Anesh2302/MR_ETamilBooks",
      short_desc="Tamil E-Book translator platform. Browse and read Tamil literature digitally. Express backend, MySQL database, Next.js frontend.",
      how_made="HOW IT WAS MADE:\n1. Frontend: Next.js with Tamil font support + paginated reader.\n2. Backend: Express REST API (books, chapters, search).\n3. Database: MySQL — books, authors, chapters tables with full-text index.\n4. Upload pipeline converts text/PDF into chapter rows.\n5. Search in Tamil + English. Static mirror on GitHub Pages."),
 dict(title="SIMONPETER AI", category="ai", tech="Flask, NVIDIA NIM, Web Speech API, Python",
      live_url="https://anesh2302.github.io/simonpeterai/", github_url="https://github.com/Anesh2302/simonpeterai",
      short_desc="AI-powered personal assistant — NVIDIA NIM integration, voice input/output, real-time chat, weather, notes, countdown timer, calculator, web search.",
      how_made="HOW IT WAS MADE:\n1. Flask backend proxies chat to NVIDIA NIM LLM API (key on server, never in browser).\n2. Web Speech API for voice input (SpeechRecognition) + speechSynthesis for output.\n3. Tools layer in JS/Python: weather (Open-Meteo), notes (localStorage), countdown timer, calculator, web search links.\n4. Chat UI with typing effect + history. Static demo on GitHub Pages, full AI needs API key."),
 dict(title="PROJECTPOP", category="tool", tech="Flask, SQLite, pyotp, SSL scan",
      live_url="https://anesh2302.github.io/projectpop/", github_url="https://github.com/Anesh2302/projectpop",
      short_desc="Security analysis platform — real website scanner (SSL, headers, ports, tech detection), IP blocker, 2FA user/admin auth, alerts, audit logging.",
      how_made="HOW IT WAS MADE:\n1. Flask + SQLite with Flask-Login + pyotp 2FA.\n2. Scanner module: ssl socket cert fetch, requests header checks (HSTS, CSP, X-Frame), socket port checks, Wappalyzer-style tech fingerprints.\n3. IP blocklist + rate limiting + audit log table.\n4. Admin dashboard with charts + alerts via email.\n5. Background scans with threading."),
 dict(title="INSYRIUM PORTAL", category="web", tech="Flask, Socket.IO, PostgreSQL",
      live_url="https://anesh2302.github.io/insyrium/", github_url="https://github.com/Anesh2302/insyrium",
      short_desc="Full SaaS portal — 3 admin roles (platform, content, support), real-time Socket.IO community, RBAC, OTP/MFA, audit logging, email alerts, rate limiting.",
      how_made="HOW IT WAS MADE:\n1. Flask + Flask-SocketIO for realtime community rooms.\n2. PostgreSQL (SQLite fallback) with RBAC tables: users, roles, permissions.\n3. OTP/MFA via email + TOTP, audit log on every sensitive action.\n4. Rate limiting with Flask-Limiter, email alerts with Flask-Mail.\n5. Deployed demo frontend to GitHub Pages."),
 dict(title="MONGODB ACADEMY", category="web", tech="HTML, CSS, JavaScript, Python",
      live_url="https://anesh2302.github.io/mongodb-academy/", github_url="https://github.com/Anesh2302/mongodb-academy",
      short_desc="MongoDB learning platform — interactive playground, progress tracking, dark/light mode, search. No login. Pure learning.",
      how_made="HOW IT WAS MADE:\n1. Static HTML/CSS/JS course with embedded Mongo shell simulator written in JS (parses find/insert/update).\n2. Progress in localStorage, dark/light via CSS variables.\n3. Python scripts generate lesson JSON from markdown.\n4. Client-side search index. Hosted on GitHub Pages."),
]

def seed():
    db.create_all()
    if not User.query.filter_by(username="admin").first():
        db.session.add(User(username="admin", email="admin@local",
            password_hash=bcrypt.generate_password_hash("Admin123!").decode(), role="admin"))
    for p in SEED_PROJECTS:
        s = slugify(p["title"])
        if not Project.query.filter_by(slug=s).first():
            db.session.add(Project(slug=s, **p))
    db.session.commit()

# sync projects from latest portfolio site (../portfolio/index.html)
def sync_from_portfolio():
    path = os.path.join(BASE, "..", "portfolio", "index.html")
    if not os.path.exists(path): return 0, "portfolio/index.html not found"
    html = open(path, encoding="utf-8", errors="ignore").read()
    cards = re.findall(r'class="project-card".*?card-title">(.*?)</h3>.*?card-desc">(.*?)</p>.*?card-tech">(.*?)</div>.*?</div>\s*</div>', html, re.S)
    gh = re.findall(r'href="(https://github\.com/[^"]+)"', html)
    live = re.findall(r'href="(https://anesh2302\.github\.io/[^"]+)"', html)
    n = 0
    # simpler: split by project-card blocks
    blocks = html.split('class="project-card"')[1:]
    for b in blocks:
        m_t = re.search(r'card-title">(.*?)</h3>', b); m_d = re.search(r'card-desc">(.*?)</p>', b)
        m_gh = re.search(r'href="(https://github\.com/[^"]+)"', b)
        m_lv = re.search(r'href="(https://anesh2302\.github\.io/[^"]+)"', b)
        m_cat = re.search(r'data-category="(\w+)"', b)
        techs = ", ".join(re.findall(r'<span>(.*?)</span>', b.split("card-tech")[1].split("</div>")[0])) if "card-tech" in b else ""
        if not m_t: continue
        title = m_t.group(1).strip(); slug = slugify(title)
        proj = Project.query.filter_by(slug=slug).first()
        vals = dict(title=title,
            short_desc=m_d.group(1).strip() if m_d else "",
            github_url=m_gh.group(1) if m_gh else "",
            live_url=m_lv.group(1) if m_lv else "",
            category=m_cat.group(1) if m_cat else "web",
            tech=techs or "Web", updated=datetime.utcnow())
        if proj:
            for k, v in vals.items(): setattr(proj, k, v)
        else:
            db.session.add(Project(slug=slug, how_made="Synced from latest portfolio website. See LIVE DEMO + GitHub for build details.", **vals))
        n += 1
    db.session.commit()
    return n, f"Synced {n} projects from latest portfolio website"

# ── ROUTES ──
@app.route("/")
def index():
    projects = Project.query.order_by(Project.id).limit(6).all()
    return render_template("index.html", projects=projects)

@app.route("/projects")
def projects():
    cat = request.args.get("cat", "all")
    q = Project.query
    if cat in ("web", "ai", "tool"): q = q.filter_by(category=cat)
    return render_template("projects.html", projects=q.order_by(Project.id).all(), cat=cat)

@app.route("/projects/<slug>")
def project_detail(slug):
    p = Project.query.filter_by(slug=slug).first_or_404()
    tech_list = [t.strip() for t in (p.tech or "").split(",") if t.strip()]
    return render_template("project_detail.html", p=p, tech_list=tech_list)

@app.route("/register", methods=["GET", "POST"])
@limiter.limit("10/hour")
def register():
    if current_user.is_authenticated: return redirect(url_for("dashboard"))
    if request.method == "POST":
        u = request.form.get("username", "").strip().lower()
        e = request.form.get("email", "").strip().lower()
        pw = request.form.get("password", "")
        if not re.match(r"^[a-z0-9_]{3,30}$", u): flash("Username: 3-30 chars, letters/numbers/_", "err"); return redirect(url_for("register"))
        if len(pw) < 8: flash("Password must be 8+ characters", "err"); return redirect(url_for("register"))
        if User.query.filter((User.username == u) | (User.email == e)).first():
            flash("Username or email already taken", "err"); return redirect(url_for("register"))
        role = "admin" if User.query.count() == 0 else "user"
        user = User(username=u, email=e, password_hash=bcrypt.generate_password_hash(pw).decode(), role=role)
        db.session.add(user); db.session.commit()
        login_user(user); flash(f"Welcome, {u}!", "ok"); return redirect(url_for("dashboard"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
@limiter.limit("10/minute")
def login():
    if current_user.is_authenticated: return redirect(url_for("dashboard"))
    if request.method == "POST":
        ident = request.form.get("ident", "").strip().lower()
        pw = request.form.get("password", "")
        user = User.query.filter((User.username == ident) | (User.email == ident)).first()
        if user and bcrypt.check_password_hash(user.password_hash, pw):
            login_user(user, remember=True); flash("Logged in", "ok")
            return redirect(request.args.get("next") or url_for("dashboard"))
        flash("Invalid login", "err")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user(); flash("Logged out", "ok"); return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.done, Task.created.desc()).all()
    rems = Reminder.query.filter_by(user_id=current_user.id, done=False).order_by(Reminder.remind_at).limit(5).all()
    return render_template("dashboard.html", tasks=tasks, rems=rems)

# — reminders —
@app.route("/reminders", methods=["GET", "POST"])
@login_required
def reminders():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        dt = request.form.get("remind_at", "")
        notes = request.form.get("notes", "").strip()
        if not title or not dt: flash("Title + date/time required", "err"); return redirect(url_for("reminders"))
        try: ra = datetime.strptime(dt, "%Y-%m-%dT%H:%M")
        except: flash("Bad date format", "err"); return redirect(url_for("reminders"))
        if ra < datetime.now() - timedelta(minutes=1): flash("Pick a future time", "err"); return redirect(url_for("reminders"))
        db.session.add(Reminder(user_id=current_user.id, title=title, notes=notes, remind_at=ra))
        db.session.commit(); flash("Reminder set — sound will play when due", "ok")
        return redirect(url_for("reminders"))
    rems = Reminder.query.filter_by(user_id=current_user.id).order_by(Reminder.done, Reminder.remind_at).all()
    return render_template("reminders.html", rems=rems)

@app.route("/reminders/<int:rid>/done", methods=["POST"])
@login_required
def reminder_done(rid):
    r = Reminder.query.filter_by(id=rid, user_id=current_user.id).first_or_404()
    r.done = True; db.session.commit(); return redirect(url_for("reminders"))

@app.route("/reminders/<int:rid>/delete", methods=["POST"])
@login_required
def reminder_del(rid):
    r = Reminder.query.filter_by(id=rid, user_id=current_user.id).first_or_404()
    db.session.delete(r); db.session.commit(); return redirect(url_for("reminders"))

@app.route("/api/reminders/due")
@login_required
def api_due():
    now = datetime.now()
    due = Reminder.query.filter_by(user_id=current_user.id, done=False, notified=False).filter(Reminder.remind_at <= now).all()
    return jsonify([{"id": r.id, "title": r.title, "notes": r.notes} for r in due])

@app.route("/api/reminders/<int:rid>/ack", methods=["POST"])
@csrf.exempt
@login_required
def api_ack(rid):
    r = Reminder.query.filter_by(id=rid, user_id=current_user.id).first_or_404()
    r.notified = True; db.session.commit(); return jsonify({"ok": True})

# — tasks —
@app.route("/tasks", methods=["GET", "POST"])
@login_required
def tasks():
    if request.method == "POST":
        t = request.form.get("title", "").strip()
        if not t: flash("Task title required", "err"); return redirect(url_for("tasks"))
        db.session.add(Task(user_id=current_user.id, title=t,
            priority=request.form.get("priority", "med"), due_date=request.form.get("due_date", "")))
        db.session.commit(); return redirect(url_for("tasks"))
    tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.done, Task.created.desc()).all()
    return render_template("tasks.html", tasks=tasks)

@app.route("/tasks/<int:tid>/toggle", methods=["POST"])
@login_required
def task_toggle(tid):
    t = Task.query.filter_by(id=tid, user_id=current_user.id).first_or_404()
    t.done = not t.done; db.session.commit(); return redirect(url_for("tasks"))

@app.route("/tasks/<int:tid>/delete", methods=["POST"])
@login_required
def task_del(tid):
    t = Task.query.filter_by(id=tid, user_id=current_user.id).first_or_404()
    db.session.delete(t); db.session.commit(); return redirect(url_for("tasks"))

# — theme (synced everywhere via user profile + localStorage) —
@app.route("/settings/theme", methods=["POST"])
@login_required
def set_theme():
    th = request.form.get("theme", "iron")
    if th in THEMES:
        current_user.theme = th; db.session.commit()
    return redirect(request.referrer or url_for("index"))

# — admin —
@app.route("/admin")
@login_required
@admin_required
def admin():
    return render_template("admin.html", users=User.query.all(),
        projects=Project.query.order_by(Project.id).all(),
        n_users=User.query.count(), n_projects=Project.query.count(),
        n_tasks=Task.query.count(), n_rems=Reminder.query.count())

@app.route("/admin/users/<int:uid>/role", methods=["POST"])
@login_required
@admin_required
def admin_role(uid):
    u = User.query.get_or_404(uid)
    if u.id == current_user.id: flash("Cannot change own role", "err"); return redirect(url_for("admin"))
    u.role = "user" if u.role == "admin" else "admin"; db.session.commit()
    flash(f"{u.username} is now {u.role}", "ok"); return redirect(url_for("admin"))

@app.route("/admin/users/<int:uid>/delete", methods=["POST"])
@login_required
@admin_required
def admin_del_user(uid):
    u = User.query.get_or_404(uid)
    if u.id == current_user.id: flash("Cannot delete yourself", "err"); return redirect(url_for("admin"))
    Reminder.query.filter_by(user_id=u.id).delete(); Task.query.filter_by(user_id=u.id).delete()
    db.session.delete(u); db.session.commit(); return redirect(url_for("admin"))

@app.route("/admin/projects/new", methods=["GET", "POST"])
@app.route("/admin/projects/<int:pid>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def admin_project(pid=None):
    p = Project.query.get(pid) if pid else None
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        slug = slugify(request.form.get("slug") or title)
        vals = dict(title=title, slug=slug,
            short_desc=request.form.get("short_desc", ""), how_made=request.form.get("how_made", ""),
            tech=request.form.get("tech", ""), category=request.form.get("category", "web"),
            live_url=request.form.get("live_url", "").strip(), github_url=request.form.get("github_url", "").strip(),
            updated=datetime.utcnow())
        if not title: flash("Title required", "err"); return redirect(request.url)
        if p:
            for k, v in vals.items(): setattr(p, k, v)
        else:
            if Project.query.filter_by(slug=slug).first(): flash("Slug exists", "err"); return redirect(request.url)
            db.session.add(Project(**vals))
        db.session.commit(); flash("Project saved — live on site + new theme instantly", "ok")
        return redirect(url_for("admin"))
    return render_template("admin_project_form.html", p=p)

@app.route("/admin/projects/<int:pid>/delete", methods=["POST"])
@login_required
@admin_required
def admin_project_del(pid):
    db.session.delete(Project.query.get_or_404(pid)); db.session.commit()
    return redirect(url_for("admin"))

@app.route("/admin/sync-portfolio", methods=["POST"])
@login_required
@admin_required
def admin_sync():
    n, msg = sync_from_portfolio(); flash(msg, "ok" if n else "err"); return redirect(url_for("admin"))

@app.errorhandler(403)
def e403(_): return render_template("error.html", code=403, msg="Admins only"), 403
@app.errorhandler(404)
def e404(_): return render_template("error.html", code=404, msg="Not found"), 404
@app.errorhandler(429)
def e429(_): return render_template("error.html", code=429, msg="Too many requests — slow down"), 429

# ensure tables + seed data exist on boot (needed for gunicorn/Render where __main__ never runs)
with app.app_context():
    seed()

if __name__ == "__main__":
    with app.app_context(): seed()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
