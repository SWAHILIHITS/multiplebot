import os
import random
import secrets
import logging
import logging.config
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, request, redirect, session, Response, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)

# ==========================================
# 📝 LOGGING INITIALIZATION
# ==========================================
LOG_CONFIG_FILE = "logging.conf"

if os.path.exists(LOG_CONFIG_FILE):
    logging.config.fileConfig(LOG_CONFIG_FILE, disable_existing_loggers=False)
    logger = logging.getLogger("appLogger")
    logger.info("Successfully loaded logging configuration from logging.conf")
else:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("appLogger")
    logger.warning("logging.conf not found. Falling back to standard basic logging.")


# ==========================================
# ⚙️ ENVIRONMENT CONFIGURATION
# ==========================================
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(32))
ADMIN_PW = os.getenv("ADMIN_PASSWORD", "admin123")
DEFAULT_GW_ADDRESS = os.getenv("DEFAULT_GW_ADDRESS", "192.168.0.46")

# MongoDB Database URI
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://swahilihit:swahilihit@cluster0.3nfk1.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
)

# ==========================================
# 🗄️ DATABASE SETUP & INDEXES
# ==========================================
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client['swahilihit56']
    
    # Collection References
    vouchers_col = db["vouchers"]
    sessions_col = db["sessions"]
    tokens_col = db["wifidog_tokens"]
    packages_col = db["packages"]
    
    # Initialize indexes for performance and automatic TTL expirations
    vouchers_col.create_index("code", unique=True)
    tokens_col.create_index("created_at", expireAfterSeconds=600)
    sessions_col.create_index("expire_date")
    
    logger.info("Successfully connected to MongoDB and verified collection indexes.")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {str(e)}")


# ==========================================
# 🛠️ HELPER FUNCTIONS
# ==========================================
def get_param(key, default=""):
    """Extract parameter from POST form or GET query string."""
    return request.form.get(key) or request.args.get(key) or default

def get_client_mac():
    """Detect client MAC address across common ReyeeOS parameter keys."""
    for key in ['mac', 'usermac', 'client_mac', 'client-mac']:
        val = get_param(key)
        if val:
            return val.strip().upper()
    return f"UNKNOWN:{secrets.token_hex(4).upper()}"

def get_gateway_address():
    """Extract Access Point LAN IP. Falls back strictly to DEFAULT_GW_ADDRESS."""
    for key in ['gw_address', 'gw_ip', 'gwaddress', 'router_ip']:
        val = get_param(key)
        if val and val.replace('.', '').isdigit():
            return val.strip()
    return DEFAULT_GW_ADDRESS

def calculate_duration_minutes(duration_val, unit):
    """Converts duration inputs to minutes for uniform database queries."""
    val = int(duration_val)
    unit = str(unit).lower()
    if unit == 'hours':
        return val * 60
    elif unit == 'days':
        return val * 1440
    elif unit == 'months':
        return val * 43200
    return val  # Default minutes


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
@app.route('/api/wifidog/portal')
@app.route('/api/wifidog/portal/')
def captive_login_page():
    """Renders voucher entry page or auto-reconnects active MAC sessions."""
    mac = get_client_mac()
    gw_address = get_gateway_address()
    gw_port = get_param('gw_port', '2060')
    gw_id = get_param('gw_id', 'G1UQ6C8027360')
    userurl = get_param('url') or get_param('userurl') or 'http://www.google.com'

    logger.info(f"Portal requested by MAC: {mac} via Gateway: {gw_address}")

    # Auto-reconnect check for active sessions after AP reboot
    now = datetime.now(timezone.utc)
    if mac and not mac.startswith("UNKNOWN"):
        try:
            active_session = sessions_col.find_one({"_id": mac, "expire_date": {"$gt": now}, "status": "ACTIVE"})
            if active_session:
                logger.info(f"Active session found for MAC: {mac}. Triggering auto-reconnect.")
                
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
            logger.error(f"Error checking active session during portal load: {str(e)}")

    return render_template(
        'portal.html',
        mac=mac,
        gw_address=gw_address,
        gw_port=gw_port,
        gw_id=gw_id,
        userurl=userurl
    ), 200


@app.route('/login', methods=['POST'])
def process_login():
    """Validates voucher code and redirects client to local AP auth endpoint."""
    code = request.form.get('voucher', '').strip()
    mac = get_client_mac()
    gw_address = get_gateway_address()
    gw_port = get_param('gw_port', '2060')
    gw_id = get_param('gw_id', 'G1UQ6C8027360')
    userurl = get_param('userurl') or get_param('url') or 'http://www.google.com'

    logger.info(f"Voucher redemption attempt: '{code}' from MAC: {mac}")

    now = datetime.now(timezone.utc)
    
    # Fetch unused voucher
    try:
        voucher = vouchers_col.find_one({"code": code, "status": "UNUSED"})
    except Exception as e:
        logger.error(f"Database error while validating voucher {code}: {str(e)}")
        voucher = None

    if not voucher:
        logger.warning(f"Failed login attempt: Invalid or used voucher '{code}' from MAC: {mac}")
        return render_template(
            'portal.html',
            mac=mac,
            gw_address=gw_address,
            gw_port=gw_port,
            gw_id=gw_id,
            userurl=userurl,
            error="Vocha hii siyo sahihi au ishatumika."
        )

    # Check if unused voucher has passed its explicit expiration date
    if voucher.get("expire_at") and voucher["expire_at"] <= now:
        vouchers_col.delete_one({"_id": voucher["_id"]})
        logger.info(f"Expired unused voucher '{code}' deleted upon redemption attempt.")
        return render_template(
            'portal.html',
            mac=mac,
            gw_address=gw_address,
            gw_port=gw_port,
            gw_id=gw_id,
            userurl=userurl,
            error="Vocha hii imepitwa na wakati (Expired)."
        )

    duration_minutes = voucher['duration_minutes']
    expire_date = now + timedelta(minutes=duration_minutes)

    # 1. Create temporary token for WifiDog handshake
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
    
    # 3. Update Voucher status to USED
    vouchers_col.update_one(
        {"code": code}, 
        {"$set": {"status": "USED", "used_by_mac": mac, "used_at": now, "expire_at": expire_date}}
    )

    logger.info(f"Successful login: MAC {mac} redeemed voucher '{code}' for {duration_minutes} mins.")

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
            .card {{ background: white; padding: 30px 20px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); max-width: 320px; margin: 0 auto; }}
            .loader {{ border: 4px solid #dfe1e6; border-top: 4px solid #0052cc; border-radius: 50%; width: 40px; height: 40px; animation: spin 0.8s linear infinite; margin: 0 auto 20px auto; }}
            @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
            .btn {{ display: block; width: 100%; padding: 12px; background: #0052cc; color: white; text-decoration: none; font-weight: bold; border: none; border-radius: 6px; cursor: pointer; margin-top: 15px; font-size: 14px; box-sizing: border-box; }}
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
            setTimeout(function() {{ window.location.replace("{auth_action_url}"); }}, 100);
        </script>
    </body>
    </html>
    """


# ==========================================
# 🐶 REYEE / WIFIDOG PROTOCOL ENDPOINTS
# ==========================================

@app.route('/auth', methods=['GET'])
@app.route('/auth/', methods=['GET'])
@app.route('/wifidog/auth', methods=['GET'])
@app.route('/wifidog/auth/', methods=['GET'])
@app.route('/api/wifidog/auth', methods=['GET'])
@app.route('/api/wifidog/auth/', methods=['GET'])
def wifidog_auth_check():
    """ReyeeOS background Auth verification."""
    stage = request.args.get('stage', '').strip()
    mac = request.args.get('mac', '').strip().upper()
    now = datetime.now(timezone.utc)

    if stage == 'logout':
        if mac:
            sessions_col.delete_one({"_id": mac})
            tokens_col.delete_many({"mac": mac})
            logger.info(f"Client logged out: MAC {mac}")
        return Response("Auth: 0\n", mimetype='text/plain')

    session_doc = sessions_col.find_one({"_id": mac}) if mac else None

    if session_doc and session_doc.get("status") == "ACTIVE":
        exp = session_doc.get('expire_date')
        if exp and (exp.tzinfo is None or exp.tzinfo != timezone.utc):
            exp = exp.replace(tzinfo=timezone.utc)

        if exp and exp > now:
            return Response("Auth: 1\n", mimetype='text/plain')

    if mac:
        tokens_col.delete_many({"mac": mac})

    logger.warning(f"WifiDog Auth denied/expired for MAC: '{mac}'. Returning Auth: 0")
    return Response("Auth: 0\n", mimetype='text/plain')


@app.route('/ping', methods=['GET'])
@app.route('/ping/', methods=['GET'])
@app.route('/wifidog/ping', methods=['GET'])
@app.route('/wifidog/ping/', methods=['GET'])
@app.route('/api/wifidog/ping', methods=['GET'])
@app.route('/api/wifidog/ping/', methods=['GET'])
def wifidog_ping():
    """Periodic Reyee Access Point heartbeat."""
    return Response("Pong\n", mimetype='text/plain')


@app.route('/gw_message', methods=['GET'])
def wifidog_gw_message():
    """Displays router-level messages."""
    msg = request.args.get('message', 'Unknown Gateway Message')
    return f"""
    <div style="font-family:sans-serif; text-align:center; padding: 40px;">
        <h2>WifiDog Status</h2>
        <p>Message: <b>{msg}</b></p>
        <a href="/">Try Again</a>
    </div>
    """, 200


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


# ==========================================
# 📊 ADMIN PANEL ROUTES
# ==========================================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PW:
            session['admin'] = True
            logger.info("Admin login successful.")
            return redirect('/admin')
        return render_template('admin_login.html', error="Nenosiri sio sahihi!")
    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    logger.info("Admin logged out.")
    return redirect('/admin/login')


@app.route('/admin')
def admin_dashboard():
    if not session.get('admin'):
        return redirect('/admin/login')

    now = datetime.now(timezone.utc)

    # 1. Cleanup expired UNUSED vouchers automatically
    vouchers_col.delete_many({
        "status": "UNUSED",
        "expire_at": {"$lte": now, "$ne": None}
    })

    # 2. Fetch Datasets
    packages = list(packages_col.find().sort("_id", -1))
    vouchers = list(vouchers_col.find().sort("_id", -1))
    active_sessions = list(sessions_col.find({"expire_date": {"$gt": now}, "status": "ACTIVE"}))
    active_macs = set(s["_id"] for s in active_sessions)

    # Compute status for UI representation
    for v in vouchers:
        if v.get('status') in ['USED', 'REVOKED']:
            exp = v.get('expire_at')
            if exp and (exp.tzinfo is None or exp.tzinfo != timezone.utc):
                exp = exp.replace(tzinfo=timezone.utc)
            if exp and exp <= now:
                v['computed_status'] = 'EXPIRED'
            else:
                v['computed_status'] = v['status']
        else:
            v['computed_status'] = v.get('status', 'UNUSED')

    # Aggregations for Users View (Fewer Details)
    user_pipeline = [
        {"$match": {"used_by_mac": {"$ne": None}}},
        {"$group": {
            "_id": "$used_by_mac",
            "vouchers_count": {"$sum": 1},
            "total_spend": {"$sum": "$price"}
        }}
    ]
    user_summary_raw = list(vouchers_col.aggregate(user_pipeline))
    user_summary = [{
        "mac": u["_id"],
        "status": "online" if u["_id"] in active_macs else "offline",
        "vouchers_count": u["vouchers_count"],
        "total_spend": u["total_spend"]
    } for u in user_summary_raw]

    # Revenue calculation
    total_rev = sum(v.get('price', 0.0) for v in vouchers if v.get('status') in ['USED', 'REVOKED'])

    return render_template(
        'admin.html',
        packages=packages,
        vouchers=vouchers,
        active_sessions=active_sessions,
        user_summary=user_summary,
        active_sessions_count=len(active_sessions),
        active_vouchers_count=vouchers_col.count_documents({"status": "UNUSED"}),
        used_vouchers_count=vouchers_col.count_documents({"status": "USED"}),
        total_revenue=f"{total_rev:,.0f}"
    )


# --- PACKAGE ACTIONS ---

@app.route('/admin/packages/create', methods=['POST'])
def create_package():
    if not session.get('admin'):
        return redirect('/admin/login')

    name = request.form.get('name')
    price = float(request.form.get('price', 0))
    duration_val = int(request.form.get('duration', 1))
    unit = request.form.get('unit', 'days')
    badge = request.form.get('badge', '')
    description = request.form.get('description', '')

    duration_minutes = calculate_duration_minutes(duration_val, unit)

    packages_col.insert_one({
        "name": name,
        "price": price,
        "duration_value": duration_val,
        "duration_unit": unit,
        "duration_minutes": duration_minutes,
        "badge": badge,
        "description": description,
        "created_at": datetime.now(timezone.utc)
    })
    logger.info(f"Package created: {name} - TZS {price}")
    return redirect('/admin#packages')


@app.route('/admin/packages/delete/<package_id>')
def delete_package(package_id):
    if not session.get('admin'):
        return redirect('/admin/login')
    
    packages_col.delete_one({"_id": ObjectId(package_id)})
    logger.info(f"Package ID {package_id} deleted.")
    return redirect('/admin#packages')


# --- VOUCHER ACTIONS ---

@app.route('/admin/generate', methods=['POST'])
def generate_vouchers():
    if not session.get('admin'):
        return redirect('/admin/login')

    package_id = request.form.get('package_id')
    qty = int(request.form.get('quantity', 1))
    custom_code = request.form.get('custom_code', '').strip()
    expire_at_str = request.form.get('expire_at')
    note = request.form.get('note', '')

    pkg = packages_col.find_one({"_id": ObjectId(package_id)}) if package_id else None
    
    price = pkg['price'] if pkg else float(request.form.get('price', 500))
    duration = pkg['duration_minutes'] if pkg else 1440
    pkg_name = pkg['name'] if pkg else "Custom Package"

    now = datetime.now(timezone.utc)
    expire_date = None
    if expire_at_str:
        expire_date = datetime.fromisoformat(expire_at_str).replace(tzinfo=timezone.utc)

    new_vouchers = []

    if custom_code:
        doc = {
            "code": custom_code,
            "package_name": pkg_name,
            "duration_minutes": duration,
            "price": price,
            "status": "UNUSED",
            "created_at": now,
            "expire_at": expire_date,
            "note": note
        }
        vouchers_col.update_one({"code": custom_code}, {"$set": doc}, upsert=True)
        new_vouchers.append(doc)
    else:
        existing_codes = set(v["code"] for v in vouchers_col.find({}, {"code": 1}))
        while len(new_vouchers) < qty and len(existing_codes) < 90000:
            code = f"{random.randint(0, 99999):05d}"
            if code not in existing_codes:
                existing_codes.add(code)
                doc = {
                    "code": code,
                    "package_name": pkg_name,
                    "duration_minutes": duration,
                    "price": price,
                    "status": "UNUSED",
                    "created_at": now,
                    "expire_at": expire_date,
                    "note": note
                }
                new_vouchers.append(doc)

        if new_vouchers:
            vouchers_col.insert_many(new_vouchers)

    return render_template('print.html', vouchers=new_vouchers)


@app.route('/admin/voucher/revoke/<code_or_mac>')
def revoke_voucher(code_or_mac):
    """
    Revocation logic:
    - UNUSED: Permanently deletes voucher record from DB.
    - USED: Sets session/voucher status to REVOKED (disconnects device).
    """
    if not session.get('admin'):
        return redirect('/admin/login')

    target = code_or_mac.strip().upper()
    v = vouchers_col.find_one({"$or": [{"code": target}, {"used_by_mac": target}]})

    if v:
        if v.get('status') == 'UNUSED':
            vouchers_col.delete_one({"_id": v["_id"]})
            logger.info(f"Unused voucher '{v['code']}' revoked and deleted.")
        elif v.get('status') == 'USED':
            mac = v.get('used_by_mac')
            if mac:
                sessions_col.update_one({"_id": mac}, {"$set": {"status": "REVOKED"}})
                tokens_col.delete_many({"mac": mac})
            vouchers_col.update_one({"_id": v["_id"]}, {"$set": {"status": "REVOKED"}})
            logger.info(f"Used voucher '{v['code']}' set to REVOKED for MAC {mac}.")

    return redirect('/admin#vouchers')


@app.route('/admin/voucher/unrevoke/<code_or_mac>')
def unrevoke_voucher(code_or_mac):
    """Restores active internet session permission for a revoked used voucher."""
    if not session.get('admin'):
        return redirect('/admin/login')

    target = code_or_mac.strip().upper()
    v = vouchers_col.find_one({"$or": [{"code": target}, {"used_by_mac": target}]})

    if v and v.get('status') == 'REVOKED':
        mac = v.get('used_by_mac')
        if mac:
            sessions_col.update_one({"_id": mac}, {"$set": {"status": "ACTIVE"}})
        vouchers_col.update_one({"_id": v["_id"]}, {"$set": {"status": "USED"}})
        logger.info(f"Voucher access restored for MAC {mac}.")

    return redirect('/admin#vouchers')


# ==========================================
# 🚀 SERVER STARTUP
# ==========================================
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting HANS WIFI Portal server on port {port}")
    app.run(host='0.0.0.0', port=port)
