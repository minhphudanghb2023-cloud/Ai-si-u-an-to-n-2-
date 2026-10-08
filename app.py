import os
import json
import uuid
import re
import requests
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, g
from dotenv import load_dotenv
import database as db
import ai_brain
from auth import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    decode_token, require_auth, require_role, require_permission,
    ROLES, get_user_permissions
)

load_dotenv()

try:
    db.archive_yesterday_moods()
except Exception as e:
    print("archive error:", e)

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.getenv("SECRET_KEY", "edusafe-secret")

# Tat cache trang de moi lan chuyen trang deu tai noi dung moi
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

@app.after_request
def no_cache(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

API_BASE = "https://opencode.ai/zen/v1"
MODELS = {
    "gemini-3.5-flash-lite": {"name": "Gemini 3.5 Flash Lite"},
    "deepseek-v2-flash": {"name": "DeepSeek V2 Flash"},
    "deepseek-v4.1-flash": {"name": "DeepSeek V4.1 Flash"},
    "gpt-5-nano": {"name": "GPT-5 Nano"},
    "muse-spark-1.3": {"name": "Muse Spark 1.3"},
}

# Thu tuu tien model re -> dat khi goi AI (model dau tien la mac dinh)
MODEL_FALLBACK_CHAIN = [
    "gemini-3.5-flash-lite",
    "deepseek-v4.1-flash",
    "deepseek-v2-flash",
    "gpt-5-nano",
    "muse-spark-1.3",
]
DEFAULT_MODEL = MODEL_FALLBACK_CHAIN[0]

def strip_accents(s):
    """Bo dau tieng Viet de so khop tu khoa (vd 'bị đánh' -> 'bi danh')."""
    import unicodedata
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D")


VIOLENCE_KEYWORDS = {
    "critical": [r"tu\s*tu", r"tu\s*hai", r"muon\s*chet", r"khong\s*muon\s*song", r"giet\s*minh", r"ket\s*lieu"],
    "high": [r"bi\s*danh\s*dap", r"bi\s*danh", r"bi\s*bat\s*nat", r"de\s*doa\s*giet", r"mang\s*vu\s*khi", r"tran\s*lot"],
    "medium": [r"danh\s*nhau", r"danh\s*nguoi", r"bao\s*luc", r"de\s*doa", r"quay\s*roi", r"tat\s*mat", r"tat\s*vao", r"dam\s*da"],
    "low": [r"bi\s*bat\s*nat", r"treu\s*choc", r"treu", r"choc", r"co\s*lap", r"tay\s*chay", r"ban\s*be\s*ghet", r"so\s*di\s*hoc", r"buon\s*ba", r"noi\s*xau", r"\bdanh\b", r"bi\s*ham\s*doa", r"ham\s*doa"],
}

SYSTEM_PROMPT = """Bạn là AI Trợ Lý Phòng Chống Bạo Lực Học Đường.
NHIỆM VỤ: Tư vấn, phát hiện nguy cơ, hướng dẫn kỹ năng đối phó, kết nối hỗ trợ.
Khi phát hiện nguy cơ, thêm [RISK_LEVEL:critical/high/medium/low].
Hotline: 111. Trả lời tiếng Việt, ngắn gọn, dễ hiểu."""


def detect_violence(text):
    text_lower = strip_accents(text.lower())
    for level in ["critical", "high", "medium", "low"]:
        for pattern in VIOLENCE_KEYWORDS[level]:
            if re.search(pattern, text_lower):
                return True, level
    return False, None


def calculate_risk_score(text):
    score = 0
    factors = []
    text_lower = strip_accents(text.lower())
    is_violence, violence_level = detect_violence(text)
    if is_violence:
        level_scores = {"critical": 40, "high": 30, "medium": 20, "low": 10}
        score += level_scores.get(violence_level, 10)
        factors.append(f"Bạo lực {violence_level}")
    for pattern, label, pts in [
        (r"can thang|stress|ap luc", "Căng thẳng", 15),
        (r"lo lang|so hai", "Lo âu", 15),
        (r"tuc gian|giet|noi dien", "Tức giận", 12),
        (r"buon|khoc|tuyet vong", "Buồn bã", 12),
    ]:
        if re.search(pattern, text_lower):
            score += pts
            factors.append(label)
    if any(w in text_lower for w in ["tu tu", "tu hai", "muon chet"]):
        score = min(score + 30, 100)
        factors.append("Nguy cơ tự hại")
    risk_level = "critical" if score >= 70 else "high" if score >= 50 else "medium" if score >= 30 else "low"
    return risk_level, min(score, 100), factors


def assess_student_state(user_id, text, text_risk_score, text_factors):
    """Danh gia trang thai tam ly cua hoc sinh: noi dung vua gui + nhat ky gan day.

    Tra ve (state_label, effective_score, effective_factors)."""
    logs = db.get_mood_logs(user_id=user_id, limit=5)
    if logs:
        avg_safety = sum(l.get("safety_score", 85) if l.get("safety_score") is not None else 85 for l in logs) / len(logs)
        neg = sum(1 for l in logs if (l.get("safety_score") is not None and l["safety_score"] < 70))
        recent_moods = [l.get("mood_label", l.get("mood", "")) for l in logs]
    else:
        avg_safety = 85
        neg = 0
        recent_moods = []
    eff = max(text_risk_score, int(100 - avg_safety))
    factors = list(text_factors)
    if recent_moods:
        factors.append(f"Nhật ký gần đây: {', '.join(recent_moods)}")
    if neg >= 3:
        eff = max(eff, 65)
        factors.append(f"{neg} nhật ký gần đây không ổn")
    if neg >= 5:
        eff = max(eff, 80)
        factors.append("Hàng loạt nhật ký không ổn")
    eff = min(eff, 100)
    if eff >= 70:
        label = "Nguy hiểm"
    elif eff >= 50:
        label = "Bất ổn"
    elif eff >= 30:
        label = "Cần theo dõi"
    else:
        label = "Ổn định"
    return label, eff, factors


def _try_one_model(api_key, model_id, messages):
    """Goi 1 model, tra ve (reply | None, loi | None)."""
    url = f"{API_BASE}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model_id, "messages": messages, "max_tokens": 2048, "temperature": 0.7}
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if resp.status_code != 200:
            return None, f"{model_id}: HTTP {resp.status_code} {resp.text[:200]}"
        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            return None, f"{model_id}: khong co choices"
        content = choices[0].get("message", {}).get("content", "").strip()
        if not content:
            return None, f"{model_id}: reply rong"
        return content, None
    except requests.exceptions.Timeout:
        return None, f"{model_id}: timeout"
    except Exception as e:
        return None, f"{model_id}: {type(e).__name__} {str(e)[:200]}"


def call_ai(model_id, messages):
    """Goi AI theo chuoi du phong. Tra ve (reply, used_offline: bool)."""
    api_key = os.getenv("OPENCODE_API_KEY", "")
    if not api_key:
        print("[AI] thieu OPENCODE_API_KEY -> dung che do offline")
        return None, True
    ordered = [model_id] + [m for m in MODEL_FALLBACK_CHAIN if m != model_id]
    errors = []
    for mid in ordered:
        if mid not in MODELS:
            continue
        reply, err = _try_one_model(api_key, mid, messages)
        if reply:
            return reply, False
        errors.append(err)
    print("[AI] tat ca model that bai:", " | ".join(errors))
    return None, True


def call_gemini(messages):
    """Goi Gemini (free tier) voi lich su hoi thoai. Tra ve reply hoac None."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    gemini_system = (
        "Bạn là AI Trợ Lý Phòng Chống Bạo Lực Học Đường tên EduSafe AI. "
        "Nhiệm vụ: tư vấn an toàn học đường, lắng nghe học sinh, hướng dẫn kỹ năng đối phó, "
        "kết nối hỗ trợ. Trả lời tiếng Việt, tự nhiên, thân thiện, ngắn gọn, dễ hiểu, "
        "KHÔNG trả lời theo mẫu cứng nhắc. Khi phát hiện nguy cơ tự hại hãy khuyên gọi "
        "Tổng đài 111 ngay. Hotline: 111."
    )
    contents = []
    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        if m["role"] == "system":
            continue
        contents.append({"role": role, "parts": [{"text": m["content"]}]})
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           "gemini-3.5-flash-lite:generateContent?key=" + api_key)
    payload = {
        "system_instruction": {"parts": [{"text": gemini_system}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.8, "maxOutputTokens": 1024},
    }
    try:
        resp = requests.post(url, json=payload, timeout=60)
        if resp.status_code != 200:
            print("[Gemini] loi:", resp.status_code, resp.text[:200])
            return None
        data = resp.json()
        ans = (data.get("candidates", [{}])[0]
                   .get("content", {}).get("parts", [{}])[0]
                   .get("text", "")).strip()
        return ans or None
    except Exception as e:
        print("[Gemini] exception:", e)
        return None


def offline_reply(user_text):
    """Tra loi tu van cuc bo khi dich vu AI ban (luon co cau tra loi)."""
    # Chuan hoa khong dau de nhan dung ca input co dau va khong dau
    t = strip_accents(user_text.lower())
    hotline = "\n\n📞 Nếu cần giúp ngay, hãy gọi Tổng đài bảo vệ trẻ em 111 (miễn phí 24/7) hoặc kể cho giáo viên/người thân tin cậy."

    def has(*words):
        # Khop theo ranh gioi tu de tranh nham (vd 'chọc' chua 'học', 'khi' chua 'hi')
        return any(re.search(r"\b" + re.escape(w) + r"\b", t) for w in words)

    if has("tu tu", "tu hai", "muon chet", "khong muon song", "ket lieu"):
        return ("Mình rất lo cho bạn lúc này. Cảm xúc này rất nặng nề, nhưng bạn không hề một mình và luôn có người sẵn sàng giúp bạn vượt qua. 💚\n\n"
                "Ngay bây giờ, bạn hãy:\n"
                "1. Ở cạnh người tin cậy (bố mẹ, thầy cô, bạn thân) — đừng ở một mình.\n"
                "2. Gọi ngay Tổng đài 111 (miễn phí, 24/7) để được lắng nghe và hỗ trợ.\n"
                "3. Nếu đang nguy hiểm, gọi cấp cứu 115." + hotline, True)
    if has("danh", "bat nat", "de doa", "tran lot", "xo nga", "tat", "dam", "chui",
             "treu", "choc", "treu choc", "che gieu", "che nhao", "xuc pham",
             "si nhuc", "noi xau", "dat dieu", "xa lanh", "khong choi", "ghet",
             "tay chay", "co lap", "be phai", "ky thi", "hat hui"):
        return ("Mình hiểu, bị đối xử như vậy khiến bạn sợ hãi và tổn thương — và đó KHÔNG phải lỗi của bạn. Bạn rất dũng cảm khi kể ra điều này. 💚\n\n"
                "Bạn có thể làm theo các bước sau:\n"
                "1. Giữ bình tĩnh, không đánh lại — tránh nơi vắng người, đến chỗ đông người.\n"
                "2. Lưu bằng chứng nếu an toàn (tin nhắn, ảnh).\n"
                "3. Báo ngay cho giáo viên chủ nhiệm hoặc bố mẹ — bạn cũng có thể gửi Báo cáo ẩn danh trong app này.\n"
                "4. Đừng giữ bí mật một mình." + hotline, True)
    if has("buon", "khoc", "co don", "mot minh", "tui than", "tuyet vong", "chan"):
        return ("Mình nghe thấy nỗi buồn của bạn. Cảm xúc này là bình thường và bạn xứng đáng được lắng nghe. 🤗\n\n"
                "Thử một vài điều nhỏ nhé:\n"
                "1. Viết hết cảm xúc ra Nhật ký trong app — AI sẽ cùng bạn theo dõi.\n"
                "2. Hít thở sâu 4-7-8 vài lần để dịu lại.\n"
                "3. Kể cho một người bạn tin: đôi khi chỉ cần được nghe là đã nhẹ hơn nhiều.\n"
                "4. Làm điều bạn thích 15 phút (nghe nhạc, đi dạo)." + hotline, True)
    if has("ap luc", "diem", "thi", "hoc", "so", "lo lang", "stress", "cang thang"):
        return ("Áp lực học tập khiến ai cũng mệt mỏi, bạn không đơn độc đâu. 💪\n\n"
                "Gợi ý để nhẹ bớt:\n"
                "1. Chia nhỏ việc học thành từng phần 25 phút, nghỉ 5 phút.\n"
                "2. Nói với bố mẹ cảm xúc thật của bạn — bố mẹ sẽ hiểu hơn bạn nghĩ.\n"
                "3. Ngủ đủ giấc trước ngày thi, đừng thức khuya nhồi nhét.\n"
                "4. Kể cho thầy cô nếu áp lực quá sức." + hotline, True)
    if has("tren mang", "mang xa hoi", "facebook", "tiktok", "zalo", "anh che", "binh luan", "tin nhan de doa", "online"):
        return ("Bị quấy rối trên mạng rất mệt mỏi, nhưng bạn hoàn toàn có thể xử lý. 📱\n\n"
                "1. Chụp màn hình lưu bằng chứng, không trả lời khiêu khích lại.\n"
                "2. Chặn và báo cáo tài khoản đó.\n"
                "3. Báo cho giáo viên và bố mẹ — trường có trách nhiệm bảo vệ bạn cả trên mạng.\n"
                "4. Tạm rời khỏi nhóm/chat độc hại một thời gian." + hotline.replace("📞", "📞"), True)
    if has("chao", "hello", "hi", "xin chao"):
        return ("Chào bạn! Mình là EduSafe AI — người bạn luôn sẵn sàng lắng nghe. 💚\n\n"
                "Hôm nay của bạn thế nào? Bạn có thể kể cho mình nghe về chuyện ở trường, ở lớp, hay bất cứ điều gì làm bạn lo lắng nhé. Mọi chia sẻ đều được giữ kín.", True)
    if has("cam on", "thank"):
        return ("Không có gì đâu bạn! Mình luôn ở đây mỗi khi bạn cần. Hãy chăm sóc bản thân thật tốt nhé! 💚" + hotline, True)
    return ("Cảm ơn bạn đã tin tưởng chia sẻ với mình. Mình đã nghe rõ điều bạn nói. 💚\n\n"
            "Bạn có thể kể thêm một chút được không — chuyện này xảy ra ở đâu, khi nào, và cảm xúc của bạn lúc đó ra sao? Càng rõ, mình càng giúp bạn tốt hơn.\n\n"
            "Trong lúc đó, nhớ rằng: giữ bình tĩnh, tránh nơi nguy hiểm, và đừng ngại nhờ người lớn tin cậy giúp đỡ.", True)


# ==================== AUTH API ====================
@app.route("/api/auth/register", methods=["POST"])
def api_register():
    data = request.json
    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")
    full_name = data.get("full_name", "").strip()
    role = data.get("role", "student")
    class_name = data.get("class_name", "")

    if not all([username, email, password, full_name]):
        return jsonify({"error": "Thiếu thông tin bắt buộc"}), 400
    if role not in ROLES:
        return jsonify({"error": "Role không hợp lệ"}), 400
    if db.get_user_by_username(username):
        return jsonify({"error": "Username đã tồn tại"}), 400
    if db.get_user_by_email(email):
        return jsonify({"error": "Email đã tồn tại"}), 400

    student_code = f"HS{datetime.now().strftime('%Y%m%d%H%M%S')}" if role == "student" else ""
    user_id = db.create_user(username, email, hash_password(password), full_name, role, "", class_name, None, student_code)
    return jsonify({"success": True, "user_id": user_id}), 201


@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.json
    username = data.get("username", "")
    password = data.get("password", "")
    user = db.get_user_by_username(username)
    if not user or not verify_password(password, user["password_hash"]):
        return jsonify({"error": "Sai tài khoản hoặc mật khẩu"}), 401
    if not user["is_active"]:
        return jsonify({"error": "Tài khoản đã bị khóa"}), 403
    access_token = create_access_token(user["id"], user["role"], {"username": user["username"], "full_name": user["full_name"]})
    refresh_token = create_refresh_token(user["id"])
    return jsonify({
        "success": True, "access_token": access_token, "refresh_token": refresh_token,
        "user": {"id": user["id"], "username": user["username"], "full_name": user["full_name"], "role": user["role"], "class_name": user["class_name"], "student_code": user.get("student_code", "")},
    })


@app.route("/api/auth/me", methods=["GET"])
@require_auth
def api_me():
    user = db.get_user_by_id(int(g.current_user["sub"]))
    if not user:
        return jsonify({"error": "User không tồn tại"}), 404
    return jsonify({"id": user["id"], "username": user["username"], "full_name": user["full_name"], "role": user["role"], "email": user["email"], "class_name": user["class_name"], "permissions": get_user_permissions(user["role"])})


# ==================== USER MANAGEMENT ====================
@app.route("/api/users", methods=["GET"])
@require_permission("user:read")
def api_get_users():
    role = request.args.get("role")
    return jsonify(db.get_all_users(role))


@app.route("/api/users", methods=["POST"])
@require_permission("user:create")
def api_create_user():
    data = request.json
    if db.get_user_by_username(data.get("username", "")):
        return jsonify({"error": "Username đã tồn tại"}), 400
    user_id = db.create_user(data["username"], data["email"], hash_password(data["password"]), data["full_name"], data["role"], data.get("phone", ""), data.get("class_name", ""))
    return jsonify({"success": True, "user_id": user_id}), 201


@app.route("/api/users/<int:user_id>", methods=["PUT"])
@require_permission("user:update")
def api_update_user(user_id):
    data = request.json
    db.update_user(user_id, **data)
    return jsonify({"success": True})


@app.route("/api/users/<int:user_id>", methods=["DELETE"])
@require_permission("user:delete")
def api_delete_user(user_id):
    db.delete_user(user_id)
    return jsonify({"success": True})


# ==================== CHAT API ====================
@app.route("/api/chat", methods=["POST"])
@require_auth
def api_chat():
    data = request.json
    user_message = data.get("message", "").strip()
    model_id = data.get("model", DEFAULT_MODEL)
    if model_id not in MODELS:
        model_id = DEFAULT_MODEL
    session_id = data.get("session_id", "")
    user_id = int(g.current_user["sub"])

    if not user_message:
        return jsonify({"error": "Tin nhắn không được trống"}), 400

    if not session_id:
        session_id = str(uuid.uuid4())
        db.create_session(session_id, user_id, model_id)

    db.save_message(session_id, "user", user_message)
    history = db.get_session_messages(session_id)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + [{"role": m["role"], "content": m["content"]} for m in history]

    # Che do AI: "gemini" (mien phi qua Google, tu nhien hon) mac dinh neu co key.
    # "local" = AI noi bo ai_brain; "online" = API OpenCode tra phi.
    ai_mode = os.getenv("AI_MODE", "gemini").strip().lower()
    if ai_mode == "online":
        ai_response, used_offline = call_ai(model_id, messages)
        if ai_response is None:
            ai_response = ai_brain.reply(user_message, session_id)
            used_offline = True
    elif ai_mode == "gemini":
        ai_response = call_gemini(messages)
        used_offline = False if ai_response else True
        if not ai_response:
            ai_response = ai_brain.reply(user_message, session_id)
            used_offline = True
    else:
        ai_response = ai_brain.reply(user_message, session_id)
        used_offline = True
    db.save_message(session_id, "assistant", ai_response)

    risk_level, risk_score, factors = calculate_risk_score(user_message)
    state_label, eff_score, eff_factors = assess_student_state(user_id, user_message, risk_score, factors)
    eff_level = "critical" if eff_score >= 70 else "high" if eff_score >= 50 else "medium" if eff_score >= 30 else "low"
    risk_data = None
    if eff_score >= 30:
        recommendation = "CẦN HÀNH ĐỘNG NGAY" if eff_level == "critical" else "Gặp cố vấn tâm lý" if eff_level == "high" else "Theo dõi thêm"
        db.save_risk_assessment(session_id, user_id, eff_level, eff_score, eff_factors, recommendation)
        risk_data = {"level": eff_level, "score": eff_score, "factors": eff_factors, "recommendation": recommendation}
        if eff_score >= 50:
            user = db.get_user_by_id(user_id)
            db.create_alert(user_id, "Cảnh báo tâm lý", f"Học sinh {user['full_name']} — Tình trạng tâm lý: {state_label}. Điểm rủi ro: {eff_score}. Yếu tố: {', '.join(eff_factors)}", "critical" if eff_score >= 70 else "warning", "teacher")

    return jsonify({"response": ai_response, "session_id": session_id, "risk": risk_data, "offline": used_offline})


@app.route("/api/chat/sessions", methods=["GET"])
@require_auth
def api_chat_sessions():
    user_id = int(g.current_user["sub"])
    sessions = db.get_user_sessions(user_id)
    return jsonify({"sessions": sessions or []})


@app.route("/api/chat/messages/<session_id>", methods=["GET"])
@require_auth
def api_chat_messages(session_id):
    user_id = int(g.current_user["sub"])
    for s in db.get_user_sessions(user_id):
        if s.get("session_id") == session_id:
            return jsonify({"messages": db.get_session_messages(session_id)})
    return jsonify({"error": "Không tìm thấy đoạn chat này"}), 404


@app.route("/api/chat/sessions/<session_id>", methods=["DELETE"])
@require_auth
def api_delete_chat_session(session_id):
    user_id = int(g.current_user["sub"])
    for s in db.get_user_sessions(user_id):
        if s.get("session_id") == session_id:
            db.delete_chat_session(session_id, user_id=user_id)
            return jsonify({"success": True})
    return jsonify({"error": "Không tìm thấy hoặc không có quyền"}), 404


# ==================== GEMINI PROXY API (giu kin API Key o server) ====================
@app.route("/api/gemini", methods=["POST"])
def api_gemini():
    data = request.json or {}
    question = (data.get("message") or "").strip()
    if not question:
        return jsonify({"error": "Tin nhắn không được trống"}), 400

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return jsonify({"error": "Chưa cấu hình GEMINI_API_KEY trong file .env"}), 500

    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           "gemini-3.5-flash-lite:generateContent?key=" + api_key)
    payload = {"contents": [{"parts": [{"text": question}]}]}
    try:
        resp = requests.post(url, json=payload, timeout=60)
        if resp.status_code != 200:
            return jsonify({"error": f"Gemini API lỗi: HTTP {resp.status_code}"}), 502
        data = resp.json()
        answer = (data.get("candidates", [{}])[0]
                      .get("content", {}).get("parts", [{}])[0]
                      .get("text", ""))
        if not answer:
            return jsonify({"error": "Gemini không trả lời"}), 502
        return jsonify({"response": answer})
    except requests.exceptions.Timeout:
        return jsonify({"error": "Hết thời gian chờ Gemini"}), 504
    except Exception as e:
        return jsonify({"error": f"Lỗi: {e}"}), 500


# ==================== MOOD API ====================
@app.route("/api/mood", methods=["POST"])
@require_auth
def api_log_mood():
    data = request.json
    user_id = int(g.current_user["sub"])
    mood = data.get("mood", "binhthuong")
    note = data.get("note", "")

    period = (data.get("period") or "sáng").strip().lower()
    # Gioi han 1 lan dang moi buoi (sang/trua/chieu) trong ngay
    today = datetime.now().date().isoformat()
    for m in db.get_mood_logs(user_id=user_id):
        if str(m.get("created_at", ""))[:10] == today and str(m.get("period", "")).strip().lower() == period:
            return jsonify({"error": f"Bạn đã đăng nhật ký buổi {period} hôm rồi! Mỗi buổi chỉ đăng 1 lần. 🌟"}), 429

    mood_map = {"vui": ("😊", "Vui vẻ"), "binhthuong": ("😐", "Bình thường"), "buon": ("😢", "Buồn bã"), "loangiang": ("😰", "Lo lắng"), "tucgian": ("😡", "Tức giận")}
    emoji, label = mood_map.get(mood, ("😐", "Bình thường"))

    risk_level, risk_score, factors = calculate_risk_score(note)

    # Tinh diem an toan truc tiep theo tam trang (theo yeu cau nguoi dung)
    mood_adjust = {"vui": 50, "binhthuong": 30, "tucgian": -100, "loangiang": -75, "buon": -50}
    adj = mood_adjust.get(mood, 0)
    safety_score = max(0, min(100 + adj - risk_score, 100))
    factors = factors + [f"Tâm trạng: {label} ({'+' if adj>=0 else ''}{adj})"]
    risk_level = "critical" if safety_score <= 30 else "high" if safety_score <= 50 else "medium" if safety_score <= 70 else "low"
    risk_score = 100 - safety_score

    advice = ""
    if safety_score >= 70:
        advice = "Tâm trạng của bạn đang ổn định. Tiếp tục giữ gìn sức khỏe tinh thần nhé! 💚"
    elif safety_score >= 40:
        advice = "Bạn đang có một số lo lắng. Hãy thử trò chuyện với người thân hoặc giáo viên để được hỗ trợ. 💛"
    else:
        advice = "Tâm lý bạn đang không tốt. Hãy gọi tổng đài 111 hoặc gặp giáo viên ngay để được giúp đỡ. ❤️"

    db.save_mood_log(user_id, mood, emoji, label, note, safety_score, risk_level, period=period)

    # Kiem tra to hop trong 4 nhat ky gan nhat: it nhat 2 (buon|lo) tinh ca lap
    recent4 = db.get_mood_logs(user_id=user_id, limit=4)
    count_neg = sum(1 for r in recent4 if r["mood"] in ("buon", "loangiang"))
    if len(recent4) >= 4 and count_neg >= 2:
        safety_score = 0
        user = db.get_user_by_id(user_id)
        db.create_alert(user_id, "CẢNH BÁO KHẨN CẤP",
                        f"Học sinh {user['full_name']} có tổ hợp Buồn bã/Lo lắng (>=2 cái) trong 4 nhật ký gần nhất. Điểm an toàn = 0.",
                        "critical", "teacher")

    # Chi can 1 ngay tuc gian: diem ve 0 + canh bao giao vien
    if mood == "tucgian":
        safety_score = 0
        user = db.get_user_by_id(user_id)
        db.create_alert(user_id, "CẢNH BÁO KHẨN CẤP",
                        f"Học sinh {user['full_name']} có tâm trạng Tức giận. Điểm an toàn = 0.",
                        "critical", "teacher")

    if risk_score >= 50:
        user = db.get_user_by_id(user_id)
        state_label, eff_score, eff_factors = assess_student_state(user_id, note, risk_score, factors)
        db.create_alert(user_id, "Cảnh báo tâm lý", f"Học sinh {user['full_name']} — Tình trạng tâm lý: {state_label}. Điểm rủi ro: {eff_score}. Yếu tố: {', '.join(eff_factors)}", "critical" if eff_score >= 70 else "warning", "teacher")

    return jsonify({"success": True, "safety_score": safety_score, "advice": advice, "mood_label": label, "mood_emoji": emoji, "streak": db.get_mood_streak(user_id)})


@app.route("/api/mood/history", methods=["GET"])
@require_auth
def api_mood_history():
    user_id = int(g.current_user["sub"])
    return jsonify({"logs": db.get_mood_logs(user_id=user_id), "streak": db.get_mood_streak(user_id)})


@app.route("/api/risk/latest", methods=["GET"])
@require_auth
def api_latest_risk():
    user_id = int(g.current_user["sub"])
    return jsonify({"risk": db.get_latest_risk_assessment(user_id)})


@app.route("/api/mood/archive", methods=["GET"])
@require_auth
def api_mood_archive():
    user_id = int(g.current_user["sub"])
    return jsonify({"logs": db.get_mood_archive(user_id=user_id)})


@app.route("/api/mood/<int:log_id>", methods=["DELETE"])
@require_auth
def api_delete_mood(log_id):
    user_id = int(g.current_user["sub"])
    deleted = db.delete_mood_log(log_id, user_id)
    if deleted == 0:
        return jsonify({"error": "Không tìm thấy hoặc không có quyền xóa"}), 404
    return jsonify({"success": True})


@app.route("/api/mood/all", methods=["GET"])
@require_permission("mood:read")
def api_mood_all():
    return jsonify({"logs": db.get_all_mood_logs()})


# ==================== REPORT API ====================
@app.route("/api/reports", methods=["GET"])
@require_auth
def api_get_reports():
    user = g.current_user
    reports = db.get_all_reports()
    if user.get("role") == "student":
        student_id = int(user["sub"])
        reports = [r for r in reports if int(r.get("user_id", 0)) == student_id]
    else:
        for r in reports:
            r["student_name"] = "🌑 Ẩn danh"
    return jsonify({"reports": reports})


@app.route("/api/reports/<int:report_id>/contact", methods=["POST"])
@require_permission("report:read")
def api_report_contact(report_id):
    # Phai nhap dung mat khau cua giao vien moi xem duoc
    data = request.json or {}
    password = data.get("password", "")
    user = db.get_user_by_id(int(g.current_user["sub"]))
    if not user or not verify_password(password, user.get("password_hash", "")):
        return jsonify({"error": "Mật khẩu không đúng"}), 403
    for r in db.get_all_reports():
        if r.get("id") == report_id and r.get("user_id"):
            u = db.get_user_by_id(r["user_id"])
            if u:
                return jsonify({"full_name": u.get("full_name"), "class_name": u.get("class_name"), "student_code": u.get("student_code") or u.get("username"), "email": u.get("email"), "phone": u.get("phone")})
    return jsonify({"error": "Không tìm thấy"}), 404


@app.route("/api/reports", methods=["POST"])
@require_permission("report:create")
def api_create_report():
    data = request.json
    user_id = int(g.current_user["sub"])
    # Gioi han 1 lan bao cao moi ngay
    today = datetime.now().date().isoformat()
    for r in db.get_all_reports():
        if r.get("user_id") == user_id and str(r.get("created_at", ""))[:10] == today:
            return jsonify({"error": "Bạn đã gửi báo cáo hôm nay rồi! Hãy quay lại vào ngày mai nhé. 🌟"}), 429
    user = db.get_user_by_id(user_id)
    report_id = db.create_report(user_id, user["full_name"], user["class_name"], data.get("report_type", "other"), data.get("description", ""), data.get("location", ""), data.get("witnesses", ""), data.get("severity", "medium"))
    return jsonify({"id": report_id, "success": True}), 201


@app.route("/api/reports/<int:report_id>", methods=["DELETE"])
@require_permission("report:update")
def api_delete_report(report_id):
    deleted = db.delete_report(report_id)
    if deleted == 0:
        return jsonify({"error": "Không tìm thấy"}), 404
    return jsonify({"success": True})


@app.route("/api/reports/<int:report_id>", methods=["PUT"])
@require_permission("report:update")
def api_update_report(report_id):
    data = request.json
    db.update_report(report_id, status=data.get("status"), notes=data.get("notes"))
    return jsonify({"success": True})


# ==================== ALERTS API ====================
@app.route("/api/alerts", methods=["GET"])
@require_auth
def api_alerts():
    user = g.current_user
    return jsonify({"alerts": db.get_all_alerts(target_role=user["role"])})


@app.route("/api/alerts/unread-count", methods=["GET"])
@require_auth
def api_alert_unread_count():
    user = g.current_user
    return jsonify({"count": db.get_unread_alert_count(user["role"])})


@app.route("/api/alerts/read", methods=["POST"])
@require_auth
def api_mark_alerts_read():
    user = g.current_user
    db.mark_alerts_read(user["role"])
    return jsonify({"success": True})


@app.route("/api/alerts/<int:alert_id>", methods=["PUT"])
@require_auth
def api_update_alert(alert_id):
    data = request.json
    db.update_alert(alert_id, notes=data.get("notes"), status=data.get("status"))
    return jsonify({"success": True})


@app.route("/api/alerts/<int:alert_id>", methods=["DELETE"])
@require_auth
def api_delete_alert(alert_id):
    user = g.current_user
    if user["role"] not in ("teacher", "admin"):
        return jsonify({"error": "Không có quyền"}), 403
    deleted = db.delete_alert(alert_id, target_role=user["role"])
    if deleted == 0:
        return jsonify({"error": "Không tìm thấy"}), 404
    return jsonify({"success": True})


# ==================== TEACHER API ====================
@app.route("/api/teacher/dashboard", methods=["GET"])
@require_role("teacher", "admin")
def api_teacher_dashboard():
    students = db.get_all_users("student")
    moods = db.get_all_mood_logs()
    reports = db.get_all_reports()
    alerts = db.get_all_alerts(target_role="teacher")

    weekly_moods = [0] * 7
    total_week = 0
    now = datetime.now()
    for m in moods:
        try:
            dt = datetime.fromisoformat(m["created_at"])
            delta = (now - dt).days
            if delta < 7:
                total_week += 1
                weekly_moods[6 - delta] += 1  # chi so 0 = cach day 6 ngay, 6 = hom nay
        except:
            pass

    report_types = {"physical": 0, "verbal": 0, "cyber": 0, "social": 0}
    for r in reports:
        t = r.get("report_type", "other")
        if t in report_types:
            report_types[t] += 1

    return jsonify({
        "totalStudents": len(students),
        "totalMoods": total_week,
        "pendingReports": len([r for r in reports if r.get("status") == "pending"]),
        "criticalAlerts": len([a for a in alerts if a.get("severity") == "critical"]),
        "weeklyMoods": weekly_moods,
        "reportTypes": report_types,
    })


@app.route("/api/students", methods=["GET"])
@require_permission("student:read")
def api_get_students():
    students = db.get_all_users("student")
    for s in students:
        logs = db.get_mood_logs(user_id=s["id"], limit=5)
        if logs:
            first4 = [l.get('mood') for l in logs[:4]]
            neg4 = sum(1 for m in first4 if m in ('buon', 'loangiang'))
            if len(logs) >= 4 and neg4 >= 2:
                s["safety_score"] = 0
            elif len(logs) >= 2 and all(l.get("mood") == "vui" for l in logs[:2]):
                s["safety_score"] = 100
            elif any(l.get("mood") == "tucgian" for l in logs):
                s["safety_score"] = 0
            else:
                total = 100
                for l in reversed(logs):
                    adj = {"vui": 50, "binhthuong": 30, "buon": -50, "loangiang": -75}.get(l.get("mood"), 0)
                    total = max(0, min(100, total + adj))
                s["safety_score"] = total
        else:
            s["safety_score"] = None
    return jsonify(students)


@app.route("/api/students/<int:student_id>/profile", methods=["GET"])
@require_permission("student:read")
def api_student_profile(student_id):
    profile = db.get_student_profile(student_id)
    if not profile:
        return jsonify({"error": "Không tìm thấy"}), 404
    return jsonify(profile)


@app.route("/api/students/<int:student_id>/notes", methods=["POST"])
@require_permission("student:note")
def api_add_student_note(student_id):
    return jsonify({"success": True}), 201


# ==================== PARENT API ====================
@app.route("/api/parent/children", methods=["GET"])
@require_role("parent")
def api_parent_children():
    user_id = int(g.current_user["sub"])
    conn = db.get_db()
    c = conn.cursor()
    c.execute("""SELECT u.id, u.full_name, u.class_name, u.student_code,
                 (SELECT safety_score FROM mood_logs WHERE user_id=u.id ORDER BY created_at DESC LIMIT 1) as safety_score
                 FROM users u WHERE u.parent_id=? AND u.role='student'""", (user_id,))
    rows = c.fetchall()
    conn.close()
    return jsonify({"children": [dict(r) for r in rows]})


# ==================== ADMIN API ====================
@app.route("/api/admin/stats", methods=["GET"])
@require_role("admin")
def api_admin_stats():
    users = db.get_all_users()
    reports = db.get_all_reports()
    alerts = db.get_all_alerts()
    total = len(reports)
    resolved = len([r for r in reports if r.get("status") == "resolved"])
    return jsonify({
        "totalUsers": len(users),
        "safetyRate": round((resolved / total * 100) if total else 85),
        "resolvedRate": round((resolved / total * 100) if total else 70),
        "activeAlerts": len([a for a in alerts if a.get("status") != "read"]),
    })


@app.route("/api/admin/config", methods=["POST"])
@require_role("admin")
def api_admin_config():
    data = request.json
    db.save_config("ai_sensitivity", data.get("ai_sensitivity", "standard"))
    return jsonify({"success": True})


@app.route("/api/quiz/score", methods=["GET"])
@require_auth
def api_quiz_score():
    user_id = int(g.current_user["sub"])
    return jsonify(db.get_quiz_score(user_id))


@app.route("/api/quiz/save", methods=["POST"])
@require_auth
def api_quiz_save():
    data = request.json
    user_id = int(g.current_user["sub"])
    db.save_quiz_score(user_id, data.get("score", 0), data.get("total", 0))
    return jsonify({"success": True})


# ==================== PAGE ROUTES ====================
@app.route("/")
def index():
    return redirect(url_for("login_page"))


@app.route("/login")
def login_page():
    return render_template("login.html")


@app.route("/student")
def student_page():
    return render_template("student.html")


@app.route("/student/chat")
def student_chat_page():
    return render_template("student_chat.html")


@app.route("/student/mood")
def student_mood_page():
    return render_template("student_mood.html")


@app.route("/student/report")
def student_report_page():
    return render_template("student_report.html")


@app.route("/student/simulate")
def student_simulate_page():
    return render_template("student_simulate.html")


@app.route("/student/quiz")
def student_quiz_page():
    return render_template("student_quiz.html")


@app.route("/student/guide")
def student_guide_page():
    return render_template("student_guide.html")


@app.route("/teacher")
def teacher_page():
    return render_template("teacher.html")


@app.route("/teacher/students")
def teacher_students_page():
    return render_template("teacher_students.html")


@app.route("/teacher/reports")
def teacher_reports_page():
    return render_template("teacher_reports.html")


@app.route("/teacher/alerts")
def teacher_alerts_page():
    return render_template("teacher_alerts.html")


@app.route("/parent")
def parent_page():
    return render_template("parent.html")


@app.route("/admin")
def admin_page():
    return render_template("admin.html")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=3000)
