# Component Spec: Database and ERD

## 1. Scope
Dac ta schema logic phuc vu:
- User/Role/Department
- Document/Tag/Sharing/Proposal
- ChatSession/ChatMessage/Attachment/SavedPrompt

## 2. Requirements (User stories)
- US-DB-01: He thong luu duoc user va phan quyen theo role.
- US-DB-02: He thong luu tai lieu theo scope ca nhan/phong ban/sqp.
- US-DB-03: He thong luu duoc hoi thoai chat va citations.
- US-DB-04: Truong phong de xuat tai lieu len SQP, admin duyet/tu choi.

## 3. Technical Constraints
### 3.1 Existing entities (from code)
- departments(id, name)
- users(id, username, hashed_password, full_name, role, is_locked, department_id, role_group_id)
- role_groups(id, name, description)
- tags(id, name)
- documents(id, filename, file_path, scope, summary, is_indexed, owner_id, department_id, chat_session_id, uploaded_at)
- document_tags(document_id, tag_id)
- sqp_proposals(id, document_id, proposed_by, status, created_at)
- chat_sessions(id, user_id, title, created_at)
- chat_messages(id, session_id, sender, content, sources, created_at)
- session_doc_attachments(id, session_id, doc_id, attached_at)
- saved_prompts(id, user_id, content, created_at)
- shared_documents(id, document_id, shared_with_dept_id, shared_by, created_at)
- contributors(id, user_id, granted_by, department_id, created_at)

### 3.2 Enum constraints
- RoleEnum: admin | manager | employee
- ScopeEnum: personal | department | sqp
- ProposalStatus: pending | approved | rejected

### 3.3 Referential integrity
- documents.owner_id -> users.id
- documents.department_id -> departments.id
- documents.chat_session_id -> chat_sessions.id
- sqp_proposals.document_id -> documents.id
- sqp_proposals.proposed_by -> users.id
- chat_messages.session_id -> chat_sessions.id (on delete cascade)
- document_tags.* on delete cascade
- session_doc_attachments.* on delete cascade

## 4. Planned schema upgrades (phase-based)
- P1 (auth/user hardening)
  - users.deleted_at (soft delete)
  - users.last_login_at
- P2 (document lifecycle)
  - documents.deleted_at
  - documents.version_number
  - documents.original_document_id
- P3 (chat citation quality)
  - chat_source_citations table (structured citations)
- P4 (governance and audit)
  - sqp_proposals.reason
  - sqp_proposals.reviewed_by
  - sqp_proposals.reviewed_at
  - audit_logs table

## 5. Acceptance Criteria
- AC-DB-01: Tao user moi phai ton tai department_id hop le (neu co cung cap).
- AC-DB-02: Tai lieu personal co owner_id, tai lieu department co department_id.
- AC-DB-03: Xoa chat session phai xoa toan bo chat_messages lien quan.
- AC-DB-04: Mot de xuat SQP phai lien ket duoc document va proposer hop le.
- AC-DB-05: Attach tag vao document tao record trong document_tags, khong duplicate key.
- AC-DB-06: Migration additive khong lam gay loi schema cu.

## 6. Verification checklist
- [ ] Chay schema sync/migration tren DB moi.
- [ ] Seed du lieu toi thieu: department, user admin, user manager, user employee.
- [ ] Tao tai lieu theo 3 scope va verify query tra dung.
- [ ] Tao chat session/message va verify cascade delete.
- [ ] Tao proposal va approve/reject flow verify status transition.
