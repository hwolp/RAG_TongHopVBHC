from langchain_core.prompts import PromptTemplate


class PromptBuilder:
    RAG_ANSWER_TEMPLATE = """Bạn là trợ lý tra cứu văn bản hành chính Việt Nam. Hãy trả lời câu hỏi gốc dựa trên ngữ cảnh trích xuất.

NGỮ CẢNH TRÍCH XUẤT:
{context}

CÂU HỎI GỐC: {question}

CÂU HỎI ĐÃ LÀM RÕ ĐỂ TÌM KIẾM: {rewritten_query}

NGUYÊN TẮC:
1. Chỉ dùng thông tin trong NGỮ CẢNH TRÍCH XUẤT.
2. Trả lời theo CÂU HỎI GỐC; chỉ dùng CÂU HỎI ĐÃ LÀM RÕ để hiểu đại từ hoặc ngữ cảnh hội thoại.
3. Nếu ngữ cảnh có Điều, khoản hoặc tiêu đề liên quan trực tiếp, phải trả lời dựa trên phần đó, không từ chối chung chung.
4. Nếu ngữ cảnh có nội dung liên quan, hãy trả lời trực tiếp, ngắn gọn và có thể tổng hợp các ý chính.
5. Khi có nhãn nguồn trong ngữ cảnh như [Điều 1], [Điều 2], hãy trích dẫn nhãn đó ở cuối ý liên quan.
6. Chỉ trả lời "Tôi không tìm thấy thông tin này trong văn bản đã nạp." khi ngữ cảnh không có nội dung liên quan đến câu hỏi.
7. Không lặp lại các ý trong cùng một câu trả lời nhiều lần.

TRẢ LỜI:"""

    REWRITE_QUERY_TEMPLATE = """Viết lại CÂU HỎI TIẾP THEO thành một câu hỏi độc lập để dùng cho tìm kiếm tài liệu.

YÊU CẦU:
- Nếu câu hỏi đã đầy đủ ý nghĩa hoặc là chủ đề mới, giữ nguyên câu hỏi.
- Chỉ dùng lịch sử để làm rõ đại từ/cụm như "văn bản này", "thông tư này", "đối tượng đó".
- Không trả lời câu hỏi.
- Chỉ trả về một câu hỏi duy nhất, không giải thích.

LỊCH SỬ:
{chat_history}

CÂU HỎI TIẾP THEO: {question}

CÂU HỎI ĐỘC LẬP:"""

    def __init__(self, answer_template: str | None = None):
        self.answer_template = answer_template or self.RAG_ANSWER_TEMPLATE

    def build_answer_prompt(self, question: str, context: str, rewritten_query: str = "") -> str:
        prompt = PromptTemplate.from_template(self.answer_template)
        return prompt.format(
            context=context,
            question=question,
            rewritten_query=rewritten_query or "(Giống câu hỏi gốc)",
        )

    def build_rewrite_prompt(self, question: str, chat_history: str = "") -> str:
        prompt = PromptTemplate.from_template(self.REWRITE_QUERY_TEMPLATE)
        return prompt.format(
            question=question,
            chat_history=chat_history or "(Chưa có lịch sử)",
        )
