import os
import random
import secrets
import logging
import logging.config
from datetime import datetime, timedelta, timezone
from bson import ObjectId
from flask import Flask, render_template, request, redirect, session, Response

# Import MongoDB collection objects from templates/database.py
from templates.database import vouchers_col, sessions_col, tokens_col, packages_col

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

def calculate_duration_minutes(val, unit):
    """Converts user package duration inputs to total minutes."""
    val = int(val)
    if unit == 'minutes':
        return val
    elif unit == 'hours':
        return val * 60
    elif unit == 'days':
        return val * 60 * 24
    elif unit == 'months':
        return val * 60 * 24 * 30
    return val


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
    """Renders voucher entry page or auto-reconnects existing active MAC sessions."""
    mac = get_client_mac()
    gw_address = get_gateway_address()
    gw_port = get_param('gw_port', '2060')
    gw_id = get_param('gw_id', 'G1UQ6C8027360')
    userurl = get_param('url') or get_param('userurl') or 'http://www.google.com'

    logger.info(f"Portal page requested by MAC: {mac} via Gateway IP: {gw_address}")

    # --- AUTO-RECONNECT CHECK AFTER AP REBOOT ---
    now = datetime.now(timezone.utc)
    if mac and not mac.startswith("UNKNOWN"):
        try:
            active_session = sessions_col.find_one({"_id": mac, "expire_date": {"$gt": now}})
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


@app.route('/favicon.ico')
def favicon():
    """Silence browser favicon requests with 204 No Content."""
    return Response(status=204)


@app.errorhandler(404)
def handle_404(e):
    """Catch routing errors without corrupting API background checks."""
    path = request.path.lower()
    
    if 'favicon.ico' in path:
        return Response(status=204)

    if path.startswith('/wifidog') or path.startswith('/api/wifidog') or 'auth' in path or 'ping' in path:
        logger.warning(f"Unhandled WifiDog API route requested: {request.path}")
        return Response("Not Found\n", status=404, mimetype='text/plain')
    
    logger.warning(f"404 redirect triggered for path: {request.path} from IP: {request.remote_addr}")
    return captive_login_page()


@app.route('/login', methods=['POST'])
def process_login():
    """Validates voucher and redirects client to local AP auth endpoint."""
    code = request.form.get('voucher', '').strip()
    mac = get_client_mac()
    gw_address = get_gateway_address()
    gw_port = get_param('gw_port', '2060')
    gw_id = get_param('gw_id', 'G1UQ6C8027360')
    userurl = get_param('userurl') or get_param('url') or 'http://www.google.com'

    logger.info(f"Voucher attempt submitted: Code '{code}' from MAC: {mac}")

    now = datetime.now(timezone.utc)

    try:
        voucher = vouchers_col.find_one({"code": code})
    except Exception as e:
        logger.error(f"Database error while checking voucher {code}: {str(e)}")
        voucher = None

    # Validate Voucher availability and expiration
    if not voucher or voucher.get("status") in ["USED", "REVOKED"]:
        error_msg = "Vocha hii siyo sahihi au ishatumika."
        if voucher and voucher.get("status") == "REVOKED":
            error_msg = "Vocha hii imesitishwa au kufutwa."
        
        logger.warning(f"Failed login attempt: Invalid/Used voucher '{code}' from MAC: {mac}")
        return render_template(
            'portal.html',
            mac=mac,
            gw_address=gw_address,
            gw_port=gw_port,
            gw_id=gw_id,
            userurl=userurl,
            error=error_msg
        )

    # Check optional voucher expiration date
    if voucher.get("expire_at"):
        exp_at = voucher.get("expire_at")
        if exp_at.tzinfo is None:
            exp_at = exp_at.replace(tzinfo=timezone.utc)
        if exp_at <= now:
            logger.warning(f"Expired voucher code entry '{code}' from MAC: {mac}")
            return render_template(
                'portal.html',
                mac=mac, gw_address=gw_address, gw_port=gw_port,
                gw_id=gw_id, userurl=userurl, error="Vocha hii imepitiliza muda wake wa matumizi (Expired)."
            )

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
    
    # 3. Update Voucher Status to USED
    vouchers_col.update_one(
        {"code": code}, 
        {"$set": {"status": "USED", "used_by_mac": mac, "used_at": now}}
    )

    logger.info(f"Successful login: MAC {mac} redeemed voucher '{code}' for {duration_minutes} minutes.")

    # 4. Redirect URL to Gateway
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
    """ReyeeOS Background Auth Verification with strict expiration enforcement."""
    stage = request.args.get('stage', '').strip()
    mac = request.args.get('mac', '').strip().upper()
    now = datetime.now(timezone.utc)

    # 1. Handle explicit client logout request
    if stage == 'logout':
        if mac:
            sessions_col.delete_one({"_id": mac})
            tokens_col.delete_many({"mac": mac})
            logger.info(f"Client logged out: MAC {mac}")
        return Response("Auth: 0\n", mimetype='text/plain')

    # 2. Session Lookup
    session_doc = sessions_col.find_one({"_id": mac}) if mac else None

    if session_doc:
        exp = session_doc.get('expire_date')
        if exp and (exp.tzinfo is None or exp.tzinfo != timezone.utc):
            exp = exp.replace(tzinfo=timezone.utc)

        # Active session found -> Allow access
        if exp and exp > now:
            return Response("Auth: 1\n", mimetype='text/plain')

    # 3. Clean up expired tokens/sessions
    if mac:
        tokens_col.delete_many({"mac": mac})
        sessions_col.delete_one({"_id": mac, "expire_date": {"$lte": now}})

    logger.warning(f"WifiDog Auth denied/expired for MAC: '{mac}'. Returning Auth: 0")
    return Response("Auth: 0\n", mimetype='text/plain')


@app.route('/ping', methods=['GET'])
@app.route('/ping/', methods=['GET'])
@app.route('/wifidog/ping', methods=['GET'])
@app.route('/wifidog/ping/', methods=['GET'])
@app.route('/api/wifidog/ping', methods=['GET'])
@app.route('/api/wifidog/ping/', methods=['GET'])
def wifidog_ping():
    """Periodic Reyee AP Heartbeat."""
    gw_id = request.args.get('gw_id', 'Unknown')
    logger.debug(f"Ping received from Access Point Gateway ID: {gw_id}")
    return Response("Pong\n", mimetype='text/plain')


@app.route('/gw_message', methods=['GET'])
@app.route('/gw_message/', methods=['GET'])
@app.route('/wifidog/gw_message', methods=['GET'])
@app.route('/wifidog/gw_message/', methods=['GET'])
@app.route('/api/wifidog/gw_message', methods=['GET'])
@app.route('/api/wifidog/gw_message/', methods=['GET'])
def wifidog_gw_message():
    """Displays router-level status messages."""
    msg = request.args.get('message', 'Unknown Error')
    logger.warning(f"Gateway status message: {msg}")
    return f"""
    <div style="font-family:sans-serif; text-align:center; padding: 40px;">
        <h2>WifiDog Gateway Status</h2>
        <p>Message: <b>{msg}</b></p>
        <a href="/">Try Again</a>
    </div>
    """, 200


# ==========================================
# 📊 ADMIN PANEL & PACKAGE ROUTES
# ==========================================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PW:
            session['admin'] = True
            logger.info("Admin login successful.")
            return redirect('/admin')
        logger.warning(f"Failed admin login attempt from IP: {request.remote_addr}")
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
    
    # Packages
    packages = list(packages_col.find().sort("created_at", -1))
    
    # Vouchers and computed status
    vouchers = list(vouchers_col.find().sort("_id", -1).limit(100))
    for v in vouchers:
        status = v.get("status", "ACTIVE")
        exp_at = v.get("expire_at")
        
        if status == "REVOKED":
            v["computed_status"] = "REVOKED"
        elif status == "USED":
            v["computed_status"] = "USED"
        elif exp_at and exp_at.replace(tzinfo=timezone.utc if exp_at.tzinfo is None else exp_at.tzinfo) <= now:
            v["computed_status"] = "EXPIRED"
        elif status == "ACTIVE":
            v["computed_status"] = "UNUSED"
        else:
            v["computed_status"] = status

    # Sessions & Counts
    active_sessions = list(sessions_col.find({"expire_date": {"$gt": now}}))
    active_vouchers_count = vouchers_col.count_documents({"status": "ACTIVE"})
    used_vouchers_count = vouchers_col.count_documents({"status": "USED"})

    # Revenue Aggregation
    rev_agg = list(vouchers_col.aggregate([
        {"$match": {"status": "USED"}},
        {"$group": {"_id": None, "total": {"$sum": "$price"}}}
    ]))
    total_rev = rev_agg[0]['total'] if rev_agg else 0.0

    # User Summary Insights Aggregation
    user_pipeline = [
        {"$match": {"used_by_mac": {"$ne": None}}},
        {"$group": {
            "_id": "$used_by_mac",
            "vouchers_count": {"$sum": 1},
            "total_spend": {"$sum": "$price"}
        }}
    ]
    user_docs = list(vouchers_col.aggregate(user_pipeline))
    active_macs = set(s["_id"] for s in active_sessions)
    
    user_summary = []
    for u in user_docs:
        mac_addr = u["_id"]
        user_summary.append({
            "mac": mac_addr,
            "status": "online" if mac_addr in active_macs else "offline",
            "vouchers_count": u["vouchers_count"],
            "total_spend": u["total_spend"]
        })

    return render_template(
        'admin.html',
        packages=packages,
        vouchers=vouchers,
        active_sessions=active_sessions,
        active_vouchers_count=active_vouchers_count,
        used_vouchers_count=used_vouchers_count,
        active_sessions_count=len(active_sessions),
        total_revenue=f"{total_rev:,.0f}",
        user_summary=user_summary
    )


# --- PACKAGE MANAGEMENT ROUTES ---

@app.route('/admin/packages/create', methods=['POST'])
def create_package():
    if not session.get('admin'):
        return redirect('/admin/login')

    name = request.form.get('name', '').strip()
    price = float(request.form.get('price', 0))
    duration_value = int(request.form.get('duration', 1))
    duration_unit = request.form.get('unit', 'hours')
    badge = request.form.get('badge', '').strip()
    description = request.form.get('description', '').strip()

    package_doc = {
        "name": name,
        "price": price,
        "duration_value": duration_value,
        "duration_unit": duration_unit,
        "duration_minutes": calculate_duration_minutes(duration_value, duration_unit),
        "badge": badge,
        "description": description,
        "created_at": datetime.now(timezone.utc)
    }

    packages_col.insert_one(package_doc)
    logger.info(f"Admin created package: '{name}' (TZS {price})")
    return redirect('/admin#packages')


@app.route('/admin/packages/edit/<pkg_id>', methods=['POST'])
def edit_package(pkg_id):
    if not session.get('admin'):
        return redirect('/admin/login')

    name = request.form.get('name', '').strip()
    price = float(request.form.get('price', 0))
    duration_value = int(request.form.get('duration', 1))
    duration_unit = request.form.get('unit', 'hours')
    badge = request.form.get('badge', '').strip()
    description = request.form.get('description', '').strip()

    packages_col.update_one(
        {"_id": ObjectId(pkg_id)},
        {"$set": {
            "name": name,
            "price": price,
            "duration_value": duration_value,
            "duration_unit": duration_unit,
            "duration_minutes": calculate_duration_minutes(duration_value, duration_unit),
            "badge": badge,
            "description": description
        }}
    )
    logger.info(f"Admin updated package ID: {pkg_id}")
    return redirect('/admin#packages')


@app.route('/admin/packages/delete/<pkg_id>')
def delete_package(pkg_id):
    if not session.get('admin'):
        return redirect('/admin/login')

    packages_col.delete_one({"_id": ObjectId(pkg_id)})
    logger.info(f"Admin deleted package ID: {pkg_id}")
    return redirect('/admin#packages')


# --- VOUCHER MANAGEMENT ROUTES ---

@app.route('/admin/generate', methods=['POST'])
def generate_vouchers():
    if not session.get('admin'):
        return redirect('/admin/login')

    pkg_id = request.form.get('package_id')
    qty = int(request.form.get('quantity', 1))
    custom_code = request.form.get('custom_code', '').strip()
    expire_at_str = request.form.get('expire_at', '').strip()
    note = request.form.get('note', '').strip()

    # Look up package details
    pkg = packages_col.find_one({"_id": ObjectId(pkg_id)}) if pkg_id else None

    duration_minutes = pkg['duration_minutes'] if pkg else 360
    price = pkg['price'] if pkg else 500.0
    package_name = pkg['name'] if pkg else "Custom"

    expire_at = None
    if expire_at_str:
        try:
            expire_at = datetime.fromisoformat(expire_at_str).replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    existing_codes = set(v["code"] for v in vouchers_col.find({}, {"code": 1}))
    new_vouchers = []

    # Custom single code generation
    if custom_code and custom_code not in existing_codes:
        doc = {
            "code": custom_code,
            "package_name": package_name,
            "duration_minutes": duration_minutes,
            "price": price,
            "status": "ACTIVE",
            "note": note,
            "expire_at": expire_at,
            "created_at": datetime.now(timezone.utc)
        }
        new_vouchers.append(doc)
    else:
        # Batch random codes generation
        while len(new_vouchers) < qty and len(existing_codes) < 90000:
            code = f"{random.randint(0, 99999):05d}"
            if code not in existing_codes:
                existing_codes.add(code)
                doc = {
                    "code": code,
                    "package_name": package_name,
                    "duration_minutes": duration_minutes,
                    "price": price,
                    "status": "ACTIVE",
                    "note": note,
                    "expire_at": expire_at,
                    "created_at": datetime.now(timezone.utc)
                }
                new_vouchers.append(doc)

    if new_vouchers:
        vouchers_col.insert_many(new_vouchers)
        logger.info(f"Generated {len(new_vouchers)} new vouchers for package '{package_name}'")

    return render_template('print.html', vouchers=new_vouchers)


@app.route('/admin/voucher/revoke/<code>')
def revoke_voucher(code):
    if not session.get('admin'):
        return redirect('/admin/login')

    voucher = vouchers_col.find_one({"code": code})
    if voucher:
        # Revoke active MAC session if in use
        if voucher.get("used_by_mac"):
            mac = voucher["used_by_mac"]
            sessions_col.delete_one({"_id": mac})
            tokens_col.delete_many({"mac": mac})

        vouchers_col.update_one({"code": code}, {"$set": {"status": "REVOKED"}})
        logger.info(f"Admin revoked voucher code: {code}")

    return redirect('/admin#vouchers')


@app.route('/admin/voucher/unrevoke/<code>')
def unrevoke_voucher(code):
    if not session.get('admin'):
        return redirect('/admin/login')

    vouchers_col.update_one({"code": code}, {"$set": {"status": "ACTIVE"}})
    logger.info(f"Admin unrevoked voucher code: {code}")
    return redirect('/admin#vouchers')


# ==========================================
# 🚀 SERVER STARTUP
# ==========================================

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting HANS WIFI Portal server on port {port}")
    app.run(host='0.0.0.0', port=port)
