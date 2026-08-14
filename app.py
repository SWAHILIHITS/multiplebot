import os
import random
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, session
from pymongo import MongoClient

app = Flask(__name__)

# --- ENVIRONMENT CONFIGURATION ---
app.secret_key = os.getenv("SECRET_KEY", "fallback_secret_key_123")
ADMIN_PW = os.getenv("ADMIN_PASSWORD", "admin123")

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://swahilihit:swahilihit@cluster0.3nfk1.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
)

client = MongoClient(MONGO_URI)
db = client['swahilihit56']
vouchers_col = db["vouchers"]
sessions_col = db["sessions"]

# --- HELPER FUNCTIONS ---
def get_param(key, default=""):
    """Extracts a parameter from request form or query args."""
    return request.form.get(key) or request.args.get(key) or default

def get_client_mac():
    """Finds MAC address across multiple standard query/form parameter keys."""
    for key in ['mac', 'usermac', 'client_mac', 'client-mac']:
        val = get_param(key)
        if val:
            return val.strip().upper()
    return "DEMO:MAC:00:11:22"

# --- HTML TEMPLATES ---
PORTAL_TEMPLATE = """
<!DOCTYPE html>
<html lang="sw">
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HANS WIFI - Connect</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f4f6f8; display: flex; justify-content: center; align-items: center; min-height: 90vh; margin: 0; padding: 20px; }
        .box { background: white; padding: 30px 20px; border-radius: 16px; width: 100%; max-width: 340px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.06); border: 1px solid #e1e4e8; box-sizing: border-box; }
        h2 { margin: 0; color: #0052cc; font-size: 24px; }
        p { color: #5e6c84; font-size: 14px; margin-top: 6px; }
        input[type="text"] { width: 100%; padding: 14px; font-size: 24px; border: 2px solid #dfe1e6; border-radius: 8px; box-sizing: border-box; margin: 15px 0; text-align: center; letter-spacing: 6px; font-weight: bold; color: #0052cc; }
        button { width: 100%; padding: 14px; background: #0052cc; color: white; border: none; border-radius: 8px; font-weight: bold; font-size: 16px; cursor: pointer; }
        button:hover { background: #0065ff; }
        .error { color: #de350b; background: #ffebe6; padding: 10px; border-radius: 6px; font-size: 13px; margin-bottom: 15px; }
        .mac { font-size: 11px; color: #888; margin-top: 15px; }
    </style>
</head>
<body>
    <div class="box">
        <h2>HANS WIFI</h2>
        <p>Ingiza namba ya vocha kuunganisha</p>
        {% if error %}
            <div class="error">{{ error }}</div>
        {% endif %}
        <form action="/login" method="POST">
            <input type="hidden" name="mac" value="{{ mac }}">
            <input type="hidden" name="gw_address" value="{{ gw_address }}">
            <input type="hidden" name="gw_port" value="{{ gw_port }}">
            <input type="hidden" name="userurl" value="{{ userurl }}">
            
            <input type="text" name="voucher" maxlength="5" pattern="\d{5}" placeholder="12345" inputmode="numeric" required autofocus>
            <button type="submit">CONNECT INTERNET</button>
        </form>
        <div class="mac">Device MAC: {{ mac }}</div>
    </div>
</body>
</html>
"""

ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="sw">
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HANS WIFI Admin</title>
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
            <h3>🖨️ Generate Vouchers</h3>
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
            <h3>📡 Connected Devices (Active MAC Sessions)</h3>
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
            <h3>🎟️ Recent Vouchers</h3>
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

# --- ROUTES ---

@app.route('/')
@app.route('/index.html')
@app.route('/portal')
@app.route('/login.html')
@app.errorhandler(404)
def portal_home(e=None):
    mac = get_client_mac()
    gw_address = get_param('gw_address')
    gw_port = get_param('gw_port', '2060')
    userurl = get_param('url') or get_param('userurl') or 'http://www.baidu.com'

    return render_template_string(
        PORTAL_TEMPLATE,
        mac=mac,
        gw_address=gw_address,
        gw_port=gw_port,
        userurl=userurl
    ), 200

@app.route('/login', methods=['POST'])
def login():
    code = request.form.get('voucher', '').strip()
    mac = get_client_mac()
    gw_address = get_param('gw_address')
    gw_port = get_param('gw_port', '2060')
    userurl = get_param('userurl') or get_param('url') or 'http://www.baidu.com'

    voucher = vouchers_col.find_one({"code": code, "status": "ACTIVE"})

    if not voucher:
        return render_template_string(
            PORTAL_TEMPLATE,
            mac=mac,
            gw_address=gw_address,
            gw_port=gw_port,
            userurl=userurl,
            error="Vocha hii siyo sahihi au ishatumika."
        )

    now = datetime.now()
    duration_minutes = voucher['duration_minutes']
    expire_date = now + timedelta(minutes=duration_minutes)

    # Database updates
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

    # Auto-submitting POST response targeting local Ruijie webauth.cgi
    if gw_address:
        ruijie_url = f"http://{gw_address}:{gw_port}/webauth.cgi"
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Connecting...</title>
            <style>
                body {{ font-family: sans-serif; text-align: center; padding: 50px 20px; background: #f4f6f8; }}
                .btn {{ padding: 12px 24px; background: #0052cc; color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; text-decoration: none; }}
            </style>
        </head>
        <body>
            <h1 style="color: #36b37e;">✅ Vocha Imekubaliwa!</h1>
            <p>Inaunganisha intaneti, tafadhali subiri...</p>

            <form id="ruijieForm" action="{ruijie_url}" method="POST">
                <input type="hidden" name="action" value="login">
                <input type="hidden" name="username" value="guest">
                <input type="hidden" name="password" value="guest">
                <input type="hidden" name="mac" value="{mac}">
                <input type="hidden" name="url" value="{userurl}">
                <button type="submit" class="btn">Bonyeza Kuunganisha</button>
            </form>

            <script>
                setTimeout(function() {{
                    document.getElementById('ruijieForm').submit();
                }}, 400);
            </script>
        </body>
        </html>
        """

    return """
    <div style="font-family: sans-serif; text-align: center; margin-top: 80px;">
        <h1 style="color: #36b37e;">✅ IMEFANIKIWA!</h1>
        <p>Device imeunganishwa na intaneti.</p>
    </div>
    """

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PW:
            session['admin'] = True
            return redirect('/admin')
        return '<div style="text-align:center;padding:50px;font-family:sans-serif;"><p style="color:red">Password Siyo Sahihi!</p><a href="/admin/login">Rudi</a></div>'
    
    return '''
    <div style="display:flex;justify-content:center;align-items:center;height:90vh;font-family:sans-serif;">
        <form method="POST" style="background:white;padding:30px;border-radius:10px;box-shadow:0 4px 10px #0001;border:1px solid #ddd;width:260px;text-align:center;">
            <h3>Admin Login</h3>
            <input type="password" name="password" placeholder="Password" style="width:100%;padding:10px;margin:10px 0;box-sizing:border-box;" required autofocus>
            <button style="width:100%;padding:10px;background:#0052cc;color:white;border:none;border-radius:6px;font-weight:bold;cursor:pointer;">Login</button>
        </form>
    </div>
    '''

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect('/admin/login')

@app.route('/admin')
def admin_dashboard():
    if not session.get('admin'):
        return redirect('/admin/login')

    now = datetime.now()
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

    new_vouchers = []
    for _ in range(qty):
        while True:
            code = ''.join(random.choices('0123456789', k=5))
            if not vouchers_col.find_one({"code": code}):
                doc = {
                    "code": code,
                    "duration_minutes": duration,
                    "price": price,
                    "status": "ACTIVE",
                    "created_at": datetime.now()
                }
                vouchers_col.insert_one(doc)
                new_vouchers.append(doc)
                break

    return render_template_string(PRINT_TEMPLATE, vouchers=new_vouchers)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
