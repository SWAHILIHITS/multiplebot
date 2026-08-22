import os
import random
import secrets
import logging
import logging.config
from datetime import datetime, timedelta, timezone
from bson import ObjectId
from flask import Flask, render_template, request, redirect, session, Response
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
    """Extract parameter from POST form or GET query string."""
    return request.form.get(key) or request.args.get(key) or default

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


def format_duration_human(duration_minutes):
    """Converts duration in minutes into a human-readable text string."""
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
    """
    Formats a datetime object based on the current hour:
    - Current hour -> "Now"
    - Earlier today -> "HH:00" (24h)
    - Previous days -> "YYYY-MM-DD HH:00"
    """
    if dt_obj.tzinfo is None:
        dt_obj = dt_obj.replace(tzinfo=timezone.utc)
        
    if dt_obj.date() == current_time.date() and dt_obj.hour == current_time.hour:
        return "Now"
    elif dt_obj.date() == current_time.date():
        return dt_obj.strftime("%H:00")
    else:
        return dt_obj.strftime("%Y-%m-%d %H:00")


def format_bytes(bytes_count):
    """Converts bytes to MB or GB readable text."""
    if not bytes_count or bytes_count <= 0:
        return "0 MB"
    mb = bytes_count / (1024 * 1024)
    if mb >= 1024:
        return f"{mb / 1024:.2f} GB"
    return f"{mb:.2f} MB"


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
    """Renders voucher entry page or auto-reconnects existing active MAC sessions."""
    mac = get_client_mac()
    gw_address = get_gateway_address()
    gw_port = get_param('gw_port', '2060')
    gw_id = get_param('gw_id', 'G1UQ6C8027360')
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

# --- HELPER FUNCTIONS ---

def clean_mac(mac_str):
    """
    Standardizes MAC addresses by removing colons/hyphens and converting to uppercase.
    Example: '80:79:5d:05:0a:5d' -> '80795D050A5D'
    """
    if not mac_str or mac_str.startswith("UNKNOWN"):
        return mac_str
    return mac_str.replace(":", "").replace("-", "").strip().upper()


def get_client_mac():
    """Detect client MAC address across ReyeeOS parameter keys and clean it."""
    for key in ['mac', 'usermac', 'client_mac', 'client-mac']:
        val = get_param(key)
        if val:
            return clean_mac(val)
    return f"UNKNOWN:{secrets.token_hex(4).upper()}"


# ==========================================
# LOGIN PROCESSOR UPDATE
# ==========================================

@app.route('/login', methods=['POST'])
def process_login():
    """Validates voucher and redirects client to local AP auth endpoint."""
    code = request.form.get('voucher', '').strip()
    mac = clean_mac(get_client_mac())
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

    if not voucher or voucher.get("status") in ["USED", "REVOKED"]:
        error_msg = "Vocha hii siyo sahihi au ishatumika."
        if voucher and voucher.get("status") == "REVOKED":
            error_msg = "Vocha hii imesitishwa au kufutwa."
        
        return render_template(
            'portal.html',
            mac=mac,
            gw_address=gw_address,
            gw_port=gw_port,
            gw_id=gw_id,
            userurl=userurl,
            error=error_msg
        )

    duration_minutes = voucher['duration_minutes']
    expire_date = now + timedelta(minutes=duration_minutes)

    token = secrets.token_hex(16)
    
    # Insert token mapping with cleaned MAC
    tokens_col.insert_one({
        "token": token,
        "mac": mac,
        "code": code,
        "expire_date": expire_date,
        "created_at": now
    })

    # Upsert active session with cleaned MAC
    sessions_col.replace_one(
        {"_id": mac},
        {
            "_id": mac,
            "code": code,
            "used_time": now,
            "expire_date": expire_date,
            "duration_minutes": duration_minutes,
            "bytes_used": 0,
            "status": "ACTIVE"
        },
        upsert=True
    )
    
    vouchers_col.update_one(
        {"code": code}, 
        {"$set": {"status": "USED", "used_by_mac": mac, "used_at": now}}
    )

    logger.info(f"Successful login: MAC {mac} redeemed voucher '{code}'")

    auth_action_url = f"http://{gw_address}:{gw_port}/wifidog/auth?token={token}"

    return redirect(auth_action_url)

# ==========================================
# REYEE / REYEEOS WIFIDOG PROTOCOL HELPERS
# ==========================================


# ==========================================
# HELPER FUNCTIONS
# ==========================================



def extract_byte_count(args_dict):
    """
    Extracts incoming and outgoing bytes across standard WifiDog & ReyeeOS query keys.
    Returns the total bytes reported in the request.
    """
    incoming = 0
    outgoing = 0

    download_keys = ['incoming', 'incoming_bytes', 'download', 'bytes_in', 'rx_bytes', 'down']
    upload_keys = ['outgoing', 'outgoing_bytes', 'upload', 'bytes_out', 'tx_bytes', 'up']

    for key in download_keys:
        val = args_dict.get(key)
        if val is not None:
            try:
                incoming = int(str(val).strip())
                if incoming > 0:
                    break
            except ValueError:
                continue

    for key in upload_keys:
        val = args_dict.get(key)
        if val is not None:
            try:
                outgoing = int(str(val).strip())
                if outgoing > 0:
                    break
            except ValueError:
                continue

    return incoming + outgoing


# ==========================================
# WIFIDOG AUTH CHECK
# ==========================================

@app.route('/auth', methods=['GET'])
@app.route('/auth/', methods=['GET'])
@app.route('/wifidog/auth', methods=['GET'])
@app.route('/wifidog/auth/', methods=['GET'])
@app.route('/api/wifidog/auth', methods=['GET'])
@app.route('/api/wifidog/auth/', methods=['GET'])
def wifidog_auth_check():
    """
    ReyeeOS Background Auth Verification.
    Validates active sessions and updates data consumption counters.
    """
    token = request.args.get('token', '').strip()
    stage = request.args.get('stage', '').strip()
    mac = clean_mac(request.args.get('mac', ''))
    now = datetime.now(timezone.utc)

    # Handle client logout stage
    if stage == 'logout':
        if mac:
            sessions_col.delete_one({"_id": mac})
            tokens_col.delete_many({"mac": mac})
            logger.info(f"Client logged out: MAC {mac}")
        return Response("Auth: 0\n", mimetype='text/plain')

    # Resolve MAC address from Token if direct MAC parameter was missing
    if not mac and token:
        token_doc = tokens_col.find_one({"token": token})
        if token_doc:
            mac = clean_mac(token_doc.get("mac", ""))

    if not mac:
        logger.warning("WifiDog Auth denied: No valid MAC address or Token provided.")
        return Response("Auth: 0\n", mimetype='text/plain')

    # Locate active user session
    session_doc = sessions_col.find_one({"_id": mac})

    if session_doc:
        exp = session_doc.get('expire_date')
        if exp and exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)

        # Confirm session is still valid
        if exp and exp > now:
            total_bytes = extract_byte_count(request.args)

            # Update database usage counters if router sent byte counts
            if total_bytes > 0:
                sessions_col.update_one(
                    {"_id": mac},
                    {"$set": {"bytes_used": total_bytes}}
                )

                voucher_code = session_doc.get("code")
                if voucher_code:
                    vouchers_col.update_one(
                        {"code": voucher_code},
                        {"$set": {"data_consumed_bytes": total_bytes}}
                    )
                logger.info(f"Auth updated data usage for MAC {mac}: {total_bytes} bytes")

            # Grant internet access
            return Response("Auth: 1\n", mimetype='text/plain')

    # Clean up expired session or unauthorized token
    tokens_col.delete_many({"mac": mac})
    sessions_col.delete_one({"_id": mac, "expire_date": {"$lte": now}})

    logger.warning(f"WifiDog Auth denied or expired for MAC: '{mac}'. Returning Auth: 0")
    return Response("Auth: 0\n", mimetype='text/plain')

# ==========================================
# REYEE / WIFIDOG PING & HEARTBEAT
# ==========================================

@app.route('/ping', methods=['GET'])
@app.route('/ping/', methods=['GET'])
@app.route('/wifidog/ping', methods=['GET'])
@app.route('/wifidog/ping/', methods=['GET'])
@app.route('/api/wifidog/ping', methods=['GET'])
@app.route('/api/wifidog/ping/', methods=['GET'])
def wifidog_ping():
    """
    Handles periodic Access Point Heartbeats.
    Extracts telemetry data and updates active session consumption.
    """
    gw_id = request.args.get('gw_id', 'Unknown')
    mac = clean_mac(request.args.get('mac', ''))

    total_bytes = extract_byte_count(request.args)

    if mac and total_bytes > 0:
        session_doc = sessions_col.find_one({"_id": mac})
        if session_doc:
            sessions_col.update_one(
                {"_id": mac},
                {"$set": {"bytes_used": total_bytes}}
            )
            voucher_code = session_doc.get("code")
            if voucher_code:
                vouchers_col.update_one(
                    {"code": voucher_code},
                    {"$set": {"data_consumed_bytes": total_bytes}}
                )
            logger.info(f"Ping updated data usage for MAC {mac}: {total_bytes} bytes")

    logger.debug(f"Ping received from Access Point Gateway ID: {gw_id}")
    return Response("Pong\n", mimetype='text/plain')

# ==========================================
# ERROR HANDLERS
# ==========================================

@app.errorhandler(404)
def handle_404(e):
    """Catch routing errors without breaking API background checks."""
    path = request.path.lower()
    
    if 'favicon.ico' in path:
        return Response(status=204)

    # Route any unhandled wifidog ping requests directly to wifidog_ping
    if 'ping' in path:
        logger.warning(f"Redirecting loose ping request '{request.path}' to wifidog_ping handler.")
        return wifidog_ping()

    if path.startswith('/wifidog') or path.startswith('/api/wifidog') or 'auth' in path:
        logger.warning(f"Unhandled WifiDog API route requested: {request.path}")
        return Response("Not Found\n", status=404, mimetype='text/plain')
    
    logger.warning(f"404 redirect triggered for path: {request.path} from IP: {request.remote_addr}")
    return captive_login_page()

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
# ADMIN PANEL & PACKAGE ROUTES
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
    start_of_today = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    start_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    # 1. Fetch active sessions lookup map
    active_sessions_cursor = list(sessions_col.find({"expire_date": {"$gt": now}}))
    active_sessions_map = {s["_id"]: s for s in active_sessions_cursor}

    # 2. Fetch packages and vouchers
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

    # 3. Fetch redeemed vouchers for usage reporting
    used_vouchers = list(vouchers_col.find({"used_by_mac": {"$ne": None}}).sort("used_at", -1))

    mac_agg = {}
    detailed_report = []
    total_bytes_consumed = 0

    for v in used_vouchers:
        mac = v.get("used_by_mac")
        if not mac:
            continue
        
        price = float(v.get("price", 0.0))
        used_at = v.get("used_at", now)
        is_online = mac in active_sessions_map
        connection_status = "online" if is_online else "offline"

        if mac not in mac_agg:
            mac_agg[mac] = {
                "mac": mac,
                "status": connection_status,
                "vouchers_count": 0,
                "total_spend": 0.0
            }
        mac_agg[mac]["vouchers_count"] += 1
        mac_agg[mac]["total_spend"] += price
        if is_online:
            mac_agg[mac]["status"] = "online"

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

    # 4. Revenue Aggregations
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
        active_vouchers_count=active_vouchers_count
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
# SERVER STARTUP
# ==========================================

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting HANS WIFI Portal server on port {port}")
    app.run(host='0.0.0.0', port=port)
