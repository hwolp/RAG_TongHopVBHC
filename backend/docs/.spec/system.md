# System Spec

## 1. Muc tieu
Tai lieu nay la nguon su that ky thuat cho RAG App backend/frontend, duoc tao tu business spec trong docs/demo.md va code hien tai.

## 2. Kien truc tong quan
- Frontend: React + TypeScript + Vite.
- Backend API: FastAPI.
- Database: MySQL qua SQLAlchemy ORM.
- Auth: JWT Bearer token.
- RAG: ChromaDB + embedding + Ollama.
- Upload storage: local filesystem theo scope (personal/department/sqp).

## 3. Bounded Context
- Auth and Access: login, token, role gate (admin/manager/employee).
- User Admin: CRUD user, lock/unlock, department assignment.
- Document Lifecycle: upload/list/download/delete, tag, folder tree.
- Chat and RAG: ask AI, sessions, attachments, citations, saved prompts.
- Governance: SQP proposals, approve/reject, sharing and delegation.
- Vector Ops: status, reindex, clear for admin.

## 4. Mapping voi code hien tai
- App composition: backend/main.py
- Auth routes: backend/routers/auth.py
- User admin routes: backend/routers/users.py
- Document routes: backend/routers/documents.py
- Chat routes: backend/routers/chat.py
- Manager routes: backend/routers/manager.py
- Admin routes: backend/routers/admin.py
- Data model: backend/database/models.py

## 5. Requirements (User stories)
- R1: Nguoi dung dang nhap duoc va nhan token hop le.
- R2: Admin quan ly user (xem, tao, sua, khoa/mo khoa, xoa).
- R3: Nhan vien quan ly tai lieu ca nhan.
- R4: Truong phong quan ly tai lieu phong ban va de xuat SQP.
- R5: Nguoi dung chat AI theo scope va xem citations.
- R6: Admin van hanh vector DB (status/reindex/clear).

## 6. Technical Constraints
- API style: REST JSON, auth bang Authorization: Bearer <token>.
- RBAC gate:
  - admin: require_admin
  - manager: require_manager
  - employee: get_current_user
- Canonical endpoint uu tien dung /documents/* va /chat/*, legacy endpoint chi de tuong thich.
- Enum quan trong trong DB:
  - RoleEnum: admin | manager | employee
  - ScopeEnum: personal | department | sqp
  - ProposalStatus: pending | approved | rejected
- Phai giu backward compatibility cho endpoint legacy cho den khi frontend chuyen xong.

## 7. Acceptance Criteria
- AC1: Khoi dong app thanh cong, root endpoint tra status ok.
- AC2: Login thanh cong tra ve access_token, token_type, role, username.
- AC3: User khong dung role bi chan truy cap endpoint admin/manager (HTTP 403).
- AC4: Upload tai lieu ca nhan/phong ban tao record Document va co the download lai.
- AC5: Chat tao duoc message user + ai, luu session history.
- AC6: Admin vector status/reindex/clear tra ket qua hop le.

## 8. Milestone implementation
- M1: Auth and User management complete.
- M2: Document lifecycle (version/trash/tag) complete.
- M3: Chat RAG (scope/citation/prompt) complete.
- M4: Sharing/delegation/proposal hardening complete.
- M5: Reliability and migration complete.
