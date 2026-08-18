import os
import random
import secrets
import logging
import logging.config
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, request, redirect, session, Response
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)

# --- LOGGING CONFIGURATION ---
LOG_CONFIG_FILE = "logging.conf"
if os.path.exists(LOG_CONFIG_FILE):
    logging.config.fileConfig(LOG_CONFIG_FILE, disable_existing_loggers=False)
    logger = logging.getLogger("appLogger")
else:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("appLogger")

# --- APP & SECURITY CONFIGURATION ---
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(32))
ADMIN_PW = os.getenv("ADMIN_PASSWORD", "admin123")
DEFAULT_GW_ADDRESS = os.getenv("DEFAULT_GW_ADDRESS", "192.168.0.46")

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://swahilihit:swahilihit@cluster0.3nfk1.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
)

# --- DATABASE SETUP ---
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client['swahilihit56']
    
    vouchers_col = db["vouchers"]
    sessions_col = db["sessions"]
    tokens_col = db["wifidog_tokens"]
    packages_col = db["packages"]
    
    # Indexes for performance and automatic expiration
    vouchers_col.create_index("code", unique=True)
    tokens_col.create_index("created_at", expireAfterSeconds=600)
    sessions_col.create_index("expire_date")
    
    logger.info("Connected to MongoDB successfully.")
except Exception as e:
    logger.error(f"MongoDB connection failure: {str(e)}")


def calculate_duration_minutes(duration_val, unit):
    """Converts various duration units into total minutes."""
    val = int(duration_val)
    unit = str(unit).lower()
    if unit == 'hours':
        return val * 60
    elif unit == 'days':
        return val * 1440
    elif unit == 'months':
        return val * 43200
    return val


# --- PUBLIC CAPTIVE PORTAL & LOGIN ---

@app.route('/')
@app.route('/portal')
def captive_portal():
    """Renders the Wi-Fi captive portal login page for captive devices."""
    gw_address = request.args.get('gw_address', DEFAULT_GW_ADDRESS)
    gw_port = request.args.get('gw_port', '2060')
    mac = request.args.get('mac', '')
    url = request.args.get('url', '')

    packages = list(packages_col.find().sort("price", 1))

    return render_template(
        'portal.html',
        gw_address=gw_address,
        gw_port=gw_port,
        mac=mac,
        userurl=url,
        packages=packages
    )


@app.route('/login', methods=['POST'])
def process_login():
    """
    Validates the voucher code entered by a user.
    Records the 'used_at' timestamp upon successful redemption.
    """
    code = request.form.get('voucher', '').strip().upper()
    mac = request.form.get('mac', '').strip().upper() or "UNKNOWN"
    gw_address = request.form.get('gw_address') or DEFAULT_GW_ADDRESS
    gw_port = request.form.get('gw_port', '2060')

    now = datetime.now(timezone.utc)
    
    # 1. Fetch unused voucher
    voucher = vouchers_col.find_one({"code": code, "status": "UNUSED"})

    if not voucher:
        return render_template('portal.html', error="Vocha hii siyo sahihi au ishatumika.")

    # 2. Check if unused voucher has expired (and self-delete if past expire_at)
    if voucher.get("expire_at"):
        exp_date = voucher["expire_at"]
        if exp_date.tzinfo is None:
            exp_date = exp_date.replace(tzinfo=timezone.utc)
        
        if exp_date <= now:
            vouchers_col.delete_one({"_id": voucher["_id"]})
            logger.info(f"Unused voucher '{code}' expired and self-deleted during redemption attempt.")
            return render_template('portal.html', error="Vocha hii imepitwa na wakati.")

    duration_minutes = voucher['duration_minutes']
    session_expire_date = now + timedelta(minutes=duration_minutes)

    # 3. Create temporary WiFiDog token
    token = secrets.token_hex(16)
    tokens_col.insert_one({
        "token": token,
        "mac": mac,
        "code": code,
        "expire_date": session_expire_date,
        "created_at": now
    })

    # 4. Save/Update active session
    sessions_col.replace_one(
        {"_id": mac},
        {
            "_id": mac,
            "code": code,
            "used_time": now,
            "expire_date": session_expire_date,
            "duration_minutes": duration_minutes,
            "status": "ACTIVE"
        },
        upsert=True
    )
    
    # 5. Update voucher status, record redemption timestamp (used_at), and set session expiration
    vouchers_col.update_one(
        {"code": code}, 
        {
            "$set": {
                "status": "USED", 
                "used_by_mac": mac, 
                "used_at": now, 
                "expire_at": session_expire_date
            }
        }
    )

    auth_action_url = f"http://{gw_address}:{gw_port}/wifidog/auth?token={token}"
    return redirect(auth_action_url)


# --- WIFIDOG GATEWAY PROTOCOL ENDPOINTS ---

@app.route('/wifidog/auth')
def wifidog_auth():
    """WiFiDog gateway validation callback route."""
    token_str = request.args.get('token')
    if not token_str:
        return Response("Auth: 0", mimetype='text/plain')

    tok = tokens_col.find_one({"token": token_str})
    if tok:
        return Response("Auth: 1", mimetype='text/plain')
    return Response("Auth: 0", mimetype='text/plain')


@app.route('/wifidog/ping')
def wifidog_ping():
    """Heartbeat route for the outdoor Access Point router."""
    return Response("Pong", mimetype='text/plain')


# --- ADMIN AUTHENTICATION ---

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Handles admin dashboard authentication."""
    if request.method == 'POST':
        pw = request.form.get('password')
        if pw == ADMIN_PW:
            session['admin'] = True
            return redirect('/admin')
        return render_template('admin_login.html', error="Neno la siri siyo sahihi.")
    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    """Clears the admin session."""
    session.pop('admin', None)
    return redirect('/admin/login')


# --- ADMIN DASHBOARD & AUTOMATED CLEANUP ---

@app.route('/admin')
def admin_dashboard():
    """
    Renders the admin panel with live analytics.
    Performs automated self-deletion for expired UNUSED vouchers.
    """
    if not session.get('admin'):
        return redirect('/admin/login')

    now = datetime.now(timezone.utc)

    # Automated Cleanup: Permanently delete UNUSED vouchers whose expire_at date has passed
    vouchers_col.delete_many({
        "status": "UNUSED",
        "expire_at": {"$lte": now, "$ne": None}
    })

    packages = list(packages_col.find().sort("_id", -1))
    vouchers = list(vouchers_col.find().sort("_id", -1))
    active_sessions = list(sessions_col.find({"expire_date": {"$gt": now}, "status": "ACTIVE"}))
    active_macs = set(s["_id"] for s in active_sessions)

    # Compute status labels for table rendering
    for v in vouchers:
        if v.get('status') in ['USED', 'REVOKED']:
            exp = v.get('expire_at')
            if exp and exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp and exp <= now:
                v['computed_status'] = 'EXPIRED'
            else:
                v['computed_status'] = v['status']
        else:
            v['computed_status'] = v.get('status', 'UNUSED')

    # Aggregate user spend and purchase statistics
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

    return render_template(
        'admin.html',
        packages=packages,
        vouchers=vouchers,
        active_sessions=active_sessions,
        user_summary=user_summary,
        active_sessions_count=len(active_sessions),
        active_vouchers_count=vouchers_col.count_documents({"status": "UNUSED"}),
        used_vouchers_count=vouchers_col.count_documents({"status": "USED"}),
        total_revenue=f"{sum(v.get('price', 0) for v in vouchers if v.get('status') in ['USED', 'REVOKED']):,.0f}"
    )


# --- PACKAGE MANAGEMENT ROUTES ---

@app.route('/admin/packages/create', methods=['POST'])
def create_package():
    """Creates a new package with name, price, duration, badge, and description."""
    if not session.get('admin'):
        return redirect('/admin/login')

    name = request.form.get('name', '').strip()
    price = float(request.form.get('price', 0))
    duration_val = int(request.form.get('duration', 1))
    unit = request.form.get('unit', 'hours')
    badge = request.form.get('badge', '').strip()
    description = request.form.get('description', '').strip()

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

    return redirect('/admin#packages')


@app.route('/admin/packages/edit/<pkg_id>', methods=['POST'])
def edit_package(pkg_id):
    """Updates an existing package by ObjectId."""
    if not session.get('admin'):
        return redirect('/admin/login')

    name = request.form.get('name', '').strip()
    price = float(request.form.get('price', 0))
    duration_val = int(request.form.get('duration', 1))
    unit = request.form.get('unit', 'hours')
    badge = request.form.get('badge', '').strip()
    description = request.form.get('description', '').strip()

    duration_minutes = calculate_duration_minutes(duration_val, unit)

    packages_col.update_one(
        {"_id": ObjectId(pkg_id)},
        {"$set": {
            "name": name,
            "price": price,
            "duration_value": duration_val,
            "duration_unit": unit,
            "duration_minutes": duration_minutes,
            "badge": badge,
            "description": description
        }}
    )

    return redirect('/admin#packages')


@app.route('/admin/packages/delete/<pkg_id>')
def delete_package(pkg_id):
    """Deletes a package by ObjectId."""
    if not session.get('admin'):
        return redirect('/admin/login')

    try:
        packages_col.delete_one({"_id": ObjectId(pkg_id)})
    except Exception as e:
        logger.error(f"Failed to delete package: {str(e)}")

    return redirect('/admin#packages')


# --- VOUCHER GENERATION ---

@app.route('/admin/generate', methods=['POST'])
def generate_vouchers():
    """Generates bulk or custom vouchers linked to a selected package."""
    if not session.get('admin'):
        return redirect('/admin/login')

    package_id = request.form.get('package_id')
    qty = int(request.form.get('quantity', 1))
    custom_code = request.form.get('custom_code', '').strip().upper()
    expire_at_str = request.form.get('expire_at')
    note = request.form.get('note', '').strip()

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
            "package_id": pkg["_id"] if pkg else None,
            "package_name": pkg_name,
            "duration_minutes": duration,
            "price": price,
            "status": "UNUSED",
            "created_at": now,
            "used_at": None,
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
                    "package_id": pkg["_id"] if pkg else None,
                    "package_name": pkg_name,
                    "duration_minutes": duration,
                    "price": price,
                    "status": "UNUSED",
                    "created_at": now,
                    "used_at": None,
                    "expire_at": expire_date,
                    "note": note
                }
                new_vouchers.append(doc)

        if new_vouchers:
            vouchers_col.insert_many(new_vouchers)

    return render_template('print.html', vouchers=new_vouchers)


# --- VOUCHER REVOCATION & UNREVOCATION ---

@app.route('/admin/voucher/revoke/<code_or_mac>')
def revoke_voucher(code_or_mac):
    """Deletes unused vouchers or disconnects active sessions."""
    if not session.get('admin'):
        return redirect('/admin/login')

    target = code_or_mac.strip().upper()
    v = vouchers_col.find_one({"$or": [{"code": target}, {"used_by_mac": target}]})

    if v:
        if v.get('status') == 'UNUSED':
            vouchers_col.delete_one({"_id": v["_id"]})
        elif v.get('status') == 'USED':
            mac = v.get('used_by_mac')
            if mac:
                sessions_col.update_one({"_id": mac}, {"$set": {"status": "REVOKED"}})
                tokens_col.delete_many({"mac": mac})
            vouchers_col.update_one({"_id": v["_id"]}, {"$set": {"status": "REVOKED"}})

    return redirect('/admin#vouchers')


@app.route('/admin/voucher/unrevoke/<code_or_mac>')
def unrevoke_voucher(code_or_mac):
    """Restores access for a previously revoked voucher/MAC."""
    if not session.get('admin'):
        return redirect('/admin/login')

    target = code_or_mac.strip().upper()
    v = vouchers_col.find_one({"$or": [{"code": target}, {"used_by_mac": target}]})

    if v and v.get('status') == 'REVOKED':
        mac = v.get('used_by_mac')
        if mac:
            sessions_col.update_one({"_id": mac}, {"$set": {"status": "ACTIVE"}})
        vouchers_col.update_one({"_id": v["_id"]}, {"$set": {"status": "USED"}})

    return redirect('/admin#vouchers')


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
