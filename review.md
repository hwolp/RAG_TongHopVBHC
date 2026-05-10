# Review hệ thống RAG_TongHopVBHC

## 1. Tổng quan hệ thống

Đây là hệ thống **RAG cho văn bản hành chính nội bộ** với kiến trúc:

- **Frontend:** React + TypeScript + Vite
- **Backend API:** FastAPI
- **Database quan hệ:** MySQL (SQLAlchemy ORM)
- **Vector DB / Retrieval:** ChromaDB
- **LLM sinh câu trả lời:** Ollama
- **Storage file:** local filesystem theo scope tài liệu

Mục tiêu chính:

1. Quản lý tài liệu theo vai trò (admin/manager/employee).
2. Tra cứu và hỏi đáp AI trên dữ liệu văn bản nội bộ.
3. Quản trị vòng đời tài liệu và quy trình đề xuất SQP.

---

## 2. Kiến trúc và thành phần chính

## 2.1 Backend (FastAPI)

Điểm vào hệ thống: `backend/main.py`

- Khởi tạo app FastAPI.
- Nạp router: `auth`, `users`, `documents`, `chat`, `tags`, `manager`, `admin`.
- Khởi tạo schema ORM + đồng bộ schema bổ sung qua `schema_sync`.

### Modules chính

- **Xác thực:** `routers/auth.py`, `services/auth_service.py`, `middleware/auth_middleware.py`
- **Quản lý người dùng:** `routers/users.py`, `services/user_service.py`
- **Quản lý tài liệu:** `routers/documents.py`, `services/document_service.py`
- **Chat/RAG:** `routers/chat.py`, `services/chat_service.py`, `rag_engine/*`
- **Tag:** `routers/tags.py`, `services/tag_service.py`
- **Trưởng phòng:** `routers/manager.py`, `services/share_service.py`, `services/sqp_service.py`
- **Quản trị hệ thống:** `routers/admin.py`

## 2.2 Frontend (React + TS)

Điểm vào frontend: `frontend/src/App.tsx`

- Routing theo role với `ProtectedRoute`.
- Sidebar điều hướng theo vai trò.
- Các màn hình chính:
  - `Login`
  - `Dashboard`
  - `Library` (kho cá nhân)
  - `Chat`
  - `SQPBrowser`
  - `ManagerDocs`
  - `AdminUsers`
  - `AdminSystem`

## 2.3 RAG Engine

`backend/rag_engine/chroma_manager.py` + `ollama_ai.py`

- Hỗ trợ ingest **PDF/Word**.
- Tự nhận diện văn bản hành chính để chọn chiến lược chunking.
- Có hỗ trợ OCR (pytesseract) cho PDF scan.
- Truy vấn ngữ cảnh theo scope + metadata filter (owner, department, scope, session_id).
- Gọi Ollama để sinh câu trả lời từ context và lịch sử hội thoại gần nhất.

---

## 3. Luồng hoạt động nghiệp vụ

## 3.1 Luồng đăng nhập và phân quyền

1. User đăng nhập qua `POST /auth/login`.
2. Backend kiểm tra mật khẩu (bcrypt), trạng thái khóa tài khoản.
3. Backend trả về JWT chứa `sub`, `role`, `id`.
4. Frontend lưu token vào `localStorage`.
5. Các request sau đó tự gắn `Authorization: Bearer <token>`.
6. Middleware kiểm quyền qua `get_current_user`, `require_admin`, `require_manager`.

## 3.2 Luồng quản lý tài liệu cá nhân

1. User upload tài liệu qua `/employee/documents/upload` (legacy endpoint).
2. File được lưu vào thư mục personal.
3. Tạo record `documents` (scope=personal).
4. Nếu là PDF, backend cố gắng index vào Chroma ngay.
5. User có thể list/search, download, delete tài liệu cá nhân.

## 3.3 Luồng tài liệu phòng ban

1. Manager upload vào `/manager/department/documents/upload`.
2. Tài liệu lưu với scope=department + department_id của manager.
3. Thành viên phòng ban có thể xem danh sách.
4. Manager có thể xóa hoặc trigger index RAG cho tài liệu phòng ban.

## 3.4 Luồng đề xuất SQP

1. Manager gửi đề xuất tài liệu lên SQP: `/manager/sqp/propose/{document_id}`.
2. Hệ thống tạo `sqp_proposals` trạng thái `pending`.
3. Admin duyệt `/admin/sqp/approve/{proposal_id}` → document scope chuyển thành `sqp`.
4. Người dùng toàn hệ thống tra cứu qua endpoint SQP.

## 3.5 Luồng chat AI (RAG)

1. User chọn scope: personal / department / company.
2. Gửi câu hỏi đến `/employee/chat` (legacy mapping đến `/chat/ask`).
3. Nếu chưa có session thì tạo mới.
4. Backend lấy lịch sử chat gần (10 message gần nhất) làm context hội thoại.
5. Backend truy vấn Chroma theo scope + tài liệu đính kèm session.
6. Gọi Ollama để sinh câu trả lời.
7. Lưu 2 message vào DB: câu hỏi user + câu trả lời AI (kèm sources).
8. Frontend hiển thị answer và danh sách nguồn.

## 3.6 Luồng đính kèm tài liệu vào session chat

1. User mở cây thư mục tài liệu (`/chat/documents/tree`).
2. Chọn tài liệu và attach vào session (`/chat/sessions/{id}/attach`).
3. Khi hỏi AI, `doc_id` đính kèm được cộng thêm vào retrieval context.
4. User có thể detach khi không cần.

## 3.7 Luồng vận hành vector DB (Admin)

1. Xem trạng thái vector: `/admin/vector/status`.
2. Reindex: `/admin/vector/reindex`.
3. Clear toàn bộ collection: `/admin/vector/clear`.

---

## 4. Thiết kế database

Nguồn: `backend/database/models.py`

## 4.1 Enum chính

- `RoleEnum`: `admin | manager | employee`
- `ScopeEnum`: `personal | department | sqp`
- `ProposalStatus`: `pending | approved | rejected`

## 4.2 Bảng dữ liệu

| Bảng | Mục đích |
|---|---|
| `departments` | Danh mục phòng ban |
| `users` | Tài khoản người dùng, role, lock, department |
| `role_groups` | Nhóm quyền mở rộng |
| `documents` | Metadata tài liệu + scope + chủ sở hữu + session liên kết |
| `tags` | Danh mục tag |
| `document_tags` | Bảng nối n-n giữa documents và tags |
| `sqp_proposals` | Đề xuất tài liệu lên SQP |
| `chat_sessions` | Phiên hội thoại |
| `chat_messages` | Tin nhắn trong phiên (user/ai + sources) |
| `session_doc_attachments` | Tài liệu thư viện gắn vào phiên chat |
| `saved_prompts` | Prompt mẫu đã lưu của user |
| `shared_documents` | Chia sẻ tài liệu liên phòng |
| `contributors` | Danh sách user được ủy quyền đóng góp |

## 4.3 Quan hệ quan trọng

- `users.department_id -> departments.id`
- `documents.owner_id -> users.id`
- `documents.department_id -> departments.id`
- `documents.chat_session_id -> chat_sessions.id`
- `chat_messages.session_id -> chat_sessions.id` (cascade delete)
- `sqp_proposals.document_id -> documents.id`
- `session_doc_attachments.session_id -> chat_sessions.id` (cascade)
- `session_doc_attachments.doc_id -> documents.id` (cascade)

## 4.4 Cơ chế đồng bộ schema

`backend/database/schema_sync.py` thực hiện bổ sung cột/bảng thiếu theo kiểu best-effort (không dùng migration framework), giúp DB cũ chạy tiếp với code mới.

---

## 5. Chức năng theo vai trò

## 5.1 Employee

- Đăng nhập, chat AI, quản lý session chat.
- Upload/list/download/delete tài liệu cá nhân.
- Tra cứu tài liệu SQP.
- Quản lý prompt cá nhân.
- Đính kèm tài liệu vào session chat.

## 5.2 Manager

- Toàn bộ quyền employee.
- Quản lý tài liệu phòng ban.
- Đề xuất tài liệu lên SQP, hủy đề xuất pending.
- Chia sẻ tài liệu cho phòng ban khác.
- Quản lý contributor trong phòng.
- Trigger index RAG cho tài liệu phòng ban.

## 5.3 Admin

- Toàn bộ quyền manager.
- Quản lý user (CRUD, lock/unlock).
- Quản lý tags toàn hệ thống.
- Duyệt/từ chối đề xuất SQP.
- Vận hành vector DB (status/reindex/clear).
- Xem danh mục phòng ban.

---

## 6. API chính theo module

## 6.1 Auth

- `POST /auth/login`

## 6.2 Admin Users

- `GET /admin/users`
- `POST /admin/users`
- `PUT /admin/users/{user_id}`
- `POST /admin/users/{user_id}/lock`
- `DELETE /admin/users/{user_id}`

## 6.3 Documents

- Canonical:
  - `/documents/personal` (GET/POST/DELETE by id)
  - `/documents/department` (GET/POST/DELETE by id)
  - `/documents/{doc_id}/download`
  - `/documents/sqp`, `/documents/company`, `/documents/sqp/{doc_id}`
  - `/documents/tree`
- Legacy compatibility:
  - `/employee/documents*`
  - `/manager/department/documents*`
  - `/employee/sqp*`, `/employee/company`

## 6.4 Chat

- `/chat/ask`
- `/chat/sessions*` (create/list/rename/delete/messages)
- `/chat/sessions/{id}/documents*` (upload/list/delete file trong session)
- `/chat/sessions/{id}/attach*` (attach/detach/list attachment)
- `/chat/prompts*`
- Legacy compatibility: `/employee/chat`, `/employee/sessions*`, `/employee/prompts*`

## 6.5 Manager / SQP / Sharing

- `/manager/sqp/proposals`
- `/manager/sqp/propose/{document_id}`
- `/manager/share/document/{doc_id}/to-dept/{dept_id}`
- `/manager/contributors*`
- `/manager/department/documents/{doc_id}/index`

## 6.6 Admin System

- `/admin/departments`
- `/admin/sqp/proposals`
- `/admin/sqp/approve/{id}`
- `/admin/sqp/reject/{id}`
- `/admin/vector/status`
- `/admin/vector/reindex`
- `/admin/vector/clear`

---

## 7. Cấu hình & môi trường chạy

## 7.1 Backend

- Config đọc từ `backend/.env` qua `python-dotenv`.
- Biến quan trọng:
  - `SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`
  - `MYSQL_URL`
  - `OLLAMA_URL`, `OLLAMA_MODEL`
  - `CHROMA_DIR`, `EMBEDDING_MODEL`

## 7.2 Frontend

- API base URL qua `VITE_API_BASE_URL`.
- Axios interceptor tự gắn JWT và tự logout khi 401.

## 7.3 Hạ tầng local (docker-compose backend)

- MySQL 8.0
- Ollama

---

## 8. Nhận xét kỹ thuật và điểm cần lưu ý

1. **Có song song canonical API và legacy API** để tương thích frontend hiện tại.
2. **Chat lưu sources dạng JSON string trong text**, chưa chuẩn hóa sang bảng citation riêng.
3. **Schema sync thủ công** (không Alembic), phù hợp môi trường dev nhỏ nhưng hạn chế cho production lớn.
4. Một số chỗ frontend còn gọi URL cứng `http://localhost:8000` (ví dụ login/download), chưa đồng nhất hoàn toàn với biến môi trường.
5. Nhiều `try/except` phía frontend đang bỏ qua lỗi (silent fail), cần chuẩn hóa để dễ vận hành và debug.

---

## 9. Kết luận

Hệ thống hiện đã có đầy đủ khối chức năng cốt lõi cho:

- Quản lý người dùng theo vai trò.
- Quản lý tài liệu cá nhân/phòng ban/SQP.
- Chat AI có scope và tài liệu đính kèm.
- Quy trình đề xuất phê duyệt SQP.
- Công cụ vận hành vector DB cho admin.

Kiến trúc hiện tại phù hợp cho mô hình nội bộ, dễ mở rộng thêm migration chuẩn, audit log, citation chuẩn hóa và hardening bảo mật trong các phiên bản tiếp theo.
