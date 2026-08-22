import os
import random
import secrets
import logging
import logging.config
from datetime import datetime, timedelta, timezone
from bson import ObjectId
from flask import Flask, render_template, request, redirect, session, Response, render_template_string
from templates.database import vouchers_col, sessions_col, tokens_col, packages_col, settings_col

app = Flask(__name__)

# --- LOGGING INITIALIZATION ---
LOG_CONFIG_FILE = "logging.conf"
if os.path.exists(LOG_CONFIG_FILE):
    logging.config.fileConfig(LOG_CONFIG_FILE, disable_existing_loggers=False)
    logger = logging.getLogger("appLogger")
else:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("appLogger")

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
    if unit == 'minutes': return val
    elif unit == 'hours': return val * 60
    elif unit == 'days': return val * 60 * 24
    elif unit == 'months': return val * 60 * 24 * 30
    return val

def format_duration_human(duration_minutes):
    if not duration_minutes or duration_minutes <= 0: return "0 mins"
    if duration_minutes < 60: return f"{duration_minutes} mins"
    hours = duration_minutes / 60
    if hours < 24: return f"{hours:.1f}".rstrip('0').rstrip('.') + " hrs"
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
    if not bytes_count or bytes_count <= 0: return "0 MB"
    mb = bytes_count / (1024 * 1024)
    if mb >= 1024: return f"{mb / 1024:.2f} GB"
    return f"{mb:.2f} MB"

def clean_mac(mac_str):
    if not mac_str or mac_str.startswith("UNKNOWN"): return mac_str
    return mac_str.replace(":", "").replace("-", "").strip().upper()

def get_client_mac():
    for key in ['mac', 'usermac', 'client_mac', 'client-mac']:
        val = get_param(key)
        if val: return clean_mac(val)
    return f"UNKNOWN:{secrets.token_hex(4).upper()}"

# --- WIFIDOG DATA CONSUMPTION TRACKER ---
def extract_byte_count(args_dict):
    """
    Directly extracts cumulative incoming and outgoing bytes from WifiDog telemetry.
    No SNMP required. This reads standard HTTP payload from the router.
    """
    incoming = 0
    outgoing = 0
    
    # Try standard WifiDog keys first, fallback to alternate ReyeeOS keys
    try:
        incoming = int(args_dict.get('incoming', args_dict.get('rx_bytes', args_dict.get('download', 0))))
    except ValueError: pass
    
    try:
        outgoing = int(args_dict.get('outgoing', args_dict.get('tx_bytes', args_dict.get('upload', 0))))
    except ValueError: pass

    return incoming + outgoing


# ==========================================
# CAPTIVE PORTAL ROUTES
# ==========================================
@app.route('/')
@app.route('/portal')
@app.route('/wifidog/portal')
def captive_login_page():
    mac = get_client_mac()
    gw_address = get_gateway_address()
    gw_port = get_param('gw_port', '2060')
    gw_id = get_param('gw_id', 'Gateway')
    userurl = get_param('url') or 'http://www.google.com'

    now = datetime.now(timezone.utc)
    if mac and not mac.startswith("UNKNOWN"):
        active_session = sessions_col.find_one({"_id": mac, "expire_date": {"$gt": now}})
        if active_session:
            token = secrets.token_hex(16)
            tokens_col.insert_one({
                "token": token, "mac": mac,
                "code": active_session.get("code"),
                "expire_date": active_session.get("expire_date"),
                "created_at": now
            })
            auth_action_url = f"http://{gw_address}:{gw_port}/wifidog/auth?token={token}"
            return redirect(auth_action_url)

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
    userurl = get_param('url') or 'http://www.google.com'
    now = datetime.now(timezone.utc)

    voucher = vouchers_col.find_one({"code": code})
    if not voucher or voucher.get("status") in ["USED", "REVOKED"]:
        error_msg = "Vocha hii imesitishwa au kufutwa." if voucher and voucher.get("status") == "REVOKED" else "Vocha hii siyo sahihi au ishatumika."
        return render_template('portal.html', mac=mac, gw_address=gw_address, gw_port=gw_port, userurl=userurl, error=error_msg)

    duration_minutes = voucher['duration_minutes']
    expire_date = now + timedelta(minutes=duration_minutes)
    token = secrets.token_hex(16)
    
    tokens_col.insert_one({"token": token, "mac": mac, "code": code, "expire_date": expire_date, "created_at": now})
    
    sessions_col.replace_one(
        {"_id": mac},
        {"_id": mac, "code": code, "used_time": now, "expire_date": expire_date, "duration_minutes": duration_minutes, "bytes_used": 0, "status": "ACTIVE"},
        upsert=True
    )
    vouchers_col.update_one({"code": code}, {"$set": {"status": "USED", "used_by_mac": mac, "used_at": now}})

    auth_action_url = f"http://{gw_address}:{gw_port}/wifidog/auth?token={token}"

    # Beautiful Transitional Success UI
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

# ==========================================
# WIFIDOG AUTH & PING (DATA TRACKING)
# ==========================================
@app.route('/auth', methods=['GET'])
@app.route('/wifidog/auth', methods=['GET'])
def wifidog_auth_check():
    token = request.args.get('token', '').strip()
    stage = request.args.get('stage', '').strip()
    mac = clean_mac(request.args.get('mac', ''))
    now = datetime.now(timezone.utc)

    if stage == 'logout':
        if mac:
            sessions_col.delete_one({"_id": mac})
            tokens_col.delete_many({"mac": mac})
        return Response("Auth: 0\n", mimetype='text/plain')

    if not mac and token:
        token_doc = tokens_col.find_one({"token": token})
        if token_doc: mac = clean_mac(token_doc.get("mac", ""))

    if not mac: return Response("Auth: 0\n", mimetype='text/plain')

    session_doc = sessions_col.find_one({"_id": mac})
    if session_doc:
        exp = session_doc.get('expire_date')
        if exp and exp.tzinfo is None: exp = exp.replace(tzinfo=timezone.utc)

        if exp and exp > now:
            total_bytes = extract_byte_count(request.args)
            if total_bytes > 0:
                sessions_col.update_one({"_id": mac}, {"$set": {"bytes_used": total_bytes}})
                voucher_code = session_doc.get("code")
                if voucher_code:
                    vouchers_col.update_one({"code": voucher_code}, {"$set": {"data_consumed_bytes": total_bytes}})
            return Response("Auth: 1\n", mimetype='text/plain')

    tokens_col.delete_many({"mac": mac})
    sessions_col.delete_one({"_id": mac, "expire_date": {"$lte": now}})
    return Response("Auth: 0\n", mimetype='text/plain')

@app.route('/ping', methods=['GET'])
@app.route('/wifidog/ping', methods=['GET'])
def wifidog_ping():
    mac = clean_mac(request.args.get('mac', ''))
    total_bytes = extract_byte_count(request.args)

    if mac and total_bytes > 0:
        session_doc = sessions_col.find_one({"_id": mac})
        if session_doc:
            sessions_col.update_one({"_id": mac}, {"$set": {"bytes_used": total_bytes}})
            voucher_code = session_doc.get("code")
            if voucher_code:
                vouchers_col.update_one({"code": voucher_code}, {"$set": {"data_consumed_bytes": total_bytes}})
    return Response("Pong\n", mimetype='text/plain')

# ==========================================
# ADMIN DASHBOARD ROUTES
# ==========================================
# [KEEP YOUR EXISTING /admin, /admin/packages/*, and /admin/voucher/* ROUTES HERE EXACLTY AS THEY WERE]
# Ensure you just copy-paste the rest of your original routing logic (admin_dashboard, generate_vouchers, etc) 
# below this point. No changes needed to the routing structures themselves.

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
