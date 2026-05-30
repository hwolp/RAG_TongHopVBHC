# Báo Cáo Phần Frontend - Hệ Thống RAG Tổng Hợp Văn Bản Hành Chính

## 1. Vai trò của Frontend trong hệ thống

Frontend là phần giao diện người dùng của hệ thống, được xây dựng để người dùng có thể:

- Đăng nhập và sử dụng hệ thống theo vai trò.
- Quản lý tài liệu cá nhân, tài liệu phòng ban và tài liệu dùng chung.
- Upload tài liệu và theo dõi trạng thái index.
- Chat hỏi đáp với AI dựa trên tài liệu đã nạp.
- Đính kèm tài liệu vào phiên chat để AI ưu tiên tra cứu.
- Quản trị tài khoản, phòng ban, tài liệu, tag, SQP và vector database.

Phần frontend không trực tiếp xử lý OCR, embedding, vector search hay sinh câu trả lời AI. Các tác vụ đó do backend đảm nhiệm. Frontend chịu trách nhiệm hiển thị, điều hướng, gửi request, nhận kết quả, theo dõi job nền và phản hồi trạng thái cho người dùng.

## 2. Công nghệ sử dụng

Frontend nằm trong thư mục `frontend/`.

Các công nghệ chính:

- React 19: xây dựng giao diện theo component.
- TypeScript: định nghĩa type cho dữ liệu, giảm lỗi khi gọi API.
- Vite: chạy dev server và build frontend.
- React Router DOM: điều hướng giữa các trang.
- Axios: gọi API backend.
- Tailwind CSS: styling nhanh bằng utility class.
- Lucide React: bộ icon dùng trong sidebar, button, trạng thái file, chat.
- JWT Decode: đọc token để xác định user, role và hạn token.

Các script chính trong `frontend/package.json`:

```bash
npm run dev
npm run build
npm run lint
npm run preview
```

## 3. Cấu trúc Frontend

Các file chính:

- `src/main.tsx`: render React app vào DOM.
- `src/App.tsx`: khai báo route, layout và phân quyền route.
- `src/api.ts`: cấu hình Axios, tự động gắn JWT token và xử lý lỗi 401.
- `src/hooks/useAuth.ts`: quản lý đăng nhập, đăng xuất, decode JWT.
- `src/components/Sidebar.tsx`: thanh menu chính theo vai trò.
- `src/components/FolderTree.tsx`: component cây thư mục tài liệu dùng lại ở nhiều màn hình.
- `src/pages/*`: các màn hình chính của hệ thống.
- `src/index.css`: style toàn cục, Tailwind và bộ class giao diện neumorphism.

## 4. Điều hướng và phân quyền

Route được khai báo tại `src/App.tsx`.

Các route chính:

| Route | Màn hình | Quyền truy cập |
|---|---|---|
| `/login` | Đăng nhập | Công khai |
| `/` | Dashboard | Đã đăng nhập |
| `/chat` | Hỏi đáp RAG | Đã đăng nhập |
| `/library` | Kho cá nhân | Đã đăng nhập |
| `/sqp` | Kho quy định SQP | Đã đăng nhập |
| `/manager/docs` | Kho phòng ban | Admin, Manager |
| `/admin/users` | Quản lý tài khoản | Admin |
| `/admin/documents` | Quản lý tài liệu và chia sẻ | Admin |
| `/admin/system` | Bảo trì hệ thống | Admin |

Cách phân quyền:

- FE đọc JWT trong `localStorage`.
- `useAuth` decode token để lấy `id`, `sub`, `role`, `exp`.
- `ProtectedRoute` kiểm tra:
  - Nếu chưa đăng nhập thì chuyển về `/login`.
  - Nếu route yêu cầu role mà user không có quyền thì chuyển về `/`.
  - Nếu token hết hạn thì token bị xóa.

## 5. Xác thực và gọi API

File `src/api.ts` tạo một Axios instance dùng chung.

Các điểm đã làm được:

- Base URL mặc định là `http://localhost:8000`.
- Có thể đổi bằng biến môi trường `VITE_API_BASE_URL`.
- Mọi request tự động gắn header:

```http
Authorization: Bearer <token>
```

- Nếu backend trả `401`, frontend tự xóa token và chuyển về trang login.
- Có hàm `waitForJob(jobId, timeoutSeconds)` để chờ các tác vụ nền như index tài liệu hoặc sinh câu trả lời AI.

## 6. Giao diện tổng thể

Frontend dùng layout 2 phần:

- Sidebar cố định bên trái.
- Nội dung chính bên phải.

Sidebar thay đổi theo vai trò:

- Người dùng thường: Dashboard, Hỏi Đáp RAG, Kho Cá Nhân, Quy Định SQP.
- Manager: thêm Thư Mục Chung.
- Admin: thêm Tài Khoản, Tài liệu & Chia sẻ, Bảo Trì Hệ Thống.

Về UI:

- Có phong cách neumorphism: panel nổi, input lõm, button có bóng đổ.
- Màu chính là xanh teal `#006666`.
- Icon dùng từ `lucide-react`.
- Các trạng thái như `Đã index`, `Chờ index`, `Đang index`, `Index lỗi` được hiển thị bằng badge.

## 7. Các chức năng đã làm được theo màn hình

### 7.1. Trang đăng nhập

File: `src/pages/Login.tsx`

Chức năng:

- Nhập username và password.
- Gửi request tới `/auth/login`.
- Nhận `access_token`.
- Lưu token vào `localStorage`.
- Decode token để cập nhật trạng thái đăng nhập.
- Chuyển về Dashboard sau khi đăng nhập thành công.
- Hiển thị lỗi nếu đăng nhập thất bại.

Câu trả lời khi thầy hỏi:

> Trang login không chỉ là form nhập liệu, mà còn là điểm khởi tạo phiên làm việc. Sau khi backend trả JWT, frontend lưu token, decode role để phân quyền route và tự động gắn token vào các request sau.

### 7.2. Dashboard

File: `src/pages/Dashboard.tsx`

Chức năng:

- Hiển thị lời chào theo username.
- Hiển thị role hiện tại.
- Thống kê số tài liệu cá nhân.
- Thống kê số phiên hội thoại.
- Nếu là admin, hiển thị thêm:
  - Tổng số người dùng.
  - Tổng số vector trong vector DB.
- Có phần hướng dẫn nhanh: tải tài liệu, hỏi AI, tra cứu SQP.

API dùng:

- `GET /employee/documents`
- `GET /employee/sessions`
- `GET /admin/users`
- `GET /admin/vector/status`

### 7.3. Kho tài liệu cá nhân

File: `src/pages/Library.tsx`

Chức năng:

- Xem danh sách tài liệu cá nhân.
- Tìm kiếm tài liệu theo tên.
- Upload file tài liệu.
- Theo dõi trạng thái index sau khi upload.
- Tải file xuống.
- Xóa tài liệu cá nhân.
- Chuyển giữa hai chế độ xem:
  - Grid view.
  - Tree view.
- Tree view hiển thị tài liệu cá nhân, phòng ban và SQP qua component `FolderTree`.

API dùng:

- `GET /employee/documents`
- `POST /employee/documents/upload`
- `DELETE /employee/documents/{id}`
- `GET /documents/tree`
- `GET /jobs/{jobId}/wait`

Điểm cần nói rõ:

> Upload file trên frontend gửi `FormData` lên backend. Nếu backend trả `job_id`, frontend gọi `waitForJob` để chờ job index và cập nhật lại trạng thái tài liệu.

### 7.4. Hỏi đáp RAG

File: `src/pages/Chat.tsx`

Đây là màn hình quan trọng nhất của frontend.

Chức năng chính:

- Tạo phiên hội thoại mới.
- Load danh sách phiên hội thoại.
- Xem tin nhắn trong một phiên.
- Tải thêm tin nhắn cũ khi scroll lên.
- Gửi câu hỏi tới backend.
- Hiển thị tin nhắn user và AI.
- Chờ job AI trả lời bằng `waitForJob`.
- Hiển thị nguồn tài liệu của câu trả lời.
- Đổi tên phiên hội thoại.
- Xóa phiên hội thoại.
- Upload file trực tiếp vào session.
- Hiển thị file đã upload trong session.
- Chọn tài liệu từ thư viện để đính kèm vào session.
- Gỡ tài liệu đã đính kèm.
- Theo dõi trạng thái index của file trong session.

Luồng gửi câu hỏi:

1. Người dùng nhập câu hỏi.
2. Frontend thêm tạm tin nhắn user vào UI.
3. Gửi request `POST /employee/chat`.
4. Backend trả `job_id`, `session_id`, `user_message_id`, `ai_message_id`.
5. Frontend thêm tin nhắn AI dạng đang xử lý.
6. Frontend gọi `waitForJob(job_id)`.
7. Khi job success, frontend cập nhật nội dung AI bằng answer thật.
8. Nếu job failed hoặc timeout, frontend hiển thị lỗi/trạng thái chờ.

API dùng:

- `GET /employee/sessions`
- `POST /employee/sessions`
- `PUT /employee/sessions/{id}`
- `DELETE /employee/sessions/{id}`
- `GET /employee/sessions/{sessionId}/messages`
- `POST /employee/chat`
- `POST /employee/sessions/{sessionId}/documents/upload`
- `GET /chat/sessions/{sessionId}/attachments`
- `GET /chat/sessions/{sessionId}/documents`
- `GET /chat/documents/tree`
- `POST /chat/sessions/{sessionId}/attach`
- `DELETE /chat/sessions/{sessionId}/attach/{docId}`
- `DELETE /chat/sessions/{sessionId}/documents/{docId}`
- `GET /jobs/{jobId}/wait`

Câu trả lời khi thầy hỏi:

> Frontend không chờ AI bằng cách treo request chat trực tiếp. FE nhận job nền từ backend, hiển thị trạng thái đang xử lý, sau đó gọi endpoint wait job để lấy kết quả. Cách này giúp UI không bị đứng khi AI/OCR/index xử lý lâu.

### 7.5. Cây thư mục tài liệu

File: `src/components/FolderTree.tsx`

Đây là component dùng lại ở nhiều màn hình.

Chức năng:

- Hiển thị tài liệu theo nhóm:
  - Tài liệu cá nhân.
  - Tài liệu phòng ban.
  - Tài liệu công ty/SQP.
- Có thể đóng/mở từng section.
- Hiển thị icon theo loại file.
- Hiển thị badge trạng thái index.
- Hỗ trợ chọn tài liệu, tải xuống, xóa, đính kèm vào chat.
- Có thể ẩn từng nhóm tài liệu bằng prop:
  - `hidePersonal`
  - `hideDepartment`
  - `hideCompany`

Điểm kỹ thuật:

> `FolderTree` được thiết kế reusable bằng props. Cùng một component nhưng có thể dùng ở thư viện cá nhân, chat picker, màn hình manager và tree view.

### 7.6. Kho quy định SQP

File: `src/pages/SQPBrowser.tsx`

Chức năng:

- Người dùng xem và tìm kiếm tài liệu SQP đã được duyệt.
- Tải tài liệu SQP xuống.
- Hiển thị trạng thái index.
- Nếu là admin:
  - Upload tài liệu SQP.
  - Đổi tên tài liệu SQP.
  - Xóa tài liệu SQP.
  - Theo dõi job index sau khi upload.

API dùng:

- `GET /documents/sqp`
- `POST /documents/sqp`
- `PUT /documents/sqp/{id}`
- `DELETE /documents/sqp/{id}`
- `GET /documents/{id}/download`
- `GET /jobs/{jobId}/wait`

### 7.7. Kho tài liệu phòng ban

File: `src/pages/ManagerDocs.tsx`

Màn hình dành cho manager và admin.

Chức năng:

- Xem tài liệu phòng ban.
- Upload tài liệu phòng ban.
- Tìm kiếm tài liệu phòng ban.
- Xóa tài liệu phòng ban.
- Index tài liệu vào RAG.
- Theo dõi trạng thái index.
- Đề xuất tài liệu lên kho SQP.
- Hủy đề xuất SQP khi còn pending.
- Xem danh sách đề xuất của mình.
- Chia sẻ tài liệu sang phòng ban khác.
- Chia sẻ tài liệu tới một user cụ thể.
- Hủy chia sẻ đã tạo.
- Chuyển giữa table view và tree view.

API dùng:

- `GET /manager/department/documents`
- `POST /manager/department/documents/upload`
- `DELETE /manager/department/documents/{id}`
- `POST /manager/department/documents/{id}/index`
- `GET /manager/sqp/proposals`
- `POST /manager/sqp/propose/{docId}`
- `DELETE /manager/sqp/proposals/{id}`
- `GET /manager/departments`
- `GET /manager/shares`
- `POST /manager/share/document/{docId}/to-dept/{deptId}`
- `POST /manager/share/document/{docId}/to-user/{username}`
- `DELETE /manager/share/{shareId}`
- `GET /documents/tree`

### 7.8. Quản lý tài khoản và phòng ban

File: `src/pages/AdminUsers.tsx`

Màn hình chỉ dành cho admin.

Chức năng:

- Xem danh sách tài khoản.
- Tìm kiếm tài khoản theo username/họ tên.
- Lọc theo vai trò: tất cả, admin, trưởng phòng, nhân viên.
- Thống kê:
  - Tổng tài khoản.
  - Tài khoản hoạt động.
  - Tài khoản bị khóa.
  - Số phòng ban.
- Thêm tài khoản.
- Sửa thông tin tài khoản.
- Đổi role.
- Gán phòng ban.
- Đổi mật khẩu.
- Khóa/mở khóa tài khoản.
- Xóa tài khoản.
- Thêm, sửa, xóa phòng ban.

API dùng:

- `GET /admin/users`
- `POST /admin/users`
- `PUT /admin/users/{id}`
- `POST /admin/users/{id}/lock`
- `DELETE /admin/users/{id}`
- `GET /admin/departments`
- `POST /admin/departments`
- `PUT /admin/departments/{id}`
- `DELETE /admin/departments/{id}`

### 7.9. Quản lý tài liệu và chia sẻ của admin

File: `src/pages/AdminDocuments.tsx`

Chức năng:

- Xem danh sách tài liệu phòng ban toàn hệ thống.
- Upload tài liệu vào phòng ban bất kỳ.
- Chọn phòng ban khi upload.
- Sửa tên file.
- Chuyển tài liệu sang phòng ban khác.
- Xóa tài liệu phòng ban.
- Xem danh sách lượt chia sẻ liên phòng.
- Tìm kiếm tài liệu/chia sẻ.
- Hiển thị trạng thái index.
- Theo dõi job index sau upload.

API dùng:

- `GET /admin/departments`
- `GET /admin/documents/department`
- `POST /admin/documents/department/upload`
- `PUT /admin/documents/department/{id}`
- `DELETE /admin/documents/department/{id}`
- `GET /admin/shares`
- `GET /jobs/{jobId}/wait`

### 7.10. Bảo trì hệ thống

File: `src/pages/AdminSystem.tsx`

Chức năng:

- Xem tổng số vector trong Vector DB.
- Re-index tài liệu chưa index.
- Xóa collection/vector và dữ liệu liên quan.
- Quản lý tag:
  - Thêm tag.
  - Xóa tag.
- Xem danh sách đề xuất SQP.
- Duyệt đề xuất SQP.
- Từ chối đề xuất SQP.
- Theo dõi job re-index sau khi duyệt SQP.

API dùng:

- `GET /admin/vector/status`
- `POST /admin/vector/reindex`
- `POST /admin/vector/clear`
- `GET /admin/tags`
- `POST /admin/tags`
- `DELETE /admin/tags/{id}`
- `GET /admin/sqp/proposals`
- `POST /admin/sqp/approve/{id}`
- `POST /admin/sqp/reject/{id}`
- `GET /jobs/{jobId}/wait`

## 8. Luồng dữ liệu tổng quát

Luồng đăng nhập:

```text
User nhập tài khoản
-> FE gọi /auth/login
-> Backend trả JWT
-> FE lưu token
-> FE decode role
-> FE điều hướng theo quyền
```

Luồng upload và index:

```text
User chọn file
-> FE gửi FormData
-> Backend lưu file và tạo job index
-> FE nhận job_id
-> FE gọi /jobs/{id}/wait
-> FE cập nhật trạng thái Đã index / Index lỗi
```

Luồng chat RAG:

```text
User gửi câu hỏi
-> FE tạo tin nhắn tạm
-> FE gọi /employee/chat
-> Backend tạo job AI
-> FE hiển thị AI đang xử lý
-> FE chờ job
-> FE cập nhật câu trả lời và nguồn tài liệu
```

Luồng đính kèm tài liệu vào chat:

```text
User mở cây thư viện
-> Chọn tài liệu cần đính kèm
-> FE gọi /chat/sessions/{id}/attach
-> Backend gắn tài liệu vào session
-> FE hiển thị chip tài liệu đã đính kèm
-> Khi hỏi AI, backend ưu tiên tài liệu trong session
```

## 9. Luồng hoạt động chi tiết của các chức năng

### 9.1. Luồng khởi động ứng dụng

```text
Người dùng mở website
-> React render App
-> App kiểm tra route hiện tại
-> ProtectedRoute gọi useAuth
-> useAuth đọc token trong localStorage
-> Nếu token hợp lệ: decode user/role và cho vào màn hình
-> Nếu token không có hoặc hết hạn: chuyển về /login
```

Ý nghĩa:

- FE không cần gọi backend mỗi lần reload chỉ để biết role.
- Role được lấy từ JWT nên route và sidebar có thể render ngay sau khi decode token.

### 9.2. Luồng đăng nhập

```text
User nhập username/password
-> Bấm Đăng nhập
-> Login.tsx gọi POST /auth/login
-> Backend kiểm tra tài khoản
-> Backend trả access_token
-> FE lưu token vào localStorage
-> FE decode token để lấy id, username, role, exp
-> FE chuyển về Dashboard
-> Sidebar render menu theo role
```

Nếu đăng nhập lỗi:

```text
Backend trả lỗi
-> FE bắt error
-> Hiển thị thông báo "Đăng nhập thất bại..."
-> User vẫn ở trang login
```

### 9.3. Luồng bảo vệ route và menu theo vai trò

```text
User truy cập một route
-> ProtectedRoute kiểm tra user
-> Nếu chưa đăng nhập: Navigate /login
-> Nếu đã đăng nhập nhưng sai role: Navigate /
-> Nếu đúng quyền: render Layout + Page
```

Ví dụ:

- User thường không vào được `/admin/users`.
- Manager vào được `/manager/docs`.
- Admin vào được toàn bộ màn hình quản trị.

Sidebar cũng dùng role để ẩn/hiện menu:

```text
employee -> Dashboard, Chat, Library, SQP
manager -> thêm Thư Mục Chung
admin -> thêm Tài Khoản, Tài liệu & Chia sẻ, Bảo Trì Hệ Thống
```

### 9.4. Luồng Dashboard

```text
User vào /
-> Dashboard đọc user từ useAuth
-> FE gọi song song:
   GET /employee/documents
   GET /employee/sessions
-> Nếu role là admin, gọi thêm:
   GET /admin/users
   GET /admin/vector/status
-> FE tổng hợp số liệu
-> Render các card thống kê
```

Dashboard không xử lý nghiệp vụ phức tạp, chủ yếu là màn hình tổng quan để user biết hệ thống hiện có bao nhiêu tài liệu, phiên chat, người dùng và vector.

### 9.5. Luồng xem và tìm kiếm tài liệu cá nhân

```text
User vào /library
-> Library gọi GET /employee/documents
-> Backend trả danh sách tài liệu
-> FE lưu vào state docs
-> FE render grid card tài liệu
```

Khi tìm kiếm:

```text
User nhập từ khóa
-> Bấm Tìm hoặc nhấn Enter
-> FE gọi GET /employee/documents?search=<keyword>
-> Backend trả danh sách đã lọc
-> FE render lại danh sách
```

Khi chuyển sang tree view:

```text
User bấm icon tree/list
-> FE gọi GET /documents/tree
-> Backend trả cây tài liệu theo personal/department/company
-> FE truyền data vào FolderTree
-> FolderTree render từng nhóm tài liệu
```

### 9.6. Luồng upload tài liệu cá nhân và chờ index

```text
User chọn file ở Library
-> FE tạo FormData
-> FE gọi POST /employee/documents/upload
-> Backend lưu file và tạo document record
-> Backend tạo job index nếu cần
-> Backend trả thông tin file và job_id
-> FE reload danh sách tài liệu
-> Nếu có job_id, FE gọi waitForJob(job_id)
-> Job success: FE báo "Index tài liệu hoàn tất" và reload docs
-> Job failed: FE báo "Index thất bại"
```

Trạng thái trên UI:

- `Chờ index`: backend đã nhận job nhưng chưa chạy.
- `Đang index`: worker đang xử lý.
- `Đã index`: tài liệu đã có vector, có thể dùng cho RAG.
- `Index lỗi`: xử lý tài liệu thất bại.

### 9.7. Luồng tải xuống tài liệu

```text
User bấm Tải xuống
-> FE mở URL download bằng window.open
-> Browser gửi request download tới backend
-> Backend kiểm tra quyền
-> Backend trả file
```

Ví dụ endpoint đang dùng:

```text
/employee/documents/{id}/download
/documents/{id}/download
```

### 9.8. Luồng xóa tài liệu cá nhân

```text
User bấm Xóa
-> FE hiện confirm
-> User xác nhận
-> FE gọi DELETE /employee/documents/{id}
-> Backend xóa hoặc đánh dấu xóa tài liệu
-> FE reload danh sách docs
```

FE dùng confirm để tránh người dùng xóa nhầm tài liệu.

### 9.9. Luồng tạo phiên chat mới

```text
User bấm "Phiên hội thoại mới"
-> FE gọi POST /employee/sessions
-> Backend tạo chat session
-> Backend trả session mới
-> FE set activeSession
-> FE xóa messages hiện tại
-> FE xóa attachedDocs/sessionDocs hiện tại
-> UI chuyển sang phiên mới
```

### 9.10. Luồng load phiên chat

```text
User chọn một session ở sidebar Chat
-> FE set activeSession
-> FE gọi GET /employee/sessions/{sessionId}/messages?limit=5
-> FE gọi GET /chat/sessions/{sessionId}/attachments
-> FE gọi GET /chat/sessions/{sessionId}/documents
-> FE render tin nhắn, file đính kèm và file trong session
-> FE scroll xuống cuối hội thoại
```

Nếu tin nhắn AI có job chưa xong:

```text
FE phát hiện message có job_id và job_status chưa success/failed
-> FE gọi waitChatJob(job_id)
-> Khi job xong thì cập nhật message AI
```

### 9.11. Luồng tải thêm tin nhắn cũ

```text
User scroll lên gần đầu khung chat
-> handleMessagesScroll được gọi
-> Nếu còn hasMoreMessages
-> FE gọi GET /employee/sessions/{id}/messages?before_id=<nextBeforeId>&limit=5
-> FE nối tin nhắn cũ vào đầu danh sách
-> FE giữ vị trí scroll để màn hình không bị nhảy
```

Điểm này giúp chat dài vẫn dùng được mà không phải load toàn bộ lịch sử ngay từ đầu.

### 9.12. Luồng gửi câu hỏi RAG

```text
User nhập câu hỏi
-> Bấm gửi hoặc Enter
-> FE tạo tin nhắn user tạm bằng Date.now()
-> FE gọi POST /employee/chat với question và session_id
-> Backend tạo user_message thật, ai_message placeholder và job AI
-> Backend trả:
   session_id
   user_message_id
   ai_message_id
   job_id
-> FE thay id tạm bằng user_message_id thật
-> FE thêm message AI "đang xử lý"
-> FE gọi waitChatJob(job_id)
```

Khi job AI thành công:

```text
Backend trả answer + sources
-> FE tìm message có ai_message_id
-> FE thay content placeholder bằng answer
-> FE lưu sources vào message
-> FE reload session docs/sessions nếu cần
-> FE scroll xuống cuối
```

Khi job AI lỗi:

```text
waitForJob trả failed hoặc request lỗi
-> FE cập nhật message AI thành thông báo lỗi
-> Người dùng biết lỗi nằm ở xử lý AI/job/backend
```

### 9.13. Luồng hiển thị nguồn câu trả lời AI

```text
Backend trả sources dạng danh sách doc_id
-> FE lưu vào message.sources dạng JSON string
-> FE tạo map sourceNameById từ attachedDocs và sessionDocs
-> Khi render AI message:
   parse sources
   đổi doc_id thành filename nếu biết
   hiển thị dòng "Nguồn: ..."
```

Nếu FE chưa biết tên file của source thì hiển thị nhãn mặc định `Tài liệu`.

### 9.14. Luồng upload file vào session chat

```text
User đang ở một activeSession
-> Bấm Upload file trong Chat
-> Chọn file
-> FE tạo FormData
-> FE gọi POST /employee/sessions/{sessionId}/documents/upload
-> Backend lưu file vào session
-> Backend tạo job index nếu cần
-> FE thêm message thông báo đã upload
-> FE reload sessionDocs
-> Nếu có job_id, FE waitIndexJob(job_id)
-> Khi job xong, FE reload sessionDocs và attachments
```

Ý nghĩa:

- File upload trong session chỉ phục vụ trực tiếp cho phiên chat đó.
- Người dùng có thể hỏi ngay sau khi file index xong.

### 9.15. Luồng chọn tài liệu từ thư viện để đính kèm vào chat

```text
User bấm "Chọn từ thư viện"
-> FE gọi GET /chat/documents/tree
-> Backend trả cây tài liệu user có quyền truy cập
-> FE render FolderTree ở panel bên phải
-> User bấm icon đính kèm trên một tài liệu
-> FE gọi POST /chat/sessions/{sessionId}/attach với doc_id
-> Backend tạo liên kết session-document
-> FE reload attachments
-> FE thêm message thông báo đã đính kèm
-> Nếu backend trả index_job_id, FE chờ index job
```

Khi tài liệu đã đính kèm:

```text
FE hiển thị chip ở đầu khung chat
-> Chip có filename, trạng thái index và nút gỡ
```

### 9.16. Luồng gỡ tài liệu khỏi chat

```text
User bấm nút X trên chip tài liệu đính kèm
-> FE gọi DELETE /chat/sessions/{sessionId}/attach/{docId}
-> Backend xóa liên kết attachment
-> FE reload attachedDocs
-> Chip biến mất khỏi UI
```

### 9.17. Luồng đổi tên phiên chat

```text
User bấm icon sửa ở session
-> FE chuyển session title thành input
-> User nhập tên mới
-> Enter hoặc bấm check
-> FE gọi PUT /employee/sessions/{id}
-> Backend cập nhật title
-> FE reload danh sách sessions
```

### 9.18. Luồng xóa phiên chat

```text
User bấm icon xóa session
-> FE hiện confirm
-> User xác nhận
-> FE gọi DELETE /employee/sessions/{id}
-> Backend xóa session
-> Nếu đang mở session đó:
   FE clear activeSession, messages, attachedDocs, sessionDocs
-> FE reload danh sách sessions
```

### 9.19. Luồng kho SQP cho người dùng thường

```text
User vào /sqp
-> FE gọi GET /documents/sqp
-> Backend trả danh sách tài liệu SQP
-> FE render bảng tài liệu
-> User có thể tìm kiếm hoặc tải về
```

Tìm kiếm SQP:

```text
User nhập keyword
-> FE gọi GET /documents/sqp?search=<keyword>
-> FE render danh sách kết quả
```

### 9.20. Luồng quản lý SQP cho admin

```text
Admin vào /sqp
-> FE nhận role admin từ JWT
-> FE hiển thị thêm khu vực upload và nút sửa/xóa
-> Admin chọn file SQP
-> FE gọi POST /documents/sqp
-> Backend lưu tài liệu SQP và tạo job index
-> FE chờ job bằng waitForJob
-> FE reload danh sách SQP
```

Sửa tên SQP:

```text
Admin bấm Sửa
-> FE mở modal
-> Admin nhập tên mới
-> FE gọi PUT /documents/sqp/{id}
-> FE đóng modal và reload docs
```

Xóa SQP:

```text
Admin bấm Xóa
-> FE confirm
-> FE gọi DELETE /documents/sqp/{id}
-> FE reload docs
```

### 9.21. Luồng tài liệu phòng ban của manager

```text
Manager vào /manager/docs
-> FE gọi:
   GET /manager/department/documents
   GET /manager/sqp/proposals
   GET /manager/departments
   GET /manager/shares
-> FE render tài liệu phòng ban, đề xuất, phòng ban và chia sẻ
```

Upload tài liệu phòng ban:

```text
Manager chọn file
-> FE gọi POST /manager/department/documents/upload
-> Backend lưu tài liệu vào phòng ban của manager
-> Backend có thể tạo job index
-> FE chờ job và reload docs
```

Index tài liệu phòng ban:

```text
Manager bấm Index RAG
-> FE gọi POST /manager/department/documents/{docId}/index
-> Backend tạo job index
-> FE chờ job và cập nhật trạng thái
```

Đề xuất lên SQP:

```text
Manager bấm Đề xuất SQP
-> FE gọi POST /manager/sqp/propose/{docId}
-> Backend tạo proposal pending
-> FE reload proposals
-> UI hiển thị "Đã đề xuất"
```

Hủy đề xuất:

```text
Manager bấm Hủy ở proposal pending
-> FE gọi DELETE /manager/sqp/proposals/{id}
-> FE reload proposals
```

### 9.22. Luồng chia sẻ tài liệu liên phòng

```text
Manager chọn tài liệu
-> Chọn mode chia sẻ:
   phòng ban hoặc user
-> Nếu chia sẻ phòng ban: chọn department
-> Nếu chia sẻ user: nhập username
-> Bấm Gửi chia sẻ
```

Nếu chia sẻ phòng ban:

```text
FE gọi POST /manager/share/document/{docId}/to-dept/{deptId}
-> Backend tạo share record
-> FE reload shares
-> UI hiển thị lượt chia sẻ mới
```

Nếu chia sẻ user:

```text
FE gọi POST /manager/share/document/{docId}/to-user/{username}
-> Backend tạo share record cho user
-> FE reload shares
```

Hủy chia sẻ:

```text
Manager bấm Hủy
-> FE gọi DELETE /manager/share/{shareId}
-> Backend xóa share record
-> FE reload shares
```

### 9.23. Luồng quản lý tài khoản admin

```text
Admin vào /admin/users
-> FE gọi song song:
   GET /admin/users
   GET /admin/departments
-> FE render thống kê, danh sách user và danh sách phòng ban
```

Thêm tài khoản:

```text
Admin bấm Thêm tài khoản
-> FE mở modal
-> Admin nhập username, họ tên, role, phòng ban, mật khẩu
-> FE gọi POST /admin/users
-> Backend tạo user
-> FE đóng modal và reload users
```

Sửa tài khoản:

```text
Admin bấm Sửa
-> FE mở modal với dữ liệu user
-> Admin đổi họ tên, role, phòng ban hoặc mật khẩu
-> FE gọi PUT /admin/users/{id}
-> FE reload users
```

Khóa/mở khóa:

```text
Admin bấm icon khóa
-> FE gọi POST /admin/users/{id}/lock
-> Backend đảo trạng thái is_locked
-> FE reload users
```

Xóa tài khoản:

```text
Admin bấm Xóa
-> FE confirm
-> FE gọi DELETE /admin/users/{id}
-> FE reload users
```

### 9.24. Luồng quản lý phòng ban admin

```text
Admin nhập tên phòng ban
-> Bấm Thêm phòng ban
-> FE gọi POST /admin/departments
-> Backend tạo phòng ban
-> FE reload departments
```

Sửa phòng ban:

```text
Admin bấm sửa ở phòng ban
-> FE đưa tên phòng ban lên input
-> Admin chỉnh tên
-> FE gọi PUT /admin/departments/{id}
-> FE reload departments
```

Xóa phòng ban:

```text
Admin bấm xóa
-> FE confirm
-> FE gọi DELETE /admin/departments/{id}
-> FE reload departments
```

### 9.25. Luồng admin quản lý tài liệu phòng ban

```text
Admin vào /admin/documents
-> FE gọi:
   GET /admin/departments
   GET /admin/documents/department
   GET /admin/shares
-> FE render thống kê, upload form, bảng tài liệu và bảng chia sẻ
```

Upload tài liệu vào phòng ban:

```text
Admin chọn phòng ban
-> Chọn file
-> Bấm Tải lên
-> FE gọi POST /admin/documents/department/upload?department_id=<id>
-> Backend lưu file vào phòng ban được chọn
-> Backend tạo job index
-> FE chờ job và reload dữ liệu
```

Sửa tài liệu:

```text
Admin bấm Sửa
-> FE mở modal
-> Admin đổi filename hoặc department_id
-> FE gọi PUT /admin/documents/department/{docId}
-> FE reload dữ liệu
```

Xóa tài liệu:

```text
Admin bấm Xóa
-> FE confirm
-> FE gọi DELETE /admin/documents/department/{docId}
-> FE reload dữ liệu
```

### 9.26. Luồng bảo trì Vector DB

```text
Admin vào /admin/system
-> FE gọi GET /admin/vector/status
-> Backend trả total_vectors
-> FE hiển thị số vector hiện có
```

Re-index:

```text
Admin bấm Re-index
-> FE gọi POST /admin/vector/reindex
-> Backend quét lại tài liệu chưa index
-> FE gọi lại GET /admin/vector/status
-> UI cập nhật số vector
```

Xóa collection:

```text
Admin bấm Xóa Collection
-> FE hiện confirm cảnh báo mạnh
-> Admin xác nhận
-> FE gọi POST /admin/vector/clear
-> Backend xóa vector, tài liệu upload, hội thoại, job liên quan
-> FE reload vector status và proposals
```

### 9.27. Luồng quản lý tag

```text
Admin vào /admin/system
-> FE gọi GET /admin/tags
-> FE render danh sách tag
```

Thêm tag:

```text
Admin nhập tên tag
-> Bấm Thêm
-> FE gọi POST /admin/tags?name=<tag>
-> FE clear input và reload tags
```

Xóa tag:

```text
Admin bấm icon xóa tag
-> FE gọi DELETE /admin/tags/{id}
-> FE reload tags
```

### 9.28. Luồng duyệt đề xuất SQP

```text
Admin vào /admin/system
-> FE gọi GET /admin/sqp/proposals
-> FE render danh sách proposal
```

Duyệt đề xuất:

```text
Admin bấm Duyệt
-> FE gọi POST /admin/sqp/approve/{proposalId}
-> Backend chuyển tài liệu thành SQP approved
-> Backend có thể tạo job re-index
-> FE reload proposals
-> Nếu có job_id, FE waitForJob
-> FE cập nhật vector status
```

Từ chối đề xuất:

```text
Admin bấm Từ chối
-> FE gọi POST /admin/sqp/reject/{proposalId}
-> FE reload proposals
```

### 9.29. Luồng xử lý lỗi chung

Lỗi token:

```text
Backend trả 401
-> Axios interceptor bắt lỗi
-> FE xóa token
-> FE chuyển về /login
```

Lỗi API thông thường:

```text
Request failed
-> FE lấy err.response.data.detail nếu có
-> Hiển thị alert, error banner hoặc message trong chat
```

Lỗi job:

```text
waitForJob trả failed
-> FE lấy job.error
-> Hiển thị thông báo job thất bại
-> FE reload dữ liệu nếu cần
```

### 9.30. Luồng hoạt động theo vai trò người dùng

Employee:

```text
Đăng nhập
-> Xem Dashboard
-> Upload tài liệu cá nhân
-> Chờ index
-> Tạo session chat
-> Upload file vào session hoặc attach từ thư viện
-> Hỏi AI
-> Xem câu trả lời và nguồn
-> Tra cứu SQP
```

Manager:

```text
Đăng nhập
-> Có toàn bộ chức năng employee
-> Vào Kho Tài Liệu Phòng Ban
-> Upload/index tài liệu phòng ban
-> Chia sẻ tài liệu liên phòng/user
-> Đề xuất tài liệu lên SQP
-> Theo dõi trạng thái proposal
```

Admin:

```text
Đăng nhập
-> Có quyền quản trị
-> Quản lý user/phòng ban
-> Quản lý tài liệu phòng ban và chia sẻ
-> Quản lý SQP
-> Duyệt/từ chối proposal SQP
-> Quản lý tag
-> Theo dõi/re-index/xóa Vector DB
```

## 10. Điểm mạnh của phần Frontend

- Có phân quyền rõ theo role: employee, manager, admin.
- Có layout thống nhất, sidebar điều hướng dễ hiểu.
- Có component tái sử dụng `FolderTree`.
- Có xử lý job nền cho tác vụ lâu như index và AI answer.
- Có hiển thị trạng thái rõ ràng cho tài liệu: chờ index, đang index, đã index, lỗi.
- Có hỗ trợ quản lý tài liệu theo nhiều phạm vi: cá nhân, phòng ban, SQP.
- Có trải nghiệm chat đầy đủ: session, lịch sử, tải thêm tin nhắn, rename, delete, upload file vào session, attach file từ thư viện.
- Có xử lý token hết hạn ở tầng Axios interceptor.
- Có giao diện admin tương đối đầy đủ cho tài khoản, phòng ban, tài liệu, tag, SQP và vector DB.

## 11. Một số điểm có thể cải thiện

Những điểm này nên nói nếu thầy hỏi hướng phát triển tiếp:

- Trang `Login.tsx` đang gọi trực tiếp `http://localhost:8000/auth/login`, nên có thể đổi sang dùng Axios instance `api` để đồng bộ với `VITE_API_BASE_URL`.
- Một vài link download cũng đang hard-code `http://localhost:8000`; có thể gom lại theo biến môi trường.
- `Upload.tsx` là màn hình upload mô phỏng cũ và hiện chưa được khai báo route trong `App.tsx`; chức năng upload thật đang nằm ở `Library`, `Chat`, `ManagerDocs`, `AdminDocuments`, `SQPBrowser`.
- Một số request `catch {}` chưa hiển thị lỗi chi tiết; có thể chuẩn hóa toast/error banner.
- Có thể bổ sung loading skeleton hoặc progress bar chi tiết hơn cho chat và index.
- Có thể thêm test frontend bằng Vitest/React Testing Library.
- Có thể refactor các phần lặp lại như index badge, job wait message, download URL.

## 12. Câu hỏi thầy có thể hỏi và gợi ý trả lời

### FE của em làm những chức năng gì?

Frontend gồm các nhóm chức năng: đăng nhập/phân quyền, dashboard, quản lý tài liệu cá nhân, chat RAG, đính kèm tài liệu vào chat, quản lý tài liệu phòng ban, đề xuất/duyệt SQP, quản lý tài khoản/phòng ban và bảo trì vector DB.

### FE có xử lý AI không?

Không. FE không trực tiếp chạy AI. FE gửi câu hỏi và tài liệu lên backend, backend xử lý RAG, OCR, embedding, retrieval và LLM. FE chỉ hiển thị trạng thái và kết quả trả lời.

### Vì sao dùng job nền?

Vì OCR, index tài liệu và sinh câu trả lời AI có thể mất nhiều thời gian. Nếu FE chờ trực tiếp trong một request dài, UI dễ bị treo hoặc timeout. Vì vậy backend trả `job_id`, FE hiển thị trạng thái đang xử lý và gọi `/jobs/{id}/wait` để lấy kết quả.

### FE phân quyền như thế nào?

Sau khi đăng nhập, backend trả JWT. FE decode JWT để lấy role. `ProtectedRoute` trong `App.tsx` kiểm tra user có đăng nhập chưa và role có được phép vào route không. Sidebar cũng dựa vào role để chỉ hiện menu phù hợp.

### Tài liệu được đính kèm vào chat như thế nào?

Trong màn hình Chat, người dùng có thể upload file mới vào session hoặc chọn file từ thư viện. FE gọi API attach file vào session, sau đó hiển thị file dưới dạng chip. Khi user hỏi, backend sẽ dùng các file trong session để retrieval.

### Khi upload tài liệu thì FE làm gì?

FE tạo `FormData`, gửi file lên backend. Nếu backend trả `job_id`, FE gọi `waitForJob` để chờ index. Sau khi index xong, FE reload danh sách tài liệu và cập nhật badge trạng thái.

### Component nào được tái sử dụng nhiều?

`FolderTree` được tái sử dụng cho thư viện cá nhân, chọn tài liệu trong chat, màn hình manager và tree view. Component này nhận props để bật/tắt chức năng chọn, tải xuống, xóa, đính kèm và ẩn hiện từng nhóm tài liệu.

### Nếu backend trả lỗi 401 thì FE xử lý sao?

Axios interceptor trong `api.ts` bắt lỗi 401, xóa token khỏi `localStorage` và chuyển người dùng về trang `/login`.

### Em thiết kế UI theo hướng nào?

UI hướng tới hệ thống hành chính: bố cục rõ, có sidebar, bảng dữ liệu, badge trạng thái, form quản trị. Style dùng neumorphism nhẹ với màu chủ đạo xanh teal, tạo cảm giác hiện đại nhưng vẫn dễ thao tác.

### Điểm khó nhất ở FE là gì?

Khó nhất là đồng bộ trạng thái bất đồng bộ: upload file, chờ index, chờ AI trả lời, cập nhật session, cập nhật file đính kèm và hiển thị nguồn trả lời. FE phải xử lý nhiều trạng thái cùng lúc để người dùng không bị mất thông tin.

## 13. Tóm tắt ngắn để trình bày

Phần frontend của hệ thống được xây dựng bằng React, TypeScript, Vite và Tailwind CSS. FE đảm nhiệm toàn bộ trải nghiệm người dùng: đăng nhập, phân quyền theo role, quản lý tài liệu, chat RAG, đính kèm tài liệu vào phiên chat, theo dõi job index/AI và các màn hình quản trị. FE giao tiếp với backend qua Axios, tự động gắn JWT, xử lý token hết hạn và cập nhật UI theo trạng thái job nền. Các chức năng được chia theo vai trò employee, manager và admin, trong đó màn hình Chat và quản lý tài liệu là hai phần chính phục vụ bài toán hỏi đáp văn bản hành chính.
