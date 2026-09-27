"""
sign_meanings.py
Bang tra y nghia 56 lop bien bao cua mo hinh, dung chung cho ca
realtime_detect.py va detect_image_gui.py.

LUU Y CHO NHOM: mot so bien the hau to a/b/c/d (dac biet R.301c/d/e va
W.205a/b/d) can doi chieu lai voi QCVN 41:2019/BGTVT truoc khi bao ve.
"""

SIGN_MEANINGS = {
    # --- Bien bao cam (P, DP) ---
    "P.102": "Cấm đi ngược chiều",
    "P.103a": "Cấm xe ô tô",
    "P.103b": "Cấm xe ô tô rẽ phải",
    "P.103c": "Cấm xe ô tô rẽ trái",
    "P.104": "Cấm xe máy",
    "P.106a": "Cấm xe ô tô tải",
    "P.106b": "Cấm xe ô tô tải theo khối lượng chuyên chở",
    "P.107a": "Cấm xe ô tô khách",
    "P.112": "Cấm người đi bộ",
    "P.115": "Hạn chế khối lượng toàn bộ xe",
    "P.117": "Hạn chế chiều cao",
    "P.123a": "Cấm rẽ trái",
    "P.123b": "Cấm rẽ phải",
    "P.124a": "Cấm quay đầu xe",
    "P.124b": "Cấm ô tô quay đầu xe",
    "P.124c": "Cấm rẽ trái và quay đầu xe",
    "P.125": "Cấm vượt",
    "P.127": "Tốc độ tối đa cho phép",
    "P.128": "Cấm sử dụng còi",
    "P.130": "Cấm dừng xe và đỗ xe",
    "P.131a": "Cấm đỗ xe",
    "P.137": "Cấm rẽ trái và rẽ phải",
    "P.245a": "Đi chậm (trùng ý nghĩa W.245a — xem ghi chú)",
    "DP.135": "Hết tất cả các lệnh cấm",

    # --- Bien bao nguy hiem (W) ---
    "W.201a": "Chỗ ngoặt nguy hiểm vòng bên trái",
    "W.201b": "Chỗ ngoặt nguy hiểm vòng bên phải",
    "W.202a": "Nhiều chỗ ngoặt nguy hiểm liên tiếp, chỗ đầu sang trái",
    "W.202b": "Nhiều chỗ ngoặt nguy hiểm liên tiếp, chỗ đầu sang phải",
    "W.203b": "Đường bị thu hẹp về phía trái",
    "W.203c": "Đường bị thu hẹp về phía phải",
    "W.205a": "Đường giao nhau cùng cấp (ngã tư)",
    "W.205b": "Đường giao nhau cùng cấp (ngã ba bên phải)",
    "W.205d": "Đường giao nhau cùng cấp (dạng chữ T)",
    "W.207a": "Giao nhau với đường không ưu tiên",
    "W.207b": "Giao nhau với đường không ưu tiên (phía bên phải)",
    "W.207c": "Giao nhau với đường không ưu tiên (phía bên trái)",
    "W.208": "Giao nhau với đường ưu tiên",
    "W.209": "Giao nhau có tín hiệu đèn",
    "W.210": "Giao nhau với đường sắt có rào chắn",
    "W.224": "Đường người đi bộ cắt ngang",
    "W.225": "Trẻ em",
    "W.227": "Công trường",
    "W.245a": "Đi chậm",

    # --- Bien hieu lenh (R) ---
    "R.301c": "Hướng đi phải theo — chỉ được rẽ trái",
    "R.301d": "Hướng đi phải theo — chỉ được rẽ phải",
    "R.301e": "Hướng đi phải theo — chỉ được rẽ trái",
    "R.302a": "Hướng phải đi vòng chướng ngại vật sang phải",
    "R.302b": "Hướng phải đi vòng chướng ngại vật sang trái",
    "R.303": "Nơi giao nhau chạy theo vòng xuyến",
    "R.407a": "Đường một chiều",
    "R.409": "Chỗ quay xe",
    "R.425": "Bệnh viện",
    "R.434": "Bến xe buýt",

    # --- Bien chi dan (I) va bien phu (S) ---
    "I408": "Nơi đỗ xe",
    "I423b": "Đường người đi bộ sang ngang",
    "S.509a": "Biển phụ — chiều cao an toàn",
}

GROUP_NOTE = {
    "P": "Biển báo cấm — hình tròn viền đỏ",
    "W": "Biển báo nguy hiểm — hình tam giác viền đỏ",
    "R": "Biển hiệu lệnh / chỉ dẫn — hình tròn hoặc vuông nền xanh",
    "I": "Biển chỉ dẫn",
    "S": "Biển phụ",
}


def meaning_of(code):
    """Tra ve y nghia tieng Viet cua ma bien bao."""
    return SIGN_MEANINGS.get(code, "(chưa có mô tả)")


def group_of(code):
    """Tra ve nhom bien bao dua tren ky tu dau cua ma."""
    return GROUP_NOTE.get(code[0].upper(), "Không xác định")


def short_label(code, conf=None):
    """Nhan ngan gon de ve len khung hinh."""
    m = SIGN_MEANINGS.get(code)
    if not m:
        return f"{code} {conf:.2f}" if conf is not None else code
    if len(m) > 34:
        m = m[:32].rstrip() + "..."
    return f"{code} - {m}  {conf:.2f}" if conf is not None else f"{code} - {m}"
