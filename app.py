from flask import Flask, render_template, request, redirect, session, jsonify
import re
import time
import requests
import random
import smtplib
import uuid
import psycopg2
from dotenv import load_dotenv
import os
from functools import wraps
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def send_email_otp(to_email, otp):
    html_template = f"""
    <div style="margin:0;padding:0;background:linear-gradient(135deg,#0f2027,#203a43,#000);font-family:Arial,sans-serif;">

        <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
                <td align="center">

                    <table width="420" cellpadding="0" cellspacing="0"
                    style="margin-top:40px;background:#0b0b0b;border-radius:16px;
                    padding:35px;border:1px solid rgba(0,255,200,0.4);
                    box-shadow:0 0 30px rgba(0,255,200,0.5);">

                        <!-- LOGO / TITLE -->
                        <tr>
                            <td align="center">
                                <h1 style="
                                    color:#00ffc3;
                                    margin:0;
                                    text-shadow:0 0 10px #00ffc3,0 0 20px #00ffc3;
                                    letter-spacing:2px;
                                ">
                                    🎮 RK GAMES
                                </h1>

                                <p style="color:#aaa;font-size:13px;margin-top:5px;">
                                    Secure Login System
                                </p>
                            </td>
                        </tr>

                        <!-- TITLE -->
                        <tr>
                            <td align="center" style="padding-top:20px;">
                                <h2 style="color:white;margin:0;">
                                    🔐 OTP Verification
                                </h2>

                                <p style="color:#888;font-size:14px;margin-top:8px;">
                                    Enter this code to continue login
                                </p>
                            </td>
                        </tr>

                        <!-- OTP BOX -->
                        <tr>
                            <td align="center">

                                <div style="
                                    margin:30px 0;
                                    padding:18px;
                                    font-size:34px;
                                    letter-spacing:10px;
                                    background:linear-gradient(135deg,#000,#111);
                                    color:#00ffc3;
                                    border-radius:10px;
                                    border:1px solid #00ffc3;
                                    font-weight:bold;
                                    box-shadow:0 0 15px #00ffc3 inset,0 0 20px rgba(0,255,200,0.5);
                                ">
                                    {otp}
                                </div>

                            </td>
                        </tr>

                        <!-- TIMER -->
                        <tr>
                            <td align="center">
                                <p style="color:#ffaa00;font-size:13px;">
                                    ⏳ Valid for 5 minutes only
                                </p>
                            </td>
                        </tr>

                        <!-- WARNING -->
                        <tr>
                            <td align="center">
                                <p style="
                                    color:#ff4d4d;
                                    font-size:12px;
                                    background:rgba(255,0,0,0.1);
                                    padding:10px;
                                    border-radius:8px;
                                    border:1px solid rgba(255,0,0,0.3);
                                ">
                                    ⚠ Never share this OTP with anyone
                                </p>
                            </td>
                        </tr>

                        <!-- BUTTON -->
                        <tr>
                            <td align="center">
                                <a href="#" style="
                                    display:inline-block;
                                    margin-top:20px;
                                    padding:12px 25px;
                                    background:#00ffc3;
                                    color:black;
                                    text-decoration:none;
                                    border-radius:8px;
                                    font-weight:bold;
                                    box-shadow:0 0 15px #00ffc3;
                                ">
                                    Verify Now
                                </a>
                            </td>
                        </tr>

                        <!-- FOOTER -->
                        <tr>
                            <td align="center">
                                <p style="color:#555;font-size:11px;margin-top:25px;">
                                    If you didn’t request this, ignore this email safely.
                                </p>

                                <p style="color:#333;font-size:10px;">
                                    © 2026 RK Games. All rights reserved.
                                </p>
                            </td>
                        </tr>

                    </table>

                </td>
            </tr>
        </table>

    </div>
    """

    message = Mail(
        from_email=os.environ.get("SENDER_EMAIL"),
        to_emails=to_email,
        subject="🔐 RK Games OTP - Secure Login Code",
        html_content=html_template
    )

    try:
        sg = SendGridAPIClient(os.environ.get("SENDGRID_API_KEY"))
        sg.send(message)
    except Exception as e:
        print(e)
def update_last_active(user_id):
    conn = get_db()
    c = conn.cursor()

    c.execute(
        "UPDATE users SET last_active=%s WHERE player_id=%s",
        (time.time(), user_id)
    )

    conn.commit()
    conn.close()

def get_db():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin"):
            return redirect("/admin_login")
        return f(*args, **kwargs)
    return decorated
load_dotenv()

from werkzeug.security import generate_password_hash, check_password_hash
from email.mime.text import MIMEText
otp_store ={}
players = []
instant_queue = []
power_queue = []
move_queue = []
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")   # strong password rakho

def valid_email(email):

    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'

    return re.match(pattern, email)


def strong_password(password):

    if len(password) < 8:
        return False

    if not re.search(r"[A-Z]", password):
        return False

    if not re.search(r"[a-z]", password):
        return False

    if not re.search(r"[0-9]", password):
        return False

    if not re.search(r"[!@#$%^&*]", password):
        return False

    return True


def valid_player_id(pid):

    if len(pid) < 4:
        return False

    if not re.search(r'[@#_]', pid):
        return False

    if not re.match(r'^[a-zA-Z0-9@#_]+$', pid):
        return False

    return True




def init_db():
    conn = get_db()
    c = conn.cursor()

    # 🔥 ANNOUNCEMENT TABLE (ADDED)
    c.execute("""
    CREATE TABLE IF NOT EXISTS announcement (
        id SERIAL PRIMARY KEY,
        message TEXT
    )
    """)

    # default message
    c.execute("SELECT * FROM announcement")
    if not c.fetchone():
        c.execute("INSERT INTO announcement (message) VALUES (%s)", ("Welcome to RK Games 🎮",))

    # ✅ USERS TABLE
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        player_id TEXT UNIQUE,
        show_panel INTEGER DEFAULT 0,
        blocked INTEGER DEFAULT 0,
        points INTEGER DEFAULT 0,
        spin_token INTEGER DEFAULT 0,
        token_id TEXT,
        token_used INTEGER DEFAULT 0,
        token_expiry DOUBLE PRECISION DEFAULT 0,
        last_active DOUBLE PRECISION DEFAULT 0
    )
    """)

    # ✅ USERS me missing columns (safe fix)
    c.execute("""
    ALTER TABLE users 
    ADD COLUMN IF NOT EXISTS points INTEGER DEFAULT 0
    """)

    c.execute("""
    ALTER TABLE users 
    ADD COLUMN IF NOT EXISTS spin_token INTEGER DEFAULT 0
    """)

    c.execute("""
    ALTER TABLE users 
    ADD COLUMN IF NOT EXISTS token_id TEXT
    """)

    c.execute("""
    ALTER TABLE users 
    ADD COLUMN IF NOT EXISTS token_used INTEGER DEFAULT 0
    """)

    c.execute("""
    ALTER TABLE users 
    ADD COLUMN IF NOT EXISTS token_expiry DOUBLE PRECISION DEFAULT 0
    """)

    c.execute("""
    ALTER TABLE users 
    ADD COLUMN IF NOT EXISTS last_active DOUBLE PRECISION DEFAULT 0
    """)

    # ✅ LIVE STREAM TABLE
    c.execute("""
    CREATE TABLE IF NOT EXISTS live_stream (
        id SERIAL PRIMARY KEY,
        video_id TEXT
    )
    """)

    # ✅ REMEMBERED DEVICES
    c.execute("""
    CREATE TABLE IF NOT EXISTS remembered_devices (
        id SERIAL PRIMARY KEY,
        email TEXT,
        device_token TEXT,
        created_at DOUBLE PRECISION
    )
    """)

    c.execute("""
    ALTER TABLE remembered_devices
    ADD COLUMN IF NOT EXISTS created_at DOUBLE PRECISION
    """)

    # ✅ LOGIN ATTEMPTS TABLE
    c.execute("""
    CREATE TABLE IF NOT EXISTS login_attempts (
        id SERIAL PRIMARY KEY,
        email TEXT,
        attempts INTEGER DEFAULT 0,
        last_attempt DOUBLE PRECISION
    )
    """)

    # 🔥 POINT HISTORY TABLE
    c.execute("""
    CREATE TABLE IF NOT EXISTS points_history (
        id SERIAL PRIMARY KEY,
        player_id TEXT,
        points INTEGER,
        reason TEXT,
        created_at DOUBLE PRECISION
    )
    """)

    # 🔥 NEW TABLE (ANTI-CHEAT ADS)
    c.execute("""
    CREATE TABLE IF NOT EXISTS ad_watch (
        id SERIAL PRIMARY KEY,
        player_id TEXT,
        ad_type INTEGER,
        watched_at DOUBLE PRECISION
    )
    """)

    # 🔥 HALL OF FAME TABLE
    c.execute("""
    CREATE TABLE IF NOT EXISTS hall_of_fame (
        id SERIAL PRIMARY KEY,
        player_id TEXT UNIQUE,
        added_at DOUBLE PRECISION
    )
    """)

    # 🆕 BASE POINT (personal start)
    c.execute("""
    ALTER TABLE users 
    ADD COLUMN IF NOT EXISTS base_points INTEGER DEFAULT 0
    """)

    # 🔥 IMPORTANT: FIRST CREATE game_state
    c.execute("""
    CREATE TABLE IF NOT EXISTS game_state (
        id SERIAL PRIMARY KEY,
        current_target INTEGER,
        tokens_given INTEGER,
        cycle_start DOUBLE PRECISION
    )
    """)

    # 🆕 milestone tracking (AFTER CREATE)
    c.execute("""
    ALTER TABLE game_state
    ADD COLUMN IF NOT EXISTS m1_claimed INTEGER DEFAULT 0
    """)

    c.execute("""
    ALTER TABLE game_state
    ADD COLUMN IF NOT EXISTS m2_claimed INTEGER DEFAULT 0
    """)

    c.execute("""
    ALTER TABLE game_state
    ADD COLUMN IF NOT EXISTS m3_claimed INTEGER DEFAULT 0
    """)

    # default row
    c.execute("SELECT * FROM game_state WHERE id=1")
    if not c.fetchone():
        c.execute("""
        INSERT INTO game_state (id, current_target, tokens_given, cycle_start)
        VALUES (1, 168, 0, %s)
        """, (time.time(),))

    # ✅ DEFAULT ROW
    c.execute("SELECT * FROM live_stream")
    if not c.fetchone():
        c.execute("INSERT INTO live_stream (video_id) VALUES (%s)", ("",))

    conn.commit()
    conn.close()
@app.route("/check_player_id")
def check_player_id():

    pid = request.args.get("player_id").lower()

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE player_id=%s", (pid,))
    user = c.fetchone()

    conn.close()

    if user:
        return jsonify({"available": False})
    else:
        return jsonify({"available": True})

@app.route("/")
def home():
    if "player_id" in session:
        return redirect("/dashboard")
    return redirect("/home")
@app.route("/signup", methods=["GET","POST"])
def signup():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        player_id = request.form["player_id"].lower()

        # 🔥 EMAIL VALIDATION
        if not valid_email(email):
            return "Invalid Email"

        # 🔐 SECURE OTP CHECK (FINAL)
        if session.get("otp_verified") != email:
            return "Email not verified ❌"

        # 🔥 HANDLE FORMAT CHECK
        if not player_id.startswith("@"):
            return "Invalid YouTube Handle"

        url = f"https://www.youtube.com/{player_id}"

        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(url, headers=headers, timeout=5, allow_redirects=True)

            final_url = r.url.rstrip("/")
            expected_url = url.rstrip("/")

            if final_url != expected_url:
                return "Invalid YouTube Handle"

        except requests.exceptions.RequestException:
            return "Verification failed"

        # 🔥 PASSWORD VALIDATION
        if not strong_password(password):
            return "Password must contain uppercase, lowercase, number and special character"

        # 🔥 PLAYER ID VALIDATION
        if not valid_player_id(player_id):
            return "Player ID must contain @ or # or _"

        conn =get_db()
        c = conn.cursor()

        # 🔥 EMAIL CHECK
        c.execute("SELECT * FROM users WHERE email=%s", (email,))
        if c.fetchone():
            conn.close()
            return "Account already exists with this email"

        # 🔥 PLAYER ID CHECK
        c.execute("SELECT * FROM users WHERE player_id=%s", (player_id,))
        if c.fetchone():
            conn.close()
            return "Player ID already taken"

        # 🔥 INSERT USER
        hashed_password = generate_password_hash(password)

        c.execute(
            "INSERT INTO users (name,email,password,player_id) VALUES (%s,%s,%s,%s)",
                                   (name,email,hashed_password,player_id)
)

        conn.commit()
        conn.close()

        # 🔥 OTP SESSION CLEAR (VERY IMPORTANT)
        session.pop("otp_verified", None)

        return redirect("/login")

    return render_template("signup.html")
def check_cycle():

    conn = get_db()
    c = conn.cursor()

    # 🔥 get current cycle start
    c.execute("SELECT cycle_start FROM game_state WHERE id=1")
    start = c.fetchone()[0]

    # 10 days = 864000 sec
    if time.time() - start > 864000:

        # 🔥 RESET MILESTONES (3 tokens system)
        c.execute("""
        UPDATE game_state
        SET m1_claimed=0,
            m2_claimed=0,
            m3_claimed=0,
            cycle_start=%s
        WHERE id=1
        """, (time.time(),))

        # 🔥 IMPORTANT: har player ka base reset karo
        c.execute("""
        UPDATE users 
        SET base_points = points
        """)

        print("🔥 NEW CYCLE STARTED (MILESTONE SYSTEM RESET)")

    conn.commit()
    conn.close()
@app.route("/give_new_power", methods=["POST"])
def give_new_power():

    if "player_id" not in session:
        return jsonify({"status": "error"}), 401

    player_id = session["player_id"].lower()

    power_queue.append({
        "playerId": player_id,
        "type": "force_field",
        "radius": 120,
        "duration": 6
    })

    print("🌀 FORCE FIELD SENT:", player_id)

    return jsonify({"status": "ok"})
@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        email = request.form["email"].strip().lower()
        password = request.form["password"]

        conn = get_db()
        c = conn.cursor()

        # 🔥 CHECK LOGIN ATTEMPTS
        c.execute("SELECT attempts, last_attempt FROM login_attempts WHERE email=%s", (email,))
        row = c.fetchone()

        if row:
            attempts, last_time = row

            # ⏱️ 5 min block
            if attempts >= 5 and time.time() - last_time < 300:
                conn.close()
                return "Too many attempts ❌ Try after 5 minutes"

            # 🔄 reset after 5 min
            if time.time() - last_time > 300:
                c.execute("UPDATE login_attempts SET attempts=0 WHERE email=%s", (email,))
                conn.commit()

        # 🔥 USER FETCH
        c.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = c.fetchone()

        # 🔐 PASSWORD CHECK
        if not user or not check_password_hash(user[3], password):

            # ❌ UPDATE ATTEMPTS
            c.execute("SELECT * FROM login_attempts WHERE email=%s", (email,))
            existing = c.fetchone()

            if existing:
                c.execute("""
                UPDATE login_attempts 
                SET attempts = attempts + 1, last_attempt = %s
                WHERE email=%s
                """, (time.time(), email))
            else:
                c.execute("""
                INSERT INTO login_attempts (email, attempts, last_attempt)
                VALUES (%s, 1, %s)
                """, (email, time.time()))

            conn.commit()
            conn.close()

            return "Login Failed ❌"

        # ✅ SUCCESS → RESET ATTEMPTS
        c.execute("DELETE FROM login_attempts WHERE email=%s", (email,))
        conn.commit()

        # 🔥 SESSION SAVE
        session["email"] = user[2]

        # 🔥 BLOCK CHECK
        if user[6] == 1:
            conn.close()
            return "Your account is blocked"

        # 🔥 CHECK REMEMBER DEVICE
        device_token = request.cookies.get("device_token")

        if device_token:
            c.execute("""
SELECT * FROM remembered_devices 
WHERE email=%s AND device_token=%s AND created_at > %s
""", (email, device_token, time.time() - (60*60*24*30)))
            device = c.fetchone()

            if device:
                session["player_id"] = user[4]
                session["name"] = user[1]
                update_last_active(user[4])
                conn.close()
                return redirect("/dashboard")

        # ❗ FIRST TIME LOGIN → SEND OTP
        otp = str(random.randint(1000,9999))
        otp_store[email] = {
            "otp": otp,
            "time": time.time()
        }

        session["temp_login_email"] = email

        send_email_otp(email, otp)

        conn.close()
        return render_template("login_otp.html", email=email)

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():

    if "player_id" not in session:
        return redirect("/login")

    conn = get_db()
    c = conn.cursor()
    pid = session["player_id"]

    check_cycle()

    # 🔥 BLOCK CHECK
    c.execute(
        "SELECT blocked FROM users WHERE player_id=%s",
        (pid,)
    )
    b = c.fetchone()

    if b and b[0] == 1:
        conn.close()
        session.clear()
        return "You are blocked by admin"

    # 🔥 SHOW PANEL
    c.execute(
        "SELECT show_panel FROM users WHERE player_id=%s",
        (pid,)
    )
    status = c.fetchone()

    controller_enable = 0
    if status and status[0] == 1:
        controller_enable = 1

    # 🎥 VIDEO
    c.execute("SELECT video_id FROM live_stream LIMIT 1")
    video = c.fetchone()

    # 🏆 POINTS
    c.execute("SELECT points FROM users WHERE player_id=%s", (pid,))
    p = c.fetchone()
    points = p[0] if p else 0

    # 🎯 REMAINING (OLD SYSTEM - untouched)
    remaining = 10000 - points
    if remaining < 0:
        remaining = 0

    # 🆕 🔥 GAME STATE (FIXED)
    c.execute("""
        SELECT m1_claimed, m2_claimed, m3_claimed 
        FROM game_state 
        WHERE id=1
    """)
    g = c.fetchone()

    if g:
        m1, m2, m3 = g
    else:
        m1, m2, m3 = 0, 0, 0

    # 🔥 TOKENS LEFT (3 total)
    tokens_left = 3 - (m1 + m2 + m3)

    # 🔥 CURRENT TARGET (NEXT MILESTONE)
    if m1 == 0:
        target = 168
    elif m2 == 0:
        target = 504
    elif m3 == 0:
        target = 1008
    else:
        target = 1008  # all claimed

    # 🎯 REMAINING TARGET
    remaining_target = target - points
    if remaining_target < 0:
        remaining_target = 0

    # 📊 RANK
    c.execute("""
        SELECT COUNT(*) + 1 FROM users
        WHERE points > %s
    """, (points,))
    rank = c.fetchone()[0]

    conn.close()

    return render_template(
        "dashboard.html",
        name=session["name"],
        player_id=pid,
        video_id=video[0] if video else "",
        controller_enable=controller_enable,
        points=points,
        remaining=remaining,
        rank=rank,
        danger_limit=11000,

        # 🆕 UI VARIABLES
        target=target,
        tokens_left=tokens_left,
        remaining_target=remaining_target
    )
@app.route("/admin/add_hof/<player_id>")
@admin_required
def add_hof(player_id):
    player_id = player_id.lower()
    conn = get_db()
    c = conn.cursor()

    c.execute("""
    INSERT INTO hall_of_fame (player_id, added_at)
    VALUES (%s,%s)
    ON CONFLICT (player_id) DO NOTHING
    """,(player_id, time.time()))

    conn.commit()
    conn.close()

    return redirect("/admin")

@app.route("/hall_of_fame")
def hall_of_fame():

    conn = get_db()
    c = conn.cursor()

    c.execute("""
    SELECT u.name, u.player_id, u.points
    FROM hall_of_fame h
    LEFT JOIN users u ON h.player_id = u.player_id
    WHERE u.player_id IS NOT NULL
    ORDER BY h.id DESC
    """)

    data = c.fetchall()

    conn.close()

    return render_template("hall_of_fame.html", data=data)
@app.route("/admin/remove_hof/<player_id>")
@admin_required
def remove_hof(player_id):
    player_id = player_id.lower()
    conn = get_db()
    c = conn.cursor()

    c.execute("DELETE FROM hall_of_fame WHERE player_id=%s",(player_id,))

    conn.commit()
    conn.close()

    return redirect("/admin")
@app.route("/logout")
def logout():

    session.clear()
    return redirect("/login")
@app.route("/home")
def home_page():

    conn = get_db()
    c = conn.cursor()

    # 🔥 announcement
    c.execute("SELECT message FROM announcement LIMIT 1")
    ann = c.fetchone()

    # 🔥 leaderboard
    c.execute("""
    SELECT name, player_id, points 
    FROM users 
    ORDER BY points DESC 
    LIMIT 10
    """)
    top = c.fetchall()

    # 🔥 hall of fame
    c.execute("""
    SELECT u.name, u.player_id, u.points
    FROM hall_of_fame h
    JOIN users u ON h.player_id = u.player_id
    ORDER BY h.id DESC 
    LIMIT 10
    """)
    hof = c.fetchall()

    conn.close()

    return render_template(
        "home.html",
        announcement = ann[0] if ann and ann[0] else "Welcome to RK Games 🎮",
        top = top if top else [],
        hof = hof if hof else [],
        logged_in = ("player_id" in session)
    )  
@app.route("/admin", methods=["GET","POST"])
@admin_required
def admin():
    
    conn = get_db()
    c = conn.cursor()

    if request.method == "POST":

        if "video_id" in request.form:
            video_id = request.form["video_id"]
            c.execute("UPDATE live_stream SET video_id=%s WHERE id=1",(video_id,))

        if "enable_id" in request.form:
            pid = request.form["enable_id"]
            c.execute("UPDATE users SET show_panel=1 WHERE player_id=%s", (pid,))

        if "disable_id" in request.form:
            pid = request.form["disable_id"]
            c.execute("UPDATE users SET show_panel=0 WHERE player_id=%s", (pid,))

        if "reset" in request.form:
            c.execute("UPDATE users SET show_panel=0")

        # 🔥 ANNOUNCEMENT UPDATE (ADDED)
        if "announcement" in request.form:
            msg = request.form["announcement"]
            c.execute("UPDATE announcement SET message=%s WHERE id=1", (msg,))

        conn.commit()

    # ✅ YAHI PE HONA CHAHIYE
    current_time = time.time()

    c.execute("""
    SELECT *,
    CASE 
        WHEN last_active > %s THEN 1 
        ELSE 0 
    END as online_status
    FROM users
    ORDER BY 
        show_panel DESC,
        online_status DESC,
        id ASC
    """, (current_time - 10,))

    users = c.fetchall()

    c.execute("SELECT video_id FROM live_stream WHERE id=1")
    video = c.fetchone()

    # 🔥 ANNOUNCEMENT FETCH (ADDED)
    c.execute("SELECT message FROM announcement LIMIT 1")
    ann = c.fetchone()

    conn.close()

    return render_template(
        "admin.html",
        users=users,
        video_id=video[0],
        time=time,
        announcement=ann[0] if ann else ""
    )

@app.route("/search_player", methods=["POST"])
@admin_required
def search_player():

    pid = request.form["search_id"]

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE player_id=%s", (pid,))
    user = c.fetchone()

    conn.close()

    return render_template("search_result.html", user=user)


@app.route("/block_player/<int:user_id>")
@admin_required
def block_player(user_id):

    conn = get_db()
    c = conn.cursor()

    c.execute("UPDATE users SET blocked=1 WHERE id=%s", (user_id,))
    conn.commit()
    conn.close()

    return redirect("/admin")


@app.route("/unblock_player/<int:user_id>")
@admin_required
def unblock_player(user_id):

    conn = get_db()
    c = conn.cursor()

    c.execute("UPDATE users SET blocked=0 WHERE id=%s", (user_id,))
    conn.commit()
    conn.close()

    return redirect("/admin")


@app.route("/toggle_player/<int:user_id>")
@admin_required
def toggle_player(user_id):

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT show_panel FROM users WHERE id=%s", (user_id,))
    status = c.fetchone()[0]

    if status == 1:
        new_status = 0
    else:
        new_status = 1

    c.execute("UPDATE users SET show_panel=%s WHERE id=%s", (new_status,user_id))
    conn.commit()
    conn.close()

    return redirect("/admin")


last_power_times = {}
POWER_COOLDOWN = 20

@app.route("/give_power", methods=["POST"])
def give_power():

    if "player_id" not in session:
        return jsonify({"status": "error"}), 401

    player_id = session["player_id"].lower()
    now = time.time()

    last_time = last_power_times.get(player_id, 0)

    if now - last_time < POWER_COOLDOWN:
        remaining = int(POWER_COOLDOWN - (now - last_time))
        return jsonify({
            "status": "cooldown",
            "remaining": remaining
        })

    last_power_times[player_id] = now

    # 🔥 QUEUE ADD (IMPORTANT)
    power_queue.append({
        "playerId": player_id,
        "value": 1
    })

    print("POWER RECEIVED:", player_id)

    return jsonify({"status": "ok"})
@app.route("/add_player", methods=["POST"])
def add_player():

    if "player_id" not in session or "name" not in session:
        return jsonify({"status": "error"}), 401

    name = session["name"]
    channelId = session["player_id"].lower()

    # already exists check
    for p in players:
        if p["channelId"] == channelId:
            return jsonify({"status": "exists"})

    player = {
        "name": name,
        "channelId": channelId
    }

    players.append(player)

    # 🔥 QUEUE ME ADD
    instant_queue.append(player)

    print("PLAYER ADDED:", player)

    return jsonify({"status": "ok"})
# 🔥 GET ALL PLAYERS
@app.route("/players")
def get_players():
    return jsonify(players)


# 🔥 REMOVE PLAYER
@app.route("/remove_player", methods=["POST"])
def remove_player():

    if "player_id" not in session:
        return jsonify({"status":"error"}), 401

    user_id = session["player_id"].lower()

    global players
    players = [p for p in players if p["channelId"] != user_id]

    return jsonify({"status": "removed"})
@app.route("/get_power")
def get_power():

    if len(power_queue) > 0:
        return jsonify(power_queue.pop(0))   # 🔥 queue se ek power nikalo

    return jsonify({
        "playerId": "",
        "value": 0
    })
@app.route("/verify_youtube", methods=["POST"])
def verify_youtube():

    data = request.get_json()
    handle = data.get("handle")

    if not handle:
        return jsonify({"status": "error"})

    if not handle.startswith("@"):
        return jsonify({"status": "invalid"})

    url = f"https://www.youtube.com/{handle}"

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=5, allow_redirects=True)

        final_url = r.url.rstrip("/")

        # 🔥 HANDLE EXACT MATCH (CASE-SENSITIVE)
        if final_url.lower() == url.lower():
            return jsonify({"status": "ok"})
        else:
            return jsonify({"status": "fail"})

    except:
        return jsonify({"status": "error"})
@app.route("/get_instant_player")
def get_instant_player():

    global instant_queue

    if len(instant_queue) > 0:

        player = instant_queue.pop(0)  # FIFO (first in first out)

        return jsonify(player)

    return jsonify({
        "name": "",
        "channelId": ""
    })
@app.route("/send_otp", methods=["POST"])
def send_otp():

    data = request.json
    email = data.get("email")

    if not valid_email(email):
        return jsonify({"status":"invalid_email"})

    otp = str(random.randint(1000,9999))

    otp_store[email] = {
    "otp": otp,
    "time": time.time()
}

    send_email_otp(email, otp)   # 🔥 EMAIL SEND

    return jsonify({"status":"sent"})
@app.route("/verify_otp", methods=["POST"])
def verify_otp():

    data = request.get_json()

    if not data:
        return jsonify({"status":"bad_request"})

    email = data.get("email")
    otp = data.get("otp")

    otp_data = otp_store.get(email)

    if not otp_data:
        return jsonify({"status":"fail"})

    if time.time() - otp_data["time"] > 300:
        otp_store.pop(email, None)
        return jsonify({"status":"expired"})

    if otp_data["otp"] == otp:
        session["otp_verified"] = email
        otp_store.pop(email,None)
        return jsonify({"status":"ok"})
    else:
        return jsonify({"status":"fail"})
@app.route("/verify_login_otp_auto", methods=["POST"])
def verify_login_otp_auto():

    data = request.get_json()

    if not data:
        return jsonify({"status": "bad_request"})

    otp = data.get("otp")

    if not otp:
        return jsonify({"status": "invalid_otp"})

    email = session.get("temp_login_email")

    if not email:
        return jsonify({"status":"session_expired"})

    otp_data = otp_store.get(email)

    if not otp_data:
        return jsonify({"status":"fail"})

    if time.time() - otp_data["time"] > 300:
        otp_store.pop(email, None)
        session.pop("temp_login_email", None)
        return jsonify({"status":"expired"})

    if otp_data["otp"] != otp:
        return jsonify({"status":"fail"})

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE email=%s", (email,))
    user = c.fetchone()

    if not user:
        conn.close()
        return jsonify({"status":"fail"})

    session["player_id"] = user[4]
    session["name"] = user[1]
    update_last_active(user[4])

    token = str(uuid.uuid4())

    c.execute(
        "INSERT INTO remembered_devices (email, device_token, created_at) VALUES (%s, %s,%s)",
        (email, token, time.time())
    )
    conn.commit()
    conn.close()

    otp_store.pop(email, None)
    session.pop("temp_login_email", None)

    response = jsonify({"status":"ok"})
    response.set_cookie(
        "device_token",
        token,
        max_age=60*60*24*30,
        httponly=True,
        secure=False,
        samesite="Lax"
    )

    return response
@app.route("/give_portal_power", methods=["POST"])
def give_portal_power():
    try:

        if "player_id" not in session:
            return jsonify({"status": "error"})

        player_id = session["player_id"].lower()

        power_queue.append({
            "playerId": player_id,
            "type": "portal"
        })

        print("🌀 PORTAL SENT:", player_id)

        return jsonify({"status": "ok"})

    except Exception as e:
        print("❌ ERROR:", str(e))
        return jsonify({"status": "error"})
@app.route("/admin_login", methods=["GET","POST"])
def admin_login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/admin")
        else:
            return "Invalid Admin Credentials ❌"

    return render_template("admin_login.html")
@app.route("/move", methods=["POST"])
def move():

    if "player_id" not in session:
        return jsonify({"status": "error"})

    data = request.get_json()
    direction = data.get("direction")

    player_id = session["player_id"].lower()

    move_queue.append({
        "playerId": player_id,
        "type": "move",
        "dir": direction
    })

    return jsonify({"status": "ok"})
@app.route("/get_move")
def get_move():

    if len(move_queue) > 0:
        return jsonify(move_queue.pop(0))

    return jsonify({
        "playerId": "",
        "type": ""
    })
@app.route("/api/online_status")
def online_status():

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT player_id, last_active FROM users")
    users = c.fetchall()

    conn.close()

    result = []

    for u in users:
        status = (time.time() - u[1]) < 8
        result.append({
            "player_id": u[0],
            "online": status
        })

    return jsonify(result)
@app.route("/admin_delete_user/<int:user_id>")
@admin_required
def admin_delete_user(user_id):

    conn = get_db()
    c = conn.cursor()

    # ❌ user delete from database
    c.execute("DELETE FROM points_history WHERE player_id IN (SELECT player_id FROM users WHERE id=%s)", (user_id,))
    c.execute("DELETE FROM users WHERE id=%s", (user_id,))
    conn.commit()
    conn.close()

    print("❌ USER DELETED:", user_id)

    return redirect("/admin")
@app.route("/api/heartbeat", methods=["POST"])
def heartbeat():

    if "player_id" in session:
        update_last_active(session["player_id"])

    return jsonify({"status": "ok"})
@app.route("/forgot_password", methods=["GET","POST"])
def forgot_password():

    if request.method == "POST":

        email = request.form["email"].strip().lower()

        if not valid_email(email):
            return "Invalid Email"

        conn = get_db()
        c = conn.cursor()

        c.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = c.fetchone()
        conn.close()

        if not user:
            return "Email not found ❌"

        # 🔥 OTP SEND
        otp = str(random.randint(1000,9999))
        otp_store[email] = {
            "otp": otp,
            "time": time.time()
        }

        session["reset_email"] = email

        send_email_otp(email, otp)

        return redirect("/reset_password")

    return render_template("forgot_password.html")
@app.route("/reset_password", methods=["GET","POST"])
def reset_password():

    email = session.get("reset_email")

    if not email:
        return redirect("/login")

    if request.method == "POST":

        otp = request.form["otp"]
        new_password = request.form["password"]

        otp_data = otp_store.get(email)

        if not otp_data:
            return "OTP expired ❌"

        if time.time() - otp_data["time"] > 300:
            otp_store.pop(email, None)
            return "OTP expired ❌"

        if otp_data["otp"] != otp:
            return "Wrong OTP ❌"

        if not strong_password(new_password):
            return "Weak password ❌"

        # 🔥 UPDATE PASSWORD
        conn = get_db()
        c = conn.cursor()

        hashed = generate_password_hash(new_password)

        c.execute("UPDATE users SET password=%s WHERE email=%s", (hashed, email))

        conn.commit()
        conn.close()

        otp_store.pop(email, None)
        session.pop("reset_email", None)

        return "Password updated ✅ <br><a href='/login'>Login</a>"

    return render_template("reset_password.html")
ad_sessions = {}
last_ad_watch = {}

@app.route("/start_ad", methods=["POST"])
def start_ad():
    if "player_id" not in session:
        return jsonify({"status":"error"})

    data = request.get_json()
    duration = data.get("duration")

    ad_sessions[session["player_id"]] = {
        "start": time.time(),
        "duration": duration
    }

    return jsonify({"status":"ok"})
@app.route("/watch_ad", methods=["POST"])
def watch_ad():

    if "player_id" not in session:
        return jsonify({"status":"error"})

    pid = session["player_id"]
    ad = ad_sessions.get(pid)

    if not ad:
        return jsonify({"status":"invalid"})

    duration = ad["duration"]  # 30 or 60
    now = time.time()

    conn = get_db()
    c = conn.cursor()

    # 🔥 COUNT LAST 24 HOURS
    c.execute("""
        SELECT COUNT(*) FROM ad_watch
        WHERE player_id=%s AND ad_type=%s AND watched_at > %s
    """, (pid, duration, now - 86400))

    count = c.fetchone()[0]

    # ❌ LIMIT CHECK
    if count >= 6:
        conn.close()
        return jsonify({
            "status": "limit_reached",
            "msg": "24 घंटे का limit पूरा हो गया"
        })

    # ⏱️ WATCH CHECK
    watched = now - ad["start"]
    if watched < duration - 3:
        conn.close()
        return jsonify({"status":"cheat"})

    # ✅ SAVE ENTRY (PERMANENT)
    c.execute("""
        INSERT INTO ad_watch (player_id, ad_type, watched_at)
        VALUES (%s,%s,%s)
    """, (pid, duration, now))

    # 🎯 POINTS
    points = 8 if duration == 30 else 20
    update_points(pid, points)

    conn.commit()
    conn.close()

    ad_sessions.pop(pid)

    return jsonify({"status":"ok","points":points})
@app.route("/admin/clean_ads")
@admin_required
def clean_ads():

    conn = get_db()
    c = conn.cursor()

    # 2 din purana data delete
    c.execute("""
        DELETE FROM ad_watch WHERE watched_at < %s
    """, (time.time() - (86400 * 2),))

    conn.commit()
    conn.close()

    return "Old ad data cleaned ✅"
@app.route("/api/ad_status")
def ad_status():

    if "player_id" not in session:
        return jsonify({"status":"error"})

    pid = session["player_id"]
    now = time.time()

    conn = get_db()
    c = conn.cursor()

    # 🔥 30 sec count
    c.execute("""
        SELECT COUNT(*) FROM ad_watch
        WHERE player_id=%s AND ad_type=30 AND watched_at > %s
    """, (pid, now - 86400))
    count30 = c.fetchone()[0]

    # 🔥 60 sec count
    c.execute("""
        SELECT COUNT(*) FROM ad_watch
        WHERE player_id=%s AND ad_type=60 AND watched_at > %s
    """, (pid, now - 86400))
    count60 = c.fetchone()[0]

    # 🔥 last watch time (timer ke liye)
    c.execute("""
        SELECT MAX(watched_at) FROM ad_watch
        WHERE player_id=%s
    """, (pid,))
    last = c.fetchone()[0]

    conn.close()

    return jsonify({
        "count30": count30,
        "count60": count60,
        "last_watch": last
    })
@app.route("/use_token", methods=["POST"])
@admin_required
def use_token():

    token = request.form["token"]

    conn = get_db()
    c = conn.cursor()

    c.execute("""
    SELECT player_id, token_used 
    FROM users 
    WHERE token_id=%s
    """,(token,))
    
    user = c.fetchone()

    if not user:
        conn.close()
        return "Invalid ❌"

    if user[1] == 1:
        conn.close()
        return "Already Used ❌"

    c.execute("""
    UPDATE users 
    SET token_used=1, spin_token=0, token_id=NULL
    WHERE player_id=%s
    """,(user[0],))

    conn.commit()
    conn.close()

    return "Token Used ✅"
@app.route("/leaderboard")
def leaderboard():

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT name,player_id,points FROM users ORDER BY points DESC LIMIT 50")
    data = c.fetchall()

    conn.close()

    return render_template("leaderboard.html", data=data)
@app.route("/claim_token", methods=["POST"])
def claim_token():

    if "player_id" not in session:
        return jsonify({"status":"login_required"})

    pid = session["player_id"]

    conn = get_db()
    c = conn.cursor()

    # 🔥 get game state
    c.execute("""
    SELECT m1_claimed, m2_claimed, m3_claimed 
    FROM game_state WHERE id=1
    """)
    m1, m2, m3 = c.fetchone()

    # 🔥 user points + base
    c.execute("""
    SELECT points, base_points 
    FROM users WHERE player_id=%s
    """,(pid,))
    points, base = c.fetchone()

    # 🎯 targets
    t1 = base + 168
    t2 = base + 504
    t3 = base + 1008

    # ❌ LEVEL 1
    if points >= t1 and m1 == 0:
        c.execute("UPDATE game_state SET m1_claimed=1 WHERE id=1")

    # ❌ LEVEL 2
    elif points >= t2 and m2 == 0:
        c.execute("UPDATE game_state SET m2_claimed=1 WHERE id=1")

    # ❌ LEVEL 3
    elif points >= t3 and m3 == 0:
        c.execute("UPDATE game_state SET m3_claimed=1 WHERE id=1")

    else:
        conn.close()
        return jsonify({"status":"not_reached"})

    # ✅ WIN
    token_code = "WIN-" + str(random.randint(10000,99999))

    c.execute("UPDATE users SET points=0 WHERE player_id=%s",(pid,))

    conn.commit()
    conn.close()

    return jsonify({
        "status":"winner",
        "token":token_code
    })
@app.route("/admin/player/<player_id>")
@admin_required
def admin_player(player_id):

    conn = get_db()
    c = conn.cursor()

    # user data
    c.execute("SELECT name,email,points FROM users WHERE player_id=%s",(player_id,))
    user = c.fetchone()

    # history
    c.execute("""
    SELECT points,reason,created_at 
    FROM points_history 
    WHERE player_id=%s 
    ORDER BY id DESC LIMIT 50
    """,(player_id,))
    history = c.fetchall()

    conn.close()

    return render_template("admin_player.html", user=user, history=history, pid=player_id)
@app.route("/admin/update_points", methods=["POST"])
@admin_required
def admin_update_points():

    pid = request.form["pid"]
    pts = int(request.form["points"])
    action = request.form["action"]

    conn = get_db()
    c = conn.cursor()

    # current points
    c.execute("SELECT points FROM users WHERE player_id=%s",(pid,))
    current = c.fetchone()[0]

    if action == "add":
        new_points = current + pts
        reason = "admin_add"
    else:
        new_points = max(0, current - pts)
        reason = "admin_remove"

    # update
    c.execute("UPDATE users SET points=%s WHERE player_id=%s",(new_points,pid))

    # history save
    c.execute("""
    INSERT INTO points_history (player_id, points, reason, created_at)
    VALUES (%s,%s,%s,%s)
    """,(pid, pts, reason, time.time()))

    conn.commit()
    conn.close()

    return redirect(f"/admin/player/{pid}")
@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")
@app.route("/admin_logout")
@admin_required
def admin_logout():
    session.pop("admin", None)
    return redirect("/admin_login")

def update_points(pid, add):

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT points FROM users WHERE player_id=%s",(pid,))
    current_points = c.fetchone()[0]

    new_points = current_points + add

    # 🧠 block system
    current_block = current_points // 10000
    new_block = new_points // 10000

    # 🎯 TOKEN GENERATE (10000,20000,30000...)
    if new_block > current_block:

        import secrets, string

        chars = string.ascii_uppercase + string.digits
        raw = ''.join(secrets.choice(chars) for _ in range(12))

        token_id = f"RK-{raw[0:4]}-{raw[4:8]}-{raw[8:12]}"
        expiry = time.time() + (60*60*24*21)

        c.execute("""
        UPDATE users 
        SET spin_token=1, token_id=%s, token_expiry=%s
        WHERE player_id=%s
        """,(token_id,expiry,pid))

    # ❌ expire after +1000
    if (new_points % 10000) >= 1000:
        c.execute("""
        UPDATE users 
        SET spin_token=0, token_id=NULL
        WHERE player_id=%s
        """,(pid,))

    # ✅ update points
    c.execute("UPDATE users SET points=%s WHERE player_id=%s",(new_points,pid))

    conn.commit()
    conn.close()
init_db()
if __name__ =="__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
