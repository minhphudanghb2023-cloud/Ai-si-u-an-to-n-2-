import sqlite3
import os
import json
from datetime import datetime

import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "edusafe.db")


def archive_yesterday_moods():
    """Chuyen nhat ky cu (truoc hom nay) vao bang luu tru va xoa khoi bang chinh."""
    conn = get_db()
    c = conn.cursor()
    today = datetime.now().date().isoformat()
    c.execute("INSERT INTO mood_logs_archive (id, user_id, mood, mood_emoji, mood_label, note, safety_score, risk_level, period, created_at)"
              " SELECT id, user_id, mood, mood_emoji, mood_label, note, safety_score, risk_level, period, created_at FROM mood_logs WHERE substr(created_at,1,10) < ?", (today,))
    c.execute("DELETE FROM mood_logs WHERE substr(created_at,1,10) < ?", (today,))
    conn.commit()
    conn.close()


def get_mood_streak(user_id):
    """So ngay lien tiep gan nhat co dang nhat ky."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT created_at, period FROM mood_logs WHERE user_id=? ORDER BY created_at DESC", (user_id,))
    rows = c.fetchall()
    try:
        c.execute("SELECT created_at, period FROM mood_logs_archive WHERE user_id=? ORDER BY created_at DESC", (user_id,))
        rows = rows + c.fetchall()
    except Exception:
        pass
    dates = set()
    for row in rows:
        try:
            d = str(row["created_at"])[:10]
            dates.add(d)
        except Exception:
            pass
    conn.close()
    if not dates:
        return 0
    sorted_dates = sorted(dates, reverse=True)
    from datetime import date as _date, timedelta as _td
    streak = 1
    try:
        prev = _date.fromisoformat(sorted_dates[0])
        for d in sorted_dates[1:]:
            cur = _date.fromisoformat(d)
            if prev - cur == _td(days=1):
                streak += 1
                prev = cur
            elif prev == cur:
                pass
            else:
                break
    except Exception:
        pass
    return streak


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'student',
        phone TEXT DEFAULT '',
        class_name TEXT DEFAULT '',
        parent_id INTEGER DEFAULT NULL,
        student_code TEXT DEFAULT '',
        is_active INTEGER DEFAULT 1,
        last_login TIMESTAMP DEFAULT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT UNIQUE NOT NULL,
        user_id INTEGER,
        model_used TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES sessions(session_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS mood_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        mood TEXT DEFAULT 'binhthuong',
        mood_emoji TEXT DEFAULT '',
        mood_label TEXT DEFAULT '',
        note TEXT DEFAULT '',
        safety_score INTEGER DEFAULT 85,
        risk_level TEXT DEFAULT 'low',
        period TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""");
    try:
        c.execute("ALTER TABLE mood_logs ADD COLUMN period TEXT DEFAULT ''")
    except Exception:
        pass

    # Archive gach tung nhat ky cu (truoc hom nay)
    try:
        c.execute("CREATE TABLE IF NOT EXISTS mood_logs_archive (id INTEGER, user_id INTEGER, mood TEXT, mood_emoji TEXT, mood_label TEXT, note TEXT, safety_score INTEGER, risk_level TEXT, period TEXT, created_at TIMESTAMP)")
    except Exception:
        pass

    c.execute("""CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        student_name TEXT DEFAULT '',
        class_name TEXT DEFAULT '',
        report_type TEXT DEFAULT 'other',
        description TEXT DEFAULT '',
        location TEXT DEFAULT '',
        witnesses TEXT DEFAULT '',
        severity TEXT DEFAULT 'medium',
        status TEXT DEFAULT 'pending',
        notes TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        severity TEXT DEFAULT 'warning',
        target_role TEXT DEFAULT 'teacher',
        status TEXT DEFAULT 'unread',
        notes TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS risk_assessments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        user_id INTEGER,
        risk_level TEXT DEFAULT 'low',
        risk_score INTEGER DEFAULT 0,
        factors TEXT DEFAULT '[]',
        recommendation TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS quiz_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        score INTEGER DEFAULT 0,
        total INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE NOT NULL,
        value TEXT NOT NULL
    )""")

    _seed_data(c)
    conn.commit()
    conn.close()


def _seed_data(c):
    from auth import hash_password

    c.execute("SELECT COUNT(*) as cnt FROM users")
    if c.fetchone()["cnt"] == 0:
        users = [
            ("admin", "admin@edusafe.vn", hash_password("admin123"), "Quản trị viên", "admin", "0123456789", "", None, "ADMIN01"),
            ("gv001", "gv001@edusafe.vn", hash_password("123456"), "Nguyễn Văn Giáo", "teacher", "0987654321", "8A", None, "GV001"),
            ("gv002", "gv002@edusafe.vn", hash_password("123456"), "Trần Thị Dạy", "teacher", "0111222333", "8B", None, "GV002"),
            ("hs001", "hs001@edusafe.vn", hash_password("123456"), "Nguyễn Minh Anh", "student", "0900000001", "8A", None, "HS001"),
            ("hs002", "hs002@edusafe.vn", hash_password("123456"), "Lê Văn Bình", "student", "0900000002", "8A", None, "HS002"),
            ("hs003", "hs003@edusafe.vn", hash_password("123456"), "Phạm Thị Cẩm", "student", "0900000003", "8B", None, "HS003"),
            ("hs004", "hs004@edusafe.vn", hash_password("123456"), "Hoàng Văn Dũng", "student", "0900000004", "8B", None, "HS004"),
            ("ph001", "ph001@edusafe.vn", hash_password("123456"), "Nguyễn Văn Phụ", "parent", "0911111111", "", None, "PH001"),
            ("ph002", "ph002@edusafe.vn", hash_password("123456"), "Lê Thị Hồng", "parent", "0922222222", "", None, "PH002"),
        ]
        c.executemany("INSERT INTO users (username, email, password_hash, full_name, role, phone, class_name, parent_id, student_code) VALUES (?,?,?,?,?,?,?,?,?)", users)

        c.execute("UPDATE users SET parent_id = (SELECT id FROM users WHERE username='ph001') WHERE username='hs001'")
        c.execute("UPDATE users SET parent_id = (SELECT id FROM users WHERE username='ph002') WHERE username='hs003'")

        moods = [
            (4, "vui", "😊", "Vui vẻ", "Hôm nay rất vui, học bài tốt", 90, "low"),
            (4, "binhthuong", "😐", "Bình thường", "Bình thường, không có gì đặc biệt", 85, "low"),
            (4, "buon", "😢", "Buồn bã", "Bị bạn trong lớp trêu chọc", 55, "medium"),
            (4, "loangiang", "😰", "Lo lắng", "Sợ đi học, sợ gặp bạn ấy", 45, "high"),
            (4, "tucgian", "😡", "Tức giận", "Bị đánh đập ở sân trường", 35, "high"),
            (5, "vui", "😊", "Vui vẻ", "Chơi với bạn thân, rất vui", 95, "low"),
            (5, "binhthuong", "😐", "Bình thường", "Hoc bai bình thường", 80, "low"),
        ]
        for uid, mood, emoji, label, note, score, risk in moods:
            c.execute("INSERT INTO mood_logs (user_id, mood, mood_emoji, mood_label, note, safety_score, risk_level) VALUES (?,?,?,?,?,?,?)", (uid, mood, emoji, label, note, score, risk))

        reports = [
            (4, "Nguyễn Minh Anh", "8A", "physical", "Bị bạn đánh ở sân trường vừa rồi", "Sân trường", "Lê Văn Bình", "high", "pending"),
            (4, "Nguyễn Minh Anh", "8A", "verbal", "Bị bạn trêu chọc mỗi ngày", "Lớp học", "", "medium", "in_progress"),
            (5, "Lê Văn Bình", "8A", "cyber", "Bị đăng ảnh chế lên nhóm lớp", "Online", "Nhiều bạn", "high", "pending"),
        ]
        for uid, name, cls, rtype, desc, loc, wit, sev, status in reports:
            c.execute("INSERT INTO reports (user_id, student_name, class_name, report_type, description, location, witnesses, severity, status) VALUES (?,?,?,?,?,?,?,?,?)", (uid, name, cls, rtype, desc, loc, wit, sev, status))

        alerts = [
            (4, "Cảnh báo tâm lý", "Hoc sinh Nguyễn Minh Anh có dấu hiệu bất ổn", "critical", "teacher"),
            (5, "Báo cáo bạo lực", "Có báo cáo về bạo lực thể chất tại sân trường", "warning", "teacher"),
            (4, "Cảnh báo nguy cơ", "Hoc sinh có tiêu chí nguy cơ cao", "critical", "admin"),
        ]
        for uid, title, msg, sev, target in alerts:
            c.execute("INSERT INTO alerts (user_id, title, message, severity, target_role) VALUES (?,?,?,?,?)", (uid, title, msg, sev, target))

        c.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('ai_sensitivity', 'high')")


# ==================== USER ====================
def create_user(username, email, password_hash, full_name, role, phone="", class_name="", parent_id=None, student_code=""):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO users (username, email, password_hash, full_name, role, phone, class_name, parent_id, student_code, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
              (username, email, password_hash, full_name, role, phone, class_name, parent_id, student_code, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    user_id = c.lastrowid
    conn.commit()
    conn.close()
    return user_id


def get_user_by_username(username):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_email(email):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email=?", (email,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def get_student_profile(user_id):
    user = get_user_by_id(user_id)
    if not user:
        return None
    moods = get_mood_logs(user_id=user_id, limit=10)
    quiz = get_quiz_score(user_id)
    return {"user": user, "recent_moods": moods or [], "quiz": quiz}


def get_all_users(role=None):
    conn = get_db()
    c = conn.cursor()
    if role:
        c.execute("SELECT id, username, email, full_name, role, phone, class_name, is_active, student_code, created_at FROM users WHERE role=?", (role,))
    else:
        c.execute("SELECT id, username, email, full_name, role, phone, class_name, is_active, student_code, created_at FROM users")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_user(user_id, **kwargs):
    conn = get_db()
    c = conn.cursor()
    allowed = ["full_name", "email", "phone", "class_name", "is_active"]
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if updates:
        set_clause = ", ".join(f"{k}=?" for k in updates)
        c.execute(f"UPDATE users SET {set_clause} WHERE id=?", list(updates.values()) + [user_id])
    conn.commit()
    conn.close()


def delete_user(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()


def update_user_password(user_id, new_hash):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET password_hash=? WHERE id=?", (new_hash, user_id))
    conn.commit()
    conn.close()


# ==================== SESSION ====================
def create_session(session_id, user_id=None, model_used=""):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO sessions (session_id, user_id, model_used, created_at) VALUES (?,?,?,?)",
              (session_id, user_id, model_used, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def delete_chat_session(session_id, user_id=None):
    conn = get_db()
    c = conn.cursor()
    if user_id is None:
        c.execute("DELETE FROM messages WHERE session_id=?", (session_id,))
        c.execute("DELETE FROM sessions WHERE session_id=?", (session_id,))
    else:
        c.execute("DELETE FROM messages WHERE session_id=?", (session_id,))
        c.execute("DELETE FROM sessions WHERE session_id=? AND user_id=?", (session_id, user_id))
    conn.commit()
    deleted = c.rowcount
    conn.close()
    return deleted


def save_message(session_id, role, content):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO messages (session_id, role, content, created_at) VALUES (?,?,?,?)", (session_id, role, content, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def get_user_sessions(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("""SELECT s.session_id, s.model_used, s.created_at,
        (SELECT content FROM messages m WHERE m.session_id=s.session_id AND m.role='user' ORDER BY m.id ASC LIMIT 1) AS first_msg
        FROM sessions s WHERE s.user_id=? ORDER BY s.created_at DESC""", (user_id,))
    rows = c.fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        d["description"] = (d.pop("first_msg") or "")
        results.append(d)
    return results


def get_session_messages(session_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT role, content, created_at FROM messages WHERE session_id=? ORDER BY created_at", (session_id,))
    rows = c.fetchall()
    conn.close()
    return [{"role": r["role"], "content": r["content"]} for r in rows]


# ==================== MOOD ====================
def save_mood_log(user_id, mood, mood_emoji, mood_label, note, safety_score, risk_level, period=""):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO mood_logs (user_id, mood, mood_emoji, mood_label, note, safety_score, risk_level, period, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
              (user_id, mood, mood_emoji, mood_label, note, safety_score, risk_level, period, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def get_mood_archive(user_id=None, limit=50):
    conn = get_db()
    c = conn.cursor()
    if user_id:
        c.execute("SELECT * FROM mood_logs_archive WHERE user_id=? ORDER BY created_at DESC LIMIT ?", (user_id, limit))
    else:
        c.execute("SELECT * FROM mood_logs_archive ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_mood_log(log_id, user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM mood_logs WHERE id=? AND user_id=?", (log_id, user_id))
    conn.commit()
    deleted = c.rowcount
    conn.close()
    return deleted


def get_mood_logs(user_id=None, limit=30):
    conn = get_db()
    c = conn.cursor()
    if user_id:
        c.execute("SELECT * FROM mood_logs WHERE user_id=? ORDER BY created_at DESC LIMIT ?", (user_id, limit))
    else:
        c.execute("SELECT * FROM mood_logs ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_mood_logs():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM mood_logs ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ==================== REPORTS ====================
def create_report(user_id, student_name, class_name, report_type, description, location, witnesses, severity):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO reports (user_id, student_name, class_name, report_type, description, location, witnesses, severity, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
              (user_id, student_name, class_name, report_type, description, location, witnesses, severity, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    report_id = c.lastrowid
    c.execute("INSERT INTO alerts (user_id, title, message, severity, target_role, created_at) VALUES (?,?,?,?,?,?)",
              (user_id, f"Báo cáo mới: {report_type}", f"Một học sinh gửi báo cáo ẩn danh", severity, "teacher", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    return report_id


def delete_report(report_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM reports WHERE id=?", (report_id,))
    conn.commit()
    deleted = c.rowcount
    conn.close()
    return deleted


def get_all_reports():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM reports ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_report(report_id, status=None, notes=None):
    conn = get_db()
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if status and notes:
        c.execute("UPDATE reports SET status=?, notes=?, updated_at=? WHERE id=?", (status, notes, now, report_id))
    elif status:
        c.execute("UPDATE reports SET status=?, updated_at=? WHERE id=?", (status, now, report_id))
    elif notes:
        c.execute("UPDATE reports SET notes=?, updated_at=? WHERE id=?", (notes, now, report_id))
    conn.commit()
    conn.close()


# ==================== ALERTS ====================
def create_alert(user_id, title, message, severity, target_role):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO alerts (user_id, title, message, severity, target_role, created_at) VALUES (?,?,?,?,?,?)", (user_id, title, message, severity, target_role, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def delete_alert(alert_id, target_role=None):
    conn = get_db()
    c = conn.cursor()
    if target_role:
        c.execute("DELETE FROM alerts WHERE id=? AND target_role=?", (alert_id, target_role))
    else:
        c.execute("DELETE FROM alerts WHERE id=?", (alert_id,))
    conn.commit()
    deleted = c.rowcount
    conn.close()
    return deleted


def get_all_alerts(target_role=None):
    conn = get_db()
    c = conn.cursor()
    if target_role:
        c.execute("SELECT * FROM alerts WHERE target_role=? ORDER BY created_at DESC", (target_role,))
    else:
        c.execute("SELECT * FROM alerts ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_alert(alert_id, notes=None, status=None):
    conn = get_db()
    c = conn.cursor()
    if notes:
        c.execute("UPDATE alerts SET notes=? WHERE id=?", (notes, alert_id))
    if status:
        c.execute("UPDATE alerts SET status=? WHERE id=?", (status, alert_id))
    conn.commit()
    conn.close()


def get_unread_alert_count(target_role):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as cnt FROM alerts WHERE target_role=? AND status='unread'", (target_role,))
    cnt = c.fetchone()["cnt"]
    conn.close()
    return cnt


def mark_alerts_read(target_role):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE alerts SET status='read' WHERE target_role=?", (target_role,))
    conn.commit()
    conn.close()


# ==================== RISK ====================
def save_risk_assessment(session_id, user_id, risk_level, risk_score, factors, recommendation):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO risk_assessments (session_id, user_id, risk_level, risk_score, factors, recommendation, created_at) VALUES (?,?,?,?,?,?,?)",
              (session_id, user_id, risk_level, risk_score, json.dumps(factors), recommendation, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def get_latest_risk_assessment(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT risk_level, risk_score, factors, recommendation, created_at FROM risk_assessments WHERE user_id=? ORDER BY created_at DESC LIMIT 1", (user_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


# ==================== QUIZ ====================
def save_quiz_score(user_id, score, total):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO quiz_scores (user_id, score, total, created_at) VALUES (?,?,?,?)", (user_id, score, total, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def get_quiz_score(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT score, total FROM quiz_scores WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else {"score": 0, "total": 0}


# ==================== CONFIG ====================
def save_config(key, value):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?,?)", (key, value))
    conn.commit()
    conn.close()


def get_config(key, default=None):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT value FROM config WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row["value"] if row else default


init_db()
