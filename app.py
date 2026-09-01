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
# Make the session expire after 30 minutes of inactivity
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

# Prevent JavaScript from reading the session cookie (XSS protection)
app.config['SESSION_COOKIE_HTTPONLY'] = True

# Ensure cookies are only sent over HTTPS (Enable this in production!)
# app.config['SESSION_COOKIE_SECURE'] = True 

# Prevent cookies from being sent in cross-site requests (CSRF protection)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
# --- HELPER FUNCTIONS ---
def get_param(key, default=""):
    return request.form.get(key) or request.args.get(key) or default
    
def format_dd_hh_mm(total_minutes):
    """Formats total minutes into dd:hh:mm format string."""
    if not total_minutes or total_minutes < 0:
        return "00:00:00"
    days = total_minutes // 1440
    remaining_mins = total_minutes % 1440
    hours = remaining_mins // 60
    mins = remaining_mins % 60
    return f"{days:02d}:{hours:02d}:{mins:02d}"
    
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

def format_time_window(start_time, current_time):
    if not start_time:
        return "Unknown"
    
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
        
    local_start = start_time + timedelta(hours=3)
    local_now = current_time + timedelta(hours=3)
    
    if local_start.date() == local_now.date():
        if local_start.hour == local_now.hour:
            return "Now"
        else:
            return local_start.strftime("%H:%M")
    else:
        return local_start.strftime("%Y-%m-%d %H:%M")

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

def calculate_voucher_consumed_minutes(voucher, db, now):
    code = voucher.get("code")
    package_id = voucher.get("package_id")
    
    pause_offline = False
    if package_id:
        pkg = db.packages.find_one({"_id": package_id})
        if pkg:
            pause_offline = pkg.get("pause_on_user_offline", False)
            
    connection_logs_col = db.connection_logs
    
    heartbeat_doc = db.system_status.find_one({"_id": "gateway_heartbeat"})
    effective_now = now
    if heartbeat_doc and heartbeat_doc.get("last_seen"):
        last_seen = heartbeat_doc.get("last_seen")
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)
        if (now - last_seen).total_seconds() > 180:
            effective_now = last_seen  

    if pause_offline:
        voucher_logs = list(connection_logs_col.find({"code": code}))
        return sum(l.get("session_used_minutes", 0) for l in voucher_logs)
    else:
        used_at = voucher.get("used_at")
        if not used_at:
            return 0
        if used_at.tzinfo is None:
            used_at = used_at.replace(tzinfo=timezone.utc)
            
        # FREEZE TIME VISUALLY IF CURRENTLY REVOKED
        if voucher.get("status") == "REVOKED" and voucher.get("revoked_at"):
            revoked_at = voucher.get("revoked_at")
            if revoked_at.tzinfo is None: revoked_at = revoked_at.replace(tzinfo=timezone.utc)
            return int(max(0, (revoked_at - used_at).total_seconds() / 60.0))
            
        return int(max(0, (effective_now - used_at).total_seconds() / 60.0))

@app.route('/api/log-domain', methods=['POST'])
def log_domain():
    mac = clean_mac(request.form.get('mac'))
    domain = request.form.get('domain')
    
    if not mac or not domain:
        return Response("Invalid data", status=400)
    
    db = vouchers_col.database
    
    active_session = sessions_col.find_one({"_id": mac})
    if active_session and active_session.get("current_log_id"):
        log_id = active_session.get("current_log_id")
        
        db.connection_logs.update_one(
            {"_id": log_id},
            {"$addToSet": {"visited_sites": domain}}
        )
        return Response("Logged", status=200)
        
    return Response("Session not found", status=404)

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
            db = vouchers_col.database
            voucher_code = None
            
            active_session = sessions_col.find_one({"_id": mac})
            if active_session:
                voucher_code = active_session.get("code")
            else:
                recent_voucher = vouchers_col.find_one(
                    {"used_by_mac": mac, "status": "USED"}, 
                    sort=[("used_at", -1)]
                )
                if recent_voucher:
                    consumed = calculate_voucher_consumed_minutes(recent_voucher, db, now)
                    if consumed < recent_voucher.get("duration_minutes", 0):
                        voucher_code = recent_voucher.get("code")
                        
            if voucher_code:
                voucher = vouchers_col.find_one({"code": voucher_code})
                if voucher:
                    consumed = calculate_voucher_consumed_minutes(voucher, db, now)
                    duration = voucher.get("duration_minutes", 0)
                    
                    if consumed < duration and voucher.get("status") != "REVOKED":
                        logger.info(f"Valid time remaining for MAC: {mac}. Triggering auto-reconnect.")
                        
                        connection_logs_col = db.connection_logs
                        session_log_id = ObjectId()
                        connection_logs_col.insert_one({
                            "_id": session_log_id,
                            "mac": mac,
                            "code": voucher_code,
                            "start_time": now,
                            "last_active": now,
                            "session_used_minutes": 0,
                            "visited_sites": ["google.com", "whatsapp.com"]
                        })
                        
                        session_expire_date = voucher.get("session_expire_date") or (now + timedelta(days=365))
                        
                        sessions_col.replace_one(
                            {"_id": mac},
                            {
                                "_id": mac, "code": voucher_code, "used_time": now, 
                                "expire_date": session_expire_date, "duration_minutes": duration, 
                                "bytes_used": 0, "status": "ACTIVE", "current_log_id": session_log_id
                            },
                            upsert=True
                        )

                        token = secrets.token_hex(16)
                        tokens_col.insert_one({
                            "token": token,
                            "mac": mac,
                            "code": voucher_code,
                            "expire_date": session_expire_date,
                            "created_at": now
                        })
                        
                        auth_action_url = f"http://{gw_address}:{gw_port}/wifidog/auth?token={token}"
                        return redirect(auth_action_url, code=302)
                        
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
    db = vouchers_col.database

    try:
        voucher = vouchers_col.find_one({"code": code})
    except Exception as e:
        logger.error(f"Database error while checking voucher {code}: {str(e)}")
        voucher = None

    is_valid = False
    if voucher:
        duration_minutes = voucher['duration_minutes']
        session_expire_date = voucher.get("session_expire_date") or (now + timedelta(days=365))

        if voucher.get("status") == "UNUSED":
            # ATOMIC VOUCHER CLAIM TO PREVENT RACE CONDITIONS
            claimed = vouchers_col.find_one_and_update(
                {"code": code, "status": "UNUSED"},
                {"$set": {
                    "status": "USED",
                    "used_by_mac": mac,
                    "used_at": now,
                    "session_expire_date": session_expire_date,
                    "expire_at": None
                }},
                return_document=True
            )
            if claimed:
                is_valid = True
                voucher = claimed
        elif voucher.get("status") == "USED" and voucher.get("used_by_mac") == mac:
            consumed = calculate_voucher_consumed_minutes(voucher, db, now)
            if consumed < duration_minutes:
                is_valid = True

    if not is_valid:
        error_msg = "Vocha hii siyo sahihi au ishatumika."
        if voucher:
            if voucher.get("status") == "REVOKED":
                error_msg = "Vocha hii imesitishwa au kufutwa."
            elif voucher.get("status") == "USED" and voucher.get("used_by_mac") != mac:
                error_msg = "Vocha hii inatumiwa na kifaa kingine."
            elif voucher.get("status") == "USED":
                error_msg = "Muda wa vocha hii umekwisha."
                
        return render_template('portal.html', mac=mac, gw_address=gw_address, gw_port=gw_port, gw_id=gw_id, userurl=userurl, error=error_msg)

    duration_minutes = voucher['duration_minutes']
    session_expire_date = voucher.get("session_expire_date") or (now + timedelta(days=365))

    connection_logs_col = db.connection_logs
    session_log_id = ObjectId()
    connection_logs_col.insert_one({
        "_id": session_log_id,
        "mac": mac,
        "code": code,
        "start_time": now,
        "last_active": now,
        "session_used_minutes": 0,
        "visited_sites": ["google.com", "whatsapp.com"]
    })

    token = secrets.token_hex(16)
    
    tokens_col.insert_one({
        "token": token, "mac": mac, "code": code,
        "expire_date": session_expire_date, "created_at": now
    })

    sessions_col.replace_one(
        {"_id": mac},
        {
            "_id": mac, "code": code, "used_time": now, 
            "expire_date": session_expire_date, "duration_minutes": duration_minutes, 
            "bytes_used": 0, "status": "ACTIVE", "current_log_id": session_log_id
        },
        upsert=True
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
            body {{ background: #0f172a; color: #fff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; text-align: center; }}
            .loader {{ border: 4px solid rgba(255,255,255,0.1); border-left-color: #10b981; border-radius: 50%; width: 50px; height: 50px; animation: spin 1s linear infinite; margin: 0 auto 20px; }}
            @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
            .card {{ background: #1e293b; padding: 40px; border-radius: 20px; box-shadow: 0 20px 40px rgba(0,0,0,0.4); max-width: 90%; width: 400px; }}
            h2 {{ margin-top: 0; color: #34d399; font-size: 24px; }}
            p {{ color: #94a3b8; font-size: 15px; margin-bottom: 30px; line-height: 1.5; }}
            .btn-manual {{ display: inline-block; padding: 10px 20px; background: rgba(255,255,255,0.05); color: #cbd5e1; border-radius: 8px; text-decoration: none; font-size: 14px; transition: background 0.2s; }}
            .btn-manual:hover {{ background: rgba(255,255,255,0.1); }}
        </style>
        <script>
            setTimeout(function() {{ window.location.href = "{auth_action_url}"; }}, 100);
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
    incoming = 0
    outgoing = 0
    download_keys = ['incoming', 'incoming_bytes', 'download', 'bytes_in', 'rx_bytes', 'bytes-in', 'rx', 'down']
    upload_keys = ['outgoing', 'outgoing_bytes', 'upload', 'bytes_out', 'tx_bytes', 'bytes-out', 'tx', 'up']
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
    if total_bytes <= 0: return

    current_session_bytes = session_doc.get("current_session_bytes", 0)
    accumulated_bytes = session_doc.get("accumulated_bytes", 0)
    
    if total_bytes < current_session_bytes:
        accumulated_bytes += current_session_bytes
        current_session_bytes = total_bytes
    else:
        current_session_bytes = total_bytes
        
    grand_total = accumulated_bytes + current_session_bytes
    
    sessions_col.update_one(
        {"_id": mac}, 
        {"$set": {
            "current_session_bytes": current_session_bytes, 
            "accumulated_bytes": accumulated_bytes,
            "bytes_used": grand_total
        }}
    )
    
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
    db = vouchers_col.database

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
        voucher_code = session_doc.get("code")
        voucher = vouchers_col.find_one({"code": voucher_code})
        
        if voucher:
            # STOP INTERNET IMMEDIATELY IF REVOKED
            if voucher.get("status") == "REVOKED":
                sessions_col.delete_one({"_id": mac})
                tokens_col.delete_many({"mac": mac})
                return Response("Auth: 0\n", mimetype='text/plain')
                
            duration_minutes = voucher.get("duration_minutes", 0)
            total_used_mins = calculate_voucher_consumed_minutes(voucher, db, now)

            if total_used_mins < duration_minutes:
                total_bytes = extract_byte_count(request)
                update_session_data_usage(mac, total_bytes, session_doc)
                
                log_id = session_doc.get("current_log_id")
                if log_id:
                    log_doc = db.connection_logs.find_one({"_id": log_id})
                    if log_doc:
                        start_time = log_doc.get("start_time", now)
                        if now.tzinfo is not None and start_time.tzinfo is None:
                            start_time = start_time.replace(tzinfo=now.tzinfo)
                        elif now.tzinfo is None and start_time.tzinfo is not None:
                            now = now.replace(tzinfo=start_time.tzinfo)
                        elapsed_mins = max(0, int((now - start_time).total_seconds() / 60.0))
                        db.connection_logs.update_one(
                            {"_id": log_id},
                            {"$set": {"last_active": now, "session_used_minutes": elapsed_mins}}
                        )

                return Response("Auth: 1\n", mimetype='text/plain')

    tokens_col.delete_many({"mac": mac})
    sessions_col.delete_one({"_id": mac})
    return Response("Auth: 0\n", mimetype='text/plain')


@app.route('/ping', methods=['GET', 'POST'])
@app.route('/ping/', methods=['GET', 'POST'])
@app.route('/wifidog/ping', methods=['GET', 'POST'])
@app.route('/wifidog/ping/', methods=['GET', 'POST'])
@app.route('/api/wifidog/ping', methods=['GET', 'POST'])
@app.route('/api/wifidog/ping/', methods=['GET', 'POST'])
def wifidog_ping():
    mac = clean_mac(request.values.get('mac', ''))
    now = datetime.now(timezone.utc)
    db = vouchers_col.database
    
    db.system_status.update_one(
        {"_id": "gateway_heartbeat"},
        {"$set": {"last_seen": now}},
        upsert=True
    )
    
    total_bytes = extract_byte_count(request)

    if mac and total_bytes > 0:
        session_doc = sessions_col.find_one({"_id": mac})
        if session_doc:
            update_session_data_usage(mac, total_bytes, session_doc)
            
            log_id = session_doc.get("current_log_id")
            if log_id:
                log_doc = db.connection_logs.find_one({"_id": log_id})
                if log_doc:
                    start_time = log_doc.get("start_time", now)
                    elapsed_mins = max(0, int((now - start_time).total_seconds() / 60.0))
                    db.connection_logs.update_one(
                        {"_id": log_id},
                        {"$set": {"last_active": now, "session_used_minutes": elapsed_mins}}
                    )
                
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
from werkzeug.security import generate_password_hash, check_password_hash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/admin/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    db = vouchers_col.database
    # Check if we have an admin password in the database
    admin_doc = db.system_status.find_one({"_id": "admin_credentials"})
    has_password = admin_doc is not None and "password_hash" in admin_doc

    if request.method == 'POST':
        action = request.form.get('action')
        
        # SETUP MODE: Creating the first password
        if action == 'setup' and not has_password:
            new_password = request.form.get('password')
            hashed = generate_password_hash(new_password)
            db.system_status.update_one(
                {"_id": "admin_credentials"},
                {"$set": {"password_hash": hashed}},
                upsert=True
            )
            session['admin'] = True
            return redirect('/admin')
            
        # LOGIN MODE: Authenticating existing password
        elif action == 'login' and has_password:
            password_attempt = request.form.get('password')
            if check_password_hash(admin_doc["password_hash"], password_attempt):
                session['admin'] = True
                return redirect('/admin')
            else:
                return render_template('admin_login.html', error="Invalid credentials", setup_mode=False)

    # Render login page (pass setup_mode=True if no password exists yet)
    return render_template('admin_login.html', setup_mode=not has_password)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect('/admin/login')

# NEW ROUTE: Change Password from Settings
@app.route('/admin/settings/password', methods=['POST'])
def update_password():
    if not session.get('admin'): 
        return redirect('/admin/login')
    
    db = vouchers_col.database
    admin_doc = db.system_status.find_one({"_id": "admin_credentials"})
    
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    
    # Verify the current password matches the hash before allowing a change
    if admin_doc and check_password_hash(admin_doc.get("password_hash", ""), current_password):
        new_hashed = generate_password_hash(new_password)
        db.system_status.update_one(
            {"_id": "admin_credentials"},
            {"$set": {"password_hash": new_hashed}}
        )
        return redirect('/admin?pwd_msg=success#settings')
    else:
        return redirect('/admin?pwd_msg=error#settings')

def cleanup_expired_vouchers():
    now = datetime.now(timezone.utc)
    vouchers_col.delete_many({
        "status": "UNUSED",
        "expire_at": {"$ne": None, "$lte": now}
    })

@app.route('/admin')
def admin_dashboard():
    if not session.get('admin'):
        return redirect('/admin/login')
    cleanup_expired_vouchers()
    now = datetime.now(timezone.utc)
    db = vouchers_col.database
    connection_logs_col = db.connection_logs

    search_query = request.args.get('q', '').strip()

    voucher_filter = {}
    if search_query:
        voucher_filter = {
            "$or": [
                {"code": {"$regex": search_query, "$options": "i"}},
                {"used_by_mac": {"$regex": search_query, "$options": "i"}},
                {"phone_number": {"$regex": search_query, "$options": "i"}},
                {"note": {"$regex": search_query, "$options": "i"}}
            ]
        }

    active_sessions_cursor = list(sessions_col.find())
    active_sessions_map = {s["_id"]: s for s in active_sessions_cursor}
    start_of_today = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    start_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    
    packages = list(packages_col.find().sort("created_at", -1))
    packages_map = {str(p["_id"]): p for p in packages}
    
    vouchers = list(vouchers_col.find(voucher_filter).sort("_id", -1))
    used_vouchers = list(vouchers_col.find({"used_by_mac": {"$ne": None}}).sort("used_at", -1))
    active_vouchers_count = 0
    
    for v in vouchers:
        status = v.get("status", "UNUSED")
        used_by_mac = v.get("used_by_mac")
        
        pkg_id = v.get("package_id")
        pkg = packages_map.get(str(pkg_id)) if pkg_id else None
        v["computed_package_name"] = pkg.get("name", "Custom") if pkg else "Custom"
        
        if not used_by_mac or status == "UNUSED":
            v["computed_status"] = "UNUSED"
        else:
            consumed = calculate_voucher_consumed_minutes(v, db, now)
            duration = v.get("duration_minutes", 0)
            if consumed >= duration:
                v["computed_status"] = "EXPIRED"
            else:
                if status == "REVOKED":
                    v["computed_status"] = "REVOKED"
                else:
                    v["computed_status"] = "ACTIVE"
                    active_vouchers_count += 1

    mac_agg = {}
    for v in used_vouchers:
        mac = v.get("used_by_mac")
        if not mac: continue
        is_online = mac in active_sessions_map
        connection_status = "online" if is_online else "offline"
        if mac not in mac_agg:
            mac_agg[mac] = {"mac": mac, "status": connection_status, "vouchers_count": 0, "total_spend": 0.0}
        mac_agg[mac]["vouchers_count"] += 1
        mac_agg[mac]["total_spend"] += float(v.get("price", 0.0))
    user_summary = list(mac_agg.values())

    detailed_report = []
    all_logs = list(connection_logs_col.find().sort("start_time", -1).limit(300))
    
    seen_vouchers = {}
    
    for log in all_logs:
        mac = log.get("mac")
        code = log.get("code")
        start_time = log.get("start_time")
        
        if not code:
            continue
            
        if start_time and start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
            
        if code in seen_vouchers:
            latest_time = seen_vouchers[code]
            if latest_time and start_time:
                diff_seconds = (latest_time - start_time).total_seconds()
                if diff_seconds < 60:
                    connection_logs_col.delete_one({"_id": log.get("_id")})
                    continue
        else:
            seen_vouchers[code] = start_time
            
        voucher = vouchers_col.find_one({"code": code})
        if not voucher: 
            continue
            
        pkg_id = voucher.get("package_id")
        pkg = packages_map.get(str(pkg_id)) if pkg_id else None
        package_name = pkg.get("name", "Custom") if pkg else "Custom"
        pause_offline = pkg.get("pause_on_user_offline", False) if pkg else False
            
        phone_number = voucher.get("phone_number") or active_sessions_map.get(mac, {}).get("phone_number", "-")
        duration_mins = voucher.get("duration_minutes", 0)
        
        session_used_mins = log.get("session_used_minutes", 0)
        total_used_mins = calculate_voucher_consumed_minutes(voucher, db, now)

        detailed_report.append({
            "mac": mac,
            "phone_number": phone_number,
            "voucher_code": code,
            "package_name": package_name,
            "time_label": format_time_window(start_time, now),
            "time_raw": start_time.strftime("%Y%m%d%H%M%S") if start_time else "0",
            "duration_formatted": f"{duration_mins} Mins",
            "session_used_mins": f"{session_used_mins}",
            "total_used_ddhhmm": format_dd_hh_mm(total_used_mins),
            "offline_policy": "PAUSE (OFF)" if pause_offline else "CONTINUE (ON)",
            "visited_sites": ", ".join(log.get("visited_sites", ["google.com"]))
        })

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

    settings = {"gw_address": DEFAULT_GW_ADDRESS, "gw_port": "2060", "gw_id": "Gateway"}

    return render_template(
        'admin.html',
        packages=packages,
        vouchers=vouchers,
        search_query=search_query,
        active_sessions=active_sessions_cursor,
        user_summary=user_summary,
        detailed_report=detailed_report,
        today_revenue=f"{today_revenue:,.0f}",
        monthly_revenue=f"{monthly_revenue:,.0f}",
        total_data_consumed=format_bytes(0),
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
    pause_policy = request.form.get('pause_on_user_offline') == 'true'

    package_doc = {
        "name": name, "price": price, "duration_value": duration_value,
        "duration_unit": duration_unit, "duration_minutes": calculate_duration_minutes(duration_value, duration_unit),
        "badge": badge, "description": description, "pause_on_user_offline": pause_policy, 
        "created_at": datetime.now(timezone.utc)
    }
    packages_col.insert_one(package_doc)
    return redirect('/admin#packages')

@app.route('/admin/packages/edit/<pkg_id>', methods=['POST'])
def edit_package(pkg_id):
    if not session.get('admin'): return redirect('/admin/login')
    
    pause_policy = request.form.get('pause_on_user_offline') == 'true'
    new_name = request.form.get('name', '').strip()
    
    packages_col.update_one(
        {"_id": ObjectId(pkg_id)},
        {"$set": {
            "name": new_name,
            "price": float(request.form.get('price', 0)),
            "duration_value": int(request.form.get('duration', 1)),
            "duration_unit": request.form.get('unit', 'hours'),
            "duration_minutes": calculate_duration_minutes(request.form.get('duration', 1), request.form.get('unit', 'hours')),
            "badge": request.form.get('badge', '').strip(),
            "description": request.form.get('description', '').strip(),
            "pause_on_user_offline": pause_policy
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
    expire_at = datetime.fromisoformat(expire_at_str).replace(tzinfo=timezone.utc) if expire_at_str else None

    existing_codes = set(v["code"] for v in vouchers_col.find({}, {"code": 1}))
    new_vouchers = []

    def make_voucher_doc(code_val):
        return {
            "code": code_val,
            "package_id": ObjectId(pkg_id) if pkg_id else None,
            "duration_minutes": duration_minutes,
            "price": price,
            "status": "UNUSED",
            "note": note,
            "expire_at": expire_at,
            "created_at": datetime.now(timezone.utc)
        }

    if custom_code and custom_code not in existing_codes:
        new_vouchers.append(make_voucher_doc(custom_code))
    else:
        while len(new_vouchers) < qty and len(existing_codes) < 90000:
            code = f"{random.randint(0, 99999):05d}"
            if code not in existing_codes:
                existing_codes.add(code)
                new_vouchers.append(make_voucher_doc(code))

    if new_vouchers:
        vouchers_col.insert_many(new_vouchers)

    return render_template('print.html', vouchers=new_vouchers)

@app.route('/admin/vouchers/delete/<code>')
def delete_voucher(code):
    vouchers_col.delete_one({"code": code, "status": "UNUSED"})
    return redirect('/admin#vouchers')

@app.route('/admin/vouchers/revoke/<code>')
def toggle_revoke_voucher(code):
    if not session.get('admin'): return redirect('/admin/login')
    voucher = vouchers_col.find_one({"code": code})
    if voucher and voucher.get("status") in ["USED", "REVOKED"]:
        now = datetime.now(timezone.utc)
        current_status = voucher.get("status")
        db = vouchers_col.database
        
        if current_status == "USED" or current_status == "ACTIVE":
            # SET TO REVOKED
            vouchers_col.update_one(
                {"code": code}, 
                {"$set": {"status": "REVOKED", "revoked_at": now}}
            )
            
            # IMMEDIATELY STOP TIME COUNTING & DISCONNECT USER
            macs_to_disconnect = sessions_col.find({"code": code})
            for m in macs_to_disconnect:
                mac_id = m["_id"]
                log_id = m.get("current_log_id")
                if log_id:
                    log_doc = db.connection_logs.find_one({"_id": log_id})
                    if log_doc:
                        start_time = log_doc.get("start_time", now)
                        if start_time.tzinfo is None: start_time = start_time.replace(tzinfo=timezone.utc)
                        elapsed_mins = max(0, int((now - start_time).total_seconds() / 60.0))
                        db.connection_logs.update_one(
                            {"_id": log_id},
                            {"$set": {"last_active": now, "session_used_minutes": elapsed_mins}}
                        )
                sessions_col.delete_one({"_id": mac_id})
                tokens_col.delete_many({"mac": mac_id})
                
        elif current_status == "REVOKED":
            # RESTORE EVERYTHING UPON UNREVOKING (SHIFT USED TIME ONLY FOR CONTINUE-TIMER PACKAGES)
            revoked_at = voucher.get("revoked_at")
            used_at = voucher.get("used_at")
            update_data = {"status": "USED", "revoked_at": None}
            
            pkg_id = voucher.get("package_id")
            pkg = packages_col.find_one({"_id": pkg_id}) if pkg_id else None
            pause_offline = pkg.get("pause_on_user_offline", False) if pkg else False
            
            if revoked_at and used_at and not pause_offline:
                if revoked_at.tzinfo is None: revoked_at = revoked_at.replace(tzinfo=timezone.utc)
                if used_at.tzinfo is None: used_at = used_at.replace(tzinfo=timezone.utc)
                
                # Figure out how much time they lost while revoked and shift start time
                time_lost = now - revoked_at
                update_data["used_at"] = used_at + time_lost
                
            vouchers_col.update_one({"code": code}, {"$set": update_data})
            
    return redirect('/admin#vouchers')

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    # Prevent captive portal pages from being aggressively cached by captive portal mini-browsers
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response

@app.route('/admin/voucher/unrevoke/<code>')
def unrevoke_voucher(code):
    return toggle_revoke_voucher(code)
from apscheduler.schedulers.background import BackgroundScheduler

def background_cleanup_job():
    try:
        now = datetime.now(timezone.utc)
        result = vouchers_col.delete_many({
            "status": "UNUSED",
            "expire_at": {"$ne": None, "$lte": now}
        })
        if result.deleted_count > 0:
            logger.info(f"Background job cleaned up {result.deleted_count} expired vouchers.")
    except Exception as e:
        logger.error(f"Error in background cleanup job: {e}")

# Initialize and start scheduler when app boots up
if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=background_cleanup_job, trigger="interval", hours=6)
    scheduler.start()                    
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
