import argparse
import json
import logging
import re
import sys
import time
import unicodedata
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_core.documents import Document as LCDocument
from transformers import AutoTokenizer

from database import models
from database.db_config import SessionLocal
from rag_engine.chroma_manager import ChromaDBManager, is_structure_context
from rag_engine.ollama_ai import OllamaAI
from services.chat.chat_service import NO_CONTEXT_ANSWER, normalize_chat_scope
from services.chat.context_service import accessible_attachment_ids, build_recent_chat_history
from services.rag.prompt_builder import PromptBuilder


OUT_DIR = Path("benchmark_outputs")
SESSION_IDS = [45, 46, 47]


QUESTION_SETS = {
    45: [
        # Easy
        {"level": "Dễ", "q": "Văn bản này là loại văn bản gì và quy định về vấn đề gì?", "expected": [["nghị định"], ["mức lương cơ sở"], ["chế độ tiền thưởng"]], "articles": [""]},
        {"level": "Dễ", "q": "Văn bản gồm bao nhiêu điều?", "expected": [["7"], ["điều"]], "articles": []},
        {"level": "Dễ", "q": "Mức lương cơ sở từ ngày 01/7/2026 là bao nhiêu?", "expected": [["2.530.000"], ["01 tháng 7 năm 2026", "01/7/2026"]], "articles": ["3"]},
        {"level": "Dễ", "q": "Nghị định này có hiệu lực thi hành từ ngày nào?", "expected": [["01 tháng 7 năm 2026", "01/7/2026"]], "articles": ["6"]},
        {"level": "Dễ", "q": "Nghị định nào hết hiệu lực khi nghị định này có hiệu lực?", "expected": [["73/2024/NĐ-CP", "73/2024/ND-CP"]], "articles": ["6"]},
        {"level": "Dễ", "q": "Điều 1 quy định nội dung gì?", "expected": [["phạm vi điều chỉnh"], ["mức lương cơ sở"], ["chế độ tiền thưởng"]], "articles": ["1"]},
        {"level": "Dễ", "q": "Điều 4 nói về vấn đề gì?", "expected": [["chế độ tiền thưởng"], ["thành tích công tác"], ["đánh giá"]], "articles": ["4"]},
        {"level": "Dễ", "q": "Quỹ tiền thưởng hằng năm bằng bao nhiêu phần trăm tổng quỹ tiền lương?", "expected": [["10%"], ["tổng quỹ tiền lương"]], "articles": ["4"]},
        {"level": "Dễ", "q": "Bộ trưởng Bộ Nội vụ có trách nhiệm gì?", "expected": [["Bộ Nội vụ"], ["hướng dẫn"], ["mức lương cơ sở"]], "articles": ["7"]},
        {"level": "Dễ", "q": "Bộ trưởng Bộ Tài chính được giao hướng dẫn những nội dung nào?", "expected": [["xác định nhu cầu"], ["nguồn"], ["phương thức chi"]], "articles": ["7"]},
        # Medium
        {"level": "Trung bình", "q": "Những nhóm nào thuộc đối tượng áp dụng mức lương cơ sở?", "expected": [["cán bộ"], ["công chức"], ["viên chức"], ["lực lượng vũ trang"]], "articles": ["2"]},
        {"level": "Trung bình", "q": "Người hưởng phụ cấp, sinh hoạt phí có thuộc đối tượng áp dụng chế độ tiền thưởng không?", "expected": [["không bao gồm"], ["phụ cấp"], ["sinh hoạt phí"]], "articles": ["2"]},
        {"level": "Trung bình", "q": "Mức lương cơ sở dùng làm căn cứ để tính những khoản nào?", "expected": [["bảng lương"], ["phụ cấp"], ["hoạt động phí", "sinh hoạt phí"], ["khoản trích"]], "articles": ["3"]},
        {"level": "Trung bình", "q": "Chế độ tiền thưởng được thực hiện dựa trên các căn cứ nào?", "expected": [["thành tích công tác đột xuất"], ["đánh giá"], ["xếp loại"]], "articles": ["4"]},
        {"level": "Trung bình", "q": "Quy chế tiền thưởng của cơ quan, đơn vị phải có những nội dung gì?", "expected": [["phạm vi"], ["đối tượng"], ["tiêu chí thưởng"], ["mức tiền thưởng"], ["quy trình"]], "articles": ["4"]},
        {"level": "Trung bình", "q": "Nếu cơ quan, đơn vị không sử dụng hết quỹ tiền thưởng của năm thì xử lý thế nào?", "expected": [["hủy dự toán", "huỷ dự toán"], ["nộp ngân sách"]], "articles": ["4"]},
        {"level": "Trung bình", "q": "Nguồn kinh phí của các Bộ, cơ quan trung ương gồm những nguồn nào?", "expected": [["10% tiết kiệm chi thường xuyên"], ["40% số thu"], ["cải cách tiền lương"]], "articles": ["5"]},
        {"level": "Trung bình", "q": "Nguồn kinh phí của các tỉnh, thành phố trực thuộc trung ương thì phân bổ như nào?", "expected": [["70% tăng thu"], ["50% tăng thu"], ["10% tiết kiệm chi thường xuyên"], ["cải cách tiền lương"], ["40% số thu"], ["35%"]], "articles": ["5"]},
        {"level": "Trung bình", "q": "Đơn vị sự nghiệp công lập nhóm 1, nhóm 2 tự đảm bảo kinh phí theo quy định nào?", "expected": [["tự đảm bảo"], ["60/2021/NĐ-CP", "60/2021/ND-CP"], ["111/2025/NĐ-CP", "111/2025/ND-CP"]], "articles": ["5"]},
        {"level": "Trung bình", "q": "Các đối tượng thuộc Quân đội và Công an được quy định như thế nào trong Điều 2?", "expected": [["sĩ quan"], ["quân nhân chuyên nghiệp"], ["công an nhân dân"], ["hạ sĩ quan"]], "articles": ["2"]},
        # Hard
        {"level": "Khó", "q": "Tóm tắt nội dung chính của nghị định theo từng nhóm: lương cơ sở, tiền thưởng, kinh phí và trách nhiệm thi hành.", "expected": [["lương cơ sở"], ["tiền thưởng"], ["kinh phí"], ["trách nhiệm thi hành"]], "articles": ["3", "4", "5", "7"]},
        {"level": "Khó", "q": "So sánh phạm vi điều chỉnh ở Điều 1 với đối tượng áp dụng ở Điều 2.", "expected": [["phạm vi điều chỉnh"], ["đối tượng áp dụng"], ["cơ quan, đơn vị"], ["người hưởng lương"]], "articles": ["1", "2"]},
        {"level": "Khó", "q": "Từ Điều 3 và Điều 6, hãy cho biết mức lương cơ sở mới áp dụng từ khi nào và thay thế quy định nào trước đó.", "expected": [["2.530.000"], ["01 tháng 7 năm 2026", "01/7/2026"], ["73/2024/NĐ-CP", "73/2024/ND-CP"]], "articles": ["3", "6"]},
        {"level": "Khó", "q": "Cơ quan, đơn vị cần làm gì để triển khai chế độ tiền thưởng theo Điều 4?", "expected": [["xây dựng Quy chế"], ["công khai"], ["thưởng đột xuất"], ["thưởng định kỳ"]], "articles": ["4"]},
        {"level": "Khó", "q": "Kinh phí thực hiện được phân bổ trách nhiệm giữa trung ương, địa phương và đơn vị sự nghiệp công lập như thế nào?", "expected": [["bộ, cơ quan trung ương"], ["tỉnh, thành phố"], ["đơn vị sự nghiệp công lập"], ["ngân sách trung ương"]], "articles": ["5"]},
        {"level": "Khó", "q": "Nếu một cơ quan trung ương đang có cơ chế tài chính, thu nhập đặc thù thì khi áp dụng mức lương cơ sở mới cần lưu ý gì?", "expected": [["bảo lưu phần chênh lệch"], ["thu nhập tăng thêm"], ["tháng 6 năm 2026"], ["01 tháng 7 năm 2026"]], "articles": ["3"]},
        {"level": "Khó", "q": "Những bộ nào được giao hướng dẫn thực hiện nghị định và mỗi bộ phụ trách nhóm nội dung nào?", "expected": [["Bộ Nội vụ"], ["Bộ Quốc phòng"], ["Bộ Công an"], ["Bộ Tài chính"]], "articles": ["7"]},
        {"level": "Khó", "q": "Nghị định này tác động đến những nhóm người hưởng lương nào trong khu vực công và lực lượng vũ trang?", "expected": [["cán bộ"], ["công chức"], ["viên chức"], ["Quân đội"], ["Công an"]], "articles": ["2"]},
        {"level": "Khó", "q": "Quy định về tiền thưởng có yêu cầu gắn mức thưởng với hệ số lương của từng người không?", "expected": [["không nhất thiết"], ["hệ số lương"], ["mức tiền thưởng cụ thể"]], "articles": ["4"]},
        {"level": "Khó", "q": "Từ toàn văn, hãy nêu các mốc thời gian quan trọng được đề cập trong nghị định.", "expected": [["01 tháng 7 năm 2026", "01/7/2026"], ["tháng 6 năm 2026"], ["30 tháng 6 năm 2024", "30/6/2024"]], "articles": ["3", "6"]},
    ],
    46: [
        # Easy
        {"level": "Dễ", "q": "Văn bản này quy định về vấn đề gì?", "expected": [["lễ tang"], ["quân nhân"], ["quốc phòng"]], "articles": ["1"]},
        {"level": "Dễ", "q": "Văn bản gồm bao nhiêu điều và bao nhiêu chương?", "expected": [["36", "37"], ["7"], ["chương"]], "articles": []},
        {"level": "Dễ", "q": "Điều 1 quy định phạm vi điều chỉnh như thế nào?", "expected": [["tổ chức lễ tang"], ["tham gia tổ chức lễ tang"], ["quân nhân"]], "articles": ["1"]},
        {"level": "Dễ", "q": "Điều 2 quy định đối tượng áp dụng là ai?", "expected": [["quân nhân"], ["công nhân"], ["viên chức quốc phòng"], ["cơ yếu"]], "articles": ["2"]},
        {"level": "Dễ", "q": "Điều 3 nêu nguyên tắc tổ chức lễ tang như thế nào?", "expected": [["trang trọng"], ["tiết kiệm"], ["phù hợp"]], "articles": ["3"]},
        {"level": "Dễ", "q": "Điều 5 quy định về nội dung gì?", "expected": [["trang phục"], ["lễ tang"], ["Quân đội chủ trì"]], "articles": ["5"]},
        {"level": "Dễ", "q": "Điều 12 nói về vấn đề gì?", "expected": [["đứng tên"], ["đưa tin buồn"]], "articles": ["12"]},
        {"level": "Dễ", "q": "Điều 20 quy định những nội dung nào?", "expected": [["tin buồn"], ["lời điếu"], ["đăng tin buồn"]], "articles": ["20"]},
        {"level": "Dễ", "q": "Điều 35 nói về vấn đề gì?", "expected": [["kinh phí"], ["xăng dầu"], ["bảo đảm"]], "articles": ["35"]},
        {"level": "Dễ", "q": "Điều 36 quy định nội dung gì?", "expected": [["hiệu lực"], ["thi hành"]], "articles": ["36"]},
        # Medium
        {"level": "Trung bình", "q": "Thông tư này áp dụng đối với những nhóm người nào?", "expected": [["quân nhân"], ["công chức quốc phòng"], ["công nhân quốc phòng"], ["viên chức quốc phòng"], ["cơ yếu"]], "articles": ["2"]},
        {"level": "Trung bình", "q": "Trang phục trong lễ tang do Quân đội chủ trì được quy định như thế nào?", "expected": [["trang phục"], ["lễ tang"], ["Quân đội chủ trì"]], "articles": ["5"]},
        {"level": "Trung bình", "q": "Lễ tang cấp cao áp dụng cho chức danh, cấp bậc nào?", "expected": [["Lễ tang Cấp cao"], ["chức danh"], ["cấp bậc quân hàm"]], "articles": ["9"]},
        {"level": "Trung bình", "q": "Ai phân cấp chủ trì tổ chức Lễ tang cấp cao?", "expected": [["phân cấp"], ["chủ trì"], ["Lễ tang"]], "articles": ["10"]},
        {"level": "Trung bình", "q": "Ban tổ chức Lễ tang cấp cao được quy định ở điều nào và gồm nội dung gì?", "expected": [["Ban Tổ chức Lễ tang"], ["Điều 11"]], "articles": ["11"]},
        {"level": "Trung bình", "q": "Lực lượng phục vụ Lễ tang cấp cao gồm những nội dung nào?", "expected": [["lực lượng phục vụ"], ["Lễ tang"]], "articles": ["14"]},
        {"level": "Trung bình", "q": "Phương tiện phục vụ Lễ tang được quy định như thế nào?", "expected": [["phương tiện"], ["phục vụ"], ["Lễ tang"]], "articles": ["15", "22"]},
        {"level": "Trung bình", "q": "Đăng tin buồn trên Báo Nhân dân và Báo Quân đội nhân dân được quy định ở đâu?", "expected": [["Báo Nhân dân"], ["Báo Quân đội nhân dân"], ["tin buồn"]], "articles": ["28"]},
        {"level": "Trung bình", "q": "Tổng cục Chính trị có trách nhiệm gì?", "expected": [["Tổng cục Chính trị"], ["tổ chức thực hiện", "hướng dẫn"]], "articles": ["29"]},
        {"level": "Trung bình", "q": "Cục Tài chính/Bộ Quốc phòng có trách nhiệm gì?", "expected": [["Cục Tài chính"], ["Bộ Quốc phòng"], ["kinh phí"]], "articles": ["33"]},
        # Hard
        {"level": "Khó", "q": "So sánh nhóm đối tượng áp dụng ở Điều 2 với phạm vi điều chỉnh ở Điều 1.", "expected": [["phạm vi điều chỉnh"], ["đối tượng áp dụng"], ["quân nhân"], ["quốc phòng"]], "articles": ["1", "2"]},
        {"level": "Khó", "q": "Tóm tắt cấu trúc văn bản theo các chương chính.", "expected": [["Quy định chung"], ["Lễ tang cấp Nhà nước"], ["Lễ tang cấp cao"], ["Tổ chức thực hiện"], ["Điều khoản thi hành"]], "articles": []},
        {"level": "Khó", "q": "Các quy định về tin buồn xuất hiện ở những điều nào và khác nhau ra sao?", "expected": [["Điều 12"], ["Điều 20"], ["Điều 25"], ["Điều 28"], ["tin buồn"]], "articles": ["12", "20", "25", "28"]},
        {"level": "Khó", "q": "Những điều nào quy định về phân cấp tổ chức hoặc phân cấp chủ trì lễ tang?", "expected": [["Điều 10"], ["Điều 17"], ["Điều 24"], ["phân cấp"]], "articles": ["10", "17", "24"]},
        {"level": "Khó", "q": "Quy định về lực lượng và phương tiện phục vụ lễ tang nằm ở những điều nào?", "expected": [["Điều 14"], ["Điều 15"], ["Điều 21"], ["Điều 22"]], "articles": ["14", "15", "21", "22"]},
        {"level": "Khó", "q": "Các đơn vị nào trong Chương VI được giao trách nhiệm tổ chức thực hiện?", "expected": [["Tổng cục Chính trị"], ["Bộ Tổng Tham mưu"], ["Tổng cục Hậu cần"], ["Cục Tài chính"], ["đơn vị trực thuộc"]], "articles": ["29", "30", "31", "33", "34"]},
        {"level": "Khó", "q": "Kinh phí và xăng dầu bảo đảm cho lễ tang được quy định như thế nào?", "expected": [["kinh phí"], ["xăng dầu"], ["bảo đảm"]], "articles": ["35"]},
        {"level": "Khó", "q": "Hiệu lực thi hành và trách nhiệm thi hành được quy định tại những điều nào?", "expected": [["Điều 36"], ["Điều 37"], ["hiệu lực"], ["trách nhiệm thi hành"]], "articles": ["36", "37"]},
        {"level": "Khó", "q": "Tóm tắt các nhóm lễ tang được văn bản phân loại.", "expected": [["Lễ tang cấp Nhà nước"], ["Lễ tang Cấp cao"], ["quân nhân từ Đại tá trở xuống"], ["quân nhân nghỉ hưu"]], "articles": []},
        {"level": "Khó", "q": "Nếu hỏi về lễ tang đối với quân nhân nghỉ hưu thì cần xem các điều nào?", "expected": [["Điều 26"], ["Điều 27"], ["Điều 28"], ["quân nhân nghỉ hưu"]], "articles": ["26", "27", "28"]},
    ],
    47: [
        # Easy
        {"level": "Dễ", "q": "Văn bản này là loại văn bản gì và nói về việc gì?", "expected": [["quyết định"], ["Ngày toàn dân tiết kiệm"], ["chống lãng phí"]], "articles": [""]},
        {"level": "Dễ", "q": "Văn bản gồm bao nhiêu điều?", "expected": [["3"], ["điều"]], "articles": []},
        {"level": "Dễ", "q": "Ngày toàn dân tiết kiệm, chống lãng phí năm 2026 là ngày nào?", "expected": [["31 tháng 5 năm 2026", "31/5/2026"]], "articles": ["1"]},
        {"level": "Dễ", "q": "Chủ đề của Ngày toàn dân tiết kiệm, chống lãng phí năm 2026 là gì?", "expected": [["Tiết kiệm năng lượng"], ["thịnh vượng tương lai"]], "articles": ["1"]},
        {"level": "Dễ", "q": "Điều 1 có mấy phần nội dung chính?", "expected": [["5"], ["phần", "nội dung"]], "articles": ["1"]},
        {"level": "Dễ", "q": "Mục đích tổ chức Ngày toàn dân tiết kiệm, chống lãng phí là gì?", "expected": [["nâng cao nhận thức"], ["ý nghĩa"], ["tiết kiệm"], ["chống lãng phí"]], "articles": ["1"]},
        {"level": "Dễ", "q": "Yêu cầu tổ chức các hoạt động hưởng ứng là gì?", "expected": [["thiết thực", "thực chất"], ["tiết kiệm"], ["hiệu quả"], ["không phô trương"]], "articles": ["1"]},
        {"level": "Dễ", "q": "Điều 2 quy định điều gì?", "expected": [["hiệu lực"], ["ngày ký ban hành"]], "articles": ["2"]},
        {"level": "Dễ", "q": "Điều 3 quy định về nội dung gì?", "expected": [["Bộ trưởng"], ["Thủ trưởng"], ["Chủ tịch Ủy ban nhân dân"], ["thi hành"]], "articles": ["3"]},
        {"level": "Dễ", "q": "Bộ Tài chính có trách nhiệm gì trong văn bản này?", "expected": [["Bộ Tài chính"], ["theo dõi"], ["hướng dẫn"], ["kiểm tra"]], "articles": ["1"]},
        # Medium
        {"level": "Trung bình", "q": "Liệt kê 5 phần nội dung của Điều 1.", "expected": [["Mục đích"], ["Yêu cầu"], ["Chủ đề"], ["hoạt động triển khai"], ["trách nhiệm thực hiện"]], "articles": ["1"]},
        {"level": "Trung bình", "q": "Các hoạt động triển khai Ngày toàn dân tiết kiệm, chống lãng phí gồm những gì?", "expected": [["tuyên truyền"], ["sáng kiến"], ["biểu dương"], ["khen thưởng"]], "articles": ["1"]},
        {"level": "Trung bình", "q": "Bộ Văn hóa, Thể thao và Du lịch được giao nhiệm vụ gì?", "expected": [["Bộ Văn hóa"], ["phong trào Văn hóa tiết kiệm"], ["chống lãng phí"]], "articles": ["1"]},
        {"level": "Trung bình", "q": "Bộ Khoa học và Công nghệ được giao nhiệm vụ gì?", "expected": [["Bộ Khoa học"], ["doanh nghiệp viễn thông"], ["nhắn tin"], ["thông điệp"]], "articles": ["1"]},
        {"level": "Trung bình", "q": "Các cơ quan báo chí có trách nhiệm gì?", "expected": [["cơ quan báo chí"], ["tuyên truyền"], ["phổ biến"], ["tiết kiệm"]], "articles": ["1"]},
        {"level": "Trung bình", "q": "Ủy ban nhân dân cấp tỉnh có trách nhiệm gì?", "expected": [["Ủy ban nhân dân cấp tỉnh"], ["tổ chức triển khai"], ["phạm vi quản lý"]], "articles": ["1"]},
        {"level": "Trung bình", "q": "Thông điệp nhắn tin tuyên truyền có nội dung gì?", "expected": [["Tiết kiệm năng lượng"], ["thịnh vượng tương lai"], ["lối sống xanh"]], "articles": ["1"]},
        {"level": "Trung bình", "q": "Thời gian tuyên truyền bằng tin nhắn là khi nào?", "expected": [["31 tháng 5 năm 2026", "31/5/2026"], ["Chủ nhật"]], "articles": ["1"]},
        {"level": "Trung bình", "q": "Tiêu đề tin nhắn tuyên truyền là gì?", "expected": [["CHINH PHU", "CHÍNH PHỦ"]], "articles": ["1"]},
        {"level": "Trung bình", "q": "Ai chịu trách nhiệm thi hành quyết định này?", "expected": [["Bộ trưởng"], ["Thủ trưởng cơ quan ngang bộ"], ["Chủ tịch Ủy ban nhân dân"], ["thi hành"]], "articles": ["3"]},
        # Hard
        {"level": "Khó", "q": "Tóm tắt nội dung Điều 1 theo 5 phần chính.", "expected": [["Mục đích"], ["Yêu cầu"], ["Chủ đề"], ["hoạt động"], ["trách nhiệm"]], "articles": ["1"]},
        {"level": "Khó", "q": "So sánh mục đích và yêu cầu của việc tổ chức Ngày toàn dân tiết kiệm, chống lãng phí.", "expected": [["nâng cao nhận thức"], ["hành động"], ["thiết thực", "thực chất"], ["không phô trương"]], "articles": ["1"]},
        {"level": "Khó", "q": "Các bộ, ngành và địa phương được phân công trách nhiệm như thế nào trong Điều 1?", "expected": [["Bộ Tài chính"], ["Bộ Văn hóa"], ["Bộ Khoa học"], ["Ủy ban nhân dân cấp tỉnh"]], "articles": ["1"]},
        {"level": "Khó", "q": "Những hình thức tuyên truyền nào được đề cập trong văn bản?", "expected": [["truyền thông"], ["mạng xã hội"], ["nhắn tin"], ["báo chí"]], "articles": ["1"]},
        {"level": "Khó", "q": "Văn bản yêu cầu biểu dương, khen thưởng những đối tượng nào?", "expected": [["tập thể"], ["cá nhân"], ["thành tích tiêu biểu"], ["sáng kiến"]], "articles": ["1"]},
        {"level": "Khó", "q": "Nêu các mốc thời gian quan trọng trong quyết định.", "expected": [["31 tháng 5 năm 2026", "31/5/2026"], ["ngày ký ban hành"], ["26.05.2026"]], "articles": ["1", "2"]},
        {"level": "Khó", "q": "Nếu cần truyền thông về chủ đề tiết kiệm năng lượng thì văn bản giao nhiệm vụ cho ai và bằng hình thức nào?", "expected": [["Bộ Khoa học"], ["doanh nghiệp viễn thông"], ["nhắn tin"], ["thông điệp"]], "articles": ["1"]},
        {"level": "Khó", "q": "Văn bản phân công cơ quan nào theo dõi, hướng dẫn, kiểm tra việc tổ chức hưởng ứng?", "expected": [["Bộ Tài chính"], ["theo dõi"], ["hướng dẫn"], ["kiểm tra"]], "articles": ["1"]},
        {"level": "Khó", "q": "Điều 1 và Điều 3 khác nhau về nội dung quản lý như thế nào?", "expected": [["Điều 1"], ["tổ chức triển khai"], ["Điều 3"], ["trách nhiệm thi hành"]], "articles": ["1", "3"]},
        {"level": "Khó", "q": "Từ toàn văn, hãy nêu mục tiêu quản lý nhà nước của quyết định này.", "expected": [["tiết kiệm"], ["chống lãng phí"], ["nâng cao nhận thức"], ["tổ chức triển khai"]], "articles": ["1"]},
    ],
}


class CaptureHandler(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.INFO)
        self.messages: list[str] = []

    def emit(self, record):
        self.messages.append(record.getMessage())


def norm(text: str) -> str:
    text = (text or "").lower().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


def group_hits(text: str, groups: list[list[str]]) -> tuple[int, int, float, str]:
    if not text or "tôi không tìm thấy" in text.lower():
        return 0, len(groups), 0.0, "FAIL"
    haystack = norm(text)
    hits = sum(1 for group in groups if any(norm(item) in haystack for item in group))
    total = len(groups)
    score = hits / total if total else 1.0
    label = "PASS" if score >= 0.75 else "PARTIAL" if score >= 0.5 else "FAIL"
    return hits, total, score, label


def count_tokens(tokenizer, text: str) -> int:
    return len(tokenizer.encode(text or "", add_special_tokens=False))


def compact_doc(doc: LCDocument) -> dict:
    meta = doc.metadata or {}
    return {
        "doc_id": meta.get("doc_id"),
        "article_number": str(meta.get("article_number") or ""),
        "article_title": str(meta.get("article_title") or ""),
        "parent_id": str(meta.get("parent_id") or ""),
        "parent_index": int(meta.get("parent_index") or 0),
        "child_index": int(meta.get("child_index") or 0),
        "chunk_index": int(meta.get("chunk_index") or 0),
        "group": str(meta.get("_retrieval_group") or ""),
        "score": float(meta.get("_retrieval_score") or 0.0),
        "preview": re.sub(r"\s+", " ", doc.page_content or "")[:260],
    }


def packing_metrics(docs: list[LCDocument], expected_articles: list[str], expected_groups: list[list[str]], context: str) -> dict:
    expected_articles = [str(item) for item in expected_articles if str(item)]
    expected_article_set = set(expected_articles)
    context_hits, context_total, context_score, _ = group_hits(context, expected_groups)
    compact = [compact_doc(doc) for doc in docs]
    relevant = []
    for item, doc in zip(compact, docs):
        text = f"{item['article_title']} {doc.page_content or ''}"
        by_article = bool(expected_article_set and item["article_number"] in expected_article_set)
        by_expected_text = group_hits(text, expected_groups)[0] > 0
        relevant.append(by_article or by_expected_text)
    parent_positions: dict[str, list[int]] = {}
    for item in compact:
        if item["parent_id"]:
            parent_positions.setdefault(item["parent_id"], []).append(item["child_index"])
    order_breaks = 0
    child_gap_count = 0
    for indices in parent_positions.values():
        for left, right in zip(indices, indices[1:]):
            if right < left:
                order_breaks += 1
            if abs(right - left) > 1:
                child_gap_count += 1
    article_counts: dict[str, int] = {}
    for item in compact:
        article = item["article_number"] or "none"
        article_counts[article] = article_counts.get(article, 0) + 1
    dominant_chunks = max(article_counts.values()) if article_counts else 0
    return {
        "final_chunks": len(compact),
        "relevant_chunks": sum(1 for item in relevant if item),
        "noise_chunks": sum(1 for item in relevant if not item),
        "relevant_ratio": round(sum(1 for item in relevant if item) / len(relevant), 3) if relevant else 0,
        "context_expected_hits": context_hits,
        "context_expected_total": context_total,
        "context_expected_score": round(context_score, 3),
        "dominant_article_ratio": round(dominant_chunks / len(compact), 3) if compact else 0,
        "parent_order_breaks": order_breaks,
        "child_gap_count": child_gap_count,
        "chunks": compact,
    }


def parse_retrieval_log(messages: list[str]) -> dict:
    data = {}
    route_matcher = re.compile(r"route=([a-zA-Z_]+)")
    hits_matcher = re.compile(r"hits=\(article:(\d+) keyword:(\d+) lexical:(\d+) attached:(\d+) vector:(\d+) final:(\d+)\)")
    number_matcher = re.compile(r"([a-zA-Z_]+)=([0-9.]+)")
    for message in messages:
        if "RAG retrieval timing" not in message:
            continue
        data.update({key: float(value) for key, value in number_matcher.findall(message)})
        route = route_matcher.search(message)
        if route:
            data["route"] = route.group(1)
        hits = hits_matcher.search(message)
        if hits:
            data.update(
                {
                    "article_hits": int(hits.group(1)),
                    "keyword_hits": int(hits.group(2)),
                    "lexical_hits": int(hits.group(3)),
                    "attached_hits": int(hits.group(4)),
                    "vector_hits": int(hits.group(5)),
                    "final_hits": int(hits.group(6)),
                }
            )
    return data


def run_question(db, tokenizer, session_id: int, item: dict, use_rewrite: bool, disable_rerank: bool) -> dict:
    session = db.query(models.ChatSession).filter(models.ChatSession.id == session_id).first()
    user = db.query(models.User).filter(models.User.id == session.user_id).first()
    question = item["q"]
    prompt_builder = PromptBuilder()
    capture = CaptureHandler()
    root = logging.getLogger()
    old_level = root.level
    root.setLevel(logging.INFO)
    root.addHandler(capture)
    captured_docs: list[LCDocument] = []
    started = time.perf_counter()
    try:
        attached_doc_ids = accessible_attachment_ids(db, user, session.id)
        history = build_recent_chat_history(db, session.id)
        ai = OllamaAI()
        rewrite_prompt = prompt_builder.build_rewrite_prompt(question, history)
        rewrite_started = time.perf_counter()
        rewritten_query = ai.rewrite_query(question, history) if use_rewrite else question
        rewrite_ms = (time.perf_counter() - rewrite_started) * 1000

        manager = ChromaDBManager()
        if disable_rerank:
            def no_rerank_pack(
                queries,
                keyword_targets,
                extra_doc_ids,
                article_docs,
                keyword_docs,
                lexical_docs,
                attached_docs,
                vector_docs,
            ):
                docs = manager._merge_document_lists(
                    article_docs,
                    keyword_docs,
                    lexical_docs,
                    attached_docs,
                    vector_docs,
                )
                return manager._trim_context_docs(docs)

            manager._rank_and_pack_context = no_rerank_pack
        original_format = manager._format_context_response

        def capture_format(docs):
            captured_docs[:] = list(docs)
            return original_format(docs)

        manager._format_context_response = capture_format
        retrieval_started = time.perf_counter()
        context, sources = manager.search_context_with_filter(
            query=rewritten_query,
            user_id=user.id,
            user_dept_id=user.department_id,
            search_scope=normalize_chat_scope("personal"),
            session_id=session.id,
            extra_doc_ids=attached_doc_ids if attached_doc_ids else None,
            original_query=question,
        )
        retrieval_ms = (time.perf_counter() - retrieval_started) * 1000
        answer_prompt = prompt_builder.build_answer_prompt(question, context, rewritten_query)
        answer_started = time.perf_counter()
        if is_structure_context(context):
            answer = context
        elif not (context or "").strip():
            answer = NO_CONTEXT_ANSWER
        else:
            answer = ai.generate_answer(question, context, rewritten_query)
        answer_ms = (time.perf_counter() - answer_started) * 1000
    finally:
        root.removeHandler(capture)
        root.setLevel(old_level)

    answer_hits, answer_total, answer_score, answer_label = group_hits(answer, item["expected"])
    packing = packing_metrics(captured_docs, item.get("articles", []), item["expected"], context)
    retrieval_log = parse_retrieval_log(capture.messages)
    return {
        "session_id": session_id,
        "level": item["level"],
        "question": question,
        "expected_articles": item.get("articles", []),
        "rewritten_query": rewritten_query,
        "sources": sources,
        "answer": re.sub(r"\s+", " ", answer or "").strip(),
        "answer_eval": answer_label,
        "answer_score": round(answer_score, 3),
        "answer_hits": answer_hits,
        "answer_total": answer_total,
        "context_chars": len(context or ""),
        "context_tokens": count_tokens(tokenizer, context),
        "rewrite_prompt_tokens": count_tokens(tokenizer, rewrite_prompt) if history.strip() and use_rewrite else 0,
        "answer_prompt_tokens": count_tokens(tokenizer, answer_prompt),
        "total_ms": round((time.perf_counter() - started) * 1000, 1),
        "rewrite_ms": round(rewrite_ms, 1),
        "retrieval_ms": round(retrieval_ms, 1),
        "answer_ms": round(answer_ms, 1),
        "retrieval_log": retrieval_log,
        "disable_rerank": disable_rerank,
        "packing": packing,
    }


def aggregate(rows: list[dict]) -> dict:
    def pct(count, total):
        return round(count * 100 / total, 1) if total else 0

    by_level = {}
    for level in ["Dễ", "Trung bình", "Khó"]:
        subset = [row for row in rows if row["level"] == level]
        if not subset:
            continue
        by_level[level] = {
            "count": len(subset),
            "pass": sum(1 for row in subset if row["answer_eval"] == "PASS"),
            "partial": sum(1 for row in subset if row["answer_eval"] == "PARTIAL"),
            "fail": sum(1 for row in subset if row["answer_eval"] == "FAIL"),
            "avg_answer_score": round(mean(row["answer_score"] for row in subset), 3),
            "avg_context_tokens": round(mean(row["context_tokens"] for row in subset), 1),
            "avg_answer_prompt_tokens": round(mean(row["answer_prompt_tokens"] for row in subset), 1),
            "avg_total_ms": round(mean(row["total_ms"] for row in subset), 1),
            "avg_relevant_ratio": round(mean(row["packing"]["relevant_ratio"] for row in subset), 3),
            "avg_context_expected_score": round(mean(row["packing"]["context_expected_score"] for row in subset), 3),
            "avg_noise_chunks": round(mean(row["packing"]["noise_chunks"] for row in subset), 2),
        }
    return {
        "count": len(rows),
        "pass": sum(1 for row in rows if row["answer_eval"] == "PASS"),
        "partial": sum(1 for row in rows if row["answer_eval"] == "PARTIAL"),
        "fail": sum(1 for row in rows if row["answer_eval"] == "FAIL"),
        "pass_pct": pct(sum(1 for row in rows if row["answer_eval"] == "PASS"), len(rows)),
        "avg_answer_score": round(mean(row["answer_score"] for row in rows), 3),
        "avg_context_tokens": round(mean(row["context_tokens"] for row in rows), 1),
        "avg_answer_prompt_tokens": round(mean(row["answer_prompt_tokens"] for row in rows), 1),
        "avg_total_ms": round(mean(row["total_ms"] for row in rows), 1),
        "stage_totals_ms": {
            "rewrite_ms": round(sum(row["rewrite_ms"] for row in rows), 1),
            "retrieval_ms": round(sum(row["retrieval_ms"] for row in rows), 1),
            "answer_ms": round(sum(row["answer_ms"] for row in rows), 1),
        },
        "packing": {
            "avg_final_chunks": round(mean(row["packing"]["final_chunks"] for row in rows), 2),
            "avg_relevant_ratio": round(mean(row["packing"]["relevant_ratio"] for row in rows), 3),
            "avg_context_expected_score": round(mean(row["packing"]["context_expected_score"] for row in rows), 3),
            "avg_noise_chunks": round(mean(row["packing"]["noise_chunks"] for row in rows), 2),
            "total_parent_order_breaks": sum(row["packing"]["parent_order_breaks"] for row in rows),
            "total_child_gap_count": sum(row["packing"]["child_gap_count"] for row in rows),
        },
        "by_level": by_level,
    }


def write_markdown(path: Path, results: dict) -> None:
    lines = ["# RAG Benchmark Sessions 45, 46, 47", ""]
    overall_rows = [row for rows in results["sessions"].values() for row in rows]
    overall = aggregate(overall_rows)
    lines.extend(
        [
            "## Tổng Quan",
            "",
            f"- Tổng câu hỏi: {overall['count']}",
            f"- PASS/PARTIAL/FAIL: {overall['pass']} / {overall['partial']} / {overall['fail']} ({overall['pass_pct']}% PASS)",
            f"- Avg answer score: {overall['avg_answer_score']}",
            f"- Avg context tokens: {overall['avg_context_tokens']}",
            f"- Avg answer prompt tokens: {overall['avg_answer_prompt_tokens']}",
            f"- Avg total time: {overall['avg_total_ms']} ms",
            f"- Avg relevant chunk ratio: {overall['packing']['avg_relevant_ratio']}",
            f"- Avg context expected score: {overall['packing']['avg_context_expected_score']}",
            f"- Avg noise chunks: {overall['packing']['avg_noise_chunks']}",
            "",
            "## Theo Session",
            "",
            "| Session | PASS | PARTIAL | FAIL | Avg Score | Avg Ctx Tok | Avg Prompt Tok | Avg Time ms | Relevant Ratio | Context Coverage | Noise Chunks |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for session_id, rows in results["sessions"].items():
        stats = aggregate(rows)
        lines.append(
            f"| {session_id} | {stats['pass']} | {stats['partial']} | {stats['fail']} | "
            f"{stats['avg_answer_score']} | {stats['avg_context_tokens']} | {stats['avg_answer_prompt_tokens']} | "
            f"{stats['avg_total_ms']} | {stats['packing']['avg_relevant_ratio']} | "
            f"{stats['packing']['avg_context_expected_score']} | {stats['packing']['avg_noise_chunks']} |"
        )
    lines.extend(["", "## Chi Tiết Câu Hỏi", ""])
    for session_id, rows in results["sessions"].items():
        lines.extend(
            [
                f"### Session {session_id}",
                "",
                "| # | Mức | Eval | Score | Route | Ctx Tok | Prompt Tok | Rel/Noise | Ctx Cover | Time s | Question |",
                "|---:|---|---|---:|---|---:|---:|---|---:|---:|---|",
            ]
        )
        for idx, row in enumerate(rows, start=1):
            route = row["retrieval_log"].get("route", "-")
            packing = row["packing"]
            lines.append(
                f"| {idx} | {row['level']} | {row['answer_eval']} | {row['answer_score']} | {route} | "
                f"{row['context_tokens']} | {row['answer_prompt_tokens']} | "
                f"{packing['relevant_chunks']}/{packing['noise_chunks']} | {packing['context_expected_score']} | "
                f"{round(row['total_ms'] / 1000, 1)} | {row['question']} |"
            )
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sessions", nargs="*", type=int, default=SESSION_IDS)
    parser.add_argument("--no-rewrite", action="store_true")
    parser.add_argument("--disable-rerank", action="store_true")
    args = parser.parse_args()

    OUT_DIR.mkdir(exist_ok=True)
    tokenizer = AutoTokenizer.from_pretrained(
        "Qwen/Qwen2.5-3B-Instruct",
        cache_dir=str(Path("models/huggingface").resolve()),
        trust_remote_code=True,
    )
    db = SessionLocal()
    results = {
        "sessions": {},
        "config": {
            "use_rewrite": not args.no_rewrite,
            "disable_rerank": args.disable_rerank,
        },
    }
    try:
        for session_id in args.sessions:
            rows = []
            print(f"SESSION {session_id}: {len(QUESTION_SETS[session_id])} questions", flush=True)
            for idx, item in enumerate(QUESTION_SETS[session_id], start=1):
                row = run_question(
                    db,
                    tokenizer,
                    session_id,
                    item,
                    use_rewrite=not args.no_rewrite,
                    disable_rerank=args.disable_rerank,
                )
                rows.append(row)
                print(
                    f"  {idx:02d}/30 {item['level']} {row['answer_eval']} "
                    f"score={row['answer_score']} ctx={row['context_tokens']} "
                    f"rel={row['packing']['relevant_ratio']} time={row['total_ms']/1000:.1f}s",
                    flush=True,
                )
            results["sessions"][str(session_id)] = rows
    finally:
        db.close()

    stamp = time.strftime("%Y%m%d_%H%M%S")
    json_path = OUT_DIR / f"rag_sessions_45_46_47_{stamp}.json"
    md_path = OUT_DIR / f"rag_sessions_45_46_47_{stamp}.md"
    json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(md_path, results)
    print(f"JSON={json_path.resolve()}")
    print(f"MARKDOWN={md_path.resolve()}")


if __name__ == "__main__":
    main()
