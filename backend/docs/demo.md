I. Chức năng Quản trị hệ thống & Tài khoản
1. Quản lý Đăng nhập / Đăng xuất
ID	FUNC-AUTH-01
Tên chức năng	Đăng nhập hệ thống
Tác nhân	Người dùng (Admin, Trưởng phòng, Nhân viên)
Mô tả	Người dùng nhập tài khoản, mật khẩu để truy cập vào hệ thống.
Đầu vào	Tên đăng nhập, mật khẩu (có thể captcha, MFA tùy cấu hình).
Xử lý	Hệ thống xác thực thông tin, kiểm tra trạng thái tài khoản (bị khóa/chưa kích hoạt), ghi log đăng nhập.
Đầu ra	Thành công: Chuyển đến màn hình chính + sinh token/session. Thất bại: Thông báo lỗi.
Điều kiện tiên quyết	Tài khoản tồn tại, chưa bị khóa, đúng mật khẩu.
Quyền	Tất cả người dùng đã đăng ký.
ID	FUNC-AUTH-02
Tên chức năng	Đăng xuất hệ thống
Tác nhân	Người dùng
Mô tả	Người dùng kết thúc phiên làm việc, hệ thống hủy session/token.
Xử lý	Xóa thông tin phiên đăng nhập trên server và client.
Đầu ra	Chuyển về màn hình đăng nhập.
2. Quản lý danh mục Người dùng & Tài khoản
ID	FUNC-USER-01
Tên	Xem danh sách người dùng + Tìm kiếm
Tác nhân	Admin
Mô tả	Admin xem danh sách tất cả người dùng, lọc theo phòng ban, vai trò, trạng thái.
Đầu vào	Từ khóa (tên, email), bộ lọc (phòng ban, vai trò, trạng thái).
Xử lý	Truy vấn cơ sở dữ liệu, phân trang.
Đầu ra	Danh sách người dùng kèm thông tin: ID, họ tên, phòng ban, vai trò, trạng thái (hoạt động/khóa).
ID	FUNC-USER-02
Tên	Thêm mới tài khoản
Tác nhân	Admin
Mô tả	Tạo tài khoản mới cho nhân viên.
Đầu vào	Họ tên, email, phòng ban, vai trò (nhân viên/trưởng phòng/admin), mật khẩu tạm thời.
Xử lý	Kiểm tra email trùng, mã hóa mật khẩu, sinh ID, gửi thông báo qua email.
Đầu ra	Thông báo thành công, tài khoản được thêm vào danh sách.
ID	FUNC-USER-03
Tên	Chỉnh sửa thông tin tài khoản
Tác nhân	Admin
Mô tả	Cập nhật họ tên, phòng ban, vai trò, reset mật khẩu.
Đầu ra	Lưu thay đổi, ghi log lịch sử sửa.
ID	FUNC-USER-04
Tên	Khóa / Mở khóa / Xóa tài khoản
Tác nhân	Admin
Mô tả	Admin thay đổi trạng thái tài khoản: khóa (không đăng nhập được), mở khóa, hoặc xóa vĩnh viễn.
Xử lý	Xóa mềm (cập nhật trạng thái deleted_at) đối với xóa.
Điều kiện	Không thể xóa tài khoản đang có tài liệu quan trọng (có thể chuyển giao hoặc cảnh báo).
3. Quản lý nhóm quyền
ID	FUNC-ROLE-01
Tên	Xem danh sách nhóm quyền
Tác nhân	Admin
Mô tả	Hiển thị các vai trò có sẵn (Admin, Trưởng phòng, Nhân viên, Khách…) và quyền chi tiết.
ID	FUNC-ROLE-02
Tên	Thêm / Sửa / Xóa nhóm quyền
Tác nhân	Admin
Mô tả	Tạo nhóm quyền mới, gán các quyền cụ thể (VD: tải lên tài liệu phòng ban, xóa tài liệu công ty...). Sửa tên hoặc quyền, xóa nhóm (nếu không còn người dùng).
4. Quản lý cấu hình hệ thống (Metadata, Tag)
ID	FUNC-CFG-01
Tên	Xem danh sách cấu hình
Tác nhân	Admin
Mô tả	Hiển thị danh sách các metadata (loại văn bản, lĩnh vực, trạng thái) và tag dùng chung.
ID	FUNC-CFG-02
Tên	Thêm / Sửa / Xóa cấu hình
Tác nhân	Admin
Mô tả	Thêm một metadata mới (VD: "Độ mật: Tuyệt mật, Nội bộ, Công khai"). Sửa tên, xóa (kiểm tra ràng buộc nếu đang được dùng).
5. Quản lý kho tài liệu chung (Public/SQP)
ID	FUNC-PUB-01
Tên	Xem danh sách tài liệu công ty
Tác nhân	Admin
Mô tả	Hiển thị toàn bộ tài liệu công khai (quy định, quy trình SQP), hỗ trợ tìm kiếm, lọc theo danh mục.
ID	FUNC-PUB-02
Tên	Tải lên tài liệu chung mới
Tác nhân	Admin
Mô tả	Upload file (PDF, Word, Excel…), nhập metadata: tiêu đề, mô tả, danh mục, tag, hiệu lực từ – đến.
Xử lý	Lưu file vào storage, thêm bản ghi vào DB, đồng thời gửi yêu cầu index lên Vector DB.
ID	FUNC-PUB-03
Tên	Sửa thông tin / Xóa tài liệu chung
Tác nhân	Admin
Mô tả	Cập nhật metadata, hoặc xóa tài liệu (xóa mềm). Khi xóa, cũng xóa vector index tương ứng.
6. Quản lý Vector DB
ID	FUNC-VEC-01
Tên	Xem trạng thái dữ liệu Vector
Tác nhân	Admin
Mô tả	Hiển thị số collection, số lượng chunks đã index, dung lượng, thời gian cập nhật cuối.
ID	FUNC-VEC-02
Tên	Thực hiện Re-index
Tác nhân	Admin
Mô tả	Quét lại toàn bộ tài liệu (hoặc từng phòng ban) để cập nhật vector embedding.
Xử lý	Chạy background job, ghi log tiến trình.
ID	FUNC-VEC-03
Tên	Xóa Collection (bảo trì)
Tác nhân	Admin
Mô tả	Xóa hoàn toàn một collection vector (khi thay đổi cấu trúc hoặc lỗi). Cảnh báo trước khi xóa.
II. Chức năng Quản lý tài liệu
7. Quản lý tài liệu cá nhân
ID	FUNC-DOC-PRI-01
Tên	Xem danh sách tài liệu cá nhân & tìm kiếm
Tác nhân	Nhân viên
Mô tả	Hiển thị các file đã upload (chỉ mình thấy). Tìm kiếm theo tên, nội dung (full-text).
ID	FUNC-DOC-PRI-02
Tên	Xem trước & Xem chi tiết
Tác nhân	Nhân viên
Mô tả	Xem nội dung tài liệu (preview dạng PDF/image/text), hiển thị metadata, lịch sử phiên bản.
ID	FUNC-DOC-PRI-03
Tên	Tải lên tài liệu mới
Tác nhân	Nhân viên
Đầu vào	File, tiêu đề, tag (tùy chọn).
Xử lý	Lưu vào thư mục cá nhân, tự động sinh phiên bản 1.0.
ID	FUNC-DOC-PRI-04
Tên	Cập nhật phiên bản (ghi đè)
Tác nhân	Nhân viên
Mô tả	Tải file mới lên thay thế file cũ, giữ nguyên metadata, tăng số phiên bản. Lưu lại file cũ dưới dạng lịch sử (nếu cần).
ID	FUNC-DOC-PRI-05
Tên	Tải xuống / Xóa
Tác nhân	Nhân viên
Mô tả	Tải file về máy. Xóa: chuyển vào thùng rác (có thể khôi phục trong 30 ngày).
8. Quản lý tài liệu phòng ban
ID	FUNC-DOC-DEPT-01
Tên	Xem / Tìm kiếm tài liệu phòng ban
Tác nhân	Trưởng phòng, Nhân viên (trong phòng)
Mô tả	Tất cả thành viên trong phòng đều có thể xem tài liệu của phòng. Trưởng phòng có thêm quyền sửa/xóa.
ID	FUNC-DOC-DEPT-02
Tên	Tải lên / Cập nhật / Xóa
Tác nhân	Trưởng phòng
Mô tả	Tương tự chức năng cá nhân nhưng áp dụng cho không gian phòng ban.
9. Quản lý Tags
ID	FUNC-TAG-01
Tên	Xem danh sách thẻ
Tác nhân	Nhân viên, Trưởng phòng
Mô tả	Xem tất cả tag đã có (toàn hệ thống).
ID	FUNC-TAG-02
Tên	Thêm thẻ / Gắn thẻ vào tài liệu
Tác nhân	Nhân viên
Mô tả	Khi upload hoặc chỉnh sửa tài liệu, có thể chọn tag có sẵn hoặc tạo tag mới. Tag mới sẽ được thêm vào danh mục chung.
ID	FUNC-TAG-03
Tên	Sửa tên thẻ / Xóa thẻ
Tác nhân	Nhân viên (chỉ sửa/xóa tag do mình tạo? Hoặc Admin toàn quyền)
Mô tả	Khi sửa tên thẻ, tất cả tài liệu gắn thẻ cũ sẽ được cập nhật. Xóa thẻ sẽ bỏ gắn khỏi tài liệu.
III. Chức năng Hỏi đáp AI & Tra cứu
10. Giao diện Chat AI
ID	FUNC-AI-01
Tên	Tùy chỉnh phạm vi quét dữ liệu (Scope)
Tác nhân	Người dùng
Mô tả	Trước khi hỏi, người dùng chọn phạm vi: chỉ tài liệu cá nhân / phòng ban / toàn công ty / một số tag cụ thể.
ID	FUNC-AI-02
Tên	Nhập câu hỏi & Nhận câu trả lời
Tác nhân	Người dùng
Đầu vào	Câu hỏi bằng tiếng Việt (hoặc Anh).
Xử lý	Hệ thống RAG: truy vấn Vector DB tìm các đoạn liên quan → gửi kèm prompt → LLM sinh câu trả lời.
Đầu ra	Câu trả lời dạng văn bản tự nhiên.
ID	FUNC-AI-03
Tên	Xem danh sách minh chứng (Citations)
Tác nhân	Người dùng
Mô tả	Bên dưới câu trả lời hiển thị các nguồn (tên tài liệu, đoạn trích, đường dẫn). Người dùng click xem chi tiết đoạn gốc.
11. Quản lý phiên hội thoại
ID	FUNC-CHAT-01
Tên	Xem lịch sử phiên hội thoại
Tác nhân	Người dùng
Mô tả	Hiển thị danh sách các cuộc trò chuyện đã có (theo thời gian, tên phiên).
ID	FUNC-CHAT-02
Tên	Tạo phiên mới / Đổi tên / Xóa
Tác nhân	Người dùng
Mô tả	Tạo phiên mới (mặc định tên "Phiên mới HH:MM"). Đổi tên phiên để dễ nhận biết chủ đề. Xóa phiên (xóa toàn bộ lịch sử chat trong phiên).
12. Tra cứu quy định công cộng (SQP)
ID	FUNC-SQP-01
Tên	Duyệt quy định theo danh mục
Tác nhân	Người dùng
Mô tả	Xem cây danh mục (VD: Quy chế nhân sự, Quy định tài chính, Quy trình ISO). Click vào xem danh sách văn bản.
ID	FUNC-SQP-02
Tên	Tra cứu bằng từ khóa
Tác nhân	Người dùng
Mô tả	Tìm kiếm trong toàn bộ kho SQP (full-text + vector).
ID	FUNC-SQP-03
Tên	Đọc / Xem chi tiết văn bản
Tác nhân	Người dùng
Mô tả	Xem nội dung văn bản quy định dạng HTML hoặc file gốc.
13. Quản lý câu lệnh tra cứu (Prompts)
ID	FUNC-PROMPT-01
Tên	Lưu câu lệnh tra cứu
Tác nhân	Người dùng
Mô tả	Trong màn hình chat, người dùng có thể lưu một câu hỏi mẫu (kèm scope, prompt) để dùng lại.
ID	FUNC-PROMPT-02
Tên	Xem danh sách / Xóa câu lệnh đã lưu
Tác nhân	Người dùng
Mô tả	Quản lý các prompt đã lưu: xem, sao chép, xóa.
IV. Chức năng Điều phối & Phân quyền
14. Chia sẻ tài liệu liên phòng
ID	FUNC-SHARE-01
Tên	Phân quyền chia sẻ tài liệu (nhập ID)
Tác nhân	Trưởng phòng (chủ sở hữu tài liệu phòng ban)
Mô tả	Trưởng phòng chọn tài liệu → nhập ID hoặc email người dùng (thuộc phòng khác) → cấp quyền Xem hoặc Xem & Tải.
Đầu ra	Người được chia sẻ thấy tài liệu trong danh sách "Được chia sẻ với tôi".
ID	FUNC-SHARE-02
Tên	Thu hồi quyền truy cập
Tác nhân	Trưởng phòng
Mô tả	Xóa quyền của một người dùng đối với tài liệu đã chia sẻ.
15. Ủy quyền đóng góp tài liệu
ID	FUNC-DELEGATE-01
Tên	Xem danh sách nhân viên được ủy quyền
Tác nhân	Trưởng phòng
Mô tả	Hiển thị những nhân viên trong phòng được phép đóng góp tài liệu lên không gian chung (kho công ty hoặc phòng ban khác).
ID	FUNC-DELEGATE-02
Tên	Ủy quyền đóng góp
Tác nhân	Trưởng phòng
Mô tả	Chọn nhân viên → chỉ định quyền "Được đề xuất tài liệu lên kho công ty" hoặc "Được upload trực tiếp lên phòng ban khác".
ID	FUNC-DELEGATE-03
Tên	Thu hồi quyền đóng góp
Tác nhân	Trưởng phòng
Mô tả	Xóa ủy quyền, nhân viên không còn quyền đó nữa.
16. Đề xuất tài liệu lên kho Công ty
ID	FUNC-PROPOSE-01
Tên	Xem danh sách tài liệu đã đề xuất
Tác nhân	Trưởng phòng
Mô tả	Hiển thị các tài liệu đã được trưởng phòng (hoặc ủy quyền) đề xuất đưa lên kho công ty, kèm trạng thái: chờ duyệt, đã duyệt, từ chối.
ID	FUNC-PROPOSE-02
Tên	Đề xuất tài liệu
Tác nhân	Trưởng phòng (hoặc người được ủy quyền)
Mô tả	Chọn một tài liệu từ phòng ban → gửi đề xuất lên Admin kèm lý do.
ID	FUNC-PROPOSE-03
Tên	Hủy đề xuất
Tác nhân	Trưởng phòng
Mô tả	Nếu chưa được Admin xử lý, trưởng phòng có thể hủy đề xuất.