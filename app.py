import os
import random
import secrets
import logging
import logging.config
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template_string, request, redirect, session, Response
from pymongo import MongoClient

app = Flask(__name__)

# --- LOGGING INITIALIZATION ---
LOG_CONFIG_FILE = "logging.conf"

if os.path.exists(LOG_CONFIG_FILE):
    logging.config.fileConfig(LOG_CONFIG_FILE, disable_existing_loggers=False)
    logger = logging.getLogger("appLogger")
    logger.info("Successfully loaded logging configuration from logging.conf")
else:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("appLogger")
    logger.warning("logging.conf not found. Falling back to basic standard logging.")


# --- ENVIRONMENT CONFIGURATION ---
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(32))
ADMIN_PW = os.getenv("ADMIN_PASSWORD", "admin123")
DEFAULT_GW_ADDRESS = os.getenv("DEFAULT_GW_ADDRESS", "192.168.0.46")

# Database URI
MONGO_URI = "mongodb+srv://swahilihit:swahilihit@cluster0.3nfk1.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"

# --- DATABASE SETUP ---
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client['swahilihit56']
    vouchers_col = db["vouchers"]
    sessions_col = db["sessions"]
    tokens_col = db["wifidog_tokens"]
    
    # Initialize indexes for performance and security
    vouchers_col.create_index("code", unique=True)
    tokens_col.create_index("created_at", expireAfterSeconds=600)
    sessions_col.create_index("expire_date")
    sessions_col.create_index("status")
    logger.info("Successfully connected to MongoDB and verified collection indexes.")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {str(e)}")


# --- HELPER FUNCTIONS ---
def get_param(key, default=""):
    """Extract parameter from POST form or GET query string."""
    return request.form.get(key) or request.args.get(key) or default

def get_client_mac():
    """Detect client MAC address across ReyeeOS parameter keys."""
    for key in ['mac', 'usermac', 'client_mac', 'client-mac']:
        val = get_param(key)
        if val:
            return val.strip().upper()
    return f"UNKNOWN:{secrets.token_hex(4).upper()}"

def get_gateway_address():
    """Extract Access Point LAN IP. Falls back strictly to DEFAULT_GW_ADDRESS for cloud hosts."""
    for key in ['gw_address', 'gw_ip', 'gwaddress', 'router_ip']:
        val = get_param(key)
        if val and val.replace('.', '').isdigit():
            return val.strip()
    return DEFAULT_GW_ADDRESS


# ==========================================
# 🎨 UI HTML TEMPLATES WITH SIDEBAR NAV
# ==========================================

NAV_SIDEBAR = """
<div class="sidebar">
    <div class="brand">
        <div class="brand-title">HANS NETWORK</div>
        <div class="brand-sub">KARIBU HANS INTERNET</div>
    </div>
    <ul class="nav-list">
        <li><a href="/admin" class="{{ 'active' if active_page == 'dashboard' else '' }}">📊 Dashboard</a></li>
        <li><a href="/admin/sessions" class="{{ 'active' if active_page == 'sessions' else '' }}">👥 Sessions</a></li>
        <li><a href="/admin" class="{{ 'active' if active_page == 'vouchers' else '' }}">🎟️ Vouchers</a></li>
        <li><a href="/admin/logout">🚪 Sign out</a></li>
    </ul>
</div>
"""

BASE_STYLE = """
<style>
    * { box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f4f6f8; margin: 0; padding: 0; color: #172b4d; display: flex; min-height: 100vh; }
    .sidebar { width: 240px; background: #1e3a5f; color: white; padding: 20px 0; flex-shrink: 0; }
    .brand { padding: 0 20px 20px 20px; border-bottom: 1px solid rgba(255,255,255,0.1); }
    .brand-title { font-weight: bold; font-size: 16px; letter-spacing: 0.5px; }
    .brand-sub { font-size: 11px; opacity: 0.7; margin-top: 4px; }
    .nav-list { list-style: none; padding: 15px 10px; margin: 0; }
    .nav-list li { margin-bottom: 4px; }
    .nav-list a { display: block; padding: 10px 15px; color: #c1c7d0; text-decoration: none; border-radius: 8px; font-size: 14px; font-weight: 500; }
    .nav-list a:hover, .nav-list a.active { background: #2c4d75; color: white; font-weight: bold; }
    .main-content { flex: 1; padding: 30px; overflow-y: auto; }
    .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; }
    .header h2 { margin: 0; color: #1e3a5f; font-size: 24px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-bottom: 25px; }
    .card { background: white; padding: 18px; border-radius: 10px; border: 1px solid #e1e4e8; }
    .card .lbl { font-size: 12px; color: #5e6c84; font-weight: bold; text-transform: uppercase; }
    .card .val { font-size: 22px; font-weight: bold; color: #0052cc; margin-top: 4px; }
    .box { background: white; padding: 20px; border-radius: 10px; border: 1px solid #e1e4e8; margin-bottom: 25px; }
    .box h3 { margin-top: 0; border-bottom: 1px solid #e1e4e8; padding-bottom: 10px; font-size: 16px; color: #1e3a5f; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 10px; }
    th, td { padding: 12px; text-align: left; border-bottom: 1px solid #e1e4e8; }
    th { background: #fafbfc; color: #5e6c84; }
    .badge { background: #ebecf0; padding: 3px 6px; border-radius: 4px; font-weight: bold; font-family: monospace; }
    .st-active { color: #006644; background: #e3fcef; padding: 3px 8px; border-radius: 10px; font-weight: bold; font-size: 11px; }
    .st-revoked { color: #bf2600; background: #ffebe6; padding: 3px 8px; border-radius: 10px; font-weight: bold; font-size: 11px; }
    .st-expired { color: #828282; background: #f4f5f7; padding: 3px 8px; border-radius: 10px; font-weight: bold; font-size: 11px; }
    .btn-action { text-decoration: none; font-weight: bold; padding: 5px 10px; border-radius: 4px; font-size: 12px; display: inline-block; }
    .btn-revoke { color: #de350b; background: #ffebe6; }
    .btn-reconnect { color: #006644; background: #e3fcef; }
    .btn-action:hover { opacity: 0.8; }
</style>
"""

PORTAL_TEMPLATE = """
<!DOCTYPE html>
<html lang="sw">
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HANS WIFI - Connect</title>
    <style>
        body { font-family: -apple-system, sans-serif; background-color: #f4f6f8; margin: 0; padding: 20px; display: flex; justify-content: center; align-items: center; min-height: 90vh; }
        .container { width: 100%; max-width: 350px; }
        .box { background: white; padding: 30px 22px; border-radius: 16px; border: 1px solid #e1e4e8; box-shadow: 0 4px 14px rgba(0,0,0,0.06); text-align: center; }
        h2 { margin: 0; color: #0052cc; font-size: 24px; }
        p { color: #5e6c84; font-size: 14px; margin-top: 6px; margin-bottom: 20px; }
        label { font-weight: bold; font-size: 13px; color: #172b4d; display: block; margin-bottom: 8px; text-align: left; }
        input[type="text"] { width: 100%; padding: 14px; font-size: 24px; border: 2px solid #dfe1e6; border-radius: 8px; margin-bottom: 18px; text-align: center; letter-spacing: 6px; font-weight: bold; color: #0052cc; }
        button { width: 100%; padding: 14px; background: #0052cc; color: white; border: none; border-radius: 8px; font-weight: bold; font-size: 16px; cursor: pointer; }
        .error { color: #de350b; background: #ffebe6; padding: 10px; border-radius: 6px; font-size: 13px; margin-bottom: 15px; }
        .mac-info { font-size: 11px; color: #888; margin-top: 15px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="box">
            <h2>HANS WIFI</h2>
            <p>Ingiza namba ya vocha kuunganisha intaneti</p>
            {% if error %}<div class="error">{{ error }}</div>{% endif %}
            <form action="/login" method="POST">
                <input type="hidden" name="mac" value="{{ mac }}">
                <input type="hidden" name="gw_address" value="{{ gw_address }}">
                <input type="hidden" name="gw_port" value="{{ gw_port }}">
                <input type="hidden" name="gw_id" value="{{ gw_id }}">
                <input type="hidden" name="userurl" value="{{ userurl }}">
                
                <label for="voucher">Namba ya Vocha (Digits 5):</label>
                <input type="text" id="voucher" name="voucher" maxlength="5" pattern="\\d{5}" placeholder="12345" inputmode="numeric" required autofocus>
                <button type="submit">CONNECT INTERNET</button>
            </form>
            <div class="mac-info">Device MAC: {{ mac }}</div>
        </div>
    </div>
</body>
</html>
"""

ADMIN_LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="sw">
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HANS WIFI - Admin Login</title>
    <style>
        body { font-family: sans-serif; background: #f4f6f8; display: flex; justify-content: center; align-items: center; height: 90vh; margin: 0; }
        .card { background: white; padding: 30px; border-radius: 12px; border: 1px solid #e1e4e8; width: 280px; text-align: center; }
        h3 { margin-top: 0; color: #0052cc; }
        input[type="password"] { width: 100%; padding: 12px; margin: 15px 0; border: 1px solid #ccc; border-radius: 6px; text-align: center; font-size: 16px; }
        button { width: 100%; padding: 12px; background: #0052cc; color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; }
        .error { color: red; font-size: 13px; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="card">
        <h3>HANS WIFI Admin</h3>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form action="/admin/login" method="POST">
            <input type="password" name="password" placeholder="Ingiza Nenosiri" required autofocus>
            <button type="submit">LOGIN</button>
        </form>
    </div>
</body>
</html>
"""

ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="sw">
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HANS WIFI - Dashboard</title>
    """ + BASE_STYLE + """
</head>
<body>
    """ + NAV_SIDEBAR + """
    <div class="main-content">
        <div class="header">
            <h2>Dashboard</h2>
        </div>
        <div class="grid">
            <div class="card"><div class="lbl">Total Revenue</div><div class="val">TZS {{ total_revenue }}</div></div>
            <div class="card"><div class="lbl">Online Devices</div><div class="val">{{ active_sessions_count }}</div></div>
            <div class="card"><div class="lbl">Active Vouchers</div><div class="val">{{ active_vouchers_count }}</div></div>
            <div class="card"><div class="lbl">Used Vouchers</div><div class="val">{{ used_vouchers_count }}</div></div>
        </div>
        <div class="box">
            <h3>🖨️ Generate 5-Digit Vouchers</h3>
            <form action="/admin/generate" method="POST">
                <div style="display:flex; gap:10px; flex-wrap:wrap;">
                    <input type="number" name="quantity" value="8" placeholder="Quantity" required style="padding:10px; border:1px solid #ccc; border-radius:6px;">
                    <input type="number" name="duration" value="360" placeholder="Duration (Mins)" required style="padding:10px; border:1px solid #ccc; border-radius:6px;">
                    <input type="number" name="price" value="500" placeholder="Price (TZS)" required style="padding:10px; border:1px solid #ccc; border-radius:6px;">
                </div>
                <button type="submit" style="background:#0052cc; color:white; padding:10px 20px; border:none; border-radius:6px; font-weight:bold; cursor:pointer; margin-top:10px;">Generate Printable Sheet</button>
            </form>
        </div>
        <div class="box">
            <h3>🎟️ Recent Vouchers</h3>
            <table>
                <tr><th>Code</th><th>Duration</th><th>Price</th><th>Status</th><th>Used By MAC</th></tr>
                {% for v in vouchers %}
                <tr>
                    <td><span class="badge">{{ v.code }}</span></td>
                    <td>{{ v.duration_minutes }} mins</td>
                    <td>TZS {{ v.price }}</td>
                    <td><span class="{{ 'st-active' if v.status == 'ACTIVE' else 'st-revoked' }}">{{ v.status }}</span></td>
                    <td>{{ v.used_by_mac or '-' }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </div>
</body>
</html>
"""

SESSIONS_TEMPLATE = """
<!DOCTYPE html>
<html lang="sw">
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HANS WIFI - Sessions Management</title>
    """ + BASE_STYLE + """
</head>
<body>
    """ + NAV_SIDEBAR + """
    <div class="main-content">
        <div class="header">
            <h2>Sessions Management</h2>
        </div>
        <div class="box">
            <h3>👥 All Device Sessions (Active, Disconnected & Expired)</h3>
            <table>
                <tr>
                    <th>MAC Address</th>
                    <th>Voucher Code</th>
                    <th>Expire Date</th>
                    <th>Status</th>
                    <th>Action</th>
                </tr>
                {% for s in sessions %}
                <tr>
                    <td><b>{{ s._id }}</b></td>
                    <td><span class="badge">{{ s.code }}</span></td>
                    <td>{{ s.expire_date.strftime('%Y-%m-%d %H:%M') if s.expire_date else '-' }}</td>
                    <td>
                        {% if s.status == 'ACTIVE' %}
                            <span class="st-active">ACTIVE</span>
                        {% elif s.status == 'REVOKED' %}
                            <span class="st-revoked">DISCONNECTED</span>
                        {% else %}
                            <span class="st-expired">EXPIRED</span>
                        {% endif %}
                    </td>
                    <td>
                        {% if s.status == 'ACTIVE' %}
                            <a href="/admin/revoke/{{ s._id }}" class="btn-action btn-revoke" onclick="return confirm('Disconnect this device?');">Disconnect</a>
                        {% else %}
                            <a href="/admin/reconnect/{{ s._id }}" class="btn-action btn-reconnect" onclick="return confirm('Reconnect this device?');">Reconnect</a>
                        {% endif %}
                    </td>
                </tr>
                {% else %}
                <tr><td colspan="5" style="color: #888; text-align:center;">No session records found.</td></tr>
                {% endfor %}
            </table>
        </div>
    </div>
</body>
</html>
"""

PRINT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Print Vouchers - HANS WIFI</title>
    <style>
        body { font-family: sans-serif; padding: 20px; background: #f4f6f8; }
        .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; background: white; padding: 20px; }
        .card { border: 2px dashed #333; border-radius: 8px; padding: 12px; text-align: center; }
        .code { font-size: 26px; font-weight: bold; letter-spacing: 4px; background: #f4f6f8; padding: 6px; margin: 6px 0; border-radius: 4px; }
        .details { font-size: 11px; color: #555; }
        @media print { .no-print { display: none; } body { background: white; padding: 0; } .grid { padding: 0; } }
    </style>
</head>
<body>
    <div class="no-print" style="margin-bottom: 20px;">
        <button onclick="window.print()" style="padding: 10px 20px; font-size: 16px; cursor: pointer;">🖨️ Print Sheet</button>
        <a href="/admin" style="margin-left: 15px;">Back to Admin</a>
    </div>
    <div class="grid">
        {% for v in vouchers %}
        <div class="card">
            <h4 style="margin: 0; font-size: 12px;">HANS WIFI PASS</h4>
            <div class="code">{{ v.code }}</div>
            <div class="details">Muda: <b>{{ v.duration_minutes }} Mins</b> | Bei: <b>TZS {{ v.price }}</b></div>
        </div>
        {% endfor %}
    </div>
</body>
</html>
"""


# ==========================================
# 🌐 CAPTIVE PORTAL ROUTES
# ==========================================

@app.route('/')
@app.route('/portal')
@app.route('/portal/')
@app.route('/index.html')
@app.route('/login.html')
@app.route('/wifidog/portal')
@app.route('/wifidog/portal/')
def captive_login_page():
    mac = get_client_mac()
    gw_address = get_gateway_address()
    gw_port = get_param('gw_port', '2060')
    gw_id = get_param('gw_id', 'G1UQ6C8027360')
    userurl = get_param('url') or get_param('userurl') or 'http://www.google.com'

    # Auto-reconnect active sessions after AP restart
    now = datetime.now(timezone.utc)
    if mac and not mac.startswith("UNKNOWN"):
        try:
            active_session = sessions_col.find_one({"_id": mac, "status": "ACTIVE", "expire_date": {"$gt": now}})
            if active_session:
                token = secrets.token_hex(16)
                tokens_col.insert_one({
                    "token": token,
                    "mac": mac,
                    "code": active_session.get("code"),
                    "expire_date": active_session.get("expire_date"),
                    "created_at": now
                })
                auth_action_url = f"http://{gw_address}:{gw_port}/wifidog/auth?token={token}"
                return redirect(auth_action_url)
        except Exception as e:
            logger.error(f"Error during auto-reconnect lookup: {str(e)}")

    return render_template_string(
        PORTAL_TEMPLATE,
        mac=mac,
        gw_address=gw_address,
        gw_port=gw_port,
        gw_id=gw_id,
        userurl=userurl
    ), 200


@app.route('/favicon.ico')
def favicon():
    return Response(status=204)


@app.errorhandler(404)
def handle_404(e):
    path = request.path.lower()
    if 'favicon.ico' in path:
        return Response(status=204)
    if path.startswith('/wifidog') or path.startswith('/api/wifidog') or 'auth' in path or 'ping' in path:
        return Response("Not Found\n", status=404, mimetype='text/plain')
    return captive_login_page()


@app.route('/login', methods=['POST'])
def process_login():
    code = request.form.get('voucher', '').strip()
    mac = get_client_mac()
    gw_address = get_gateway_address()
    gw_port = get_param('gw_port', '2060')
    gw_id = get_param('gw_id', 'G1UQ6C8027360')
    userurl = get_param('userurl') or get_param('url') or 'http://www.google.com'

    try:
        voucher = vouchers_col.find_one({"code": code, "status": "ACTIVE"})
    except Exception as e:
        logger.error(f"DB error checking voucher {code}: {str(e)}")
        voucher = None

    if not voucher:
        return render_template_string(
            PORTAL_TEMPLATE,
            mac=mac,
            gw_address=gw_address,
            gw_port=gw_port,
            gw_id=gw_id,
            userurl=userurl,
            error="Vocha hii siyo sahihi au ishatumika."
        )

    now = datetime.now(timezone.utc)
    duration_minutes = voucher['duration_minutes']
    expire_date = now + timedelta(minutes=duration_minutes)

    token = secrets.token_hex(16)
    tokens_col.insert_one({
        "token": token,
        "mac": mac,
        "code": code,
        "expire_date": expire_date,
        "created_at": now
    })

    sessions_col.replace_one(
        {"_id": mac},
        {
            "_id": mac,
            "code": code,
            "used_time": now,
            "expire_date": expire_date,
            "duration_minutes": duration_minutes,
            "status": "ACTIVE"
        },
        upsert=True
    )
    vouchers_col.update_one({"code": code}, {"$set": {"status": "USED", "used_by_mac": mac}})

    auth_action_url = f"http://{gw_address}:{gw_port}/wifidog/auth?token={token}"

    return f"""
    <!DOCTYPE html>
    <html lang="sw">
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="refresh" content="0;url={auth_action_url}">
        <title>Inaunganisha...</title>
        <style>
            body {{ font-family: -apple-system, sans-serif; text-align: center; padding: 50px 20px; background: #f4f6f8; color: #172b4d; }}
            .card {{ background: white; padding: 30px 20px; border-radius: 12px; max-width: 320px; margin: 0 auto; }}
            .loader {{ border: 4px solid #dfe1e6; border-top: 4px solid #0052cc; border-radius: 50%; width: 40px; height: 40px; animation: spin 0.8s linear infinite; margin: 0 auto 20px auto; }}
            @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
            .btn {{ display: block; width: 100%; padding: 12px; background: #0052cc; color: white; text-decoration: none; font-weight: bold; border-radius: 6px; margin-top: 15px; font-size: 14px; box-sizing: border-box; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="loader"></div>
            <h3 style="margin: 0 0 8px 0; color: #0052cc;">Vocha Imekubaliwa!</h3>
            <p style="font-size: 14px; color: #5e6c84; margin-bottom: 10px;">Inaunganisha intaneti...</p>
            <a href="{auth_action_url}" class="btn">Bonyeza Hapa Kama Haujaunganishwa</a>
        </div>

        <script>
            setTimeout(function() {{
                window.location.replace("{auth_action_url}");
            }}, 100);
        </script>
    </body>
    </html>
    """


# ==========================================
# 🐶 REYEE / REYEEOS WIFIDOG PROTOCOL
# ==========================================

@app.route('/auth', methods=['GET'])
@app.route('/auth/', methods=['GET'])
@app.route('/wifidog/auth', methods=['GET'])
@app.route('/wifidog/auth/', methods=['GET'])
@app.route('/api/wifidog/auth', methods=['GET'])
@app.route('/api/wifidog/auth/', methods=['GET'])
def wifidog_auth_check():
    """Background authentication verification with status validation."""
    stage = request.args.get('stage', '').strip()
    mac = request.args.get('mac', '').strip().upper()
    now = datetime.now(timezone.utc)

    # 1. Client Logout Request
    if stage == 'logout':
        if mac:
            sessions_col.update_one({"_id": mac}, {"$set": {"status": "REVOKED"}})
            tokens_col.delete_many({"mac": mac})
        return Response("Auth: 0\n", mimetype='text/plain')

    # 2. Lookup Session in DB
    session_doc = sessions_col.find_one({"_id": mac}) if mac else None

    if session_doc:
        status = session_doc.get('status', 'ACTIVE')
        exp = session_doc.get('expire_date')
        
        if exp and (exp.tzinfo is None or exp.tzinfo != timezone.utc):
            exp = exp.replace(tzinfo=timezone.utc)

        # Allow access ONLY if status is ACTIVE and time hasn't expired
        if status == 'ACTIVE' and exp and exp > now:
            return Response("Auth: 1\n", mimetype='text/plain')

        # Auto-mark expired sessions without deleting the record
        if exp and exp <= now and status == 'ACTIVE':
            sessions_col.update_one({"_id": mac}, {"$set": {"status": "EXPIRED"}})

    # Purge tokens and deny internet
    if mac:
        tokens_col.delete_many({"mac": mac})

    return Response("Auth: 0\n", mimetype='text/plain')


@app.route('/ping', methods=['GET'])
@app.route('/ping/', methods=['GET'])
@app.route('/wifidog/ping', methods=['GET'])
@app.route('/wifidog/ping/', methods=['GET'])
def wifidog_ping():
    return Response("Pong\n", mimetype='text/plain')


@app.route('/gw_message', methods=['GET'])
@app.route('/wifidog/gw_message', methods=['GET'])
def wifidog_gw_message():
    msg = request.args.get('message', 'Unknown Error')
    return f"""
    <div style="font-family:sans-serif; text-align:center; padding: 40px;">
        <h2>WifiDog Gateway Status</h2>
        <p>Message: <b>{msg}</b></p>
        <a href="/">Try Again</a>
    </div>
    """, 200


# ==========================================
# 📊 ADMIN PANEL & SESSIONS MANAGEMENT
# ==========================================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PW:
            session['admin'] = True
            return redirect('/admin')
        return render_template_string(ADMIN_LOGIN_TEMPLATE, error="Nenosiri sio sahihi!")
    return render_template_string(ADMIN_LOGIN_TEMPLATE)


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect('/admin/login')


@app.route('/admin')
def admin_dashboard():
    if not session.get('admin'):
        return redirect('/admin/login')

    now = datetime.now(timezone.utc)
    vouchers = list(vouchers_col.find().sort("_id", -1).limit(50))

    rev_agg = list(vouchers_col.aggregate([
        {"$match": {"status": "USED"}},
        {"$group": {"_id": None, "total": {"$sum": "$price"}}}
    ]))
    total_rev = rev_agg[0]['total'] if rev_agg else 0.0

    return render_template_string(
        ADMIN_TEMPLATE,
        active_page="dashboard",
        vouchers=vouchers,
        active_vouchers_count=vouchers_col.count_documents({"status": "ACTIVE"}),
        used_vouchers_count=vouchers_col.count_documents({"status": "USED"}),
        active_sessions_count=sessions_col.count_documents({"status": "ACTIVE", "expire_date": {"$gt": now}}),
        total_revenue=f"{total_rev:,.0f}"
    )


@app.route('/admin/sessions')
def admin_sessions_page():
    """Dedicated page to view and manage all active, revoked, and expired sessions."""
    if not session.get('admin'):
        return redirect('/admin/login')

    sessions_list = list(sessions_col.find().sort("used_time", -1))
    return render_template_string(
        SESSIONS_TEMPLATE,
        active_page="sessions",
        sessions=sessions_list
    )


@app.route('/admin/revoke/<mac>')
def revoke_session(mac):
    """Soft-revokes session access without deleting historical records."""
    if not session.get('admin'):
        return redirect('/admin/login')

    mac = mac.strip().upper()
    sessions_col.update_one({"_id": mac}, {"$set": {"status": "REVOKED"}})
    tokens_col.delete_many({"mac": mac})
    
    logger.info(f"Admin disconnected MAC: {mac}")
    return redirect(request.referrer or '/admin/sessions')


@app.route('/admin/reconnect/<mac>')
def reconnect_session(mac):
    """Reactivates a disconnected/expired session, extending duration if necessary."""
    if not session.get('admin'):
        return redirect('/admin/login')

    mac = mac.strip().upper()
    now = datetime.now(timezone.utc)
    session_doc = sessions_col.find_one({"_id": mac})

    if session_doc:
        exp = session_doc.get('expire_date')
        if exp and (exp.tzinfo is None or exp.tzinfo != timezone.utc):
            exp = exp.replace(tzinfo=timezone.utc)

        duration = session_doc.get('duration_minutes', 60)
        
        # If already expired, give fresh time based on original duration
        new_expire = now + timedelta(minutes=duration) if (not exp or exp <= now) else exp

        sessions_col.update_one(
            {"_id": mac},
            {"$set": {"status": "ACTIVE", "expire_date": new_expire}}
        )
        logger.info(f"Admin re-connected MAC: {mac}")

    return redirect(request.referrer or '/admin/sessions')


@app.route('/admin/generate', methods=['POST'])
def generate_vouchers():
    if not session.get('admin'):
        return redirect('/admin/login')

    qty = int(request.form.get('quantity', 8))
    duration = int(request.form.get('duration', 360))
    price = float(request.form.get('price', 500))

    existing_codes = set(v["code"] for v in vouchers_col.find({}, {"code": 1}))
    new_vouchers = []
    
    while len(new_vouchers) < qty and len(existing_codes) < 90000:
        code = f"{random.randint(0, 99999):05d}"
        if code not in existing_codes:
            existing_codes.add(code)
            doc = {
                "code": code,
                "duration_minutes": duration,
                "price": price,
                "status": "ACTIVE",
                "created_at": datetime.now(timezone.utc)
            }
            new_vouchers.append(doc)

    if new_vouchers:
        vouchers_col.insert_many(new_vouchers)

    return render_template_string(PRINT_TEMPLATE, vouchers=new_vouchers)


# ==========================================
# 🚀 SERVER STARTUP
# ==========================================

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
