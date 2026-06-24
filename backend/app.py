import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ==================================================
# DATABASE CONFIG — SQLite (production) / MySQL (local)
# ==================================================
USE_SQLITE = os.environ.get('USE_SQLITE', 'true').lower() == 'true'

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'minelytics.db')

def get_connection():
    if USE_SQLITE:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    else:
        from flask_mysqldb import MySQL
        app.config['MYSQL_HOST'] = os.environ.get('MYSQL_HOST', 'localhost')
        app.config['MYSQL_USER'] = os.environ.get('MYSQL_USER', 'root')
        app.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_PASSWORD', '')
        app.config['MYSQL_DB'] = os.environ.get('MYSQL_DB', 'tambang_db')
        mysql = MySQL(app)
        return mysql.connection

def init_sqlite():
    """Buat tabel jika belum ada (SQLite only)."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'Viewer'
        );
        CREATE TABLE IF NOT EXISTS alat_berat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kode_alat TEXT NOT NULL UNIQUE,
            jenis_alat TEXT NOT NULL,
            status_terakhir TEXT NOT NULL DEFAULT 'Idle'
        );
        CREATE TABLE IF NOT EXISTS log_aktivitas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alat_id INTEGER NOT NULL,
            status_aktivitas TEXT NOT NULL,
            waktu_mulai TIMESTAMP NOT NULL,
            waktu_selesai TIMESTAMP NULL,
            FOREIGN KEY (alat_id) REFERENCES alat_berat(id)
        );
    """)

    # Seed data jika tabel users kosong
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            [
                ('admin', 'admin123', 'Planner'),
                ('viewer', 'viewer123', 'Viewer'),
            ]
        )
        cur.executemany(
            "INSERT INTO alat_berat (kode_alat, jenis_alat, status_terakhir) VALUES (?, ?, ?)",
            [
                ('EXCA-01', 'Excavator PC2000', 'Operating'),
                ('DUMP-01', 'Dump Truck CAT 777', 'Idle'),
                ('DOZ-01', 'Dozer D6T', 'Breakdown'),
            ]
        )
    conn.commit()
    conn.close()

if USE_SQLITE:
    init_sqlite()


# ==================================================
# 1. OTENTIKASI & LOGIN REST API
# ==================================================
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, role FROM users WHERE username = ? AND password = ?", (username, password))
    user = cur.fetchone()
    cur.close()
    if not USE_SQLITE:
        pass  # MySQL connection managed by flask_mysqldb
    else:
        conn.close()

    if user:
        return jsonify({
            "success": True,
            "token": f"mock-token-enterprise-{user['id'] if isinstance(user, dict) else user[0]}",
            "user": {
                "username": user['username'] if isinstance(user, dict) else user[1],
                "role": user['role'] if isinstance(user, dict) else user[2],
            }
        }), 200
    return jsonify({"success": False, "message": "Username atau Password salah!"}), 401


# ==================================================
# 2. ENDPOINT DASHBOARD (SNAPSHOT REAL-TIME DARI STATUS_TERAKHIR)
# ==================================================
@app.route('/api/dashboard/metrics', methods=['GET'])
def get_metrics():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            COUNT(*) as total_alat,
            SUM(CASE WHEN status_terakhir = 'Operating' THEN 1 ELSE 0 END) as total_operating,
            SUM(CASE WHEN status_terakhir = 'Idle' THEN 1 ELSE 0 END) as total_idle,
            SUM(CASE WHEN status_terakhir = 'Breakdown' THEN 1 ELSE 0 END) as total_breakdown
        FROM alat_berat
    """)
    row = cur.fetchone()
    cur.close()
    if not USE_SQLITE:
        pass
    else:
        conn.close()

    total_alat = row[0] if row[0] else 0
    unit_operating = row[1] if row[1] else 0
    unit_idle = row[2] if row[2] else 0
    unit_breakdown = row[3] if row[3] else 0

    if total_alat == 0:
        pa = 0.0
        ua = 0.0
    else:
        pa = ((unit_operating + unit_idle) / total_alat) * 100
        available_units = unit_operating + unit_idle
        ua = (unit_operating / available_units) * 100 if available_units > 0 else 0.0

    return jsonify({
        "metrics": {
            "total_alat": total_alat,
            "unit_operating": unit_operating,
            "unit_idle": unit_idle,
            "unit_breakdown": unit_breakdown,
            "pa": round(pa, 1),
            "ua": round(ua, 1)
        }
    })


# ==================================================
# 3. ENDPOINT HISTORY REPORT
# ==================================================
@app.route('/api/history', methods=['GET'])
def get_history():
    start_date = request.args.get('start_date', datetime.now().strftime('%Y-%m-01'))
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d 23:59:59'))

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT l.id, a.kode_alat, a.jenis_alat, l.status_aktivitas, l.waktu_mulai, l.waktu_selesai
        FROM log_aktivitas l
        JOIN alat_berat a ON l.alat_id = a.id
        WHERE l.waktu_mulai BETWEEN ? AND ?
        ORDER BY l.waktu_mulai DESC
    """, (start_date, end_date))
    rows = cur.fetchall()
    cur.close()
    if not USE_SQLITE:
        pass
    else:
        conn.close()

    history_list = []
    for r in rows:
        wm = r[4]
        ws = r[5]

        # Convert string to datetime if SQLite (returns strings)
        if isinstance(wm, str):
            wm = datetime.strptime(wm, '%Y-%m-%d %H:%M:%S')
        if ws and isinstance(ws, str):
            ws = datetime.strptime(ws, '%Y-%m-%d %H:%M:%S')

        if ws:
            durasi = round((ws - wm).total_seconds() / 3600.0, 2)
            waktu_selesai_str = ws.strftime('%Y-%m-%d %H:%M:%S')
        else:
            durasi = None
            waktu_selesai_str = None

        history_list.append({
            "id": r[0],
            "kode_alat": r[1],
            "jenis_alat": r[2],
            "status": r[3],
            "waktu_mulai": wm.strftime('%Y-%m-%d %H:%M:%S'),
            "waktu_selesai": waktu_selesai_str,
            "durasi_jam": durasi
        })

    return jsonify(history_list)


# ==================================================
# 4. KONTROL DATA FLEET (CRUD)
# ==================================================
@app.route('/api/fleet', methods=['GET', 'POST'])
def manage_fleet():
    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'GET':
        cur.execute("SELECT id, kode_alat, jenis_alat, status_terakhir FROM alat_berat")
        rows = cur.fetchall()
        cur.close()
        if not USE_SQLITE:
            pass
        else:
            conn.close()
        return jsonify([{
            "id": r[0] if not isinstance(r, dict) else r['id'],
            "kode_alat": r[1] if not isinstance(r, dict) else r['kode_alat'],
            "jenis_alat": r[2] if not isinstance(r, dict) else r['jenis_alat'],
            "status": r[3] if not isinstance(r, dict) else r['status_terakhir']
        } for r in rows])

    elif request.method == 'POST':
        data = request.json
        kode = data.get('kode_alat')
        jenis = data.get('jenis_alat')
        status = data.get('status', 'Idle')
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        cur.execute("INSERT INTO alat_berat (kode_alat, jenis_alat, status_terakhir) VALUES (?, ?, ?)", (kode, jenis, status))
        alat_id = cur.lastrowid
        cur.execute("INSERT INTO log_aktivitas (alat_id, status_aktivitas, waktu_mulai) VALUES (?, ?, ?)", (alat_id, status, now))

        conn.commit()
        cur.close()
        if not USE_SQLITE:
            pass
        else:
            conn.close()
        return jsonify({"success": True, "message": "Armada baru berhasil didaftarkan"}), 201


@app.route('/api/fleet/<int:id_alat>/status', methods=['PUT'])
def update_status(id_alat):
    data = request.json
    status_baru = data.get('status')
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE log_aktivitas SET waktu_selesai = ? WHERE alat_id = ? AND waktu_selesai IS NULL", (now, id_alat))
    cur.execute("INSERT INTO log_aktivitas (alat_id, status_aktivitas, waktu_mulai) VALUES (?, ?, ?)", (id_alat, status_baru, now))
    cur.execute("UPDATE alat_berat SET status_terakhir = ? WHERE id = ?", (status_baru, id_alat))

    conn.commit()
    cur.close()
    if not USE_SQLITE:
        pass
    else:
        conn.close()
    return jsonify({"success": True, "message": "Log aktivitas beralih ke status baru"})


@app.route('/api/fleet/<int:id_alat>', methods=['DELETE'])
def delete_alat(id_alat):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM alat_berat WHERE id = ?", (id_alat,))
    conn.commit()
    cur.close()
    if not USE_SQLITE:
        pass
    else:
        conn.close()
    return jsonify({"success": True, "message": "Unit berhasil dihapus secara permanen"})


if __name__ == '__main__':
    app.run(port=5000, debug=True)
