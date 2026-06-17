# System Spec

## 1. Muc tieu
Tai lieu nay la nguon su that ky thuat cho RAG App backend/frontend, duoc tao tu business spec trong docs/demo.md va code hien tai.

## 2. Kien truc tong quan
- Frontend: React + TypeScript + Vite.
- Backend API: FastAPI.
- Database: MySQL qua SQLAlchemy ORM.
- Auth: JWT Bearer token.
- RAG: ChromaDB + embedding + Ollama.
- Background jobs: xu ly index tai lieu va cau tra loi chat bat dong bo.
- Upload storage: local filesystem theo scope (personal/department/sqp).

## 3. Bounded Context
- Auth and Access: login, token, role gate (admin/manager/employee).
- User Admin: CRUD user, lock/unlock, department assignment, role group.
- Document Lifecycle: upload/list/download/update/delete, version, trash, tag, folder tree.
- Chat and RAG: sessions, attachments, session uploads, jobs, citations, saved prompts.
- Governance: SQP proposals, approve/reject, sharing and delegation.
- System Config: admin metadata/config items and global tags.
- Vector Ops: status, reindex, clear for admin.

## 4. Mapping voi code hien tai
- App composition: backend/main.py
- Auth routes: backend/routers/auth.py
- User admin routes: backend/routers/users.py
- Document routes: backend/routers/documents.py
- Tag routes: backend/routers/tags.py
- Chat routes: backend/routers/chat.py
- Job routes: backend/routers/jobs.py
- Manager routes: backend/routers/manager.py
- Admin routes: backend/routers/admin.py
- Data model: backend/database/models.py

## 5. Requirements (User stories)
- R1: Nguoi dung dang nhap duoc va nhan token hop le.
- R2: Admin quan ly user, phong ban, nhom quyen, cau hinh va tag dung chung.
- R3: Nhan vien quan ly tai lieu ca nhan, doi ten file, doi tag va tai version moi.
- R4: Truong phong quan ly tai lieu phong ban, doi thong tin/tag cua tai lieu phong ban va de xuat SQP.
- R5: Admin quan ly tai lieu phong ban toan he thong va kho SQP.
- R6: Nguoi dung chat AI theo session, dinh kem tai lieu va xem citations.
- R7: Admin van hanh vector DB (status/reindex/clear).

## 6. Technical Constraints
- API style: REST JSON, auth bang Authorization: Bearer <token>.
- Multipart upload dung `file` va co the kem repeated `tag_ids`.
- RBAC gate:
  - admin: require_admin
  - manager/admin: require_manager
  - manager only: require_manager_only
  - authenticated user: get_current_user
- Canonical endpoint uu tien dung /documents/*, /chat/*, /admin/* va /manager/*; legacy endpoint chi de tuong thich.
- Enum quan trong trong DB:
  - RoleEnum: admin | manager | employee
  - ScopeEnum: personal | department | sqp
  - ProposalStatus: pending | approved | rejected
- Tag la metadata quan he trong `document_tags`; tao/sua/xoa tag hoac gan tag khong duoc tu dong re-index vector.
- Re-index chi can khi noi dung file doi, tai lieu moi duoc upload, tai lieu duoc attach khi chua index, hoac scope thay doi khi approve SQP.
- Phai giu backward compatibility cho endpoint legacy cho den khi frontend chuyen xong.

## 7. Acceptance Criteria
- AC1: Khoi dong app thanh cong, root endpoint tra status ok.
- AC2: Login thanh cong tra ve access_token, token_type, role, username.
- AC3: User khong dung role bi chan truy cap endpoint admin/manager (HTTP 403).
- AC4: Upload tai lieu ca nhan/phong ban/SQP tao record Document, luu tag neu co va enqueue index job neu file ho tro.
- AC5: Sua ten file hoac tag chi cap nhat metadata/document_tags, khong tao index job moi.
- AC6: Chat ask tao message user + placeholder AI, enqueue background job va co the doc ket qua qua job/message.
- AC7: Admin vector status/reindex/clear tra ket qua hop le.

## 8. Milestone implementation
- M1: Auth and User management complete.
- M2: Document lifecycle (metadata/tag/version/trash) complete.
- M3: Chat RAG (session/upload/attach/citation/prompt/job) complete.
- M4: Sharing/delegation/proposal hardening complete.
- M5: Admin config/SQP/vector operations complete.
