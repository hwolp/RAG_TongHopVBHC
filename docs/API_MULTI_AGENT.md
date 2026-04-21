# API Master for Multi Agent Coding

## 1. Purpose
Tai lieu nay tach rieng phan API de chia task cho nhieu AI agent code song song.
Nguon du lieu duoc tong hop tu backend routers va schema hien tai.

## 2. Global API Contract
- Base URL: / (FastAPI app)
- Auth type: Bearer JWT
- Header:
  - Authorization: Bearer <access_token>
- Token claims toi thieu:
  - sub, id, role
- Role gate:
  - admin: require_admin
  - manager: require_manager (admin hoac manager)
  - any user: get_current_user
- Canonical endpoints duoc uu tien su dung.
- Legacy endpoints giu de backward compatibility trong giai doan chuyen doi.

## 3. Shared Error Rules
- 400: bad request/business validation
- 401: invalid credentials hoac token het han
- 403: role khong du quyen
- 404: resource khong ton tai
- 500: internal error

## 4. Agent Partitioning

### Agent A: Auth and Session Boundary
Scope:
- Dang nhap, token, guard behavior

Endpoints:
- POST /auth/login

Request schema:
- username: string
- password: string

Response schema:
- access_token: string
- token_type: bearer
- role: admin | manager | employee
- username: string

Acceptance for Agent A:
- Login dung credentials tra 200 + token payload day du.
- User bi lock tra 403.
- Sai credentials tra 401.
- Token duoc middleware decode thanh user payload co id.

Dependency:
- middleware/auth_middleware.py
- schemas/auth_schema.py
- services/auth_service.py

---

### Agent B: User and RBAC Admin
Scope:
- CRUD user, lock/unlock, role assignment, department assignment

Endpoints:
- GET /admin/users
- POST /admin/users
- PUT /admin/users/{user_id}
- POST /admin/users/{user_id}/lock
- DELETE /admin/users/{user_id}
- GET /admin/departments

Request schema:
- POST /admin/users
  - username: string
  - full_name: string
  - role: string
  - department_id: int | null
  - password: string
- PUT /admin/users/{user_id}
  - full_name: string | null
  - role: string | null
  - department_id: int | null

Acceptance for Agent B:
- Non-admin goi /admin/* bi 403.
- Create user duplicate username bi 400.
- Update user role invalid bi 400.
- Lock endpoint dao trang thai is_locked.

Dependency:
- routers/users.py
- schemas/user_schema.py
- services/user_service.py
- database/models.py (User, Department, RoleGroup)

---

### Agent C: Document Lifecycle and Tags
Scope:
- Personal docs, department docs, tree, download, tag attach

Canonical endpoints:
- GET /documents/tree
- GET /documents/personal
- POST /documents/personal
- DELETE /documents/personal/{doc_id}
- GET /documents/department
- POST /documents/department
- DELETE /documents/department/{doc_id}
- GET /documents/{doc_id}/download
- GET /documents/sqp
- GET /documents/company
- GET /documents/sqp/{doc_id}
- GET /tags
- POST /tags
- PUT /tags/{tag_id}
- DELETE /tags/{tag_id}
- POST /documents/{doc_id}/tags/{tag_id}

Legacy endpoints (compat only):
- /employee/documents*
- /manager/department/documents*
- /employee/department/documents
- /employee/sqp*
- /employee/company
- /employee/tags*
- /admin/tags*

Acceptance for Agent C:
- Employee upload personal doc thanh cong.
- Chi manager/admin moi upload department doc.
- Download chi thanh cong neu user co quyen.
- Attach tag tao duoc relation document_tags.

Dependency:
- routers/documents.py
- routers/tags.py
- services/document_service.py
- services/tag_service.py
- services/folder_service.py

---

### Agent D: Chat, RAG, Session, Prompt
Scope:
- Ask AI, session history, rename/delete session, prompt save/delete, attachment flow

Endpoints:
- POST /chat/ask
- POST /chat/sessions/{session_id}/documents
- GET /chat/documents/tree
- POST /chat/sessions/{session_id}/attach
- DELETE /chat/sessions/{session_id}/attach/{doc_id}
- GET /chat/sessions/{session_id}/attachments
- GET /chat/sessions/{session_id}/documents
- DELETE /chat/sessions/{session_id}/documents/{doc_id}
- GET /chat/sessions
- GET /chat/sessions/{session_id}/messages
- PUT /chat/sessions/{session_id}
- DELETE /chat/sessions/{session_id}
- GET /chat/prompts
- POST /chat/prompts
- DELETE /chat/prompts/{prompt_id}

Legacy endpoints (compat only):
- /employee/chat
- /employee/sessions*
- /employee/prompts*

Request schema highlights:
- POST /chat/ask
  - question: string
  - scope: string (default personal)
  - session_id: int | null
- PUT /chat/sessions/{session_id}
  - title: string
- POST /chat/prompts
  - content: string
- POST /chat/sessions/{session_id}/attach
  - doc_id: int

Acceptance for Agent D:
- Ask tao message user + ai trong session.
- Session list va paginated messages hoat dong.
- Rename/delete session dung ownership rule.
- Prompt create/list/delete theo user.

Dependency:
- routers/chat.py
- schemas/chat_schema.py
- services/chat_service.py
- rag_engine/chroma_manager.py
- rag_engine/ollama_ai.py

---

### Agent E: Manager Collaboration and SQP Proposal
Scope:
- Sharing, contributor delegation, manager proposal actions

Endpoints:
- GET /manager/sqp/proposals
- POST /manager/sqp/propose/{document_id}
- DELETE /manager/sqp/proposals/{proposal_id}
- POST /manager/share/document/{doc_id}/to-dept/{dept_id}
- DELETE /manager/share/{share_id}
- GET /manager/contributors
- POST /manager/contributors/{user_id}
- DELETE /manager/contributors/{contrib_id}
- POST /manager/department/documents/{doc_id}/index

Acceptance for Agent E:
- Chi manager/admin duoc goi /manager/*.
- Share tao record shared_documents hop le.
- Add/remove contributor cap nhat danh sach dung.
- Propose tao proposal status pending.

Dependency:
- routers/manager.py
- services/share_service.py
- services/sqp_service.py
- database/models.py (SharedDocument, Contributor, SQPProposal)

---

### Agent F: Admin Governance and Vector Ops
Scope:
- SQP proposal review and vector operations

Endpoints:
- GET /admin/sqp/documents
- GET /admin/sqp/proposals
- POST /admin/sqp/approve/{proposal_id}
- POST /admin/sqp/reject/{proposal_id}
- GET /admin/vector/status
- POST /admin/vector/reindex
- POST /admin/vector/clear

Acceptance for Agent F:
- Chi admin duoc goi /admin/*.
- Approve/reject thay doi status proposal dung.
- Reindex tra ket qua so doc/chunk da xu ly.
- Clear vector tra success va canh bao destructive action tren UI.

Dependency:
- routers/admin.py
- services/sqp_service.py
- services/document_service.py
- rag_engine/chroma_manager.py

## 5. Parallel Work Plan (Recommended)
- Wave 1 (co the song song): Agent A, Agent B, Agent D
- Wave 2 (sau Wave 1 contracts): Agent C, Agent E
- Wave 3 (sau Wave 2 data stable): Agent F

## 6. Integration Gates
Gate 1:
- Auth + User APIs pass role boundary tests.

Gate 2:
- Document + Tag + Chat APIs pass ownership/scope tests.

Gate 3:
- Proposal + Sharing + Admin vector APIs pass workflow tests.

## 7. Notes for Multi Agent Orchestration
- Moi agent chi duoc sua file trong domain cua minh.
- Neu sua schema/chung contract, bat buoc tao shared task va merge truoc.
- Canonical endpoint la contract chinh; legacy endpoint chi regression test, khong mo rong tinh nang moi.
