import os
import random
import re
import secrets
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template_string, request, redirect, session, Response
from pymongo import MongoClient

app = Flask(__name__)

# --- ENVIRONMENT CONFIGURATION ---
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(32))
ADMIN_PW = os.getenv("ADMIN_PASSWORD", "admin123")
DEFAULT_GW_ADDRESS = os.getenv("DEFAULT_GW_ADDRESS", "192.168.0.46")

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://swahilihit:swahilihit@cluster0.3nfk1.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
)

# --- DATABASE SETUP ---
client = MongoClient(MONGO_URI)
db = client['swahilihit56']
vouchers_col = db["vouchers"]
sessions_col = db["sessions"]
tokens_col = db["wifidog_tokens"]


# --- HELPER FUNCTIONS ---
def get_param(key, default=""):
    """Extract parameter from POST form or GET query string."""
    return request.form.get(key) or request.args.get(key) or default

def clean_mac(raw_mac):
    """Normalize MAC address string to standard XX:XX:XX:XX:XX:XX format."""
    if not raw_mac:
        return "DEMO:MAC:00:11:22"
    cleaned = re.sub(r'[^a-fA-F0-9]', '', raw_mac).upper()
    if len(cleaned) == 12:
        return ":".join(cleaned[i:i+2] for i in range(0, 12, 2))
    return raw_mac.strip().upper()

def get_client_mac():
    """Detect client MAC address across ReyeeOS parameter keys."""
    for key in ['mac', 'usermac', 'client_mac', 'client-mac']:
        val = get_param(key)
        if val:
            return clean_mac(val)
    return "DEMO:MAC:00:11:22"

def get_gateway_address():
    """Extract Access Point LAN IP from query params or form data."""
    for key in ['gw_address', 'gw_ip', 'gwaddress', 'router_ip', 'nasip']:
        val = get_param(key)
        if val and val.replace('.', '').isdigit():
            return val.strip()
    return DEFAULT_GW_ADDRESS


# ==========================================
# 🎨 UI HTML TEMPLATES
# ==========================================

PORTAL_TEMPLATE = """
<!DOCTYPE html>
<html lang="sw">
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HANS WIFI - Connect</title>
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; 
            background-color: #f4f6f8; margin: 0; padding: 20px;
            display: flex; justify-content: center; align-items: center; min-height: 90vh;
        }
        .container { width: 100%; max-width: 350px; }
        .box { 
            background: white; padding: 30px 22px; border-radius: 16px; 
            border: 1px solid #e1e4e8; box-shadow: 0 4px 14px rgba(0,0,0,0.06); text-align: center; 
            box-sizing: border-box;
        }
        h2 { margin: 0; color: #0052cc; font-size: 24px; }
        p { color: #5e6c84; font-size: 14px; margin-top: 6px; margin-bottom: 20px; }
        label { font-weight: bold; font-size: 13px; color: #172b4d; display: block; margin-bottom: 8px; text-align: left; }
        input[type="text"] { 
            width: 100%; padding: 14px; font-size: 24px; border: 2px solid #dfe1e6; 
            border-radius: 8px; box-sizing: border-box; margin-bottom: 18px; 
            text-align: center; letter-spacing: 6px; font-weight: bold; color: #0052cc;
        }
        input[type="text"]:focus { border-color: #0052cc; outline: none; }
        button { 
            width: 100%; padding: 14px; background: #0052cc; color: white; 
            border: none; border-radius: 8px; font-weight: bold; font-size: 16px; cursor: pointer; 
            transition: background 0.2s;
        }
        button:hover { background: #0065ff; }
        .error { color: #de350b; background: #ffebe6; padding: 10px; border-radius: 6px; font-size: 13px; margin-bottom: 15px; }
        .mac-info { font-size: 11px; color: #888; margin-top: 15px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="box">
            <h2>HANS WIFI</h2>
            <p>Ingiza namba ya vocha kuunganisha intaneti</p>
            {% if error %}
                <div class="error">{{ error }}</div>
            {% endif %}
            <form action="/process-voucher" method="POST">
                <input type="hidden" name="mac" value="{{ mac }}">
                <input type="hidden" name="gw_address" value="{{ gw_address }}">
                <input type="hidden" name="gw_port" value="{{ gw_port }}">
                <input type="hidden" name="gw_id" value="{{ gw_id }}">
                <input type="hidden" name="userurl" value="{{ userurl }}">
                
                <label for="voucher">Namba ya Vocha (Digits 5):</label>
                <input 
                    type="text" 
                    id="voucher" 
                    name="voucher" 
                    maxlength="5" 
                    pattern="\d{5}" 
                    placeholder="12345" 
                    inputmode="numeric"
                    required 
                    autofocus
                >
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
        .card { background: white; padding: 30px; border-radius: 12px; border: 1px solid #e1e4e8; width: 280px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
        h3 { margin-top: 0; color: #0052cc; }
        input[type="password"] { width: 100%; padding: 12px; margin: 15px 0; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; text-align: center; font-size: 16px; }
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
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f4f6f8; margin: 0; padding: 20px; color: #172b4d; }
        .container { max-width: 960px; margin: 0 auto; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .header h2 { margin: 0; color: #0052cc; }
        .btn-logout { background: #ff5630; color: white; padding: 8px 14px; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 13px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .card { background: white; padding: 18px; border-radius: 10px; border: 1px solid #e1e4e8; }
        .card .lbl { font-size: 12px; color: #5e6c84; font-weight: bold; text-transform: uppercase; }
        .card .val { font-size: 22px; font-weight: bold; color: #0052cc; margin-top: 4px; }
        .box { background: white; padding: 20px; border-radius: 10px; border: 1px solid #e1e4e8; margin-bottom: 20px; }
        .box h3 { margin-top: 0; border-bottom: 1px solid #e1e4e8; padding-bottom: 10px; font-size: 16px; }
        .form-row { display: flex; gap: 10px; flex-wrap: wrap; }
        .form-row input { flex: 1; min-width: 120px; padding: 10px; border: 1px solid #ccc; border-radius: 6px; }
        .btn-gen { background: #0052cc; color: white; padding: 10px 20px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; margin-top: 10px; width: 100%; }
        table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 10px; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #e1e4e8; }
        th { background: #fafbfc; color: #5e6c84; }
        .badge { background: #ebecf0; padding: 3px 6px; border-radius: 4px; font-weight: bold; font-family: monospace; }
        .st-active { color: #006644; background: #e3fcef; padding: 3px 8px; border-radius: 10px; font-weight: bold; font-size: 11px; }
        .st-used { color: #bf2600; background: #ffebe6; padding: 3px 8px; border-radius: 10px; font-weight: bold; font-size: 11px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>HANS WIFI Admin Panel</h2>
            <a href="/admin/logout" class="btn-logout">Logout</a>
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
                <div class="form-row">
                    <input type="number" name="quantity" value="8" placeholder="Quantity" required>
                    <input type="number" name="duration" value="360" placeholder="Duration (Mins)" required>
                    <input type="number" name="price" value="500" placeholder="Price (TZS)" required>
                </div>
                <button type="submit" class="btn-gen">Generate Printable Sheet</button>
            </form>
        </div>
        <div class="box">
            <h3>📡 Connected Devices (Active Sessions)</h3>
            <table>
                <tr><th>MAC Address</th><th>Voucher Code</th><th>Expire Date</th></tr>
                {% for s in active_sessions %}
                <tr>
                    <td><b>{{ s._id }}</b></td>
                    <td><span class="badge">{{ s.code }}</span></td>
                    <td><span class="st-active">{{ s.expire_date.strftime('%Y-%m-%d %H:%M') if s.expire_date else '-' }}</span></td>
                </tr>
                {% else %}
                <tr><td colspan="3" style="color: #888;">No active sessions.</td></tr>
                {% endfor %}
            </table>
        </div>
        <div class="box">
            <h3>🎟️ Recent Voucher Inventory</h3>
            <table>
                <tr><th>Code</th><th>Duration</th><th>Price</th><th>Status</th><th>Used By MAC</th></tr>
                {% for v in vouchers %}
                <tr>
                    <td><span class="badge">{{ v.code }}</span></td>
                    <td>{{ v.duration_minutes }} mins</td>
                    <td>TZS {{ v.price }}</td>
                    <td><span class="{{ 'st-active' if v.status == 'ACTIVE' else 'st-used' }}">{{ v.status }}</span></td>
                    <td>{{ v.used_by_mac or '-' }}</td>
                </tr>
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

@app.route('/', methods=['GET'])
@app.route('/login', methods=['GET'])
@app.route('/login/', methods=['GET'])
@app.route('/portal', methods=['GET'])
@app.route('/portal/', methods=['GET'])
@app.route('/index.html', methods=['GET'])
@app.route('/login.html', methods=['GET'])
@app.route('/wifidog/portal', methods=['GET'])
@app.route('/wifidog/portal/', methods=['GET'])
@app.route('/api/wifidog/portal', methods=['GET'])
@app.route('/api/wifidog/portal/', methods=['GET'])
def captive_login_page():
    """Renders portal page and handles router GET parameters."""
    mac = get_client_mac()
    gw_address = get_gateway_address()
    gw_port = get_param('gw_port', '2060')
    gw_id = get_param('gw_sn') or get_param('gw_id', 'G1UQ6C8027360')
    userurl = get_param('url') or get_param('userurl') or 'http://www.google.com'
    now = datetime.now(timezone.utc)

    # Automatically grant access if session exists for this MAC
    existing_session = sessions_col.find_one({"_id": mac})
    if existing_session and existing_session.get("expire_date"):
        exp = existing_session["expire_date"]
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp > now:
            token = secrets.token_hex(16)
            tokens_col.insert_one({
                "token": token,
                "mac": mac,
                "code": existing_session.get("code", "ACTIVE"),
                "expire_date": exp,
                "created_at": now
            })
            auth_action_url = f"http://{gw_address}:{gw_port}/wifidog/auth?token={token}"
            return redirect(auth_action_url, code=303)

    return render_template_string(
        PORTAL_TEMPLATE,
        mac=mac,
        gw_address=gw_address,
        gw_port=gw_port,
        gw_id=gw_id,
        userurl=userurl
    ), 200

@app.errorhandler(404)
def handle_404(e):
    """Catch routing errors without corrupting background API requests."""
    if request.path.startswith('/wifidog') or request.path.startswith('/api/wifidog'):
        return Response("Not Found\n", status=404, mimetype='text/plain')
    return captive_login_page()

@app.route('/process-voucher', methods=['POST'])
def process_login():
    """Validates voucher and issues HTTP 303 Redirect back to local AP."""
    code = request.form.get('voucher', '').strip()
    mac = get_client_mac()
    gw_address = get_gateway_address()
    gw_port = get_param('gw_port', '2060')
    gw_id = get_param('gw_id', 'G1UQ6C8027360')
    userurl = get_param('userurl') or get_param('url') or 'http://www.google.com'

    voucher = vouchers_col.find_one({"code": code, "status": "ACTIVE"})

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

    # 1. Create temporary token
    token = secrets.token_hex(16)
    tokens_col.insert_one({
        "token": token,
        "mac": mac,
        "code": code,
        "expire_date": expire_date,
        "created_at": now
    })

    # 2. Register Active MAC session
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

    # 3. Form destination URL pointing to router HTTP gateway
    auth_action_url = f"http://{gw_address}:{gw_port}/wifidog/auth?token={token}"

    # 4. HTTP 303 Redirect (Prevents Android WebView POST security drop)
    return redirect(auth_action_url, code=303)


# ==========================================
# 🐶 REYEE / REYEEOS WIFIDOG PROTOCOL
# ==========================================

@app.route('/wifidog/auth', methods=['GET'])
@app.route('/wifidog/auth/', methods=['GET'])
@app.route('/api/wifidog/auth', methods=['GET'])
@app.route('/api/wifidog/auth/', methods=['GET'])
def wifidog_auth_check():
    """ReyeeOS background Auth Verification."""
    try:
        stage = request.args.get('stage', '').strip()
        token = request.args.get('token', '').strip()
        mac = clean_mac(request.args.get('mac', ''))
        now = datetime.now(timezone.utc)

        # Handle disconnect/logout
        if stage == 'logout':
            if mac:
                sessions_col.delete_one({"_id": mac})
            return Response("Auth: 0\n", mimetype='text/plain')

        # Check Token (Login phase)
        if token:
            token_doc = tokens_col.find_one({"token": token})
            if token_doc:
                exp = token_doc.get('expire_date')
                if exp and exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if exp and exp > now:
                    return Response("Auth: 1\n", mimetype='text/plain')

        # Check MAC Address (Heartbeat check)
        if mac:
            session_doc = sessions_col.find_one({"_id": mac})
            if session_doc:
                exp = session_doc.get('expire_date')
                if exp and exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if exp and exp > now:
                    return Response("Auth: 1\n", mimetype='text/plain')

        return Response("Auth: 0\n", mimetype='text/plain')
    except Exception:
        return Response("Auth: 0\n", mimetype='text/plain')

@app.route('/wifidog/ping', methods=['GET'])
@app.route('/wifidog/ping/', methods=['GET'])
@app.route('/api/wifidog/ping', methods=['GET'])
@app.route('/api/wifidog/ping/', methods=['GET'])
def wifidog_ping():
    """Periodic Reyee AP Heartbeat."""
    return Response("Pong\n", mimetype='text/plain')

@app.route('/wifidog/gw_message', methods=['GET'])
@app.route('/wifidog/gw_message/', methods=['GET'])
@app.route('/api/wifidog/gw_message', methods=['GET'])
@app.route('/api/wifidog/gw_message/', methods=['GET'])
def wifidog_gw_message():
    """Displays router status messages."""
    msg = request.args.get('message', 'Success')
    return f"""
    <div style="font-family:sans-serif; text-align:center; padding: 40px;">
        <h2>WifiDog Status</h2>
        <p>Status: <b>{msg}</b></p>
        <a href="/">Return to Home</a>
    </div>
    """, 200


# ==========================================
# 📊 ADMIN PANEL ROUTES
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
    active_sessions = list(sessions_col.find({"expire_date": {"$gt": now}}))

    rev_agg = list(vouchers_col.aggregate([
        {"$match": {"status": "USED"}},
        {"$group": {"_id": None, "total": {"$sum": "$price"}}}
    ]))
    total_rev = rev_agg[0]['total'] if rev_agg else 0.0

    return render_template_string(
        ADMIN_TEMPLATE,
        vouchers=vouchers,
        active_sessions=active_sessions,
        active_vouchers_count=vouchers_col.count_documents({"status": "ACTIVE"}),
        used_vouchers_count=vouchers_col.count_documents({"status": "USED"}),
        active_sessions_count=len(active_sessions),
        total_revenue=f"{total_rev:,.0f}"
    )

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
