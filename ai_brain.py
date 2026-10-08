# -*- coding: utf-8 -*-
"""ai_brain.py — Bo nao AI mien phi, chay hoan toan local cho EduSafe.

Khong can API tra phi: hoi thoai theo chu de + cham diem tu khoa,
bau bao nhieu chu de an toan hoc duong.
"""
import re
import random
import unicodedata


def strip_accents(s):
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D")


HOTLINE = "\n\n📞 Nếu cần giúp ngay: gọi Tổng đài 111 (bảo vệ trẻ em, miễn phí 24/7), 115 (cấp cứu), hoặc kể cho giáo viên / bố mẹ / người thân tin cậy."

GREETINGS = [
    (["chao", "xin chao", "hello", "hi", "hey", "alo"],
     "Chào bạn! Mình là EduSafe AI — người bạn luôn sẵn sàng lắng nghe. 💚\n\nHôm nay của bạn thế nào? Bạn có thể kể chuyện ở trường, ở lớp, hay bất cứ điều gì lo lắng nhé. Mọi chia sẻ đều được giữ kín."),
    (["cam on", "thank"],
     "Không có gì đâu bạn! Mình luôn ở đây mỗi khi bạn cần. Hãy chăm sóc bản thân thật tốt nhé! 💚"),
    (["tam biet", "bye", "bai bai", "hen gap lai"],
     "Tạm biệt bạn! Chúc bạn một ngày an lành ở trường nhé. Mình luôn chờ bạn quay lại. 💚"),
    (["ban ten gi", "ten ban la gi", "ban la ai"],
     "Mình là EduSafe AI — trợ lý ảo về an toàn học đường. Mình có thể trò chuyện về rất nhiều chuyện: bạo lực học đường, bắt nạt, áp lực học tập, an toàn trên mạng, ma túy, phòng cháy chữa cháy, an toàn giao thông... Bạn muốn hỏi gì nào?"),
    (["ban khoe khong", "khoe khong"],
     "Mình rất vui khi bạn hỏi thăm! Mình luôn sẵn sàng trò chuyện với bạn. Còn bạn hôm nay thế nào?"),
]

TOPICS = [
    {
        "id": "suicide",
        "keywords": ["tu tu", "tu hai", "muon chet", "khong muon song", "ket lieu", "cat co tay", "chet di", "song vo nghia", "khong con y nghia"],
        "answer": ("Mình rất lo cho bạn lúc này. Cảm xúc này rất nặng nề, nhưng bạn không hề một mình và luôn có người sẵn sàng giúp bạn vượt qua. 💚\n\n"
                   "Ngay bây giờ, bạn hãy:\n"
                   "1. Ở cạnh người tin cậy (bố mẹ, thầy cô, bạn thân) — đừng ở một mình.\n"
                   "2. Gọi ngay Tổng đài 111 (miễn phí, 24/7) để được lắng nghe và hỗ trợ.\n"
                   "3. Nếu đang gặp nguy hiểm, gọi cấp cứu 115.\n\n"
                   "Bạn có muốn kể thêm cho mình nghe điều gì đã khiến bạn cảm thấy như vậy không?"),
    },
    {
        "id": "violence_physical",
        "keywords": ["bi danh", "danh dap", "bi danh dap", "bi dam", "bi tat", "xo nga", "tran lot", "dam nhau", "danh nhau", "mang vu khi", "de doa giet", "bi danh don", "danh em", "danh toi", "dua danh", "de doa", "danh", "bi danh doan"],
        "answer": ("Mình hiểu, bị đối xử như vậy khiến bạn sợ hãi và tổn thương — đó KHÔNG phải lỗi của bạn. Bạn rất dũng cảm khi kể ra. 💚\n\n"
                   "1. Ưu tiên an toàn: tránh nơi vắng người, đến chỗ đông người.\n"
                   "2. Không đánh lại — chuyện sẽ càng leo thang.\n"
                   "3. Lưu bằng chứng nếu an toàn (tin nhắn, ảnh).\n"
                   "4. Báo ngay cho giáo viên chủ nhiệm hoặc bố mẹ; bạn cũng có thể gửi Báo cáo ẩn danh trong app." + HOTLINE),
    },
    {
        "id": "cyberbullying",
        "keywords": ["tren mang", "mang xa hoi", "facebook", "tiktok", "zalo", "binh luan", "tin nhan de doa", "anh che", "quay video", "anh nhuc", "che bai tren mang", "quang cao lua dao", "online bi..."],
        "answer": ("Bị làm phiền hay quấy rối trên mạng thật mệt mỏi, nhưng bạn hoàn toàn có thể xử lý. 📱\n\n"
                   "1. Chụp màn hình lưu bằng chứng; đừng trả lời khiêu khích lại.\n"
                   "2. Chặn và báo cáo tài khoản đó.\n"
                   "3. Báo ngay cho giáo viên và bố mẹ — trường có trách nhiệm bảo vệ bạn cả trên mạng.\n"
                   "4. Tạm rời khỏi nhóm/chat độc hại một thời gian, nghỉ ngơi nhẹ đầu." + HOTLINE),
    },
    {
        "id": "bullying_general",
        "keywords": ["bat nat", "treu choc", "treu", "choc", "che gieu", "che nhao", "xuc pham", "si nhuc", "noi xau", "dat dieu", "xa lanh", "khong choi", "co lap", "tay chay", "be phai", "ky thi", "hat hui", "ghet", "bi chon mat", "bi doa", "chan duong"],
        "answer": ("Mình hiểu, bị đối xử như vậy khiến bạn sợ hãi và tổn thương — đó KHÔNG phải lỗi của bạn. 💚\n\n"
                   "1. Giữ bình tĩnh, không đáp trả bằng lời lẽ hay hành động cay cú.\n"
                   "2. Tránh ở một mình, đi cùng bạn bè.\n"
                   "3. Lưu bằng chứng nếu có (tin nhắn, ảnh chụp).\n"
                   "4. Báo ngay cho giáo viên chủ nhiệm hoặc bố mẹ; bạn cũng có thể gửi Báo cáo ẩn danh trong app này." + HOTLINE),
    },
    {
        "id": "abuse",
        "keywords": ["xam hai", "lam dung", "dung cham", "boi moc", "ke xau lam dung", "bi xam pham", "dung cham khong phu hop"],
        "answer": ("Cảm ơn bạn đã tin mình. Nếu ai đó đụng chạm không phù hợp hoặc làm bạn sợ, đó là sai của họ, không phải lỗi của bạn. 💚\n\n"
                   "1. Nói ngay với bố mẹ, thầy cô hoặc người lớn tin cậy.\n"
                   "2. Gọi Tổng đài 111 để được bảo vệ.\n"
                   "3. Không giữ bí mật một mình, không gặp riêng người đó nữa." + HOTLINE),
    },
    {
        "id": "drugs",
        "keywords": ["ma tuy", "can sa", "ma tuy da", "heroin", "hut thuoc", "thuoc la", "vape", "chat kich thich", "ruou", "bia", "nhau"],
        "answer": ("Thuốc lá, rượu bia và ma túy rất nguy hại cho sức khỏe và học tập, đặc biệt với tuổi học sinh. 🚭\n\n"
                   "1. Nói KHÔNG với lời mời thử; rủ bạn cùng từ chối thật dứt khoát.\n"
                   "2. Tránh xa nơi có người sử dụng.\n"
                   "3. Nếu lỡ thử, kể ngay cho bố mẹ hoặc thầy cô — không có gì phải xấu hổ.\n"
                   "4. Tìm hoạt động lành mạnh thay thế: thể thao, âm nhạc, câu lạc bộ." + HOTLINE),
    },
    {
        "id": "stress_study",
        "keywords": ["ap luc", "diem", "thi", "so thi", "lo lang", "stress", "cang thang", "ganh nang", "bai tap", "mon hoc", "so rot", "truoc ky thi"],
        "answer": ("Áp lực học tập khiến ai cũng mệt mỏi, bạn không đơn độc đâu. 💪\n\n"
                   "1. Chia nhỏ việc học thành từng phần 25 phút, nghỉ 5 phút.\n"
                   "2. Nói với bố mẹ cảm xúc thật của bạn — bố mẹ sẽ hiểu hơn bạn nghĩ.\n"
                   "3. Ngủ đủ giấc trước ngày thi, đừng thức khuya nhồi nhét.\n"
                   "4. Kể cho thầy cô nếu áp lực quá sức." + HOTLINE),
    },
    {
        "id": "anxiety",
        "keywords": ["lo au", "so hai", "hoang loan", "tram cam", "suy nghi tieu cuc", "mat ngu", "khong ngu duoc", "bat an", "khoc nhieu", "chan nan", "tuyet vong", "buon ba", "co don", "mot minh", "tui than", "chan nan", "buon", "bat man", "so toi"],
        "answer": ("Mình nghe thấy cảm xúc của bạn. Đó là điều bình thường và bạn xứng đáng được lắng nghe. 🤗\n\n"
                   "1. Viết hết cảm xúc vào Nhật ký trong app — mình sẽ cùng bạn theo dõi.\n"
                   "2. Hít thở sâu 4-7-8 vài lần để dịu lại.\n"
                   "3. Kể cho một người bạn tin — đôi khi chỉ cần được nghe là đã nhẹ hơn.\n"
                   "4. Làm điều bạn thích 15 phút: nghe nhạc, đi dạo." + HOTLINE),
    },
    {
        "id": "game_addiction",
        "keywords": ["nghien game", "choi game", "game nhieu", "thuc dem choi game", "nap game", "mat tai khoan game"],
        "answer": ("Chơi game không xấu, nhưng nếu quá nhiều sẽ ảnh hưởng sức khỏe và học tập. 🎮\n\n"
                   "1. Đặt giới hạn giờ chơi mỗi ngày, nghỉ ngơi mắt 20 phút.\n"
                   "2. Không nạp tiền, không mua vật phẩm cho người lạ trên mạng.\n"
                   "3. Bảo vệ mật khẩu tài khoản, bật xác thực 2 bước.\n"
                   "4. Tập thể thao, đọc sách, gặp bạn bè ngoài đời thực." + HOTLINE),
    },
    {
        "id": "online_safety",
        "keywords": ["an toan tren mang", "lua dao", "tin gia", "phishing", "lo thong tin", "mat khau", "tai khoan facebook", "bi hack", "link la", "click vao link", "nhan qua"],
        "answer": ("Cẩn thận trên mạng sẽ giúp bạn tránh được nhiều rủi ro. 🔒\n\n"
                   "1. Không chia sẻ tên, địa chỉ, số điện thoại, mật khẩu cho người lạ.\n"
                   "2. Không click vào link lạ, không nhận quà từ người không quen.\n"
                   "3. Bật xác thực 2 lớp, đặt mật khẩu mạnh.\n"
                   "4. Kiểm chứng thông tin trước khi tin/chia sẻ — tránh tin giả." + HOTLINE),
    },
    {
        "id": "stranger_danger",
        "keywords": ["bat coc", "nguoi la", "ke xau doi ngon", "bat tre em", "nguoi la cho di nho", "theo doi", "bam theo"],
        "answer": ("Nếu người lạ tiếp cận, bạn hãy:\n\n"
                   "1. Không đi theo, không nhận quà, không lên xe người lạ.\n"
                   "2. Nói to 'KHÔNG' và chạy đến nơi đông người/trường học/cảnh sát.\n"
                   "3. Kể ngay cho bố mẹ hoặc thầy cô. Gọi 113 nếu khẩn cấp." + HOTLINE),
    },
    {
        "id": "traffic",
        "keywords": ["giao thong", "di xe", "xe dap", "xe may", "an toan giao thong", "qua duong", "mu bao hiem", "den do", "tai nan giao thong", "vuot den do"],
        "answer": ("An toàn giao thông rất quan trọng:\n\n"
                   "1. Đội mũ bảo hiểm đúng quy cách khi đi xe máy.\n"
                   "2. Qua đường ở vạch kẻ đường, nhìn trái - phải - trái.\n"
                   "3. Không vừa đi vừa dùng điện thoại.\n"
                   "4. Không đi xe khi chưa đủ tuổi, không chở quá số người." + HOTLINE),
    },
    {
        "id": "fire",
        "keywords": ["chay", "hoa hoan", "pccc", "phong chay chua chay", "khan chay", "luyen tap", "binh cuu hoa", "thoat hiem", "chay chay", "dam chay"],
        "answer": ("Phòng cháy chữa cháy tại trường:\n\n"
                   "1. Biết rõ lối thoát hiểm và điểm tập kết gần nhất.\n"
                   "2. Khi có cháy: giữ bình tĩnh, cúi thấp, chạy ra ngoài, tuyệt đối không đi thang máy.\n"
                   "3. Gọi 114 khi có sự cố.\n"
                   "4. Không tắc nghẽn lối đi, không vứt rác dễ cháy bừa bãi." + HOTLINE),
    },
    {
        "id": "disaster",
        "keywords": ["dong dat", "bao lu", "lu lut", "sat lo", "thien tai", "bao lon", "ap thap", "mua lon", "gio manh", "sut lo dat"],
        "answer": ("Khi gặp thiên tai:\n\n"
                   "1. Lắng nghe thông báo từ nhà trường/cơ quan chức năng.\n"
                   "2. Động đất: chui xuống gầm bàn chắc chắn, bảo vệ đầu.\n"
                   "3. Bão/lũ: ở nơi cao ráo, tránh xa cửa sổ và đường dây điện.\n"
                   "4. Chuẩn bị sẵn túi khẩn cấp, không tò mò xem mưa lũ." + HOTLINE),
    },
    {
        "id": "health_hygiene",
        "keywords": ["dich benh", "covid", "cam cum", "sot", "ho", "rua tay", "ve sinh", "an toan thuc pham", "ngu doc", "ngộ độc", "khong khi o nhiem", "bau cung"],
        "answer": ("Giữ vệ sinh và an toàn thực phẩm:\n\n"
                   "1. Rửa tay thường xuyên bằng xà phòng/sát khuẩn.\n"
                   "2. Ăn chín uống sôi, chọn thực phẩm rõ nguồn gốc.\n"
                   "3. Đeo khẩu trang khi ho sốt hoặc nơi đông người.\n"
                   "4. Khi bị ngộ độc: ngừng ăn, báo ngay cho giáo viên/y tế." + HOTLINE),
    },
    {
        "id": "first_aid",
        "keywords": ["so cuu", "bi nga", "bi thuong", "chay", "bong gien", "chay mau", "ngat", "co giat", "bi ong dot", "hoa hoc"],
        "answer": ("Sơ cứu cơ bản:\n\n"
                   "1. Giữ bình tĩnh, bảo vệ bản thân an toàn.\n"
                   "2. Báo ngay cho giáo viên/y tế trường.\n"
                   "3. Với vết thương nhỏ: rửa sạch, băng lại. Với chấn thương nặng: không tự ý di chuyển, gọi 115.\n"
                   "4. Ghi nhớ số hotline y tế 115." + HOTLINE),
    },
    {
        "id": "friendship",
        "keywords": ["ban be", "mau thuan", "cai nhau", "xung dot", "khong hop voi ban", "chia tay ban", "mat ban", "tinh ban", "nhom ban"],
        "answer": ("Mâu thuẫn bạn bè là chuyện thường. Bạn có thể:\n\n"
                   "1. Lắng nghe đối phương, nói chuyện thẳng thắn và tôn trọng.\n"
                   "2. Xin lỗi nếu mình sai; cũng đừng ngại bỏ qua cho bạn.\n"
                   "3. Nếu bị bắt nạt hay đe dọa, báo người lớn chứ đừng im lặng.\n"
                   "4. Tránh kéo bè phái — mâu thuẫn càng dễ lan rộng." + HOTLINE),
    },
    {
        "id": "teachers",
        "keywords": ["thay co", "giao vien", "co giao", "thay giao", "ky luat", "bi phat", "bi nhac nho", "so thay co", "giao vien khong..."],
        "answer": ("Nếu bạn lo lắng với thầy cô:\n\n"
                   "1. Nói chuyện thẳng thắn, tôn trọng với thầy cô mình tin.\n"
                   "2. Nếu bị đối xử không công bằng, kể cho bố mẹ hoặc giáo viên khác.\n"
                   "3. Chuẩn bị kỹ cho buổi nói chuyện: ghi lại sự việc, cảm xúc của bạn.\n"
                   "4. Mọi thắc mắc về học tập đều có thể hỏi — thầy cô luôn sẵn sàng." + HOTLINE),
    },
    {
        "id": "parents",
        "keywords": ["bo me", "phu huynh", "khong hop voi me", "bi la mang", "bi quat", "ap luc tu gia dinh", "me la", "bo la", "la mang", "bi mang", "me mang", "bo mang"],
        "answer": ("Mâu thuẫn với bố mẹ khá căng thẳng. Bạn thử:\n\n"
                   "1. Chọn lúc bình tĩnh để nói chuyện, tránh lúc đang giận.\n"
                   "2. Diễn đạt cảm xúc bằng 'mình cảm thấy...' thay vì đổ lỗi.\n"
                   "3. Nghe bố mẹ nói hết rồi mới đáp.\n"
                   "4. Nếu có bạo lực gia đình, nói ngay với thầy cô tin cậy hoặc gọi 111." + HOTLINE),
    },
    {
        "id": "exam_result",
        "keywords": ["diem kem", "bi rot", "truot", "bi diem thap", "so diem", "thi lai", "truot dai hoc", "khong do", "truot dai hoc"],
        "answer": ("Điểm thấp hay trượt kỳ thi không có nghĩa là bạn thất bại. 💚\n\n"
                   "1. Bình tĩnh, hít thở sâu, đừng tự trách quá nhiều.\n"
                   "2. Nói với bố mẹ và thầy cô — họ sẽ hỗ trợ bạn.\n"
                   "3. Rút kinh nghiệm: xem lại cách học, lập kế hoạch cho lần sau.\n"
                   "4. Có rất nhiều con đường khác nhau để thành công." + HOTLINE),
    },
    {
        "id": "sexual_safety",
        "keywords": ["tinh duc", "yeu", "ban gai", "ban trai", "anh rieng tu", "anh nhay cam", "quen he tinh cam"],
        "answer": ("Tình cảm học đường cũng cần an toàn:\n\n"
                   "1. Không gửi ảnh/video nhạy cảm cho ai, dù thân thiết.\n"
                   "2. Không để người khác đụng chạm khi bạn không muốn.\n"
                   "3. Nếu bị quấy rối, nói ngay cho người lớn tin cậy.\n"
                   "4. Tập trung học tập, giữ giới hạn bản thân lành mạnh." + HOTLINE),
    },
    {
        "id": "bullying_witness",
        "keywords": ["chuyen nhan", "thay ban bi danh", "thay nguoi khac bi bat nat", "khong biet giup gi", "chung kien", " thay ban bi quay roi"],
        "answer": ("Khi chứng kiến bạn bị bắt nạt, bạn có thể giúp:\n\n"
                   "1. Không cổ vũ, không quay video — điều đó chỉ làm tổn thương thêm.\n"
                   "2. Báo ngay cho giáo viên hoặc người lớn gần nhất.\n"
                   "3. An ủi, ở lại với bạn bị bắt nạt sau sự việc.\n"
                   "4. Nếu an toàn, đứng ra can gián bằng lời nói nhẹ nhàng." + HOTLINE),
    },
]

# ---------------------------------------------------------------------------
# ĐỘNG CƠ CHẤM ĐIỂM
# ---------------------------------------------------------------------------
def _tokenize(s):
    return re.findall(r"[a-z0-9]+", s)


def _score_topic(text_norm, topic):
    score = 0
    for kw in topic["keywords"]:
        # Khớp theo ranh giới từ để "ba" không khớp trong "ban"
        if re.search(r"\b" + re.escape(kw) + r"\b", text_norm):
            score += 2
    return score


_last_topic = {}      # session_id -> topic_id
_last_answer = {}     # session_id -> text vua tra loi

# Nhóm câu hỏi tiếp nối: phải khớp cả cụm từ, không dùng substring ngắn
_FOLLOWUP = [
    r"\bke\s+them\b", r"\bnhu\s+the\s+nao\b", r"\blam\s+sao\b", r"\blam\s+the\s+nao\b",
    r"\bchi\s+tiet\s+hon\b", r"\bro\s+hon\b", r"\btiep\b", r"\bcon\s+gi\b", r"\bcon\s+gi\s+nua\b",
    r"\bgiup\s+to\b", r"\bgiup\s+em\b", r"\btoi\s+phai\s+lam\s+gi\b", r"\bphai\s+lam\s+gi\b",
    r"\bem\s+phai\s+lam\s+gi\b", r"\blam\s+gi\b",
]

FALLBACKS = [
    ("Cảm ơn bạn đã tin tưởng chia sẻ với mình. Mình đã nghe rõ điều bạn nói. 💚\n\n"
     "Bạn có thể kể thêm một chút được không — chuyện này xảy ra ở đâu, khi nào, và cảm xúc của bạn lúc đó ra sao? Càng rõ, mình càng giúp bạn tốt hơn.\n\n"
     "Trong lúc đó, nhớ rằng: giữ bình tĩnh, tránh nơi nguy hiểm, và đừng ngại nhờ người lớn tin cậy giúp đỡ."),
    ("Mình đang lắng nghe bạn đây. 💚 Bạn muốn nói về chủ đề nào trong các chủ đề sau: bắt nạt, bạo lực, áp lực học tập, an toàn trên mạng, ma túy, phòng cháy chữa cháy, an toàn giao thông?\n\n"
     "Bạn cứ hỏi thẳng chủ đề, ví dụ: 'em bị bạn bắt nạt thì làm sao' hay 'cách phòng cháy chữa cháy'."),
    ("Xin lỗi, mình chưa hiểu lắm ý bạn. 😅 Bạn có thể nói rõ hơn một chút được không? Hoặc thử hỏi một trong các chủ đề: bắt nạt, bạo lực, stress học tập, an toàn mạng, ma túy, cháy nổ, giao thông..."),
]


def reply(user_text, session_id=""):
    """Tra lo thoai tron chuoi, uu tien AI local mien phi."""
    t = strip_accents(user_text.lower())

    # Nho truoc tra loi: neu cau ngan / tiep theo, tiep tuc chu de truoc
    last = _last_topic.get(session_id)
    if last and len(t.split()) <= 6 and any(re.search(p, t) for p in _FOLLOWUP):
        for topic in TOPICS:
            if topic["id"] == last:
                ans = ("Về chủ đề này, hành động cụ thể bạn có thể làm:\n\n"
                       "• Kể với người lớn tin cậy (bố mẹ, thầy cô).\n"
                       "• Gửi Báo cáo ẩn danh ngay trong app.\n"
                       "• Gọi Tổng đài 111 nếu cần hỗ trợ khẩn cấp.\n\n"
                       "Bạn muốn mình tư vấn sâu hơn phần nào?")
                if ans == _last_answer.get(session_id):
                    ans = ("Bạn có muốn mình nói về một chủ đề khác không? Ví dụ: bắt nạt, áp lực học tập, an toàn mạng, ma túy, phòng cháy chữa cháy, giao thông...")
                _last_answer[session_id] = ans
                return ans + HOTLINE

    # Greetings / small talk
    for kws, ans in GREETINGS:
        if any(re.search(r"\b" + re.escape(k) + r"\b", t) for k in kws):
            _last_topic.pop(session_id, None)
            return ans

    # Chu de chinh
    best = None
    best_score = 0
    for topic in TOPICS:
        s = _score_topic(t, topic)
        if s > best_score:
            best_score = s
            best = topic
    if best and best_score >= 2:
        prev = _last_answer.get(session_id)
        _last_topic[session_id] = best["id"]
        ans = best["answer"]
        if ans == prev:
            # Cùng chủ đề lặp lại → đổi cách tiếp cận
            ans = ("Về vấn đề này, bạn có thể chia sẻ thêm chi tiết không — xảy ra ở đâu, khi nào, ai liên quan? "
                   "Càng rõ mình càng tư vấn được chính xác hơn. 💚")
        _last_answer[session_id] = ans
        return ans

    # Fallback xoay vòng, không lặp cùng 1 câu
    _last_topic.pop(session_id, None)
    import random as _r
    ans = _r.choice(FALLBACKS)
    if ans == _last_answer.get(session_id):
        ans = FALLBACKS[(FALLBACKS.index(ans) + 1) % len(FALLBACKS)]
    _last_answer[session_id] = ans
    return ans
