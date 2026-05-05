# Feature Coverage Matrix (A/B)

## 1. Muc tieu
Tai lieu nay doi chieu danh sach chuc nang nghiep vu A/B voi cac component spec trong `backend/docs/.spec/components` de dam bao khong bo sot plan.

## 2. Mapping chuc nang -> spec
- Quan tri he thong & tai khoan:
  - Dang nhap / dang xuat -> `auth-flow.md`
  - Danh muc nguoi dung / tai khoan -> `user-rbac.md`
  - Danh muc nhom quyen -> `user-rbac.md`
  - Danh muc cau hinh he thong (metadata/tag) -> `config-public-docs.md`
  - Kho tai lieu chung (public/sqp) -> `config-public-docs.md`, `document-lifecycle.md`
  - Vector DB (status/re-index/clear collection) -> `vector-ops.md`
- Quan ly tai lieu:
  - Tai lieu ca nhan / phong ban / tag -> `document-lifecycle.md`
- Hoi dap AI & tra cuu:
  - Chat AI + citations -> `chat-rag-sqp-prompt.md`
  - Chat sessions -> `chat-rag-sqp-prompt.md`
  - SQP tra cuu -> `chat-rag-sqp-prompt.md`, `config-public-docs.md`
  - Prompts -> `chat-rag-sqp-prompt.md`
- Dieu phoi & phan quyen:
  - Chia se lien phong -> `sharing-delegation-proposal.md`
  - Uy quyen dong gop -> `sharing-delegation-proposal.md`
  - De xuat tai lieu len kho cong ty -> `sharing-delegation-proposal.md`

## 3. Ghi chu bo sung sau khi soat plan
- Da bo sung `POST /auth/logout` vao `auth-flow.md`.
- Da bo sung va implement nhom API tai lieu:
  - `GET /documents/{doc_id}`
  - `GET /documents/{doc_id}/preview`
  - `PUT /documents/personal/{doc_id}`
  - `PUT /documents/department/{doc_id}`
  - `GET/POST /documents/{doc_id}/versions`
  - `GET /documents/trash`
  - `POST /documents/{doc_id}/restore`
- Da bo sung va implement:
  - `GET/POST/PUT/DELETE /admin/configs*`
  - `POST/PUT/DELETE /admin/company/documents*`
  - `GET/POST/PUT/DELETE /admin/role-groups*`
  - `PUT /admin/users/{user_id}/role-group`
  - `GET /chat/citations/{citation_id}`
  - `POST /chat/prompts/{prompt_id}/execute`
  - `GET /documents/sqp/categories`
