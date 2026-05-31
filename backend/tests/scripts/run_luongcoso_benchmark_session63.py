from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

BASE_URL = "http://localhost:8000"
SESSION_ID = 63
USERNAME = "admin"
PASSWORD = "admin123"
TIMEOUT_SECONDS = 180
POLL_SECONDS = 2


QA = [
    {
        "q": "Đối với các cơ quan, đơn vị đang áp dụng cơ chế tài chính, thu nhập đặc thù ở Trung ương, khoản chênh lệch nào được bảo lưu khi chuyển sang lương từ ngày 01/7/2026?",
        "a": "Thực hiện bảo lưu phần chênh lệch giữa tiền lương và thu nhập tăng thêm tháng 6 năm 2026 của cán bộ, công chức, viên chức với tiền lương từ ngày 01 tháng 7 năm 2026 sau khi sửa đổi hoặc bãi bỏ cơ chế tài chính và thu nhập đặc thù.",
    },
    {
        "q": "Trong thời gian chưa sửa đổi hoặc bãi bỏ cơ chế tài chính, thu nhập đặc thù ở Trung ương, mức tiền lương và thu nhập tăng thêm hằng tháng từ 01/7/2026 được tính và bị giới hạn như thế nào?",
        "a": "Trong thời gian chưa sửa đổi hoặc bãi bỏ các cơ chế này thì thực hiện mức tiền lương và thu nhập tăng thêm hằng tháng tính theo mức lương cơ sở 2.530.000 đồng/tháng theo cơ chế đặc thù từ ngày 01 tháng 7 năm 2026 bảo đảm không vượt quá mức tiền lương và thu nhập tăng thêm được hưởng tháng 6 năm 2026 (không bao gồm phần tiền lương và thu nhập tăng thêm do điều chỉnh hệ số tiền lương ngạch, bậc khi nâng ngạch, nâng bậc).",
    },
    {
        "q": "Nếu tính theo cơ chế đặc thù mà tiền lương và thu nhập tăng thêm từ 01/7/2026 thấp hơn mức tiền lương theo quy định chung thì áp dụng chế độ nào?",
        "a": "Trường hợp tính theo nguyên tắc trên, nếu mức tiền lương và thu nhập tăng thêm từ ngày 01 tháng 7 năm 2026 theo cơ chế đặc thù thấp hơn mức tiền lương theo quy định chung thì thực hiện chế độ tiền lương theo quy định chung.",
    },
    {
        "q": "Quỹ tiền thưởng hằng năm được xác định bằng bao nhiêu phần trăm và trên cơ sở quỹ nào?",
        "a": "Quỹ tiền thưởng hằng năm quy định tại Điều này nằm ngoài quỹ khen thưởng theo quy định của Luật Thi đua, khen thưởng, được xác định bằng 10% tổng quỹ tiền lương (không bao gồm phụ cấp) theo chức vụ, chức danh, ngạch, bậc và cấp bậc quân hàm của các đối tượng trong danh sách trả lương của cơ quan, đơn vị.",
    },
    {
        "q": "Đến hết năm ngân sách, kể cả thời gian chỉnh lý quyết toán, nếu cơ quan, đơn vị không sử dụng hết quỹ tiền thưởng của năm thì xử lý ra sao?",
        "a": "Đến hết năm ngân sách, kể cả thời gian chỉnh lý quyết toán, nếu cơ quan, đơn vị không sử dụng hết quỹ tiền thưởng của năm thì huỷ dự toán (đối với trường hợp dư dự toán) hoặc nộp ngân sách nhà nước (đối với trường hợp dư tạm ứng).",
    },
    {
        "q": "Quy chế tiền thưởng của cơ quan, đơn vị phải bao gồm những nội dung nào?",
        "a": "Quy chế tiền thưởng phải bao gồm: phạm vi và đối tượng áp dụng; tiêu chí thưởng theo thành tích công tác đột xuất và theo kết quả đánh giá, xếp loại mức độ hoàn thành nhiệm vụ hằng năm; mức tiền thưởng cụ thể đối với từng trường hợp, không nhất thiết gắn với mức lương theo hệ số lương; quy trình, thủ tục xét thưởng; các quy định khác theo yêu cầu quản lý nếu cần thiết.",
    },
    {
        "q": "Người đứng đầu nào có trách nhiệm xây dựng Quy chế cụ thể để thực hiện chế độ tiền thưởng?",
        "a": "Người đứng đầu đơn vị lực lượng vũ trang theo quy định của Bộ Quốc phòng, Bộ Công an; người đứng đầu cơ quan có thẩm quyền quản lý hoặc được phân cấp thẩm quyền quản lý cán bộ, công chức và người đứng đầu đơn vị sự nghiệp công lập có trách nhiệm xây dựng Quy chế cụ thể để thực hiện chế độ tiền thưởng.",
    },
    {
        "q": "Nguồn kinh phí của các Bộ, cơ quan trung ương để thực hiện gồm những nguồn nào?",
        "a": "Nguồn kinh phí của các Bộ, cơ quan trung ương gồm: 10% tiết kiệm chi thường xuyên dự toán năm 2026 tăng thêm so với dự toán năm 2025; tối thiểu 40% số thu được để lại theo chế độ năm 2026 sau khi trừ chi phí liên quan trực tiếp đến hoạt động cung cấp dịch vụ, thu phí, riêng cơ sở y tế công lập tối thiểu 35%; nguồn thực hiện cải cách tiền lương năm 2025 chưa sử dụng hết chuyển sang nếu có.",
    },
    {
        "q": "Nguồn kinh phí của các tỉnh, thành phố trực thuộc trung ương theo khoản 2 Điều 5 gồm những nhóm nguồn chính nào?",
        "a": "Nguồn kinh phí của các tỉnh, thành phố trực thuộc trung ương gồm: 70% tăng thu ngân sách địa phương năm 2025 thực hiện so với dự toán; 50% tăng thu ngân sách địa phương dự toán các năm 2026, 2025, 2024 so với dự toán năm trước; 10% tiết kiệm chi thường xuyên theo các năm/dự toán tăng thêm; nguồn cải cách tiền lương đến hết năm 2025 còn dư chuyển sang; kinh phí ngân sách địa phương tiết kiệm chi hỗ trợ hoạt động thường xuyên do tinh giản biên chế, sắp xếp tổ chức bộ máy thực hiện mô hình chính quyền địa phương 02 cấp; tối thiểu 40% số thu được để lại năm 2026, riêng cơ sở y tế công lập tối thiểu 35%.",
    },
    {
        "q": "Đối với số thu từ dịch vụ khám bệnh, chữa bệnh, y tế dự phòng và dịch vụ y tế khác của cơ sở y tế công lập, tỷ lệ tối thiểu phải sử dụng là bao nhiêu?",
        "a": "Riêng đối với số thu từ việc cung cấp các dịch vụ khám bệnh, chữa bệnh, y tế dự phòng và dịch vụ y tế khác của cơ sở y tế công lập sử dụng tối thiểu 35% sau khi trừ các chi phí liên quan trực tiếp đến hoạt động cung cấp dịch vụ, thu phí.",
    },
    {
        "q": "Ngân sách trung ương bổ sung kinh phí còn thiếu cho những cơ quan, địa phương nào sau khi đã thực hiện khoản 1 và khoản 2 Điều 5?",
        "a": "Ngân sách trung ương bổ sung nguồn kinh phí còn thiếu do điều chỉnh mức lương cơ sở và thực hiện chế độ tiền thưởng năm 2026 cho các bộ, cơ quan ngang bộ, cơ quan thuộc Chính phủ, cơ quan khác ở trung ương và các tỉnh, thành phố trực thuộc trung ương sau khi đã thực hiện quy định tại khoản 1 và khoản 2 Điều 5.",
    },
    {
        "q": "Các đơn vị sự nghiệp công lập nhóm 1 và nhóm 2 tự bảo đảm kinh phí thực hiện cải cách tiền lương, tiền thưởng theo quy định nào?",
        "a": "Kinh phí thực hiện cải cách tiền lương, thực hiện chế độ tiền thưởng của viên chức, người lao động trong các đơn vị sự nghiệp công lập nhóm 1, nhóm 2 do đơn vị tự đảm bảo theo quy định tại Nghị định số 60/2021/NĐ-CP ngày 21 tháng 6 năm 2021, Nghị định số 111/2025/NĐ-CP ngày 22 tháng 5 năm 2025 và các văn bản sửa đổi, bổ sung, thay thế nếu có.",
    },
    {
        "q": "Mức lương cơ sở dùng làm căn cứ cho những việc gì theo khoản 1 Điều 3?",
        "a": "Mức lương cơ sở dùng làm căn cứ: tính mức lương trong các bảng lương, mức phụ cấp và thực hiện các chế độ khác theo quy định của pháp luật đối với các đối tượng tại Điều 2; tính mức hoạt động phí, sinh hoạt phí theo quy định của pháp luật; tính các khoản trích và các chế độ được hưởng theo mức lương cơ sở.",
    },
    {
        "q": "Từ ngày nào mức lương cơ sở là 2.530.000 đồng/tháng?",
        "a": "Từ ngày 01 tháng 7 năm 2026, mức lương cơ sở là 2.530.000 đồng/tháng.",
    },
    {
        "q": "Chính phủ điều chỉnh mức lương cơ sở sau khi báo cáo Quốc hội xem xét, quyết định dựa trên những yếu tố nào?",
        "a": "Chính phủ điều chỉnh mức lương cơ sở sau khi báo cáo Quốc hội xem xét, quyết định phù hợp khả năng ngân sách nhà nước, chỉ số giá tiêu dùng và tốc độ tăng trưởng kinh tế của đất nước.",
    },
    {
        "q": "Chế độ tiền thưởng được thực hiện trên cơ sở những tiêu chí nào?",
        "a": "Thực hiện chế độ tiền thưởng trên cơ sở thành tích công tác đột xuất và kết quả đánh giá, xếp loại mức độ hoàn thành nhiệm vụ hằng năm đối với các đối tượng quy định tại khoản 2 Điều 2 Nghị định này.",
    },
    {
        "q": "Chế độ tiền thưởng được dùng để thưởng những loại nào?",
        "a": "Chế độ tiền thưởng được dùng để thưởng đột xuất theo thành tích công tác và thưởng định kỳ hằng năm theo kết quả đánh giá, xếp loại mức độ hoàn thành công việc của từng người hưởng lương trong cơ quan, đơn vị.",
    },
    {
        "q": "Theo khoản 2 Điều 2, những đối tượng nào thuộc đối tượng áp dụng chế độ tiền thưởng?",
        "a": "Người hưởng lương quy định tại các điểm a, b, c, d, đ, e và g khoản 1 Điều 2, không bao gồm đối tượng hưởng phụ cấp, sinh hoạt phí, thuộc đối tượng áp dụng chế độ tiền thưởng.",
    },
    {
        "q": "Liệt kê các nhóm người hưởng lương, phụ cấp áp dụng mức lương cơ sở theo khoản 1 Điều 2.",
        "a": "Bao gồm cán bộ, công chức từ Trung ương đến cấp xã; viên chức trong đơn vị sự nghiệp công lập; người làm việc theo hợp đồng lao động theo Nghị định 111/2022/NĐ-CP thuộc trường hợp được áp dụng hoặc thỏa thuận xếp lương theo Nghị định 204/2004/NĐ-CP; người làm việc trong chỉ tiêu biên chế tại hội được ngân sách hỗ trợ; sĩ quan, quân nhân chuyên nghiệp, công nhân, viên chức quốc phòng và lao động hợp đồng thuộc Quân đội nhân dân; sĩ quan, hạ sĩ quan hưởng lương, công nhân công an và lao động hợp đồng thuộc Công an nhân dân; người làm việc trong tổ chức cơ yếu; hạ sĩ quan và binh sĩ thuộc Quân đội nhân dân, hạ sĩ quan và chiến sĩ nghĩa vụ thuộc Công an nhân dân; người hoạt động không chuyên trách ở thôn và tổ dân phố.",
    },
    {
        "q": "Người làm việc trong chỉ tiêu biên chế tại các hội được ngân sách nhà nước hỗ trợ kinh phí hoạt động được viện dẫn theo nghị định nào?",
        "a": "Người làm việc trong chỉ tiêu biên chế tại các hội được ngân sách nhà nước hỗ trợ kinh phí hoạt động theo quy định tại Nghị định số 126/2024/NĐ-CP ngày 08 tháng 10 năm 2024 của Chính phủ quy định về tổ chức, hoạt động và quản lý hội.",
    },
    {
        "q": "Người làm công việc theo hợp đồng lao động trong cơ quan hành chính và đơn vị sự nghiệp công lập được nhắc đến theo Nghị định nào?",
        "a": "Người làm các công việc theo chế độ hợp đồng lao động quy định tại Nghị định số 111/2022/NĐ-CP ngày 30 tháng 12 năm 2022 của Chính phủ, thuộc trường hợp được áp dụng hoặc có thỏa thuận trong hợp đồng lao động áp dụng xếp lương theo Nghị định số 204/2004/NĐ-CP ngày 14 tháng 12 năm 2004.",
    },
    {
        "q": "Nghị định này quy định phạm vi điều chỉnh đối với những cơ quan, tổ chức, địa bàn và lực lượng nào?",
        "a": "Nghị định này quy định mức lương cơ sở áp dụng đối với người hưởng lương, phụ cấp và chế độ tiền thưởng áp dụng đối với người hưởng lương làm việc trong các cơ quan, tổ chức, đơn vị sự nghiệp công lập của Đảng, Nhà nước, Mặt trận Tổ quốc Việt Nam, tổ chức chính trị - xã hội và hội được ngân sách nhà nước hỗ trợ kinh phí hoạt động ở Trung ương, cấp tỉnh, cấp xã, đơn vị hành chính - kinh tế đặc biệt và lực lượng vũ trang.",
    },
    {
        "q": "Trong Nghị định, cấp tỉnh và cấp xã được hiểu như thế nào?",
        "a": "Tỉnh, thành phố trực thuộc trung ương gọi chung là cấp tỉnh; xã, phường, đặc khu trực thuộc cấp tỉnh gọi chung là cấp xã.",
    },
    {
        "q": "Nghị định này có hiệu lực thi hành từ ngày nào?",
        "a": "Nghị định này có hiệu lực thi hành kể từ ngày 01 tháng 7 năm 2026.",
    },
    {
        "q": "Nghị định nào hết hiệu lực kể từ ngày Nghị định này có hiệu lực thi hành?",
        "a": "Nghị định số 73/2024/NĐ-CP ngày 30 tháng 6 năm 2024 của Chính phủ quy định mức lương cơ sở và chế độ tiền thưởng đối với cán bộ, công chức, viên chức và lực lượng vũ trang hết hiệu lực kể từ ngày Nghị định này có hiệu lực thi hành.",
    },
    {
        "q": "Bộ trưởng Bộ Nội vụ có trách nhiệm hướng dẫn thực hiện nội dung nào?",
        "a": "Bộ trưởng Bộ Nội vụ hướng dẫn thực hiện các quy định về mức lương cơ sở tại Nghị định này đối với các đối tượng hưởng lương, phụ cấp trong các cơ quan, tổ chức, đơn vị sự nghiệp công lập của Đảng, Nhà nước, Mặt trận Tổ quốc Việt Nam, tổ chức chính trị - xã hội và hội.",
    },
    {
        "q": "Bộ trưởng Bộ Quốc phòng và Bộ trưởng Bộ Công an có trách nhiệm gì?",
        "a": "Bộ trưởng Bộ Quốc phòng, Bộ trưởng Bộ Công an hướng dẫn thực hiện các quy định tại Nghị định này đối với các đối tượng thuộc phạm vi quản lý.",
    },
    {
        "q": "Bộ trưởng Bộ Tài chính có những trách nhiệm nào theo khoản 3 Điều 7?",
        "a": "Bộ trưởng Bộ Tài chính hướng dẫn việc xác định nhu cầu, nguồn và phương thức chi thực hiện mức lương cơ sở và chế độ tiền thưởng, phạm vi trích số thu được để lại; hướng dẫn việc chi tiền lương và thu nhập đối với các cơ quan, đơn vị đang thực hiện cơ chế tài chính, thu nhập đặc thù ở trung ương trong thời gian chưa sửa đổi hoặc bãi bỏ; tổng hợp nhu cầu nguồn và trình cấp có thẩm quyền bổ sung kinh phí còn thiếu.",
    },
    {
        "q": "Dự thảo Nghị định này được Chính phủ ban hành theo đề nghị của ai?",
        "a": "Theo đề nghị của Bộ trưởng Bộ Nội vụ; Chính phủ ban hành Nghị định quy định mức lương cơ sở và chế độ tiền thưởng đối với cán bộ, công chức, viên chức và lực lượng vũ trang.",
    },
    {
        "q": "Tên đầy đủ của dự thảo Nghị định là gì?",
        "a": "NGHỊ ĐỊNH Quy định mức lương cơ sở và chế độ tiền thưởng đối với cán bộ, công chức, viên chức và lực lượng vũ trang.",
    },
]


def normalize(value: str) -> str:
    value = value.lower()
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def token_set(value: str) -> set[str]:
    return {x for x in re.findall(r"[\w./%-]+", normalize(value), flags=re.UNICODE) if len(x) >= 2}


def numbers(value: str) -> set[str]:
    return set(re.findall(r"\d+[./-]?\d*%?|\d{1,2}/\d{1,2}/\d{4}|nđ-cp|qh\d+", normalize(value)))


def judge(expected: str, actual: str, status: str) -> tuple[float, str]:
    if status != "success":
        return 0.0, f"Không có câu trả lời thành công: job {status}."
    if not actual.strip():
        return 0.0, "RAG trả lời rỗng."
    if "xử lý ai thất bại" in normalize(actual):
        return 0.0, "RAG báo lỗi xử lý AI."

    expected_tokens = token_set(expected)
    actual_tokens = token_set(actual)
    coverage = len(expected_tokens & actual_tokens) / max(len(expected_tokens), 1)
    expected_nums = numbers(expected)
    actual_nums = numbers(actual)
    missing_nums = sorted(expected_nums - actual_nums)

    score = min(10.0, max(0.0, coverage * 10.5))
    if missing_nums:
        score -= min(3.0, 0.8 * len(missing_nums))
    if any(marker in normalize(actual) for marker in ["không tìm thấy", "không có thông tin"]):
        score = min(score, 3.0)
    score = round(max(0.0, min(10.0, score)), 1)

    notes = []
    if score >= 8.5:
        notes.append("Đúng phần lớn nội dung cốt lõi.")
    elif score >= 6:
        notes.append("Đúng một phần nhưng còn thiếu ý đáng kể.")
    else:
        notes.append("Sai hoặc thiếu nhiều ý trọng yếu.")
    if missing_nums:
        notes.append("Thiếu/khác mốc pháp lý hoặc số liệu: " + ", ".join(missing_nums[:8]) + ".")
    extra_flags = []
    for flag in ["70%", "50%", "40%", "35%", "2.530.000", "01 tháng 7 năm 2026", "73/2024", "60/2021", "111/2025"]:
        if flag.lower() in normalize(actual) and flag.lower() not in normalize(expected):
            extra_flags.append(flag)
    if extra_flags:
        notes.append("Có dấu hiệu nêu thêm ngoài đáp án chuẩn: " + ", ".join(extra_flags[:5]) + ".")
    return score, " ".join(notes)


def mark_failed(job_id: int, message_id: int, reason: str) -> None:
    try:
        from database import models
        from database.db_config import SessionLocal
        from utils.time_utils import utc_now

        db = SessionLocal()
        try:
            job = db.query(models.BackgroundJob).filter_by(id=job_id).first()
            if job and job.status in {"queued", "running"}:
                job.status = "failed"
                job.progress = 100
                job.error = reason
                job.updated_at = utc_now()
                job.finished_at = utc_now()
            msg = db.query(models.ChatMessage).filter_by(id=message_id).first()
            if msg and msg.content == "Đang xử lý câu trả lời...":
                msg.content = "Xử lý AI thất bại.\n\n" + reason
            db.commit()
        finally:
            db.close()
    except Exception:
        pass


def ask_one(session: requests.Session, headers: dict[str, str], index: int, item: dict[str, str]) -> dict:
    started = time.time()
    response = session.post(
        f"{BASE_URL}/employee/chat",
        json={"question": item["q"], "session_id": SESSION_ID, "scope": "personal"},
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    job_id = data["job_id"]
    message_id = data.get("ai_message_id")

    final = None
    while time.time() - started < TIMEOUT_SECONDS:
        job_response = session.get(f"{BASE_URL}/jobs/{job_id}", headers=headers, timeout=20)
        job_response.raise_for_status()
        job = job_response.json()
        if job.get("status") in {"success", "failed"}:
            final = job
            break
        time.sleep(POLL_SECONDS)

    if final is None:
        reason = f"Timeout sau {TIMEOUT_SECONDS}s khi benchmark câu {index}."
        mark_failed(job_id, message_id, reason)
        final = {
            "id": job_id,
            "status": "timeout",
            "progress": None,
            "message_id": message_id,
            "result": None,
            "error": reason,
        }

    result = final.get("result") or {}
    actual = result.get("answer") or ""
    score, note = judge(item["a"], actual, final.get("status", "unknown"))
    elapsed = round(time.time() - started, 2)
    print(f"[{index:02d}/{len(QA)}] {final.get('status')} score={score} elapsed={elapsed}s", flush=True)
    return {
        "stt": index,
        "question": item["q"],
        "expected": item["a"],
        "rag_answer": actual,
        "score": score,
        "note": note,
        "job_id": job_id,
        "message_id": message_id,
        "status": final.get("status"),
        "elapsed_seconds": elapsed,
        "sources": result.get("sources") or [],
        "error": final.get("error"),
    }


def write_outputs(results: list[dict]) -> tuple[Path, Path]:
    output_dir = BACKEND / "benchmark_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"luongcoso_session63_30q_{stamp}.json"
    md_path = output_dir / f"luongcoso_session63_30q_{stamp}.md"
    average = round(sum(item["score"] for item in results) / max(len(results), 1), 2)
    success_count = sum(1 for item in results if item["status"] == "success")

    payload = {
        "session_id": SESSION_ID,
        "source_pdf": r"C:\Users\ADMIN\Downloads\duthaoluongcoso-17749265503301968823886.pdf",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "total": len(results),
            "success": success_count,
            "average_score": average,
            "max_context_chars": 4000,
        },
        "results": results,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Benchmark RAG - Dự thảo lương cơ sở",
        "",
        f"- Session: `{SESSION_ID}`",
        f"- Tổng số câu: `{len(results)}`",
        f"- Job thành công: `{success_count}/{len(results)}`",
        f"- Điểm trung bình: `{average}/10`",
        f"- Context cap: `_MAX_CONTEXT_CHARS=4000`",
        "",
        "| STT | Câu hỏi | Đáp án gốc chuẩn (PDF) | Câu trả lời RAG | Điểm & nhận xét |",
        "|---:|---|---|---|---|",
    ]
    for item in results:
        def cell(value: str) -> str:
            return (value or "").replace("\n", "<br>").replace("|", "\\|")

        lines.append(
            f"| {item['stt']} | {cell(item['question'])} | {cell(item['expected'])} | "
            f"{cell(item['rag_answer'] or item.get('error') or '')} | "
            f"**{item['score']}/10**<br>{cell(item['note'])}<br>`job={item['job_id']}` `status={item['status']}` |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> None:
    session = requests.Session()
    login = session.post(
        f"{BASE_URL}/auth/login",
        json={"username": USERNAME, "password": PASSWORD},
        timeout=20,
    )
    login.raise_for_status()
    headers = {"Authorization": "Bearer " + login.json()["access_token"]}

    results = []
    for index, item in enumerate(QA, 1):
        try:
            results.append(ask_one(session, headers, index, item))
        except Exception as exc:
            print(f"[{index:02d}/{len(QA)}] exception {type(exc).__name__}: {exc}", flush=True)
            score, note = judge(item["a"], "", "exception")
            results.append(
                {
                    "stt": index,
                    "question": item["q"],
                    "expected": item["a"],
                    "rag_answer": "",
                    "score": score,
                    "note": note,
                    "job_id": None,
                    "message_id": None,
                    "status": "exception",
                    "elapsed_seconds": None,
                    "sources": [],
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            break

    json_path, md_path = write_outputs(results)
    print("JSON=" + str(json_path).encode("unicode_escape").decode("ascii"), flush=True)
    print("MD=" + str(md_path).encode("unicode_escape").decode("ascii"), flush=True)


if __name__ == "__main__":
    main()
