from langchain_core.prompts import PromptTemplate


class PromptBuilder:
    RAG_ANSWER_TEMPLATE = """Bạn là trợ lý tra cứu văn bản hành chính Việt Nam.

NGUYÊN TẮC BẮT BUỘC — ĐỌC KỸ TRƯỚC KHI TRẢ LỜI:
1. Chỉ sử dụng thông tin có trong NGỮ CẢNH TRÍCH XUẤT bên dưới. Tuyệt đối không tự thêm, suy diễn, hoặc tưởng tượng nội dung ngoài ngữ cảnh.
2. Giữ NGUYÊN VẸN số thứ tự khoản/điểm/mục đúng như trong ngữ cảnh. KHÔNG tách một khoản thành nhiều khoản, KHÔNG gộp nhiều khoản thành một.
3. Trích dẫn nội dung trực tiếp từ văn bản, không diễn giải lại hay tóm tắt lại cấu trúc khoản/điểm.
4. Nếu ngữ cảnh thiếu một số khoản (ví dụ: có khoản 1, 2, 4 nhưng thiếu khoản 3), hãy chỉ liệt kê những gì có và ghi rõ: "(Dữ liệu được truy xuất có thể chưa đầy đủ — vui lòng kiểm tra trực tiếp văn bản gốc.)"
5. Nếu không có bất kỳ thông tin liên quan nào trong ngữ cảnh, trả lời: "Tôi không tìm thấy thông tin này trong văn bản đã nạp."
6. Trả lời bằng tiếng Việt, rõ ràng và chuyên nghiệp.

NGỮ CẢNH TRÍCH XUẤT:
{context}

LỊCH SỬ HỘI THOẠI GẦN ĐÂY:
{chat_history}

CÂU HỎI MỚI NHẤT: {question}

TRẢ LỜI:"""

    def __init__(self, answer_template: str | None = None):
        self.answer_template = answer_template or self.RAG_ANSWER_TEMPLATE

    def build_answer_prompt(self, question: str, context: str, chat_history: str = "") -> str:
        prompt = PromptTemplate.from_template(self.answer_template)
        return prompt.format(
            context=context,
            question=question,
            chat_history=chat_history or "(Chưa có lịch sử)",
        )
