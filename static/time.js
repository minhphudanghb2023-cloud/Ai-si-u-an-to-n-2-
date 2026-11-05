/* EduSafe AI - Định dạng thời gian chuẩn (Giờ Hà Nội UTC+7) */
var THU = ['Chủ Nhật', 'Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy'];

function fmtTime(ts) {
    if (!ts) return '';
    try {
        var d = new Date(ts);
        var opts = { timeZone: 'Asia/Ho_Chi_Minh', day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false };
        return d.toLocaleString('vi-VN', opts);
    } catch (e) { return String(ts); }
}
function fmtDate(ts) {
    if (!ts) return '';
    try {
        var d = new Date(ts);
        var opts = { timeZone: 'Asia/Ho_Chi_Minh', day: '2-digit', month: '2-digit', year: 'numeric' };
        return d.toLocaleDateString('vi-VN', opts);
    } catch (e) { return String(ts); }
}
/* Hiển thị đầy đủ: "Thứ Bảy, 10/10/2026 • 15:49" */
function fmtFull(ts) {
    if (!ts) return '';
    try {
        var d = new Date(ts);
        var hn = new Date(d.toLocaleString('en-US', { timeZone: 'Asia/Ho_Chi_Minh' }));
        var thu = THU[hn.getDay()];
        var p = function (n) { return String(n).padStart(2, '0'); };
        return thu + ', ' + p(hn.getDate()) + '/' + p(hn.getMonth() + 1) + '/' + hn.getFullYear()
            + ' • ' + p(hn.getHours()) + ':' + p(hn.getMinutes());
    } catch (e) { return fmtTime(ts); }
}
