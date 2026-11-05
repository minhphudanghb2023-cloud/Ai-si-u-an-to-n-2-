"""
EduSafe AI - Backup & Data Protection Module
Tự động backup database an toàn vĩnh viễn
"""
import os
import shutil
import json
import zipfile
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Múi giờ Hà Nội (UTC+7)
HANOI_TZ = timezone(timedelta(hours=7))

def now_hanoi():
    """Lấy thời gian hiện tại theo giờ Hà Nội"""
    return datetime.now(HANOI_TZ)

# ============ CẤU HÌNH BACKUP ============
BACKUP_CONFIG = {
    "backup_dir": os.path.join(os.path.expanduser("~"), "OneDrive", "EduSafe_Backup"),
    "local_backup_dir": os.path.join(os.path.dirname(__file__), "backups"),
    "max_backups": 0,            # 0 = không giới hạn số bản backup (lưu vĩnh viễn)
    "max_days": 0,               # 0 = không giới hạn ngày (lưu vĩnh viễn)
    "auto_backup_hours": 4,      # Backup mỗi 4 giờ
    "db_file": os.path.join(os.path.dirname(__file__), "edusafe.db"),
}

def ensure_backup_dirs():
    """Tạo thư mục backup nếu chưa có"""
    for key in ["backup_dir", "local_backup_dir"]:
        Path(BACKUP_CONFIG[key]).mkdir(parents=True, exist_ok=True)

def get_timestamp():
    """Lấy timestamp dạng YYYYMMDD_HHMMSS"""
    return now_hanoi().strftime("%Y%m%d_%H%M%S")

def backup_database(source=None, backup_type="manual"):
    """
    Backup database đến thư mục local và OneDrive
    backup_type: "manual", "auto", "pre_update", "daily"
    """
    ensure_backup_dirs()
    source = source or BACKUP_CONFIG["db_file"]
    
    if not os.path.exists(source):
        return {"success": False, "error": "Database file not found"}
    
    timestamp = get_timestamp()
    filename = f"edusafe_{backup_type}_{timestamp}.db"
    
    results = {
        "success": True,
        "timestamp": timestamp,
        "type": backup_type,
        "backups": []
    }
    
    # Backup 1: Local backup
    local_dest = os.path.join(BACKUP_CONFIG["local_backup_dir"], filename)
    try:
        shutil.copy2(source, local_dest)
        results["backups"].append({
            "location": "local",
            "path": local_dest,
            "size": os.path.getsize(local_dest)
        })
    except Exception as e:
        results["success"] = False
        results["error"] = f"Local backup failed: {e}"
    
    # Backup 2: OneDrive backup (nếu có)
    try:
        onedrive_dest = os.path.join(BACKUP_CONFIG["backup_dir"], filename)
        shutil.copy2(source, onedrive_dest)
        results["backups"].append({
            "location": "onedrive",
            "path": onedrive_dest,
            "size": os.path.getsize(onedrive_dest)
        })
    except Exception as e:
        # OneDrive không có - không sao, backup local vẫn OK
        print(f"OneDrive backup skipped: {e}")
    
    # Dọn dẹp backup cũ (giữ lại max_backups bản)
    cleanup_old_backups()
    
    # Log backup
    log_backup_event(filename, backup_type, results["success"])
    
    return results

def cleanup_old_backups():
    """Xóa backup cũ theo số lượng và số ngày (0 = không giới hạn)"""
    max_backups = BACKUP_CONFIG["max_backups"]  # 0 = unlimited
    max_days = BACKUP_CONFIG["max_days"]        # 0 = unlimited
    from datetime import timedelta
    
    # Nếu cả 2 đều = 0 thì không xóa gì cả (lưu vĩnh viễn)
    if max_backups == 0 and max_days == 0:
        return
    
    cutoff_date = now_hanoi() - timedelta(days=max_days) if max_days > 0 else None
    
    for backup_type_dir in ["local_backup_dir", "backup_dir"]:
        backup_dir = BACKUP_CONFIG[backup_type_dir]
        try:
            backups = []
            for f in os.listdir(backup_dir):
                if f.startswith("edusafe_") and f.endswith(".db"):
                    filepath = os.path.join(backup_dir, f)
                    stat = os.stat(filepath)
                    mtime = datetime.fromtimestamp(stat.st_mtime)
                    backups.append((f, filepath, mtime))
            
            # Sắp xếp mới nhất trước
            backups.sort(key=lambda x: x[2], reverse=True)
            
            deleted_count = 0
            
            # Xóa theo số ngày (nếu cấu hình > 0)
            if cutoff_date:
                for f, filepath, mtime in backups[:]:
                    if mtime < cutoff_date:
                        try:
                            os.remove(filepath)
                            deleted_count += 1
                        except Exception:
                            pass
                        backups.remove((f, filepath, mtime))
            
            # Xóa theo số lượng (nếu cấu hình > 0, giữ lại max_backups bản mới nhất)
            if max_backups > 0 and len(backups) > max_backups:
                to_delete = backups[max_backups:]
                for f, filepath, mtime in to_delete:
                    try:
                        os.remove(filepath)
                        deleted_count += 1
                    except Exception:
                        pass
            
            if deleted_count > 0:
                print(f"Cleaned up {deleted_count} old backups from {backup_type_dir}")
                
        except Exception as e:
            print(f"Cleanup error: {e}")

def log_backup_event(filename, backup_type, success):
    """Ghi log backup"""
    log_file = os.path.join(BACKUP_CONFIG["local_backup_dir"], "backup.log")
    timestamp = now_hanoi().strftime("%Y-%m-%d %H:%M:%S")
    status = "OK" if success else "FAILED"
    
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {backup_type}: {filename} - {status}\n")
    except Exception:
        pass

def export_all_data(user_id=None):
    """
    Export toàn bộ dữ liệu ra file JSON
    user_id: nếu None thì export tất cả, nếu có thì export của user đó
    """
    import database as db
    
    data = {
        "export_date": now_hanoi().isoformat(),
        "app": "EduSafe AI",
        "version": "2.0",
        "data": {}
    }
    
    try:
        # Users
        conn = db.get_db()
        c = conn.cursor()
        
        if user_id:
            c.execute("SELECT * FROM users WHERE id=?", (user_id,))
            data["data"]["users"] = [dict(row) for row in c.fetchall()]
            
            c.execute("SELECT * FROM mood_logs WHERE user_id=?", (user_id,))
            data["data"]["mood_logs"] = [dict(row) for row in c.fetchall()]
            
            c.execute("SELECT * FROM mood_logs_archive WHERE user_id=?", (user_id,))
            data["data"]["mood_archive"] = [dict(row) for row in c.fetchall()]
            
            c.execute("SELECT * FROM reports WHERE user_id=?", (user_id,))
            data["data"]["reports"] = [dict(row) for row in c.fetchall()]
        else:
            c.execute("SELECT * FROM users")
            data["data"]["users"] = [dict(row) for row in c.fetchall()]
            
            c.execute("SELECT * FROM mood_logs")
            data["data"]["mood_logs"] = [dict(row) for row in c.fetchall()]
            
            c.execute("SELECT * FROM mood_logs_archive")
            data["data"]["mood_archive"] = [dict(row) for row in c.fetchall()]
            
            c.execute("SELECT * FROM reports")
            data["data"]["reports"] = [dict(row) for row in c.fetchall()]
        
        conn.close()
        
        # Thống kê
        data["stats"] = {
            "total_users": len(data["data"].get("users", [])),
            "total_mood_logs": len(data["data"].get("mood_logs", [])) + len(data["data"].get("mood_archive", [])),
            "total_reports": len(data["data"].get("reports", []))
        }
        
        return data
        
    except Exception as e:
        return {"error": str(e)}

def import_data(data):
    """
    Import dữ liệu từ file JSON
    """
    import database as db
    
    try:
        conn = db.get_db()
        c = conn.cursor()
        
        imported = {"users": 0, "mood_logs": 0, "reports": 0}
        
        # Import users
        for user in data.get("data", {}).get("users", []):
            try:
                c.execute("""
                    INSERT OR IGNORE INTO users (id, username, email, password_hash, full_name, role, phone, class_name, parent_id, student_code, is_active, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user.get("id"), user.get("username"), user.get("email"),
                    user.get("password_hash"), user.get("full_name"), user.get("role"),
                    user.get("phone"), user.get("class_name"), user.get("parent_id"),
                    user.get("student_code"), user.get("is_active", 1), user.get("created_at")
                ))
                imported["users"] += 1
            except Exception:
                pass
        
        # Import mood_logs
        for log in data.get("data", {}).get("mood_logs", []):
            try:
                c.execute("""
                    INSERT OR IGNORE INTO mood_logs (id, user_id, mood, mood_emoji, mood_label, note, safety_score, risk_level, period, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    log.get("id"), log.get("user_id"), log.get("mood"),
                    log.get("mood_emoji"), log.get("mood_label"), log.get("note"),
                    log.get("safety_score"), log.get("risk_level"), log.get("period"),
                    log.get("created_at")
                ))
                imported["mood_logs"] += 1
            except Exception:
                pass
        
        # Import mood_logs_archive
        for log in data.get("data", {}).get("mood_archive", []):
            try:
                c.execute("""
                    INSERT OR IGNORE INTO mood_logs_archive (id, user_id, mood, mood_emoji, mood_label, note, safety_score, risk_level, period, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    log.get("id"), log.get("user_id"), log.get("mood"),
                    log.get("mood_emoji"), log.get("mood_label"), log.get("note"),
                    log.get("safety_score"), log.get("risk_level"), log.get("period"),
                    log.get("created_at")
                ))
                imported["mood_logs"] += 1
            except Exception:
                pass
        
        # Import reports
        for report in data.get("data", {}).get("reports", []):
            try:
                c.execute("""
                    INSERT OR IGNORE INTO reports (id, user_id, student_name, class_name, report_type, description, location, witnesses, severity, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    report.get("id"), report.get("user_id"), report.get("student_name"),
                    report.get("class_name"), report.get("report_type"), report.get("description"),
                    report.get("location"), report.get("witnesses"), report.get("severity"),
                    report.get("status"), report.get("created_at")
                ))
                imported["reports"] += 1
            except Exception:
                pass
        
        conn.commit()
        conn.close()
        
        return {"success": True, "imported": imported}
        
    except Exception as e:
        return {"error": str(e)}

def get_backup_list():
    """Lấy danh sách backup hiện có"""
    ensure_backup_dirs()
    
    backups = []
    for location in ["local", "onedrive"]:
        backup_dir = BACKUP_CONFIG["local_backup_dir" if location == "local" else "backup_dir"]
        try:
            for f in os.listdir(backup_dir):
                if f.startswith("edusafe_") and f.endswith(".db"):
                    filepath = os.path.join(backup_dir, f)
                    stat = os.stat(filepath)
                    backups.append({
                        "filename": f,
                        "location": location,
                        "path": filepath,
                        "size": stat.st_size,
                        "size_mb": round(stat.st_size / (1024*1024), 2),
                        "created": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
        except Exception:
            pass
    
    # Sort theo thời gian mới nhất
    backups.sort(key=lambda x: x["created"], reverse=True)
    return backups

def start_auto_backup():
    """Khởi động thread backup tự động"""
    def backup_loop():
        while True:
            time.sleep(BACKUP_CONFIG["auto_backup_hours"] * 3600)  # Chờ N giờ
            try:
                print("[Auto Backup] Đang backup database...")
                result = backup_database(backup_type="auto")
                if result["success"]:
                    print(f"[Auto Backup] OK: {result['timestamp']}")
            except Exception as e:
                print(f"[Auto Backup] Loi: {e}")
    
    thread = threading.Thread(target=backup_loop, daemon=True)
    thread.start()
    print(f"[Backup] Auto-backup enabled (moi {BACKUP_CONFIG['auto_backup_hours']}h)")

# ============ BACKUP TRƯỚC KHI UPDATE ============
def backup_before_update():
    """Backup trước khi update (gọi trước khi sửa database)"""
    return backup_database(backup_type="pre_update")
