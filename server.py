"""
MRABILITY Finance Backend — Flask + PostgreSQL / SQLite
Full production-ready server:
  - JWT authentication (login / register)
  - Admin role protection
  - Loan applications storage
  - Credit score records
  - Admin dashboard API
  - PostgreSQL for production, SQLite for local development
"""

import os, sqlite3, hashlib, hmac, secrets, json, re, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import Flask, request, jsonify, g, send_from_directory, redirect
from flask_cors import CORS
import jwt
import bcrypt

try:
    import psycopg2
    import psycopg2.extras
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

# ── Load .env file automatically (no manual export needed) ──────
def _load_dotenv():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if not os.path.exists(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, _, val = line.partition('=')
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            # Only set if not already set by the shell environment
            # (shell env vars take priority over .env file)
            if key and not os.environ.get(key):
                os.environ[key] = val
_load_dotenv()

# ── Config ─────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL  = os.environ.get('DATABASE_URL', '')
USE_POSTGRES  = bool(DATABASE_URL) and HAS_PSYCOPG2
DB_PATH       = os.path.join(BASE_DIR, 'mrability.db')
SECRET_KEY    = os.environ.get('SECRET_KEY', 'mrability-secret-key-change-in-prod-2026')
JWT_EXPIRY_HOURS = 24
PORT = int(os.environ.get('PORT', 8080))

# Google OAuth — set these via environment or replace with your Google Console credentials
GOOGLE_CLIENT_ID     = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
GOOGLE_REDIRECT_URI  = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:8080/api/auth/google/callback')

# Facebook OAuth
FACEBOOK_APP_ID      = os.environ.get('FACEBOOK_APP_ID', '')
FACEBOOK_APP_SECRET  = os.environ.get('FACEBOOK_APP_SECRET', '')

# SMS OTP — Twilio (optional). Without these, OTP prints to server console (for testing).
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN  = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_FROM_NUMBER = os.environ.get('TWILIO_FROM_NUMBER', '')

# Email OTP — SMTP (optional). Without these, OTP prints to server console (for testing).
SMTP_HOST     = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT     = int(os.environ.get('SMTP_PORT', 587))
SMTP_USER     = os.environ.get('SMTP_USER', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
SMTP_FROM     = os.environ.get('SMTP_FROM', '')

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ── Database Abstraction Layer ────────────────────────────
# Supports PostgreSQL (production) and SQLite (local dev)
# Set DATABASE_URL env var for Postgres, otherwise SQLite is used

class PgRowProxy(dict):
    """Make psycopg2 DictRow behave like sqlite3.Row (key access)."""
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)

def _pg_connect():
    url = DATABASE_URL
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    conn = psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)
    conn.autocommit = False
    return conn

class DbWrapper:
    """Thin wrapper that translates SQLite `?` placeholders to `%s` for PostgreSQL."""
    def __init__(self, conn, is_pg=False):
        self._conn = conn
        self._pg   = is_pg
    def _q(self, sql):
        return sql.replace('?', '%s') if self._pg else sql
    def execute(self, sql, params=None):
        cur = self._conn.cursor()
        cur.execute(self._q(sql), params or ([] if self._pg else ()))
        return cur
    def executescript(self, sql):
        if self._pg:
            self._conn.cursor().execute(sql)
        else:
            self._conn.executescript(sql)
    def commit(self):
        self._conn.commit()
    def rollback(self):
        if self._pg:
            self._conn.rollback()
    def close(self):
        self._conn.close()

def get_db():
    if 'db' not in g:
        if USE_POSTGRES:
            conn = _pg_connect()
            g.db = DbWrapper(conn, is_pg=True)
        else:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            g.db = DbWrapper(conn, is_pg=False)
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db: db.close()

def _now():
    return datetime.now(timezone.utc).isoformat()

def _serial():
    return "SERIAL" if USE_POSTGRES else "INTEGER"

def _autoincrement():
    return "" if USE_POSTGRES else "AUTOINCREMENT"

def _default_now():
    return "DEFAULT NOW()" if USE_POSTGRES else "DEFAULT (datetime('now'))"

def _on_conflict_ignore():
    return "ON CONFLICT DO NOTHING" if USE_POSTGRES else "OR IGNORE"

def init_db():
    if USE_POSTGRES:
        conn = _pg_connect()
        cur = conn.cursor()
        print("   Using PostgreSQL")
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        print("   Using SQLite")

    SER = "SERIAL" if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"
    NOW = "DEFAULT NOW()" if USE_POSTGRES else "DEFAULT (datetime('now'))"
    PK  = " PRIMARY KEY" if USE_POSTGRES else ""

    stmts = [
        f"""CREATE TABLE IF NOT EXISTS users (
            id          {SER}{PK},
            name        TEXT NOT NULL,
            mobile      TEXT NOT NULL,
            email       TEXT NOT NULL UNIQUE,
            password    TEXT NOT NULL,
            role        TEXT NOT NULL DEFAULT 'user',
            created_at  TEXT NOT NULL {NOW},
            last_login  TEXT
        )""",
        f"""CREATE TABLE IF NOT EXISTS applications (
            id            {SER}{PK},
            ref_id        TEXT NOT NULL UNIQUE,
            user_id       INTEGER,
            loan_type     TEXT NOT NULL,
            full_name     TEXT,
            mobile        TEXT,
            email         TEXT,
            employment    TEXT,
            monthly_income TEXT,
            loan_amount   TEXT,
            property_type TEXT,
            property_value TEXT,
            car_budget    TEXT,
            business_name TEXT,
            annual_turnover TEXT,
            dob           TEXT,
            pincode       TEXT,
            extra_data    TEXT,
            status        TEXT NOT NULL DEFAULT 'Submitted',
            notes         TEXT,
            created_at    TEXT NOT NULL {NOW},
            updated_at    TEXT NOT NULL {NOW},
            FOREIGN KEY(user_id) REFERENCES users(id)
        )""",
        f"""CREATE TABLE IF NOT EXISTS credit_scores (
            id          {SER}{PK},
            user_id     INTEGER,
            name        TEXT,
            pan         TEXT,
            mobile      TEXT,
            score       INTEGER NOT NULL,
            tier        TEXT NOT NULL,
            checked_at  TEXT NOT NULL {NOW},
            FOREIGN KEY(user_id) REFERENCES users(id)
        )""",
        f"""CREATE TABLE IF NOT EXISTS activity_log (
            id         {SER}{PK},
            user_id    INTEGER,
            action     TEXT NOT NULL,
            details    TEXT,
            ip         TEXT,
            created_at TEXT NOT NULL {NOW}
        )""",
        f"""CREATE TABLE IF NOT EXISTS otp_requests (
            id         {SER}{PK},
            identifier TEXT NOT NULL,
            otp        TEXT NOT NULL,
            purpose    TEXT NOT NULL DEFAULT 'password_reset',
            expires_at TEXT NOT NULL,
            used       INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL {NOW}
        )""",
        f"""CREATE TABLE IF NOT EXISTS interest_rates (
            id             {SER}{PK},
            loan_type      TEXT NOT NULL,
            bank_name      TEXT NOT NULL,
            rate_min       REAL NOT NULL,
            rate_max       REAL NOT NULL,
            processing_fee TEXT NOT NULL DEFAULT '—',
            max_amount     TEXT NOT NULL DEFAULT '—',
            tenure_max     INTEGER NOT NULL DEFAULT 5,
            is_featured    INTEGER NOT NULL DEFAULT 0,
            display_order  INTEGER NOT NULL DEFAULT 99,
            updated_at     TEXT NOT NULL {NOW},
            UNIQUE(loan_type, bank_name)
        )""",
        f"""CREATE TABLE IF NOT EXISTS calculator_defaults (
            id         {SER}{PK},
            key        TEXT NOT NULL UNIQUE,
            value      REAL NOT NULL,
            label      TEXT NOT NULL,
            updated_at TEXT NOT NULL {NOW}
        )""",
    ]

    for stmt in stmts:
        cur.execute(stmt)
    conn.commit()

    # Migrate: add dob + pincode columns if missing (existing DBs)
    for col in ['dob', 'pincode']:
        try:
            cur.execute(f"ALTER TABLE applications ADD COLUMN {col} TEXT DEFAULT ''")
            conn.commit()
        except Exception:
            conn.rollback()

    # Ensure unique index exists BEFORE seeding
    try:
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_rates_unique ON interest_rates(loan_type, bank_name)")
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_calc_defaults_unique ON calculator_defaults(key)")
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Index: {e}")

    # Placeholder helpers
    P = "%s" if USE_POSTGRES else "?"
    OCI = "ON CONFLICT DO NOTHING" if USE_POSTGRES else "OR IGNORE"

    # Create default admin user if not exists
    admin_pw = bcrypt.hashpw(b'Admin@1234', bcrypt.gensalt()).decode()
    try:
        cur.execute(f"""
            INSERT {OCI} INTO users (name, mobile, email, password, role)
            VALUES ({P},{P},{P},{P},{P})
        """, ('Admin User', '9999999999', 'admin@mrability.in', admin_pw, 'admin'))
        conn.commit()
        print("✅ Default admin: admin@mrability.in / Admin@1234")
    except Exception as e:
        conn.rollback()
        print(f"Admin seed: {e}")

    # Seed interest rates
    rates_seed = [
        ('personal_loan','HDFC Bank',     10.99, 24.00, 'Up to 2.5%', '₹40 Lakh',  5, 1, 1),
        ('personal_loan','SBI',           11.15, 15.30, '1% + taxes',  '₹20 Lakh',  5, 0, 2),
        ('personal_loan','ICICI Bank',    10.99, 16.25, 'Up to 2.5%', '₹50 Lakh',  5, 0, 3),
        ('personal_loan','Axis Bank',     11.25, 22.00, 'Up to 2%',   '₹40 Lakh',  5, 0, 4),
        ('personal_loan','Bajaj Finserv', 13.00, 35.00, 'Up to 3.99%','₹35 Lakh',  5, 0, 5),
        ('home_loan','SBI',               8.50,  10.15, '0.35%',       '₹5 Crore',  30, 1, 1),
        ('home_loan','HDFC Bank',         8.70,  9.95,  'Up to 0.5%',  '₹10 Crore', 30, 0, 2),
        ('home_loan','ICICI Bank',        8.75,  9.80,  'Up to 0.5%',  '₹5 Crore',  30, 0, 3),
        ('home_loan','Kotak Mahindra',    8.65,  9.50,  '0.5%',        '₹5 Crore',  20, 0, 4),
        ('home_loan','LIC Housing',       8.50,  10.50, 'Nil',         '₹15 Crore', 30, 0, 5),
        ('car_loan','SBI',                8.75,  10.25, 'Nil',         '₹1 Crore',  7, 1, 1),
        ('car_loan','HDFC Bank',          8.80,  10.00, 'Up to 0.5%',  '₹1.5 Crore',7, 0, 2),
        ('car_loan','ICICI Bank',         9.00,  10.75, 'Up to 1%',    '₹1 Crore',  7, 0, 3),
        ('car_loan','Axis Bank',          9.05,  11.50, 'Up to 1%',    '₹1 Crore',  7, 0, 4),
        ('business_loan','HDFC Bank',     10.75, 22.50, 'Up to 2%',    '₹75 Lakh',  4, 1, 1),
        ('business_loan','ICICI Bank',    11.00, 18.00, 'Up to 2%',    '₹2 Crore',  5, 0, 2),
        ('business_loan','Axis Bank',     14.95, 19.20, 'Up to 2%',    '₹50 Lakh',  3, 0, 3),
        ('business_loan','Bajaj Finserv', 14.00, 26.00, 'Up to 3%',    '₹80 Lakh',  5, 0, 4),
        ('lap','SBI',                      9.25,  11.50, 'Up to 1%',   '₹7.5 Crore',15, 1, 1),
        ('lap','HDFC Bank',                9.40,  12.00, 'Up to 1%',   '₹10 Crore', 15, 0, 2),
        ('lap','ICICI Bank',               9.50,  12.50, 'Up to 1%',   '₹5 Crore',  15, 0, 3),
        ('used_car_loan','SBI',           11.00, 15.50, 'Nil',         '₹50 Lakh',  5, 1, 1),
        ('used_car_loan','HDFC Bank',     11.50, 16.00, 'Up to 1%',    '₹50 Lakh',  5, 0, 2),
        ('used_car_loan','Mahindra Fin.', 10.00, 18.00, 'Up to 2%',    '₹30 Lakh',  5, 0, 3),
    ]
    for r in rates_seed:
        try:
            cur.execute(f"""
                INSERT {OCI} INTO interest_rates
                  (loan_type,bank_name,rate_min,rate_max,processing_fee,max_amount,tenure_max,is_featured,display_order)
                VALUES ({P},{P},{P},{P},{P},{P},{P},{P},{P})""", r)
        except Exception as e:
            conn.rollback()
            print(f"Rate seed skip: {e}")
    conn.commit()

    # Seed calculator defaults
    calc_defaults = [
        ('emi_rate',       10.99, 'EMI Calculator default interest rate (% p.a.)'),
        ('emi_amount',    500000, 'EMI Calculator default loan amount (₹)'),
        ('emi_tenure',         5, 'EMI Calculator default tenure (years)'),
        ('eligibility_rate',10.99,'Eligibility Calculator assumed rate (% p.a.)'),
        ('sip_rate',        12.00, 'SIP Calculator default return rate (% p.a.)'),
        ('fd_rate',          7.50, 'FD Calculator default rate (% p.a.)'),
        ('ppf_rate',         7.10, 'PPF rate (% p.a.) — set by Govt, update as notified'),
    ]
    for k, v, lbl in calc_defaults:
        try:
            cur.execute(f"INSERT {OCI} INTO calculator_defaults (key,value,label) VALUES ({P},{P},{P})", (k, v, lbl))
        except Exception as e:
            conn.rollback()
            print(f"Calc default seed skip: {e}")
    conn.commit()

    conn.close()

# ── JWT Helpers ─────────────────────────────────────────
def create_token(user_id, role, name):
    payload = {
        'sub':  str(user_id),
        'role': role,
        'name': name,
        'iat':  datetime.now(timezone.utc),
        'exp':  datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def decode_token(token):
    data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    data['sub'] = int(data['sub'])   # convert back to int for DB queries
    return data

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        try:
            payload = decode_token(auth.split(' ', 1)[1])
            request.user = payload
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        return f(*args, **kwargs)
    return decorated

def require_admin(f):
    @wraps(f)
    @require_auth
    def decorated(*args, **kwargs):
        if request.user.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated

# ── Utility ─────────────────────────────────────────────
def gen_ref_id(loan_type):
    prefix = {'personal_loan':'PL','home_loan':'HL','business_loan':'BL',
              'car_loan':'CL','lap':'LAP','used_car_loan':'UCL',
              'credit_card':'CC'}.get(loan_type, 'APP')
    return f"FN-{prefix}-{int(datetime.now().timestamp())}"

def log_action(db, user_id, action, details=None):
    db.execute("INSERT INTO activity_log (user_id, action, details, ip) VALUES (?,?,?,?)",
               (user_id, action, details, request.remote_addr))

# ── OTP Helpers ─────────────────────────────────────────────
def _send_sms_otp(mobile, otp):
    """Send OTP via Twilio SMS. Returns (success, message)."""
    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_FROM_NUMBER):
        return False, 'sms_not_configured'
    try:
        import base64
        url = f'https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json'
        body = urllib.parse.urlencode({
            'To':   mobile if mobile.startswith('+') else f'+91{mobile}',
            'From': TWILIO_FROM_NUMBER,
            'Body': f'Your MRABILITY Finance password reset OTP is: {otp}. Valid for 10 minutes. Do not share with anyone.'
        }).encode()
        creds = base64.b64encode(f'{TWILIO_ACCOUNT_SID}:{TWILIO_AUTH_TOKEN}'.encode()).decode()
        req = urllib.request.Request(url, data=body, headers={
            'Authorization': f'Basic {creds}',
            'Content-Type': 'application/x-www-form-urlencoded'
        })
        urllib.request.urlopen(req)
        return True, 'sms_sent'
    except Exception as e:
        print(f'[OTP] SMS error: {e}')
        return False, str(e)

def _send_email_otp(email, otp, name='User'):
    """Send OTP via SMTP email. Returns (success, message)."""
    if not (SMTP_USER and SMTP_PASSWORD):
        return False, 'email_not_configured'
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'MRABILITY Finance — Your Password Reset OTP'
        msg['From']    = SMTP_FROM or SMTP_USER
        msg['To']      = email
        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;padding:24px;border:1px solid #e5e7eb;border-radius:12px">
          <h2 style="color:#5c6bc0">MRABILITY Finance Password Reset</h2>
          <p>Hi {name},</p>
          <p>Your One-Time Password (OTP) to reset your MRABILITY Finance password is:</p>
          <div style="font-size:36px;font-weight:bold;letter-spacing:8px;text-align:center;
                      padding:20px;background:#f3f4f6;border-radius:8px;color:#1a1a2e;margin:20px 0">
            {otp}
          </div>
          <p style="color:#666">This OTP is valid for <strong>10 minutes</strong>. Do not share it with anyone.</p>
          <hr style="border:none;border-top:1px solid #e5e7eb">
          <p style="color:#999;font-size:12px">If you did not request a password reset, please ignore this email.</p>
        </div>"""
        msg.attach(MIMEText(html, 'html'))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM or SMTP_USER, email, msg.as_string())
        return True, 'email_sent'
    except Exception as e:
        print(f'[OTP] Email error: {e}')
        return False, str(e)

def _store_otp(db, identifier, otp):
    """Store OTP in DB, invalidating any previous unused OTPs for same identifier."""
    db.execute("UPDATE otp_requests SET used=1 WHERE identifier=? AND used=0", (identifier,))
    expires = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    db.execute(
        "INSERT INTO otp_requests (identifier, otp, expires_at) VALUES (?,?,?)",
        (identifier, otp, expires)
    )
    db.commit()

def _verify_otp(db, identifier, otp):
    """Verify OTP. Returns (valid, reason)."""
    row = db.execute(
        """SELECT * FROM otp_requests
           WHERE identifier=? AND used=0
           ORDER BY created_at DESC LIMIT 1""",
        (identifier,)
    ).fetchone()
    if not row:
        return False, 'OTP not found or already used'
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    exp = datetime.fromisoformat(row['expires_at'].replace('Z','').split('+')[0])
    if now > exp:
        return False, 'OTP has expired. Please request a new one.'
    if row['otp'] != otp.strip():
        return False, 'Incorrect OTP. Please try again.'
    db.execute("UPDATE otp_requests SET used=1 WHERE id=?", (row['id'],))
    db.commit()
    return True, 'ok'

# ── Auth Routes ─────────────────────────────────────────
@app.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password():
    """Step 1: Send OTP to mobile or email."""
    data = request.get_json() or {}
    identifier = (data.get('identifier') or '').strip()
    if not identifier:
        return jsonify({'error': 'Mobile number or email is required'}), 400

    db = get_db()
    # Find user by mobile or email
    user = db.execute(
        "SELECT * FROM users WHERE mobile=? OR email=?",
        (identifier, identifier.lower())
    ).fetchone()
    if not user:
        # Don't reveal if user exists — generic message
        return jsonify({'success': True, 'message': 'If that account exists, an OTP has been sent.', 'demo': True}), 200

    otp = str(secrets.randbelow(900000) + 100000)  # 6-digit OTP
    _store_otp(db, identifier, otp)

    sent_via = []
    # Try SMS first (if mobile provided or user has mobile)
    mobile = user['mobile']
    if mobile:
        sms_ok, _ = _send_sms_otp(mobile, otp)
        if sms_ok:
            sent_via.append('SMS')

    # Try email
    email = user['email']
    if email:
        email_ok, _ = _send_email_otp(email, otp, user['name'])
        if email_ok:
            sent_via.append('email')

    # If neither is configured, show OTP in console (dev/testing mode)
    if not sent_via:
        print(f"\n{'='*50}")
        print(f"[DEV MODE] OTP for {identifier}: {otp}")
        print(f"{'='*50}\n")
        return jsonify({
            'success': True,
            'dev_mode': True,
            'message': 'OTP delivery not configured. Check server console for the OTP.',
            'masked_to': f"***{identifier[-3:]}" if len(identifier) > 3 else '***'
        }), 200

    masked = []
    if 'SMS' in sent_via:
        m = user['mobile']
        masked.append(f"SMS to +91-XXXXXX{m[-4:]}")
    if 'email' in sent_via:
        e = user['email']
        parts = e.split('@')
        masked.append(f"email to {parts[0][:2]}***@{parts[1]}")

    return jsonify({
        'success': True,
        'message': f"OTP sent via {' & '.join(sent_via)}",
        'sent_to': ' and '.join(masked)
    }), 200


@app.route('/api/auth/verify-otp', methods=['POST'])
def verify_otp():
    """Step 2: Verify OTP."""
    data = request.get_json() or {}
    identifier = (data.get('identifier') or '').strip()
    otp        = (data.get('otp') or '').strip()
    if not identifier or not otp:
        return jsonify({'error': 'Identifier and OTP are required'}), 400

    db = get_db()
    valid, reason = _verify_otp(db, identifier, otp)
    if not valid:
        return jsonify({'error': reason}), 400

    # Issue a short-lived reset token (valid 15 min)
    reset_token = secrets.token_urlsafe(32)
    expires = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
    _store_otp(db, f'reset:{identifier}', reset_token)  # reuse table for reset token
    db.execute(
        "INSERT INTO otp_requests (identifier, otp, purpose, expires_at) VALUES (?,?,?,?)",
        (f'reset:{identifier}', reset_token, 'reset_token', expires)
    )
    db.commit()
    return jsonify({'success': True, 'reset_token': reset_token}), 200


@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    """Step 3: Set new password using reset token."""
    data        = request.get_json() or {}
    identifier  = (data.get('identifier') or '').strip()
    reset_token = (data.get('reset_token') or '').strip()
    new_password = (data.get('password') or '').strip()

    if not all([identifier, reset_token, new_password]):
        return jsonify({'error': 'All fields are required'}), 400
    if len(new_password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400

    db = get_db()
    # Verify reset token
    row = db.execute(
        """SELECT * FROM otp_requests
           WHERE identifier=? AND otp=? AND purpose='reset_token' AND used=0
           ORDER BY created_at DESC LIMIT 1""",
        (f'reset:{identifier}', reset_token)
    ).fetchone()
    if not row:
        return jsonify({'error': 'Invalid or expired reset session. Please start over.'}), 400

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    exp = datetime.fromisoformat(row['expires_at'].replace('Z','').split('+')[0])
    if now > exp:
        return jsonify({'error': 'Reset session expired. Please request a new OTP.'}), 400

    # Update password
    hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    db.execute(
        "UPDATE users SET password=? WHERE mobile=? OR email=?",
        (hashed, identifier, identifier.lower())
    )
    db.execute("UPDATE otp_requests SET used=1 WHERE id=?", (row['id'],))
    db.commit()

    # Log it
    user = db.execute("SELECT id FROM users WHERE mobile=? OR email=?",
                      (identifier, identifier.lower())).fetchone()
    if user:
        log_action(db, user['id'], 'password_reset', f'Password reset for {identifier}')
        db.commit()

    return jsonify({'success': True, 'message': 'Password reset successfully! You can now log in.'}), 200


@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    name   = (data.get('name') or '').strip()
    mobile = (data.get('mobile') or '').strip()
    email  = (data.get('email') or '').strip().lower()
    pw     = (data.get('password') or '')

    if not all([name, mobile, email, pw]):
        return jsonify({'error': 'All fields are required'}), 400
    if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
        return jsonify({'error': 'Invalid email address'}), 400
    if len(pw) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400

    hashed = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO users (name, mobile, email, password) VALUES (?,?,?,?)",
            (name, mobile, email, hashed)
        )
        db.commit()
        user_id = cur.lastrowid
        log_action(db, user_id, 'REGISTER', f'New user: {email}')
        db.commit()
        token = create_token(user_id, 'user', name)
        return jsonify({'token': token, 'name': name, 'role': 'user', 'id': user_id}), 201
    except (sqlite3.IntegrityError, Exception) as e:
        db.rollback()
        err_msg = str(e).lower()
        if 'unique' in err_msg or 'duplicate' in err_msg or 'already exists' in err_msg:
            return jsonify({'error': 'Email already registered'}), 409
        return jsonify({'error': 'Registration failed'}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    data  = request.get_json() or {}
    ident = (data.get('identifier') or '').strip().lower()
    pw    = (data.get('password') or '')

    if not ident or not pw:
        return jsonify({'error': 'Mobile/email and password are required'}), 400

    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE email=? OR mobile=?", (ident, ident)
    ).fetchone()

    if not user or not bcrypt.checkpw(pw.encode(), user['password'].encode()):
        return jsonify({'error': 'Invalid credentials'}), 401

    db.execute("UPDATE users SET last_login=? WHERE id=?",
               (datetime.now(timezone.utc).isoformat(), user['id']))
    log_action(db, user['id'], 'LOGIN', f'{ident}')
    db.commit()

    token = create_token(user['id'], user['role'], user['name'])
    return jsonify({'token': token, 'name': user['name'], 'role': user['role'], 'id': user['id']})

@app.route('/api/auth/me', methods=['GET'])
@require_auth
def me():
    db   = get_db()
    user = db.execute("SELECT id, name, mobile, email, role, created_at, last_login FROM users WHERE id=?",
                      (request.user['sub'],)).fetchone()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(dict(user))

# ── Applications Routes ──────────────────────────────────
@app.route('/api/applications', methods=['POST'])
def submit_application():
    data = request.get_json() or {}
    loan_type = data.get('loan_type', 'unknown')
    ref_id    = gen_ref_id(loan_type)

    # Extract user_id from token if present
    user_id = None
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        try:
            payload = decode_token(auth.split(' ', 1)[1])
            user_id = payload.get('sub')
        except Exception:
            pass

    db = get_db()
    db.execute("""
        INSERT INTO applications
          (ref_id, user_id, loan_type, full_name, mobile, email, employment,
           monthly_income, loan_amount, property_type, property_value,
           car_budget, business_name, annual_turnover, dob, pincode, extra_data)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        ref_id,
        user_id,
        loan_type,
        data.get('full_name') or data.get('loanName') or data.get('name', ''),
        data.get('mobile') or data.get('loanMobile', ''),
        data.get('email') or data.get('loanEmail', ''),
        data.get('employment', ''),
        data.get('monthly_income', ''),
        data.get('loan_amount', ''),
        data.get('property_type', ''),
        data.get('property_value', ''),
        data.get('car_budget', ''),
        data.get('business_name', ''),
        data.get('annual_turnover', ''),
        data.get('dob', ''),
        data.get('pincode', ''),
        json.dumps({k: v for k, v in data.items() if k not in [
            'full_name','name','mobile','email','employment','monthly_income',
            'loan_amount','property_type','property_value','car_budget',
            'business_name','annual_turnover','loan_type','dob','pincode'
        ]})
    ))
    if user_id:
        log_action(db, user_id, 'APPLICATION', f'{loan_type} | {ref_id}')
    db.commit()
    return jsonify({'ref_id': ref_id, 'status': 'Submitted', 'message': 'Application received successfully'}), 201

@app.route('/api/applications/my', methods=['GET'])
@require_auth
def my_applications():
    db      = get_db()
    user_id = request.user['sub']
    # Also look up user's email so we can match apps submitted before login
    user_row = db.execute("SELECT email FROM users WHERE id=?", (user_id,)).fetchone()
    user_email = user_row['email'] if user_row else None

    apps = db.execute(
        """SELECT ref_id, loan_type, status, created_at, loan_amount FROM applications
           WHERE user_id=? OR (user_id IS NULL AND email=?)
           ORDER BY created_at DESC""",
        (user_id, user_email)
    ).fetchall()

    # Back-fill user_id for applications matched by email
    if user_email:
        db.execute(
            "UPDATE applications SET user_id=? WHERE user_id IS NULL AND email=?",
            (user_id, user_email)
        )
        db.commit()

    return jsonify([dict(a) for a in apps])

# ── Credit Score Route ───────────────────────────────────
@app.route('/api/credit-score', methods=['POST'])
def save_credit_score():
    data  = request.get_json() or {}
    score = data.get('score')
    tier  = data.get('tier', '')
    pan   = data.get('pan', '')
    name  = data.get('name', '')
    mobile = data.get('mobile', '')

    user_id = None
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        try:
            payload = decode_token(auth.split(' ', 1)[1])
            user_id = payload.get('sub')
        except Exception:
            pass

    db = get_db()
    db.execute(
        "INSERT INTO credit_scores (user_id, name, pan, mobile, score, tier) VALUES (?,?,?,?,?,?)",
        (user_id, name, pan, mobile, score, tier)
    )
    db.commit()
    return jsonify({'message': 'Credit score saved'}), 201

# ── Admin Routes ─────────────────────────────────────────
@app.route('/api/admin/stats', methods=['GET'])
@require_admin
def admin_stats():
    db = get_db()
    total_users = db.execute("SELECT COUNT(*) AS c FROM users WHERE role='user'").fetchone()['c']
    total_apps  = db.execute("SELECT COUNT(*) AS c FROM applications").fetchone()['c']
    total_scores = db.execute("SELECT COUNT(*) AS c FROM credit_scores").fetchone()['c']
    pending_apps = db.execute("SELECT COUNT(*) AS c FROM applications WHERE status='Submitted'").fetchone()['c']
    approved     = db.execute("SELECT COUNT(*) AS c FROM applications WHERE status='Approved'").fetchone()['c']
    rejected     = db.execute("SELECT COUNT(*) AS c FROM applications WHERE status='Rejected'").fetchone()['c']

    by_type = db.execute("""
        SELECT loan_type, COUNT(*) AS count FROM applications GROUP BY loan_type ORDER BY count DESC
    """).fetchall()

    recent_apps = db.execute("""
        SELECT a.id, a.ref_id, a.loan_type, a.full_name, a.mobile, a.loan_amount,
               a.status, a.created_at, a.email,
               u.name AS user_name, u.email AS user_email
        FROM applications a
        LEFT JOIN users u ON a.user_id = u.id
        ORDER BY a.created_at DESC LIMIT 20
    """).fetchall()

    return jsonify({
        'total_users': total_users,
        'total_apps': total_apps,
        'total_scores': total_scores,
        'pending_apps': pending_apps,
        'approved': approved,
        'rejected': rejected,
        'by_loan_type': [dict(r) for r in by_type],
        'recent_apps': [dict(r) for r in recent_apps],
    })

@app.route('/api/admin/users', methods=['GET'])
@require_admin
def admin_users():
    db = get_db()
    search = request.args.get('search', '').strip()
    role   = request.args.get('role', '').strip()
    page   = max(1, int(request.args.get('page', 1)))
    limit  = int(request.args.get('limit', 20))
    offset = (page - 1) * limit

    where_parts, params = [], []
    if search:
        where_parts.append("(name LIKE ? OR mobile LIKE ? OR email LIKE ?)")
        params.extend([f'%{search}%', f'%{search}%', f'%{search}%'])
    if role:
        where_parts.append("role=?")
        params.append(role)

    where = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""
    users = db.execute(f"""
        SELECT id, name, mobile, email, role, created_at, last_login
        FROM users {where}
        ORDER BY created_at DESC LIMIT ? OFFSET ?
    """, params + [limit, offset]).fetchall()
    total = db.execute(f"SELECT COUNT(*) AS c FROM users {where}", params).fetchone()['c']

    return jsonify({'users': [dict(u) for u in users], 'total': total, 'page': page, 'limit': limit})

@app.route('/api/admin/applications', methods=['GET'])
@require_admin
def admin_applications():
    db     = get_db()
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '')
    loan_type = request.args.get('loan_type', '')
    page   = max(1, int(request.args.get('page', 1)))
    limit  = int(request.args.get('limit', 20))
    offset = (page - 1) * limit

    conditions, params = [], []
    if search:
        conditions.append("(a.full_name LIKE ? OR a.mobile LIKE ? OR a.email LIKE ? OR a.ref_id LIKE ?)")
        params.extend([f'%{search}%'] * 4)
    if status:
        conditions.append("a.status = ?"); params.append(status)
    if loan_type:
        conditions.append("a.loan_type = ?"); params.append(loan_type)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    apps = db.execute(f"""
        SELECT a.id, a.ref_id, a.loan_type, a.full_name, a.mobile, a.email,
               a.employment, a.monthly_income, a.loan_amount,
               a.property_type, a.property_value, a.car_budget,
               a.business_name, a.annual_turnover,
               a.status, a.notes, a.created_at, a.updated_at,
               u.name AS user_name, u.email AS user_email
        FROM applications a
        LEFT JOIN users u ON a.user_id = u.id
        {where}
        ORDER BY a.created_at DESC LIMIT ? OFFSET ?
    """, params + [limit, offset]).fetchall()

    total = db.execute(f"SELECT COUNT(*) AS c FROM applications a {where}", params).fetchone()['c']
    return jsonify({'applications': [dict(a) for a in apps], 'total': total, 'page': page, 'limit': limit})

@app.route('/api/admin/applications/<int:app_id>', methods=['GET'])
@require_admin
def get_application(app_id):
    db  = get_db()
    row = db.execute("""
        SELECT a.*, u.email AS user_email, u.name AS user_name
        FROM applications a LEFT JOIN users u ON u.id = a.user_id
        WHERE a.id = ?
    """, (app_id,)).fetchone()
    if not row:
        return jsonify({'error': 'Application not found'}), 404
    return jsonify(dict(row))


@app.route('/api/admin/applications/<int:app_id>', methods=['PATCH'])
@require_admin
def update_application(app_id):
    data   = request.get_json() or {}
    status = data.get('status')
    notes  = data.get('notes')
    db     = get_db()

    updates, params = [], []
    if status:
        updates.append("status=?"); params.append(status)
    if notes is not None:
        updates.append("notes=?"); params.append(notes)
    if not updates:
        return jsonify({'error': 'Nothing to update'}), 400

    updates.append("updated_at=?"); params.append(datetime.now(timezone.utc).isoformat())
    params.append(app_id)
    db.execute(f"UPDATE applications SET {', '.join(updates)} WHERE id=?", params)
    log_action(db, request.user['sub'], 'UPDATE_APP', f'App {app_id} → {status}')
    db.commit()
    return jsonify({'message': 'Updated'})

@app.route('/api/admin/credit-scores', methods=['GET'])
@require_admin
def admin_credit_scores():
    db    = get_db()
    page  = max(1, int(request.args.get('page', 1)))
    limit = int(request.args.get('limit', 20))
    search = request.args.get('search', '').strip()

    if search:
        rows = db.execute("""
            SELECT cs.id, cs.name, cs.pan, cs.mobile, cs.score, cs.tier, cs.checked_at,
                   u.email AS user_email
            FROM credit_scores cs
            LEFT JOIN users u ON cs.user_id = u.id
            WHERE cs.name LIKE ? OR cs.pan LIKE ? OR cs.mobile LIKE ? OR u.email LIKE ?
            ORDER BY cs.checked_at DESC LIMIT ? OFFSET ?
        """, (f'%{search}%', f'%{search}%', f'%{search}%', f'%{search}%', limit, (page-1)*limit)).fetchall()
        total = db.execute("""
            SELECT COUNT(*) AS c FROM credit_scores cs
            LEFT JOIN users u ON cs.user_id = u.id
            WHERE cs.name LIKE ? OR cs.pan LIKE ? OR cs.mobile LIKE ? OR u.email LIKE ?
        """, (f'%{search}%', f'%{search}%', f'%{search}%', f'%{search}%')).fetchone()['c']
    else:
        rows  = db.execute("""
            SELECT cs.id, cs.name, cs.pan, cs.mobile, cs.score, cs.tier, cs.checked_at,
                   u.email AS user_email
            FROM credit_scores cs
            LEFT JOIN users u ON cs.user_id = u.id
            ORDER BY cs.checked_at DESC LIMIT ? OFFSET ?
        """, (limit, (page-1)*limit)).fetchall()
        total = db.execute("SELECT COUNT(*) AS c FROM credit_scores").fetchone()['c']

    return jsonify({'scores': [dict(r) for r in rows], 'total': total})

@app.route('/api/admin/activity', methods=['GET'])
@require_admin
def admin_activity():
    db   = get_db()
    rows = db.execute("""
        SELECT al.id, al.action, al.details, al.ip, al.created_at,
               u.name AS user_name, u.email AS user_email
        FROM activity_log al
        LEFT JOIN users u ON al.user_id = u.id
        ORDER BY al.created_at DESC LIMIT 100
    """).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/admin/users/<int:user_id>/role', methods=['PATCH'])
@require_admin
def change_user_role(user_id):
    data = request.get_json() or {}
    role = data.get('role')
    if role not in ('user', 'admin'):
        return jsonify({'error': 'Invalid role'}), 400
    db = get_db()
    db.execute("UPDATE users SET role=? WHERE id=?", (role, user_id))
    log_action(db, request.user['sub'], 'ROLE_CHANGE', f'User {user_id} → {role}')
    db.commit()
    return jsonify({'message': f'Role updated to {role}'})

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@require_admin
def admin_delete_user(user_id):
    db = get_db()
    u = db.execute("SELECT name, email FROM users WHERE id=?", (user_id,)).fetchone()
    if not u:
        return jsonify({'error': 'User not found'}), 404
    db.execute("DELETE FROM applications WHERE user_id=?", (user_id,))
    db.execute("DELETE FROM credit_scores WHERE user_id=?", (user_id,))
    db.execute("DELETE FROM activity_log WHERE user_id=?", (user_id,))
    db.execute("DELETE FROM users WHERE id=?", (user_id,))
    log_action(db, request.user['sub'], 'DELETE_USER', f'{u["name"]} ({u["email"]})')
    db.commit()
    return jsonify({'success': True})

@app.route('/api/admin/users', methods=['POST'])
@require_admin
def admin_add_user():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    mobile = data.get('mobile', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    role = data.get('role', 'user')
    if not name or not email:
        return jsonify({'error': 'Name and email are required'}), 400
    if not password:
        password = 'Welcome@123'
    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    if existing:
        return jsonify({'error': 'Email already registered'}), 409
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        "INSERT INTO users (name, mobile, email, password, role, created_at) VALUES (?,?,?,?,?,?)",
        (name, mobile, email, pw_hash, role, now)
    )
    log_action(db, request.user['sub'], 'ADD_USER', f'{name} ({email})')
    db.commit()
    return jsonify({'success': True, 'message': f'User {name} created'}), 201

@app.route('/api/admin/applications/<int:app_id>', methods=['DELETE'])
@require_admin
def admin_delete_application(app_id):
    db = get_db()
    row = db.execute("SELECT ref_id FROM applications WHERE id=?", (app_id,)).fetchone()
    if not row:
        return jsonify({'error': 'Application not found'}), 404
    db.execute("DELETE FROM applications WHERE id=?", (app_id,))
    log_action(db, request.user['sub'], 'DELETE_APP', f'Application {row["ref_id"]} deleted')
    db.commit()
    return jsonify({'success': True})

@app.route('/api/admin/applications', methods=['POST'])
@require_admin
def admin_add_application():
    data = request.get_json() or {}
    loan_type = data.get('loan_type', 'personal_loan')
    full_name = data.get('full_name', '').strip()
    mobile = data.get('mobile', '').strip()
    email = data.get('email', '').strip()
    dob = data.get('dob', '').strip()
    pincode = data.get('pincode', '').strip()
    loan_amount = data.get('loan_amount', '')
    status = data.get('status', 'Submitted')
    if not full_name or not mobile:
        return jsonify({'error': 'Name and mobile are required'}), 400
    ref_id = gen_ref_id(loan_type)
    db = get_db()
    db.execute("""
        INSERT INTO applications (ref_id, loan_type, full_name, mobile, email, dob, pincode, loan_amount, status, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (ref_id, loan_type, full_name, mobile, email, dob, pincode, loan_amount, status, datetime.now(timezone.utc).isoformat()))
    log_action(db, request.user['sub'], 'ADD_APP', f'{loan_type} | {ref_id}')
    db.commit()
    return jsonify({'success': True, 'ref_id': ref_id}), 201

# ── Google OAuth ─────────────────────────────────────
@app.route('/api/auth/google')
def google_oauth_start():
    """Redirect user to Google's OAuth consent page."""
    if not GOOGLE_CLIENT_ID:
        # No credentials configured — return helpful error as JSON for the frontend
        return jsonify({'error': 'Google OAuth not configured. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to server environment.', 'setup_required': True}), 501

    state = secrets.token_urlsafe(16)
    params = urllib.parse.urlencode({
        'client_id':     GOOGLE_CLIENT_ID,
        'redirect_uri':  GOOGLE_REDIRECT_URI,
        'response_type': 'code',
        'scope':         'openid email profile',
        'state':         state,
        'access_type':   'online',
    })
    return redirect(f'https://accounts.google.com/o/oauth2/v2/auth?{params}')

@app.route('/api/auth/google/callback')
def google_oauth_callback():
    """Exchange Google code for user info, upsert user, return JWT."""
    code  = request.args.get('code')
    error = request.args.get('error')
    if error or not code:
        return redirect(f"/?oauth_error={error or 'cancelled'}#login")

    # Exchange code for tokens
    try:
        token_data = urllib.parse.urlencode({
            'code':          code,
            'client_id':     GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'redirect_uri':  GOOGLE_REDIRECT_URI,
            'grant_type':    'authorization_code',
        }).encode()
        req = urllib.request.Request('https://oauth2.googleapis.com/token', data=token_data,
                                     headers={'Content-Type': 'application/x-www-form-urlencoded'})
        resp     = urllib.request.urlopen(req)
        tokens   = json.loads(resp.read().decode())
        id_token = tokens.get('id_token', '')

        # Decode id_token without verification (for simplicity) — or use userinfo endpoint
        import base64
        payload_b64 = id_token.split('.')[1] + '=='
        user_info   = json.loads(base64.urlsafe_b64decode(payload_b64))
    except Exception as e:
        return redirect(f'/?oauth_error=token_exchange#login')

    email = user_info.get('email', '')
    name  = user_info.get('name', email.split('@')[0])

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if not user:
        # Auto-register via Google
        placeholder_pw = bcrypt.hashpw(secrets.token_bytes(32), bcrypt.gensalt()).decode()
        cur = db.execute(
            "INSERT INTO users (name, mobile, email, password, role) VALUES (?,?,?,?,?)",
            (name, '', email, placeholder_pw, 'user')
        )
        db.commit()
        user_id   = cur.lastrowid
        user_role = 'user'
        log_action(db, user_id, 'GOOGLE_REGISTER', email)
    else:
        user_id   = user['id']
        user_role = user['role']
        name      = user['name']
        log_action(db, user_id, 'GOOGLE_LOGIN', email)

    db.execute("UPDATE users SET last_login=? WHERE id=?",
               (datetime.now(timezone.utc).isoformat(), user_id))
    db.commit()

    fin_token = create_token(user_id, user_role, name)
    # Redirect back to frontend with token in hash so JS can pick it up
    return redirect(f'/?oauth_token={urllib.parse.quote(fin_token)}&oauth_name={urllib.parse.quote(name)}&oauth_role={user_role}#oauth_done')

@app.route('/api/auth/google/check')
def google_oauth_check():
    """Returns whether Google OAuth is configured."""
    return jsonify({'configured': bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET),
                    'client_id': GOOGLE_CLIENT_ID or ''})

@app.route('/api/auth/google/token', methods=['POST'])
def google_token_signin():
    """
    Verify a Google ID token (from Google Identity Services JS SDK popup flow).
    The frontend sends the credential (id_token) directly here.
    We verify it with Google's tokeninfo endpoint, upsert the user, return our JWT.
    """
    data       = request.get_json() or {}
    credential = data.get('credential', '')
    if not credential:
        return jsonify({'error': 'Missing credential'}), 400

    # Verify token with Google's public endpoint (no secret needed for tokeninfo)
    try:
        verify_url = f'https://oauth2.googleapis.com/tokeninfo?id_token={credential}'
        req        = urllib.request.Request(verify_url)
        resp       = urllib.request.urlopen(req, timeout=8)
        info       = json.loads(resp.read().decode())
    except Exception as e:
        return jsonify({'error': 'Google token verification failed', 'detail': str(e)}), 401

    # Validate audience if client_id is configured
    if GOOGLE_CLIENT_ID and info.get('aud') != GOOGLE_CLIENT_ID:
        return jsonify({'error': 'Token audience mismatch'}), 401

    email   = info.get('email', '')
    name    = info.get('name', '') or email.split('@')[0]
    picture = info.get('picture', '')

    if not email:
        return jsonify({'error': 'Could not get email from Google'}), 400

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if not user:
        placeholder_pw = bcrypt.hashpw(secrets.token_bytes(32), bcrypt.gensalt()).decode()
        cur = db.execute(
            "INSERT INTO users (name, mobile, email, password, role) VALUES (?,?,?,?,?)",
            (name, '', email, placeholder_pw, 'user')
        )
        db.commit()
        user_id   = cur.lastrowid
        user_role = 'user'
        log_action(db, user_id, 'GOOGLE_REGISTER', email)
    else:
        user_id   = user['id']
        user_role = user['role']
        name      = user['name']
        log_action(db, user_id, 'GOOGLE_LOGIN', email)

    db.execute("UPDATE users SET last_login=? WHERE id=?",
               (datetime.now(timezone.utc).isoformat(), user_id))
    db.commit()

    fin_token = create_token(user_id, user_role, name)
    return jsonify({'token': fin_token, 'name': name, 'role': user_role, 'id': user_id,
                    'email': email, 'picture': picture}), 200

@app.route('/api/auth/facebook/check')
def facebook_oauth_check():
    """Returns whether Facebook OAuth is configured."""
    return jsonify({'configured': bool(FACEBOOK_APP_ID and FACEBOOK_APP_SECRET)})

# ── Facebook OAuth ────────────────────────────────────
FACEBOOK_REDIRECT_URI = os.environ.get('FACEBOOK_REDIRECT_URI', 'http://localhost:8080/api/auth/facebook/callback')

@app.route('/api/auth/facebook')
def facebook_oauth_start():
    if not FACEBOOK_APP_ID:
        return jsonify({'error': 'Facebook OAuth not configured. Add FACEBOOK_APP_ID and FACEBOOK_APP_SECRET.', 'setup_required': True}), 501
    params = urllib.parse.urlencode({
        'client_id':     FACEBOOK_APP_ID,
        'redirect_uri':  FACEBOOK_REDIRECT_URI,
        'response_type': 'code',
        'scope':         'email,public_profile',
    })
    return redirect(f'https://www.facebook.com/v19.0/dialog/oauth?{params}')

@app.route('/api/auth/facebook/callback')
def facebook_oauth_callback():
    code  = request.args.get('code')
    error = request.args.get('error')
    if error or not code:
        return redirect('/?oauth_error=cancelled#login')
    try:
        token_url = (f'https://graph.facebook.com/v19.0/oauth/access_token'
                     f'?client_id={FACEBOOK_APP_ID}&redirect_uri={urllib.parse.quote(FACEBOOK_REDIRECT_URI, safe="")}'
                     f'&client_secret={FACEBOOK_APP_SECRET}&code={code}')
        token_resp = json.loads(urllib.request.urlopen(token_url).read().decode())
        access_token = token_resp.get('access_token', '')
        me_resp = json.loads(urllib.request.urlopen(
            f'https://graph.facebook.com/me?fields=id,name,email&access_token={access_token}'
        ).read().decode())
    except Exception:
        return redirect('/?oauth_error=token_exchange#login')

    email = me_resp.get('email', f"{me_resp.get('id','fb')}@facebook.com")
    name  = me_resp.get('name', 'Facebook User')
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if not user:
        placeholder_pw = bcrypt.hashpw(secrets.token_bytes(32), bcrypt.gensalt()).decode()
        cur = db.execute("INSERT INTO users (name, mobile, email, password, role) VALUES (?,?,?,?,?)",
                         (name, '', email, placeholder_pw, 'user'))
        db.commit()
        user_id = cur.lastrowid; user_role = 'user'
        log_action(db, user_id, 'FACEBOOK_REGISTER', email)
    else:
        user_id = user['id']; user_role = user['role']; name = user['name']
        log_action(db, user_id, 'FACEBOOK_LOGIN', email)
    db.execute("UPDATE users SET last_login=? WHERE id=?", (datetime.now(timezone.utc).isoformat(), user_id))
    db.commit()
    fin_token = create_token(user_id, user_role, name)
    return redirect(f'/?oauth_token={urllib.parse.quote(fin_token)}&oauth_name={urllib.parse.quote(name)}&oauth_role={user_role}#oauth_done')

# ── Interest Rates — Public (read-only) ─────────────────────
@app.route('/api/rates', methods=['GET'])
def get_rates_public():
    """Returns all rates grouped by loan_type. Public — no auth needed."""
    from collections import defaultdict
    loan_type = request.args.get('loan_type', '')
    db  = get_db()
    sql = "SELECT * FROM interest_rates"
    params = []
    if loan_type:
        sql += " WHERE loan_type=?"
        params.append(loan_type)
    sql += " ORDER BY loan_type, display_order"
    rows = db.execute(sql, params).fetchall()
    grouped = defaultdict(list)
    for r in rows:
        grouped[r['loan_type']].append(dict(r))
    return jsonify({'rates': dict(grouped), 'flat': [dict(r) for r in rows]})


@app.route('/api/rates/calculators', methods=['GET'])
def get_calc_defaults():
    """Returns calculator default rates. Public — no auth needed."""
    db   = get_db()
    rows = db.execute("SELECT * FROM calculator_defaults ORDER BY key").fetchall()
    return jsonify({r['key']: {'value': r['value'], 'label': r['label']} for r in rows})


# ── Interest Rates — Admin CRUD ──────────────────────────────
@app.route('/api/admin/rates', methods=['GET'])
@require_admin
def admin_get_rates():
    db    = get_db()
    rows  = db.execute("SELECT * FROM interest_rates ORDER BY loan_type, display_order").fetchall()
    calcs = db.execute("SELECT * FROM calculator_defaults ORDER BY key").fetchall()
    return jsonify({
        'rates': [dict(r) for r in rows],
        'calculator_defaults': [dict(r) for r in calcs]
    })


@app.route('/api/admin/rates/<int:rate_id>', methods=['PATCH'])
@require_admin
def admin_update_rate(rate_id):
    data    = request.get_json() or {}
    allowed = ['bank_name','rate_min','rate_max','processing_fee',
               'max_amount','tenure_max','is_featured','display_order']
    updates, params = [], []
    for field in allowed:
        if field in data:
            updates.append(f"{field}=?")
            params.append(data[field])
    if not updates:
        return jsonify({'error': 'Nothing to update'}), 400
    updates.append("updated_at=?")
    params.append(datetime.now(timezone.utc).isoformat())
    params.append(rate_id)
    db = get_db()
    db.execute(f"UPDATE interest_rates SET {','.join(updates)} WHERE id=?", params)
    db.commit()
    log_action(db, request.user['sub'], 'UPDATE_RATE', f'Rate ID {rate_id} updated')
    db.commit()
    return jsonify({'success': True})


@app.route('/api/admin/rates', methods=['POST'])
@require_admin
def admin_add_rate():
    data = request.get_json() or {}
    for f in ['loan_type','bank_name','rate_min','rate_max']:
        if not data.get(f):
            return jsonify({'error': f'{f} is required'}), 400
    db  = get_db()
    cur = db.execute("""
        INSERT INTO interest_rates
          (loan_type,bank_name,rate_min,rate_max,processing_fee,max_amount,tenure_max,is_featured,display_order)
        VALUES (?,?,?,?,?,?,?,?,?)""", (
        data['loan_type'], data['bank_name'],
        float(data['rate_min']), float(data['rate_max']),
        data.get('processing_fee','—'), data.get('max_amount','—'),
        int(data.get('tenure_max', 5)),
        int(data.get('is_featured', 0)),
        int(data.get('display_order', 99))
    ))
    db.commit()
    log_action(db, request.user['sub'], 'ADD_RATE', f"{data['bank_name']} — {data['loan_type']}")
    db.commit()
    return jsonify({'success': True, 'id': cur.lastrowid}), 201


@app.route('/api/admin/rates/<int:rate_id>', methods=['DELETE'])
@require_admin
def admin_delete_rate(rate_id):
    db = get_db()
    db.execute("DELETE FROM interest_rates WHERE id=?", (rate_id,))
    db.commit()
    log_action(db, request.user['sub'], 'DELETE_RATE', f'Rate ID {rate_id} deleted')
    db.commit()
    return jsonify({'success': True})


@app.route('/api/admin/calculator-defaults/<key>', methods=['PATCH'])
@require_admin
def admin_update_calc_default(key):
    data  = request.get_json() or {}
    value = data.get('value')
    if value is None:
        return jsonify({'error': 'value is required'}), 400
    db = get_db()
    db.execute("UPDATE calculator_defaults SET value=?, updated_at=? WHERE key=?",
               (float(value), datetime.now(timezone.utc).isoformat(), key))
    db.commit()
    log_action(db, request.user['sub'], 'UPDATE_CALC_DEFAULT', f'{key} = {value}')
    db.commit()
    return jsonify({'success': True})


# ── Static File Serving ──────────────────────────────────
@app.after_request
def add_cache_headers(response):
    if response.content_type and 'text/html' in response.content_type:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    if os.path.exists(os.path.join(BASE_DIR, path)):
        return send_from_directory('.', path)
    return send_from_directory('.', 'index.html')

# ── Initialise DB on import (works with both gunicorn and direct run) ──
print("🚀 Initialising MRABILITY Finance database...")
init_db()

# ── Run ─────────────────────────────────────────────────
if __name__ == '__main__':
    print(f"🌐 Starting server at http://localhost:{PORT}")
    app.run(debug=True, port=PORT, host='0.0.0.0')
