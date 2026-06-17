# Feature Coverage Matrix

## 1. Muc tieu
Tai lieu nay doi chieu danh sach chuc nang nghiep vu voi cac component spec trong `backend/docs/.spec/components` de dam bao khong bo sot workflow hien tai.

## 2. Mapping chuc nang -> spec
- Quan tri he thong & tai khoan:
  - Dang nhap / dang xuat -> `auth-flow.md`
  - Danh muc nguoi dung / tai khoan -> `user-rbac.md`
  - Danh muc nhom quyen -> `user-rbac.md`
  - Danh muc cau hinh he thong -> `config-public-docs.md`
  - Tags dung chung -> `config-public-docs.md`, `document-lifecycle.md`
  - Vector DB (status/re-index/clear collection) -> `vector-ops.md`
- Quan ly tai lieu:
  - Tai lieu ca nhan -> `document-lifecycle.md`
  - Tai lieu phong ban cua truong phong -> `document-lifecycle.md`
  - Tai lieu phong ban do admin quan ly -> `document-lifecycle.md`, `config-public-docs.md`
  - Tai lieu SQP/kho chung -> `document-lifecycle.md`, `config-public-docs.md`, `chat-rag-sqp-prompt.md`
  - Version/trash -> `document-lifecycle.md`
- Hoi dap AI & tra cuu:
  - Chat AI + citations -> `chat-rag-sqp-prompt.md`
  - Chat sessions -> `chat-rag-sqp-prompt.md`
  - Attach/upload tai lieu vao session -> `chat-rag-sqp-prompt.md`, `document-lifecycle.md`
  - SQP tra cuu -> `chat-rag-sqp-prompt.md`, `config-public-docs.md`
  - Prompts -> `chat-rag-sqp-prompt.md`
  - Background jobs -> `chat-rag-sqp-prompt.md`, `vector-ops.md`
- Dieu phoi & phan quyen:
  - Chia se lien phong -> `sharing-delegation-proposal.md`
  - Chia se den user -> `sharing-delegation-proposal.md`
  - Uy quyen dong gop -> `sharing-delegation-proposal.md`
  - De xuat tai lieu len SQP -> `sharing-delegation-proposal.md`

## 3. Current implementation status
- Implemented canonical document APIs:
  - `GET /documents/{doc_id}`
  - `GET /documents/{doc_id}/download`
  - `PUT /documents/personal/{doc_id}`
  - `PUT /documents/department/{doc_id}`
  - `GET/POST /documents/{doc_id}/versions`
  - `GET /documents/trash`
  - `POST /documents/{doc_id}/restore`
- Implemented tag workflow:
  - upload accepts `tag_ids`
  - metadata update accepts `tag_ids`
  - tag assignment writes only `document_tags`
  - tag changes do not trigger re-index
- Implemented admin/config APIs:
  - `GET/POST/PUT/DELETE /admin/configs*`
  - `GET/POST /admin/role-groups*`
  - `PUT /admin/users/{user_id}/role-group`
- Implemented admin document APIs:
  - `GET/POST/PUT/DELETE /admin/documents/department*`
  - `GET /admin/sqp/documents`
  - SQP mutate APIs are `POST/PUT/DELETE /documents/sqp*`
- Implemented chat/job APIs:
  - `POST /chat/ask`
  - `POST /chat/prompts/{prompt_id}/execute`
  - `GET /chat/citations/{message_id}`
  - `GET /jobs/{job_id}`
  - `GET /jobs/{job_id}/wait`
- Implemented sharing/proposal APIs:
  - manager share to department/user
  - admin share to department/user
  - SQP propose/approve/reject

## 4. Explicit non-goals or not-current endpoints
- Khong dung `/admin/company/documents*`; kho chung/SQP duoc quan ly qua `/documents/sqp*` va list admin qua `/admin/sqp/documents`.
- Chua co endpoint rieng `/documents/{doc_id}/preview`.
- Chua co endpoint rieng `/documents/sqp/categories`.
- Tag khong phai dieu kien index vector; neu can filter theo tag thi filter bang SQL/document_tags.
