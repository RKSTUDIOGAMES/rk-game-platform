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
instant_player = None

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

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


current_power = None

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        player_id TEXT UNIQUE,
        show_panel INTEGER DEFAULT 0,
        blocked INTEGER DEFAULT 0
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS live_stream (
        id SERIAL PRIMARY KEY,
        video_id TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS remembered_devices (
        id SERIAL PRIMARY KEY,
        email TEXT,
        device_token TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS login_attempts (
        id SERIAL PRIMARY KEY,
        email TEXT,
        attempts INTEGER DEFAULT 0,
        last_attempt DOUBLE PRECISION
    )
    """)

    # default row
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

def send_email_otp(receiver_email, otp):

    sender_email = os.getenv("SENDER_EMAIL")
    app_password = os.getenv("EMAIL_PASS")

    subject = "🔐 OTP Verification - RK Games"

    msg = MIMEText(f"""
    <html>
    <body style="margin:0;padding:0;background:#f2f3f5;font-family:Arial,Helvetica,sans-serif;">

    <div style="max-width:420px;margin:30px auto;background:#ffffff;border-radius:12px;
    box-shadow:0 4px 12px rgba(0,0,0,0.1);overflow:hidden;">

    <!-- Header -->
    <div style="background:#4CAF50;padding:15px;text-align:center;">
    <h2 style="color:white;margin:0;">RK Games 🎮</h2>
    </div>

    <!-- Body -->
    <div style="padding:25px;text-align:center;">

    <h3 style="margin-top:0;color:#333;">OTP Verification</h3>

    <p style="color:#555;font-size:15px;">
    Use the OTP below to complete your signup
    </p>

    <!-- OTP BOX -->
    <div style="margin:20px 0;">
    <span style="display:inline-block;background:#f4f4f4;padding:15px 25px;
    font-size:28px;letter-spacing:8px;border-radius:8px;color:#333;">
    {otp}
    </span>
    </div>

    <p style="color:#777;font-size:13px;">
    This OTP is valid for 5 minutes
    </p>

    <hr style="margin:20px 0;border:none;border-top:1px solid #eee;">

    <p style="font-size:12px;color:#999;">
    Do not share this OTP with anyone.<br>
    If you didn’t request this, please ignore this email.
    </p>

    </div>

    <!-- Footer -->
    <div style="background:#fafafa;padding:12px;text-align:center;font-size:12px;color:#888;">
    © RK Games | Secure Login System
    </div>

    </div>

    </body>
    </html>
    """, "html")

    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = receiver_email

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(sender_email, app_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        print("OTP SENT SUCCESS ✅")

    except Exception as e:
        print("EMAIL ERROR:", e)
@app.route("/")
def home():
    return redirect("/login")


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
            c.execute(
                "SELECT * FROM remembered_devices WHERE email=%s AND device_token=%s",
                (email, device_token)
            )
            device = c.fetchone()

            if device:
                session["player_id"] = user[4]
                session["name"] = user[1]
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

    c.execute(
        "SELECT blocked FROM users WHERE player_id=%s",
        (session["player_id"],)
    )

    b = c.fetchone()

    if b and b[0] == 1:
        conn.close()
        session.clear()
        return "You are blocked by admin"

    c.execute(
        "SELECT show_panel FROM users WHERE player_id=%s",
        (session["player_id"],)
    )

    status = c.fetchone()

    controller_enable = 0

    if status and status[0] == 1:
        controller_enable = 1

    c.execute("SELECT video_id FROM live_stream LIMIT 1")
    video = c.fetchone()

    conn.close()

    return render_template(
        "dashboard.html",
        name=session["name"],
        player_id=session["player_id"],
        video_id=video[0],
        controller_enable=controller_enable
    )


@app.route("/logout")
def logout():

    session.clear()

    response = redirect("/login")
    response.delete_cookie("device_token")

    return response
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

        conn.commit()

    c.execute("SELECT * FROM users ORDER BY show_panel DESC, id ASC")
    users = c.fetchall()

    c.execute("SELECT video_id FROM live_stream WHERE id=1")
    video = c.fetchone()

    conn.close()

    return render_template("admin.html", users=users, video_id=video[0])


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


@app.route("/give_power", methods=["POST"])
def give_power():

    global current_power

    data = request.json

    current_power = data

    print("POWER RECEIVED:", current_power)

    return jsonify({"status":"ok"})
# 🔥 ADD PLAYER
@app.route("/add_player", methods=["POST"])
def add_player():

    data = request.json

    name = data.get("name")
    channelId = data.get("channelId")

    if not name or not channelId:
        return jsonify({"status": "error"})

    channelId = channelId.lower()

    # 🔥 अगर already मौजूद है (LIVE या पहले से)
    for p in players:
        if p["channelId"] == channelId:
            return jsonify({"status": "exists"})

    # ✅ तभी add होगा जब नहीं है
    player = {
        "name": name,
        "channelId": channelId
    }

    players.append(player)
    global instant_player
    instant_player = player

    print("PLAYER ADDED FROM WEB:", player)

    return jsonify({"status": "ok"})
# 🔥 GET ALL PLAYERS
@app.route("/players")
def get_players():
    return jsonify(players)


# 🔥 REMOVE PLAYER
@app.route("/remove_player", methods=["POST"])
def remove_player():

    data = request.json
    channelId = data.get("channelId").lower()

    global players
    players = [p for p in players if p["channelId"] != channelId]

    return jsonify({"status": "removed"})

@app.route("/get_power")
def get_power():

    global current_power

    if current_power:

        temp = current_power
        current_power = None

        return jsonify(temp)

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

    global instant_player

    if instant_player:
        temp = instant_player
        instant_player = None
        return jsonify(temp)

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

    data = request.json
    email = data.get("email")
    otp = data.get("otp")

    otp_data = otp_store.get(email)

    if not otp_data:
        return jsonify({"status":"fail"})

    # ⏱️ expiry check
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

   
    data = request.json
    otp = data.get("otp")
    email = session.get("temp_login_email")

    # ❌ email session missing
    if not email:
        return jsonify({"status":"fail"})

    otp_data = otp_store.get(email)

    # ❌ OTP exist nahi karta
    if not otp_data:
        return jsonify({"status":"fail"})

    # ⏱️ EXPIRY CHECK (5 min = 300 sec)
    if time.time() - otp_data["time"] > 300:
        otp_store.pop(email, None)
        session.pop("temp_login_email", None)
        return jsonify({"status":"expired"})

    # ❌ OTP match nahi
    if otp_data["otp"] != otp:
        return jsonify({"status":"fail"})

    # ✅ OTP correct → login
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE email=%s", (email,))
    user = c.fetchone()

    if not user:
        conn.close()
        return jsonify({"status":"fail"})

    session["player_id"] = user[4]
    session["name"] = user[1]

    # 🔥 AUTO REMEMBER DEVICE
    token = str(uuid.uuid4())

    c.execute(
        "INSERT INTO remembered_devices (email, device_token) VALUES (%s, %s)",
        (email, token)
    )
    conn.commit()
    conn.close()

    # 🔥 CLEANUP
    otp_store.pop(email, None)
    session.pop("temp_login_email", None)

    response = jsonify({"status":"ok"})
    response.set_cookie(
    "device_token",
    token,
    max_age=60*60*24*30,
    httponly=True,
    secure = os.getenv("ENV") == "production",
    samesite="Lax"
)

    return response
@app.route("/admin_login", methods=["GET","POST"])
def admin_login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:

            otp = str(random.randint(1000,9999))
            otp_store[email] = {
    "otp": otp,
    "time": time.time()
}
            session["admin_temp"] = email

            send_email_otp(email, otp)

            return render_template("admin_otp.html")

        else:
            return "Invalid Admin Credentials ❌"

    return render_template("admin_login.html")
@app.route("/verify_admin_otp", methods=["POST"])
def verify_admin_otp():

    otp = request.form["otp"]
    email = session.get("admin_temp")

    if not email:
        return "Session expired ❌"

    otp_data = otp_store.get(email)

    if not otp_data:
        return "OTP not found ❌"

    # ⏱️ expiry check
    if time.time() - otp_data["time"] > 300:
        otp_store.pop(email, None)
        session.pop("admin_temp", None)
        return "OTP Expired ⏱️ Please login again"

    if otp_data["otp"] == otp:

        session["admin"] = True

        otp_store.pop(email, None)
        session.pop("admin_temp", None)

        return redirect("/admin")

    return "Wrong OTP ❌"
@app.route("/admin_logout")
@admin_required
def admin_logout():
    session.pop("admin", None)
    return redirect("/admin_login")
init_db()
if __name__ =="__main__":
    app.run(host="0.0.0.0", port=5000)
