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

# --- LOGGING CONFIGURATION ---
LOG_CONFIG_FILE = "logging.conf"
if os.path.exists(LOG_CONFIG_FILE):
    logging.config.fileConfig(LOG_CONFIG_FILE, disable_existing_loggers=False)
    logger = logging.getLogger("appLogger")
else:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("appLogger")

# --- APP CONFIGURATION ---
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(32))
ADMIN_PW = os.getenv("ADMIN_PASSWORD", "admin123")
DEFAULT_GW_ADDRESS = os.getenv("DEFAULT_GW_ADDRESS", "192.168.0.46")

MONGO_URI = "mongodb+srv://swahilihit:swahilihit@cluster0.3nfk1.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"

# --- DATABASE SETUP ---
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client['swahilihit56']
    vouchers_col = db["vouchers"]
    sessions_col = db["sessions"]
    tokens_col = db["wifidog_tokens"]
    packages_col = db["packages"]  # Package collection
    
    # Indexes
    vouchers_col.create_index("code", unique=True)
    tokens_col.create_index("created_at", expireAfterSeconds=600)
    sessions_col.create_index("expire_date")
    logger.info("Connected to MongoDB and initialized collections.")
except Exception as e:
    logger.error(f"MongoDB connection failure: {str(e)}")


# --- HELPER FUNCTIONS ---
def calculate_duration_minutes(duration_val, unit):
    """Converts duration inputs to minutes."""
    val = int(duration_val)
    unit = unit.lower()
    if unit == 'hours':
        return val * 60
    elif unit == 'days':
        return val * 1440
    elif unit == 'months':
        return val * 43200
    return val  # Default minutes


# --- ADMIN PACKAGE ROUTES ---

@app.route('/admin/packages/create', methods=['POST'])
def create_package():
    """Creates and saves a new internet plan package into MongoDB."""
    if not session.get('admin'):
        return redirect('/admin/login')

    name = request.form.get('name')
    price = float(request.form.get('price', 0))
    duration_val = int(request.form.get('duration', 1))
    unit = request.form.get('unit', 'days')
    badge = request.form.get('badge', '')
    description = request.form.get('description', '')

    duration_minutes = calculate_duration_minutes(duration_val, unit)

    package_doc = {
        "name": name,
        "price": price,
        "duration_value": duration_val,
        "duration_unit": unit,
        "duration_minutes": duration_minutes,
        "badge": badge,
        "description": description,
        "created_at": datetime.now(timezone.utc)
    }

    packages_col.insert_one(package_doc)
    logger.info(f"Package created: {name} - TZS {price}")
    return redirect('/admin#packages')


@app.route('/admin/packages/delete/<package_id>')
def delete_package(package_id):
    """Removes a package from MongoDB."""
    if not session.get('admin'):
        return redirect('/admin/login')
    
    packages_col.delete_one({"_id": ObjectId(package_id)})
    return redirect('/admin#packages')


# --- VOUCHER LIFECYCLE ROUTES ---

@app.route('/admin/generate', methods=['POST'])
def generate_vouchers():
    """Generates vouchers linked to selected packages."""
    if not session.get('admin'):
        return redirect('/admin/login')

    package_id = request.form.get('package_id')
    qty = int(request.form.get('quantity', 1))
    custom_code = request.form.get('custom_code', '').strip()
    expire_at_str = request.form.get('expire_at')
    note = request.form.get('note', '')

    pkg = packages_col.find_one({"_id": ObjectId(package_id)}) if package_id else None
    
    price = pkg['price'] if pkg else float(request.form.get('price', 500))
    duration = pkg['duration_minutes'] if pkg else int(request.form.get('duration', 1440))
    pkg_name = pkg['name'] if pkg else "Custom Package"

    now = datetime.now(timezone.utc)
    expire_date = None
    if expire_at_str:
        expire_date = datetime.fromisoformat(expire_at_str).replace(tzinfo=timezone.utc)

    new_vouchers = []

    # Custom Code generation forces single voucher creation
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
    Revokes voucher access:
    - If UNUSED/ACTIVE: Deletes voucher record completely from DB.
    - If USED: Revokes session access while leaving voucher history intact.
    """
    if not session.get('admin'):
        return redirect('/admin/login')

    target = code_or_mac.strip().upper()
    v = vouchers_col.find_one({"$or": [{"code": target}, {"used_by_mac": target}]})

    if v:
        # If Unused, delete completely from DB
        if v.get('status') == 'UNUSED':
            vouchers_col.delete_one({"_id": v["_id"]})
            logger.info(f"Unused voucher '{v['code']}' revoked and deleted from MongoDB.")
        
        # If Used, revoke internet session access
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


# --- MAIN ADMIN DASHBOARD ROUTE ---

@app.route('/admin')
def admin_dashboard():
    if not session.get('admin'):
        return redirect('/admin/login')

    now = datetime.now(timezone.utc)

    # 1. Automatic Cleanup: Delete expired UNUSED vouchers
    vouchers_col.delete_many({
        "status": "UNUSED",
        "expire_at": {"$lte": now, "$ne": None}
    })

    # 2. Fetch Datasets
    packages = list(packages_col.find().sort("_id", -1))
    vouchers = list(vouchers_col.find().sort("_id", -1))
    active_sessions = list(sessions_col.find({"expire_date": {"$gt": now}, "status": "ACTIVE"}))
    active_macs = set(s["_id"] for s in active_sessions)

    # Process Vouchers for UI Time Calculations
    for v in vouchers:
        if v.get('status') == 'USED' or v.get('status') == 'REVOKED':
            exp = v.get('expire_at')
            if exp and exp <= now:
                v['computed_status'] = 'EXPIRED'
            else:
                v['computed_status'] = v['status']
        else:
            v['computed_status'] = v.get('status', 'UNUSED')

    # Aggregations for Users View
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
        total_revenue=f"{sum(v.get('price', 0) for v in vouchers if v.get('status') in ['USED', 'REVOKED']):,.0f}"
    )


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
