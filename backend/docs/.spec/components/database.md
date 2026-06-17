# Component Spec: Database and ERD

## 1. Scope
Dac ta schema logic phuc vu:
- User/Role/Department/RoleGroup
- Document/Tag/Version/Sharing/Proposal
- ChatSession/ChatMessage/Attachment/SavedPrompt
- ConfigItem/BackgroundJob

## 2. Requirements (User stories)
- US-DB-01: He thong luu duoc user va phan quyen theo role.
- US-DB-02: He thong luu tai lieu theo scope ca nhan/phong ban/sqp.
- US-DB-03: He thong luu tag rieng trong bang quan he document_tags.
- US-DB-04: He thong luu duoc hoi thoai chat va citations JSON.
- US-DB-05: Truong phong de xuat tai lieu len SQP, admin duyet/tu choi.
- US-DB-06: He thong theo doi background jobs cho index/chat.

## 3. Technical Constraints
### 3.1 Existing entities (from code)
- departments(id, name)
- users(id, username, hashed_password, full_name, role, is_locked, department_id, role_group_id)
- role_groups(id, name, description)
- tags(id, name)
- documents(id, filename, file_path, scope, summary, is_indexed, is_deleted, deleted_at, version_number, owner_id, department_id, chat_session_id, uploaded_at)
- document_tags(document_id, tag_id)
- document_versions(id, document_id, filename, file_path, version_number, uploaded_by, created_at)
- sqp_proposals(id, document_id, proposed_by, status, created_at)
- chat_sessions(id, user_id, title, created_at)
- chat_messages(id, session_id, sender, content, sources, created_at)
- session_doc_attachments(id, session_id, doc_id, attached_at)
- saved_prompts(id, user_id, content, created_at)
- config_items(id, key, value, type)
- background_jobs(id, type, status, progress, created_by, document_id, session_id, message_id, payload, result, error, created_at, updated_at, finished_at)
- shared_documents(id, document_id, shared_with_dept_id, shared_with_user_id, shared_by, created_at)
- contributors(id, user_id, granted_by, department_id, created_at)

### 3.2 Enum constraints
- RoleEnum: admin | manager | employee
- ScopeEnum: personal | department | sqp
- ProposalStatus: pending | approved | rejected
- BackgroundJobStatus: queued | running | completed | failed

### 3.3 Referential integrity
- users.department_id -> departments.id
- users.role_group_id -> role_groups.id
- documents.owner_id -> users.id
- documents.department_id -> departments.id
- documents.chat_session_id -> chat_sessions.id
- document_versions.document_id -> documents.id
- document_versions.uploaded_by -> users.id
- sqp_proposals.document_id -> documents.id
- sqp_proposals.proposed_by -> users.id
- chat_sessions.user_id -> users.id
- chat_messages.session_id -> chat_sessions.id (on delete cascade)
- document_tags.document_id -> documents.id (on delete cascade)
- document_tags.tag_id -> tags.id (on delete cascade)
- session_doc_attachments.session_id -> chat_sessions.id (on delete cascade)
- session_doc_attachments.doc_id -> documents.id (on delete cascade)
- saved_prompts.user_id -> users.id
- background_jobs.created_by -> users.id
- background_jobs.document_id -> documents.id (on delete set null)
- background_jobs.session_id -> chat_sessions.id (on delete set null)
- background_jobs.message_id -> chat_messages.id (on delete set null)
- shared_documents.document_id -> documents.id
- shared_documents.shared_with_dept_id -> departments.id
- shared_documents.shared_with_user_id -> users.id
- shared_documents.shared_by -> users.id
- contributors.user_id -> users.id
- contributors.granted_by -> users.id
- contributors.department_id -> departments.id

## 4. Current data rules
- `document_tags` la nguon su that cua tag tren tai lieu.
- Sua tag chi them/xoa rows trong `document_tags`; khong cap nhat ChromaDB va khong doi `documents.is_indexed`.
- `documents.is_indexed` phan anh noi dung file da co trong vector store, khong phan anh tag.
- `background_jobs` la nguon theo doi tien trinh index/chat cho frontend.
- Personal delete la soft delete qua `is_deleted/deleted_at`; restore dat lai trang thai active.
- Department/SQP delete hien tai co the xoa file/record theo service tuong ung.
- Approve SQP chuyen document sang scope=sqp, dat can index lai va enqueue index job.

## 5. Planned schema upgrades (phase-based)
- P1 (audit)
  - users.last_login_at
  - audit_logs table
- P2 (document governance)
  - sqp_proposals.reason
  - sqp_proposals.reviewed_by
  - sqp_proposals.reviewed_at
- P3 (chat citation quality)
  - chat_source_citations table (structured citations, neu can thay JSON)

## 6. Acceptance Criteria
- AC-DB-01: Tao user moi phai ton tai department_id hop le neu co cung cap.
- AC-DB-02: Tai lieu personal co owner_id, tai lieu department co department_id, tai lieu SQP co scope=sqp.
- AC-DB-03: Gan tag vao document tao record trong document_tags, khong duplicate key.
- AC-DB-04: Sua tag cua document khong lam doi is_indexed va khong tao background job.
- AC-DB-05: Xoa chat session phai xoa toan bo chat_messages va session_doc_attachments lien quan.
- AC-DB-06: Mot de xuat SQP phai lien ket duoc document va proposer hop le.
- AC-DB-07: Background job co status/progress/result hoac error de frontend poll.
- AC-DB-08: Migration additive khong lam gay loi schema cu.

## 7. Verification checklist
- [ ] Chay schema sync/migration tren DB moi.
- [ ] Seed du lieu toi thieu: department, user admin, user manager, user employee.
- [ ] Tao tai lieu theo 3 scope va verify query tra dung.
- [ ] Upload/update tag va verify chi thay doi document_tags.
- [ ] Tao chat session/message/job va verify cascade delete.
- [ ] Tao proposal va approve/reject flow verify status transition.
