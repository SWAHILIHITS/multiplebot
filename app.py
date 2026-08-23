import os
import random
import secrets
import logging
import logging.config
from datetime import datetime, timedelta, timezone
from bson import ObjectId
from flask import Flask, render_template, request, redirect, session, Response, render_template_string
# Import MongoDB collection objects
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
    return request.form.get(key) or request.args.get(key) or default

def get_gateway_address():
    for key in ['gw_address', 'gw_ip', 'gwaddress', 'router_ip']:
        val = get_param(key)
        if val and val.replace('.', '').isdigit():
            return val.strip()
    return DEFAULT_GW_ADDRESS

def calculate_duration_minutes(val, unit):
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

def format_duration_human(duration_minutes):
    if not duration_minutes or duration_minutes <= 0:
        return "0 mins"
    if duration_minutes < 60:
        return f"{duration_minutes} mins"
    hours = duration_minutes / 60
    if hours < 24:
        return f"{hours:.1f}".rstrip('0').rstrip('.') + " hrs"
    days = hours / 24
    return f"{days:.1f}".rstrip('0').rstrip('.') + " days"

def format_report_time(dt_obj, current_time):
    if dt_obj.tzinfo is None:
        dt_obj = dt_obj.replace(tzinfo=timezone.utc)
    if dt_obj.date() == current_time.date() and dt_obj.hour == current_time.hour:
        return "Now"
    elif dt_obj.date() == current_time.date():
        return dt_obj.strftime("%H:00")
    else:
        return dt_obj.strftime("%Y-%m-%d %H:00")

def format_bytes(bytes_count):
    if not bytes_count or bytes_count <= 0:
        return "0 MB"
    mb = bytes_count / (1024 * 1024)
    if mb >= 1024:
        return f"{mb / 1024:.2f} GB"
    return f"{mb:.2f} MB"

def clean_mac(mac_str):
    if not mac_str or mac_str.startswith("UNKNOWN"):
        return mac_str
    return mac_str.replace(":", "").replace("-", "").strip().upper()

def get_client_mac():
    for key in ['mac', 'usermac', 'client_mac', 'client-mac']:
        val = get_param(key)
        if val:
            return clean_mac(val)
    return f"UNKNOWN:{secrets.token_hex(4).upper()}"


# ==========================================
# CAPTIVE PORTAL ROUTES
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
    mac = get_client_mac()
    gw_address = get_gateway_address()
    gw_port = get_param('gw_port', '2060')
    gw_id = get_param('gw_id', 'Gateway')
    userurl = get_param('url') or get_param('userurl') or 'http://www.google.com'

    logger.info(f"Portal page requested by MAC: {mac} via Gateway IP: {gw_address}")

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

    return render_template('portal.html', mac=mac, gw_address=gw_address, gw_port=gw_port, gw_id=gw_id, userurl=userurl), 200


@app.route('/favicon.ico')
def favicon():
    return Response(status=204)


@app.route('/login', methods=['POST'])
def process_login():
    code = request.form.get('voucher', '').strip()
    mac = clean_mac(get_client_mac())
    gw_address = get_gateway_address()
    gw_port = get_param('gw_port', '2060')
    gw_id = get_param('gw_id', 'Gateway')
    userurl = get_param('userurl') or get_param('url') or 'http://www.google.com'

    now = datetime.now(timezone.utc)

    try:
        voucher = vouchers_col.find_one({"code": code})
    except Exception as e:
        logger.error(f"Database error while checking voucher {code}: {str(e)}")
        voucher = None

    if not voucher or voucher.get("status") in ["USED", "REVOKED"]:
        error_msg = "Vocha hii siyo sahihi au ishatumika."
        if voucher and voucher.get("status") == "REVOKED":
            error_msg = "Vocha hii imesitishwa au kufutwa."
        
        return render_template('portal.html', mac=mac, gw_address=gw_address, gw_port=gw_port, gw_id=gw_id, userurl=userurl, error=error_msg)

    duration_minutes = voucher['duration_minutes']
    expire_date = now + timedelta(minutes=duration_minutes)

    token = secrets.token_hex(16)
    
    tokens_col.insert_one({
        "token": token, "mac": mac, "code": code,
        "expire_date": expire_date, "created_at": now
    })

    sessions_col.replace_one(
        {"_id": mac},
        {"_id": mac, "code": code, "used_time": now, "expire_date": expire_date, "duration_minutes": duration_minutes, "bytes_used": 0, "status": "ACTIVE"},
        upsert=True
    )
    
    vouchers_col.update_one(
        {"code": code}, 
        {"$set": {"status": "USED", "used_by_mac": mac, "used_at": now}}
    )

    auth_action_url = f"http://{gw_address}:{gw_port}/wifidog/auth?token={token}"

    success_html = f"""
    <!DOCTYPE html>
    <html lang="sw">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Connecting...</title>
        <style>
            body {{ background: #0f172a; color: #fff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; text-align: center; }}
            .loader {{ border: 4px solid rgba(255,255,255,0.1); border-left-color: #10b981; border-radius: 50%; width: 50px; height: 50px; animation: spin 1s linear infinite; margin: 0 auto 20px; }}
            @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
            .card {{ background: #1e293b; padding: 40px; border-radius: 20px; box-shadow: 0 20px 40px rgba(0,0,0,0.4); max-width: 90%; width: 400px; }}
            h2 {{ margin-top: 0; color: #34d399; font-size: 24px; }}
            p {{ color: #94a3b8; font-size: 15px; margin-bottom: 30px; line-height: 1.5; }}
            .btn-manual {{ display: inline-block; padding: 10px 20px; background: rgba(255,255,255,0.05); color: #cbd5e1; border-radius: 8px; text-decoration: none; font-size: 14px; transition: background 0.2s; }}
            .btn-manual:hover {{ background: rgba(255,255,255,0.1); }}
        </style>
        <script>
            setTimeout(function() {{ window.location.href = "{auth_action_url}"; }}, 2500);
        </script>
    </head>
    <body>
        <div class="card">
            <div class="loader"></div>
            <h2>Imekubali! 🚀</h2>
            <p>Vocha yako ni sahihi.<br>Tafadhali subiri kidogo tunakuunganisha na mtandao...</p>
            <a href="{auth_action_url}" class="btn-manual">Bofya hapa kama inachelewa</a>
        </div>
    </body>
    </html>
    """
    return render_template_string(success_html)

def extract_byte_count(req):
    """
    Extracts incoming and outgoing bytes directly from WifiDog telemetry payload.
    Checks both GET (req.args) and POST (req.form) via req.values.
    """
    incoming = 0
    outgoing = 0

    # Extended list of keys used by different router brands (Reyee, Mikrotik, OpenWrt, etc.)
    download_keys = ['incoming', 'incoming_bytes', 'download', 'bytes_in', 'rx_bytes', 'bytes-in', 'rx', 'down']
    upload_keys = ['outgoing', 'outgoing_bytes', 'upload', 'bytes_out', 'tx_bytes', 'bytes-out', 'tx', 'up']

    # Log the payload to see exactly what the router is sending
    payload = req.values.to_dict()
    if payload.get('stage') == 'counters' or any(k in payload for k in download_keys):
        logger.info(f"Telemetry Payload Received: {payload}")

    for key in download_keys:
        val = req.values.get(key)
        if val is not None:
            try:
                incoming = int(str(val).strip())
                if incoming > 0: break
            except ValueError:
                continue

    for key in upload_keys:
        val = req.values.get(key)
        if val is not None:
            try:
                outgoing = int(str(val).strip())
                if outgoing > 0: break
            except ValueError:
                continue

    return incoming + outgoing

def update_session_data_usage(mac, total_bytes, session_doc):
    """
    Safely increments data consumption. Prevents data from resetting to 0 
    if the router restarts its counters upon user reconnect.
    """
    if total_bytes <= 0:
        return

    current_session_bytes = session_doc.get("current_session_bytes", 0)
    accumulated_bytes = session_doc.get("accumulated_bytes", 0)
    
    # If the router's counter is lower than last time, it means the router restarted
    if total_bytes < current_session_bytes:
        accumulated_bytes += current_session_bytes
        current_session_bytes = total_bytes
    else:
        current_session_bytes = total_bytes
        
    grand_total = accumulated_bytes + current_session_bytes
    
    # Update Session Database
    sessions_col.update_one(
        {"_id": mac}, 
        {"$set": {
            "current_session_bytes": current_session_bytes, 
            "accumulated_bytes": accumulated_bytes,
            "bytes_used": grand_total
        }}
    )
    
    # Update Voucher Database
    voucher_code = session_doc.get("code")
    if voucher_code:
        vouchers_col.update_one(
            {"code": voucher_code}, 
            {"$set": {"data_consumed_bytes": grand_total}}
        )

# ==========================================
# WIFIDOG AUTH CHECK (TELEMETRY)
# ==========================================

@app.route('/auth', methods=['GET', 'POST'])
@app.route('/auth/', methods=['GET', 'POST'])
@app.route('/wifidog/auth', methods=['GET', 'POST'])
@app.route('/wifidog/auth/', methods=['GET', 'POST'])
@app.route('/api/wifidog/auth', methods=['GET', 'POST'])
@app.route('/api/wifidog/auth/', methods=['GET', 'POST'])
def wifidog_auth_check():
    token = request.values.get('token', '').strip()
    stage = request.values.get('stage', '').strip()
    mac = clean_mac(request.values.get('mac', ''))
    now = datetime.now(timezone.utc)

    if stage == 'logout':
        if mac:
            sessions_col.delete_one({"_id": mac})
            tokens_col.delete_many({"mac": mac})
        return Response("Auth: 0\n", mimetype='text/plain')

    if not mac and token:
        token_doc = tokens_col.find_one({"token": token})
        if token_doc:
            mac = clean_mac(token_doc.get("mac", ""))

    if not mac:
        return Response("Auth: 0\n", mimetype='text/plain')

    session_doc = sessions_col.find_one({"_id": mac})

    if session_doc:
        exp = session_doc.get('expire_date')
        if exp and exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)

        if exp and exp > now:
            # Extract data and run the safety update function
            total_bytes = extract_byte_count(request)
            update_session_data_usage(mac, total_bytes, session_doc)
            
            return Response("Auth: 1\n", mimetype='text/plain')

    tokens_col.delete_many({"mac": mac})
    sessions_col.delete_one({"_id": mac, "expire_date": {"$lte": now}})
    return Response("Auth: 0\n", mimetype='text/plain')


@app.route('/ping', methods=['GET', 'POST'])
@app.route('/ping/', methods=['GET', 'POST'])
@app.route('/wifidog/ping', methods=['GET', 'POST'])
@app.route('/wifidog/ping/', methods=['GET', 'POST'])
@app.route('/api/wifidog/ping', methods=['GET', 'POST'])
@app.route('/api/wifidog/ping/', methods=['GET', 'POST'])
def wifidog_ping():
    mac = clean_mac(request.values.get('mac', ''))
    
    # Check if this router sends user telemetry on the /ping route
    total_bytes = extract_byte_count(request)

    if mac and total_bytes > 0:
        session_doc = sessions_col.find_one({"_id": mac})
        if session_doc:
            update_session_data_usage(mac, total_bytes, session_doc)
                
    return Response("Pong\n", mimetype='text/plain')


@app.errorhandler(404)
def handle_404(e):
    path = request.path.lower()
    if 'favicon.ico' in path: return Response(status=204)
    if 'ping' in path: return wifidog_ping()
    if path.startswith('/wifidog') or path.startswith('/api/wifidog') or 'auth' in path:
        return Response("Not Found\n", status=404, mimetype='text/plain')
    return captive_login_page()


# ==========================================
# ADMIN DASHBOARD ROUTES
# ==========================================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PW:
            session['admin'] = True
            return redirect('/admin')
        return render_template('admin_login.html', error="Nenosiri sio sahihi!")
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect('/admin/login')

@app.route('/admin')
def admin_dashboard():
    if not session.get('admin'):
        return redirect('/admin/login')

    now = datetime.now(timezone.utc)
    start_of_today = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    start_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    active_sessions_cursor = list(sessions_col.find({"expire_date": {"$gt": now}}))
    active_sessions_map = {s["_id"]: s for s in active_sessions_cursor}

    packages = list(packages_col.find().sort("created_at", -1))
    vouchers = list(vouchers_col.find().sort("_id", -1).limit(100))

    active_vouchers_count = 0
    used_vouchers_count = 0

    for v in vouchers:
        status = v.get("status", "ACTIVE")
        exp_at = v.get("expire_at")
        
        if status == "REVOKED":
            v["computed_status"] = "REVOKED"
        elif status == "USED":
            v["computed_status"] = "USED"
            used_vouchers_count += 1
        elif exp_at and exp_at.replace(tzinfo=timezone.utc if exp_at.tzinfo is None else exp_at.tzinfo) <= now:
            v["computed_status"] = "EXPIRED"
        elif status == "ACTIVE":
            v["computed_status"] = "UNUSED"
            active_vouchers_count += 1
        else:
            v["computed_status"] = status

    used_vouchers = list(vouchers_col.find({"used_by_mac": {"$ne": None}}).sort("used_at", -1))

    mac_agg = {}
    detailed_report = []
    total_bytes_consumed = 0

    for v in used_vouchers:
        mac = v.get("used_by_mac")
        if not mac: continue
        
        price = float(v.get("price", 0.0))
        used_at = v.get("used_at", now)
        is_online = mac in active_sessions_map
        connection_status = "online" if is_online else "offline"

        if mac not in mac_agg:
            mac_agg[mac] = {"mac": mac, "status": connection_status, "vouchers_count": 0, "total_spend": 0.0}
        
        mac_agg[mac]["vouchers_count"] += 1
        mac_agg[mac]["total_spend"] += price
        if is_online: mac_agg[mac]["status"] = "online"

        bytes_used = v.get("data_consumed_bytes", 0) or active_sessions_map.get(mac, {}).get("bytes_used", 0)
        total_bytes_consumed += bytes_used
        duration_mins = v.get("duration_minutes", 0)

        detailed_report.append({
            "mac": mac,
            "voucher_code": v.get("code"),
            "voucher_status": v.get("status", "USED"),
            "connection_status": connection_status,
            "time_label": format_report_time(used_at, now),
            "duration_formatted": format_duration_human(duration_mins),
            "data_consumed": format_bytes(bytes_used)
        })

    user_summary = list(mac_agg.values())

    today_rev_agg = list(vouchers_col.aggregate([
        {"$match": {"status": "USED", "used_at": {"$gte": start_of_today}}},
        {"$group": {"_id": None, "total": {"$sum": "$price"}}}
    ]))
    today_revenue = today_rev_agg[0]['total'] if today_rev_agg else 0.0

    month_rev_agg = list(vouchers_col.aggregate([
        {"$match": {"status": "USED", "used_at": {"$gte": start_of_month}}},
        {"$group": {"_id": None, "total": {"$sum": "$price"}}}
    ]))
    monthly_revenue = month_rev_agg[0]['total'] if month_rev_agg else 0.0

    # Dummy settings object to prevent template crash if removed from db
    settings = {"gw_address": DEFAULT_GW_ADDRESS, "gw_port": "2060", "gw_id": "Gateway"}

    return render_template(
        'admin.html',
        packages=packages,
        vouchers=vouchers,
        active_sessions=active_sessions_cursor,
        user_summary=user_summary,
        detailed_report=detailed_report,
        today_revenue=f"{today_revenue:,.0f}",
        monthly_revenue=f"{monthly_revenue:,.0f}",
        total_data_consumed=format_bytes(total_bytes_consumed),
        online_users_count=len(active_sessions_map),
        active_vouchers_count=active_vouchers_count,
        settings=settings
    )

@app.route('/admin/packages/create', methods=['POST'])
def create_package():
    if not session.get('admin'): return redirect('/admin/login')
    name = request.form.get('name', '').strip()
    price = float(request.form.get('price', 0))
    duration_value = int(request.form.get('duration', 1))
    duration_unit = request.form.get('unit', 'hours')
    badge = request.form.get('badge', '').strip()
    description = request.form.get('description', '').strip()

    package_doc = {
        "name": name, "price": price, "duration_value": duration_value,
        "duration_unit": duration_unit, "duration_minutes": calculate_duration_minutes(duration_value, duration_unit),
        "badge": badge, "description": description, "created_at": datetime.now(timezone.utc)
    }
    packages_col.insert_one(package_doc)
    return redirect('/admin#packages')

@app.route('/admin/packages/edit/<pkg_id>', methods=['POST'])
def edit_package(pkg_id):
    if not session.get('admin'): return redirect('/admin/login')
    packages_col.update_one(
        {"_id": ObjectId(pkg_id)},
        {"$set": {
            "name": request.form.get('name', '').strip(),
            "price": float(request.form.get('price', 0)),
            "duration_value": int(request.form.get('duration', 1)),
            "duration_unit": request.form.get('unit', 'hours'),
            "duration_minutes": calculate_duration_minutes(request.form.get('duration', 1), request.form.get('unit', 'hours')),
            "badge": request.form.get('badge', '').strip(),
            "description": request.form.get('description', '').strip()
        }}
    )
    return redirect('/admin#packages')

@app.route('/admin/packages/delete/<pkg_id>')
def delete_package(pkg_id):
    if not session.get('admin'): return redirect('/admin/login')
    packages_col.delete_one({"_id": ObjectId(pkg_id)})
    return redirect('/admin#packages')

@app.route('/admin/generate', methods=['POST'])
def generate_vouchers():
    if not session.get('admin'): return redirect('/admin/login')
    pkg_id = request.form.get('package_id')
    qty = int(request.form.get('quantity', 1))
    custom_code = request.form.get('custom_code', '').strip()
    expire_at_str = request.form.get('expire_at', '').strip()
    note = request.form.get('note', '').strip()

    pkg = packages_col.find_one({"_id": ObjectId(pkg_id)}) if pkg_id else None
    duration_minutes = pkg['duration_minutes'] if pkg else 360
    price = pkg['price'] if pkg else 500.0
    package_name = pkg['name'] if pkg else "Custom"
    expire_at = datetime.fromisoformat(expire_at_str).replace(tzinfo=timezone.utc) if expire_at_str else None

    existing_codes = set(v["code"] for v in vouchers_col.find({}, {"code": 1}))
    new_vouchers = []

    if custom_code and custom_code not in existing_codes:
        new_vouchers.append({
            "code": custom_code, "package_name": package_name, "duration_minutes": duration_minutes,
            "price": price, "status": "ACTIVE", "note": note, "expire_at": expire_at, "created_at": datetime.now(timezone.utc)
        })
    else:
        while len(new_vouchers) < qty and len(existing_codes) < 90000:
            code = f"{random.randint(0, 99999):05d}"
            if code not in existing_codes:
                existing_codes.add(code)
                new_vouchers.append({
                    "code": code, "package_name": package_name, "duration_minutes": duration_minutes,
                    "price": price, "status": "ACTIVE", "note": note, "expire_at": expire_at, "created_at": datetime.now(timezone.utc)
                })

    if new_vouchers:
        vouchers_col.insert_many(new_vouchers)

    return render_template('print.html', vouchers=new_vouchers)

@app.route('/admin/voucher/delete/<code>')
def delete_voucher(code):
    # Permanently delete unused vouchers
    db.vouchers.delete_one({"code": code, "status": "UNUSED"})
    return redirect('/admin#vouchers')

@app.route('/admin/voucher/revoke/<code>')
def revoke_voucher(code):
    voucher = db.vouchers.find_one({"code": code})
    if voucher and voucher.get("status") == "USED":
        # Block internet usage and update status
        db.vouchers.update_one({"code": code}, {"$set": {"status": "REVOKED"}})
        disconnect_router_user(voucher.get("used_by_mac"))
    return redirect('/admin#vouchers')

@app.route('/admin/voucher/unrevoke/<code>')
def unrevoke_voucher(code):
    voucher = db.vouchers.find_one({"code": code})
    if voucher and voucher.get("status") == "REVOKED":
        # Restore usage and allow internet access
        db.vouchers.update_one({"code": code}, {"$set": {"status": "USED"}})
        reauthorize_router_user(voucher.get("used_by_mac"))
    return redirect('/admin#vouchers')
                        
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
