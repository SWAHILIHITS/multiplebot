import os
import random
import secrets
import logging
import logging.config
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template_string, request, redirect, session, Response
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)

# --- LOGGING INITIALIZATION ---
LOG_CONFIG_FILE = "logging.conf"
if os.path.exists(LOG_CONFIG_FILE):
    logging.config.fileConfig(LOG_CONFIG_FILE, disable_existing_loggers=False)
    logger = logging.getLogger("appLogger")
else:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("appLogger")

# --- CONFIGURATION ---
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
    packages_col = db["packages"]
    routers_col = db["routers"]
    
    vouchers_col.create_index("code", unique=True)
    vouchers_col.create_index("status")
    sessions_col.create_index("status")
    logger.info("Successfully connected to MongoDB.")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {str(e)}")

# --- HELPER FUNCTIONS ---
def generate_numeric_code(length=6):
    """Generates a random numeric voucher code."""
    return "".join([str(random.randint(0, 9)) for _ in range(length)])

# ==========================================
# 🎨 UI STYLES & LAYOUT
# ==========================================

NAV_SIDEBAR = """
<div class="mobile-header">
    <button class="menu-btn" onclick="toggleSidebar()">☰</button>
    <div class="mobile-title">HANS NETWORK</div>
</div>
<div class="sidebar-overlay" id="sidebarOverlay" onclick="toggleSidebar()"></div>

<div class="sidebar" id="sidebar">
    <div class="brand">
        <div class="brand-title">📡 Sensible Network</div>
        <div class="brand-sub">KARIBU HANS INTERNET<br>KITONGA 0624667219</div>
    </div>
    <ul class="nav-list">
        <li><a href="/admin" class="{{ 'active' if active_page == 'dashboard' else '' }}">📊 Dashboard</a></li>
        <li><a href="/admin/packages" class="{{ 'active' if active_page == 'packages' else '' }}">🏷️ Packages</a></li>
        <li><a href="/admin/vouchers" class="{{ 'active' if active_page == 'vouchers' else '' }}">🎟️ Vouchers</a></li>
        <li><a href="/admin/sessions" class="{{ 'active' if active_page == 'sessions' else '' }}">👥 Sessions</a></li>
        <li><a href="/admin/logout">🚪 Sign out</a></li>
    </ul>
</div>
"""

BASE_STYLE = """
<style>
    * { box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f8fafc; margin: 0; padding: 0; color: #1e293b; display: flex; min-height: 100vh; }
    
    .sidebar { width: 250px; background: #1e3a5f; color: white; padding: 20px 0; flex-shrink: 0; transition: transform 0.3s ease; z-index: 1000; }
    .brand { padding: 0 20px 20px 20px; border-bottom: 1px solid rgba(255,255,255,0.1); }
    .brand-title { font-weight: bold; font-size: 16px; color: #ffffff; }
    .brand-sub { font-size: 11px; opacity: 0.7; margin-top: 4px; line-height: 1.4; }
    .nav-list { list-style: none; padding: 15px 10px; margin: 0; }
    .nav-list li { margin-bottom: 4px; }
    .nav-list a { display: block; padding: 12px 16px; color: #cbd5e1; text-decoration: none; border-radius: 8px; font-size: 14px; font-weight: 500; transition: all 0.2s; }
    .nav-list a:hover, .nav-list a.active { background: #2c4d75; color: white; font-weight: bold; }
    
    .mobile-header { display: none; background: #1e3a5f; color: white; padding: 12px 16px; align-items: center; gap: 12px; position: sticky; top: 0; z-index: 900; }
    .menu-btn { background: none; border: none; color: white; font-size: 22px; cursor: pointer; padding: 0; }
    .mobile-title { font-weight: bold; font-size: 16px; }
    .sidebar-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 999; }
    
    .main-content { flex: 1; padding: 25px; overflow-y: auto; width: 100%; }
    .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
    .header h2 { margin: 0; color: #0f172a; font-size: 24px; }
    
    .box { background: white; padding: 24px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 25px; box-shadow: 0 1px 3px rgba(0,0,0,0.02); }
    .box h3 { margin-top: 0; border-bottom: 1px solid #f1f5f9; padding-bottom: 12px; font-size: 17px; color: #1e3a5f; }
    
    /* Form Inputs */
    .form-group { margin-bottom: 18px; }
    .form-group label { display: block; font-size: 13px; font-weight: 600; color: #334155; margin-bottom: 6px; }
    .form-subtext { font-size: 12px; color: #64748b; margin-top: 4px; }
    .form-control { width: 100%; padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 14px; background: #f8fafc; }
    .form-control:focus { outline: none; border-color: #0052cc; background: white; }
    
    /* Buttons */
    .btn-primary { background: #1e3a5f; color: white; padding: 12px 20px; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 14px; width: 100%; }
    .btn-primary:hover { background: #2c4d75; }
    .btn-danger { background: #ffebe6; color: #de350b; padding: 6px 12px; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 12px; }
    
    /* Status Filter Pills */
    .filter-pills { display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }
    .pill { padding: 8px 16px; border-radius: 20px; font-size: 12px; font-weight: bold; text-decoration: none; color: #64748b; background: #f1f5f9; text-transform: uppercase; }
    .pill.active { background: #1e3a5f; color: white; }
    
    /* Tables */
    table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 10px; }
    th, td { padding: 12px; text-align: left; border-bottom: 1px solid #f1f5f9; }
    th { background: #f8fafc; color: #64748b; font-weight: 600; }
    .badge { background: #e2e8f0; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-family: monospace; }
    .badge-active { background: #e3fcef; color: #006644; }
    .badge-used { background: #e0f2fe; color: #0369a1; }
    .badge-revoked { background: #ffebe6; color: #de350b; }
    
    @media (max-width: 768px) {
        body { flex-direction: column; }
        .mobile-header { display: flex; }
        .sidebar { position: fixed; top: 0; left: 0; bottom: 0; transform: translateX(-100%); height: 100vh; }
        .sidebar.active { transform: translateX(0); }
        .sidebar-overlay.active { display: block; }
        .main-content { padding: 16px; }
    }
</style>
<script>
    function toggleSidebar() {
        document.getElementById('sidebar').classList.toggle('active');
        document.getElementById('sidebarOverlay').classList.toggle('active');
    }
</script>
"""

# ==========================================
# 🎟️ VOUCHERS TEMPLATE
# ==========================================

VOUCHERS_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HANS WIFI - Vouchers</title>
    """ + BASE_STYLE + """
</head>
<body>
    """ + NAV_SIDEBAR + """
    <div class="main-content">
        <div class="header">
            <h2>Vouchers</h2>
        </div>

        <!-- GENERATE VOUCHER FORM (Matches UI Screenshot) -->
        <div class="box" style="max-width: 600px;">
            <form action="/admin/vouchers/create" method="POST">
                <div class="form-group">
                    <label>Router / hotspot</label>
                    <select name="router" class="form-control">
                        <option value="HANS1 INTERNET KITONGA">HANS1 INTERNET KITONGA 0624667219</option>
                    </select>
                    <div class="form-subtext">Code only works when the customer is connected to this router.</div>
                </div>

                <div class="form-group">
                    <label>Package</label>
                    <select name="package_id" class="form-control" required>
                        <option value="" disabled selected>Select package</option>
                        {% for pkg in packages %}
                        <option value="{{ pkg._id }}">{{ pkg.name }} - TZS {{ pkg.price }} ({{ pkg.duration }} {{ pkg.duration_unit }})</option>
                        {% endfor %}
                    </select>
                </div>

                <div class="form-group">
                    <label>How many codes</label>
                    <input type="number" name="count" class="form-control" value="1" min="1" max="100" required>
                </div>

                <div class="form-group">
                    <label>Custom code (optional, numbers only)</label>
                    <input type="text" name="custom_code" class="form-control" placeholder="Leave empty to auto-generate digits">
                </div>

                <div class="form-group">
                    <label>Max uses per code</label>
                    <input type="number" name="max_uses" class="form-control" value="1" min="1" required>
                </div>

                <div class="form-group">
                    <label>Expires at (optional)</label>
                    <input type="datetime-local" name="expires_at" class="form-control">
                </div>

                <div class="form-group">
                    <label>Note (optional)</label>
                    <input type="text" name="note" class="form-control" placeholder="e.g. Cash sale, staff access, VIP guest">
                </div>

                <button type="submit" class="btn-primary">Generate Vouchers</button>
            </form>
        </div>

        <!-- VOUCHERS LIST TABLE & STATUS FILTERS -->
        <div class="box">
            <h3>🎟️ Voucher Collection</h3>
            
            <div class="filter-pills">
                <a href="/admin/vouchers?status=ALL" class="pill {{ 'active' if current_filter == 'ALL' else '' }}">ALL</a>
                <a href="/admin/vouchers?status=UNUSED" class="pill {{ 'active' if current_filter == 'UNUSED' else '' }}">UNUSED / ACTIVE</a>
                <a href="/admin/vouchers?status=USED" class="pill {{ 'active' if current_filter == 'USED' else '' }}">USED</a>
                <a href="/admin/vouchers?status=REVOKED" class="pill {{ 'active' if current_filter == 'REVOKED' else '' }}">REVOKED</a>
            </div>

            <table>
                <tr>
                    <th>Code</th>
                    <th>Package</th>
                    <th>Price</th>
                    <th>Uses</th>
                    <th>Created Date</th>
                    <th>Status</th>
                    <th>Action</th>
                </tr>
                {% for v in vouchers %}
                <tr>
                    <td><span class="badge">{{ v.code }}</span></td>
                    <td><b>{{ v.package_name }}</b></td>
                    <td>TZS {{ v.price }}</td>
                    <td>{{ v.used_count }}/{{ v.max_uses }}</td>
                    <td>{{ v.created_at.strftime('%Y-%m-%d %H:%M') if v.created_at else '-' }}</td>
                    <td>
                        <span class="badge {{ 'badge-active' if v.status == 'ACTIVE' else ('badge-used' if v.status == 'USED' else 'badge-revoked') }}">
                            {{ v.status }}
                        </span>
                    </td>
                    <td>
                        {% if v.status != 'REVOKED' %}
                        <a href="/admin/vouchers/revoke/{{ v._id }}" class="btn-danger" onclick="return confirm('Revoke this voucher?');">Revoke</a>
                        {% endif %}
                    </td>
                </tr>
                {% else %}
                <tr><td colspan="7" style="color: #888; text-align:center;">No vouchers found for this status.</td></tr>
                {% endfor %}
            </table>
        </div>
    </div>
</body>
</html>
"""

# ==========================================
# 👥 SESSIONS TEMPLATE WITH STATUS FILTERS
# ==========================================

SESSIONS_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HANS WIFI - Sessions</title>
    """ + BASE_STYLE + """
</head>
<body>
    """ + NAV_SIDEBAR + """
    <div class="main-content">
        <div class="header">
            <h2>Sessions</h2>
        </div>

        <div class="box">
            <div class="filter-pills">
                <a href="/admin/sessions?status=ALL" class="pill {{ 'active' if current_filter == 'ALL' else '' }}">ALL</a>
                <a href="/admin/sessions?status=ACTIVE" class="pill {{ 'active' if current_filter == 'ACTIVE' else '' }}">ACTIVE</a>
                <a href="/admin/sessions?status=EXPIRED" class="pill {{ 'active' if current_filter == 'EXPIRED' else '' }}">EXPIRED</a>
                <a href="/admin/sessions?status=REVOKED" class="pill {{ 'active' if current_filter == 'REVOKED' else '' }}">REVOKED</a>
            </div>

            <table>
                <tr>
                    <th>MAC Address</th>
                    <th>Voucher Code</th>
                    <th>Package</th>
                    <th>Expiration Time</th>
                    <th>Status</th>
                    <th>Action</th>
                </tr>
                {% for s in sessions %}
                <tr>
                    <td><b>{{ s._id }}</b></td>
                    <td><span class="badge">{{ s.code }}</span></td>
                    <td>{{ s.package_name or 'Default' }}</td>
                    <td>{{ s.expire_date.strftime('%Y-%m-%d %H:%M') if s.expire_date else '-' }}</td>
                    <td>
                        <span class="badge {{ 'badge-active' if s.status == 'ACTIVE' else 'badge-revoked' }}">
                            {{ s.status }}
                        </span>
                    </td>
                    <td>
                        {% if s.status == 'ACTIVE' %}
                            <a href="/admin/revoke/{{ s._id }}" class="btn-danger" onclick="return confirm('Disconnect session?');">Revoke</a>
                        {% endif %}
                    </td>
                </tr>
                {% else %}
                <tr><td colspan="6" style="color:#888; text-align:center;">No active sessions for this filter.</td></tr>
                {% endfor %}
            </table>
        </div>
    </div>
</body>
</html>
"""

# ==========================================
# ⚡ CONTROLLERS & ROUTES
# ==========================================

@app.route('/admin/vouchers')
def admin_vouchers():
    if not session.get('admin'):
        return redirect('/admin/login')

    status_filter = request.args.get('status', 'ALL').upper()
    query = {}
    
    if status_filter == 'UNUSED':
        query['status'] = 'ACTIVE'
    elif status_filter in ['USED', 'REVOKED']:
        query['status'] = status_filter

    vouchers = list(vouchers_col.find(query).sort("created_at", -1))
    packages = list(packages_col.find())

    return render_template_string(
        VOUCHERS_TEMPLATE,
        active_page="vouchers",
        vouchers=vouchers,
        packages=packages,
        current_filter=status_filter
    )


@app.route('/admin/vouchers/create', methods=['POST'])
def create_vouchers():
    if not session.get('admin'):
        return redirect('/admin/login')

    pkg_id = request.form.get('package_id')
    count = int(request.form.get('count', 1))
    custom_code = request.form.get('custom_code', '').strip()
    max_uses = int(request.form.get('max_uses', 1))
    note = request.form.get('note', '').strip()

    pkg = packages_col.find_one({"_id": ObjectId(pkg_id)}) if pkg_id else None
    pkg_name = pkg['name'] if pkg else "Standard"
    duration_mins = pkg['total_minutes'] if pkg else 60
    price = pkg['price'] if pkg else 0.0

    created_vouchers = []
    for i in range(count):
        code = custom_code if (custom_code and count == 1) else generate_numeric_code(6)
        v_doc = {
            "code": code,
            "package_name": pkg_name,
            "duration_minutes": duration_mins,
            "price": price,
            "max_uses": max_uses,
            "used_count": 0,
            "status": "ACTIVE",
            "note": note,
            "created_at": datetime.now(timezone.utc)
        }
        try:
            vouchers_col.insert_one(v_doc)
            created_vouchers.append(code)
        except Exception as e:
            logger.error(f"Voucher creation conflict for {code}: {e}")

    return redirect('/admin/vouchers')


@app.route('/admin/vouchers/revoke/<v_id>')
def revoke_voucher(v_id):
    if not session.get('admin'):
        return redirect('/admin/login')
    
    vouchers_col.update_one({"_id": ObjectId(v_id)}, {"$set": {"status": "REVOKED"}})
    return redirect('/admin/vouchers')


@app.route('/admin/sessions')
def admin_sessions():
    if not session.get('admin'):
        return redirect('/admin/login')

    status_filter = request.args.get('status', 'ALL').upper()
    query = {}
    if status_filter != 'ALL':
        query['status'] = status_filter

    sessions_list = list(sessions_col.find(query).sort("used_time", -1))
    return render_template_string(
        SESSIONS_TEMPLATE,
        active_page="sessions",
        sessions=sessions_list,
        current_filter=status_filter
    )


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
