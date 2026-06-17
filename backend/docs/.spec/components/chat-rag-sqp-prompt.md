# Component Spec: Chat RAG, SQP, and Prompts

## 1. Scope
Phu trach cac chuc nang:
- FUNC-AI-01..03: Hoi dap AI, context retrieval, citations.
- FUNC-CHAT-01..04: Quan ly session, message, attachments, session uploads.
- FUNC-SQP-01..03: Duyet va tra cuu van ban SQP.
- FUNC-PROMPT-01..03: Luu, quan ly va execute prompts.

## 2. Requirements (User stories)
- US-AI-01: Nguoi dung hoi AI theo session hien tai va uu tien tai lieu dinh kem/upload trong session.
- US-AI-02: Nguoi dung nhan cau tra loi AI kem danh sach nguon.
- US-CHAT-01: Nguoi dung xem lich su session, doi ten, xoa session.
- US-CHAT-02: Nguoi dung upload file rieng vao session hoac attach tai lieu co san tu thu vien.
- US-SQP-01: Nguoi dung tra cuu van ban SQP theo keyword va xem chi tiet.
- US-PROMPT-01: Nguoi dung luu prompt mau de tai su dung.
- US-PROMPT-02: Nguoi dung execute prompt da luu nhu mot cau hoi chat.

## 3. Technical Constraints
### 3.1 Existing API endpoints
- POST /chat/ask
- POST /chat/sessions
- GET /chat/sessions
- GET /chat/sessions/{session_id}/messages
- PUT /chat/sessions/{session_id}
- DELETE /chat/sessions/{session_id}
- GET /chat/prompts
- POST /chat/prompts
- DELETE /chat/prompts/{prompt_id}
- POST /chat/prompts/{prompt_id}/execute
- GET /chat/citations/{message_id}
- GET /chat/documents/tree
- POST /chat/sessions/{session_id}/attach
- DELETE /chat/sessions/{session_id}/attach/{doc_id}
- GET /chat/sessions/{session_id}/attachments
- POST /chat/sessions/{session_id}/documents
- GET /chat/sessions/{session_id}/documents
- DELETE /chat/sessions/{session_id}/documents/{doc_id}
- GET /documents/sqp
- GET /documents/sqp/{doc_id}
- GET /documents/company
- GET /jobs/{job_id}
- GET /jobs/{job_id}/wait

### 3.2 Legacy compatibility endpoints
- POST /employee/chat
- POST /employee/sessions
- GET /employee/sessions
- GET /employee/sessions/{session_id}/messages
- PUT /employee/sessions/{session_id}
- DELETE /employee/sessions/{session_id}
- POST /employee/sessions/{session_id}/documents/upload
- GET/POST/DELETE /employee/prompts*
- GET /employee/sqp*
- GET /employee/company

### 3.3 Payload constraints
- POST /chat/ask body toi thieu:
  - question: string
  - scope: personal | department | company
  - session_id: optional int
- POST /chat/sessions/{session_id}/documents:
  - multipart `file`: UploadFile, required.
  - multipart `tag_ids`: repeated int, optional.
- Prompt model hien tai luu content text.
- ChatMessage.sources hien tai dang Text (JSON string) trong DB.

### 3.4 Retrieval constraints
- Scope phai duoc enforce khi query vector:
  - personal -> owner cua user va tai lieu session upload/attach co quyen.
  - department -> tai lieu cung department hoac tai lieu duoc share.
  - company -> SQP/company sources.
- Attachments cua session duoc uu tien trong context khi ask.
- Neu attached/session document chua indexed, service co the enqueue index job va tra trang thai cho user cho xu ly tiep.
- Tag cua tai lieu khong tham gia ranking vector; tag chi dung de hien thi/filter SQL.

## 4. Workflow
### 4.1 Ask AI
1. Frontend goi POST /chat/ask voi question va session_id.
2. Backend tao session neu can.
3. Backend luu ChatMessage sender=user.
4. Backend tao placeholder ChatMessage sender=ai va background job `chat_answer`.
5. Worker lay context tu vector store theo scope + attachments.
6. Worker cap nhat AI message content, sources JSON va job status.
7. Frontend poll /jobs/{job_id} hoac lay lai messages de hien thi ket qua.

### 4.2 Session upload and attach
1. Upload file vao session tao personal document co `chat_session_id`.
2. Tags neu co duoc luu vao `document_tags`.
3. Neu file ho tro, enqueue index job.
4. Attach tai lieu co san chi tao lien ket `session_doc_attachments`; neu tai lieu chua index thi co the enqueue index.

### 4.3 SQP browsing
1. User goi GET /documents/sqp hoac /documents/company de tim kiem.
2. Backend chi tra scope=sqp, khong can admin.
3. Detail/download van check access hop le.

## 5. Acceptance Criteria
- AC-CR-01:
  - Given user token
  - When goi POST /chat/ask voi scope hop le
  - Then tao user message, AI placeholder va background job.
- AC-CR-02:
  - Given chat job hoan thanh
  - When frontend reload messages hoac citations
  - Then AI message co content va sources/citations de hien thi.
- AC-CR-03:
  - Given user so huu session
  - When goi PUT /chat/sessions/{id}
  - Then title session duoc cap nhat.
- AC-CR-04:
  - Given user goi DELETE /chat/sessions/{id}
  - Then session va messages lien quan bi xoa.
- AC-CR-05:
  - Given user upload file vao session kem tag_ids
  - When upload thanh cong
  - Then document co chat_session_id, co document_tags va duoc uu tien trong chat session.
- AC-CR-06:
  - Given user luu prompt
  - When goi POST /chat/prompts/{prompt_id}/execute
  - Then prompt duoc gui vao chat workflow nhu cau hoi.
- AC-CR-07:
  - Given user tra cuu SQP
  - When goi GET /documents/sqp?search=...
  - Then tra danh sach van ban phu hop.

## 6. Implementation Notes
- Router lien quan:
  - backend/routers/chat.py
  - backend/routers/documents.py
  - backend/routers/jobs.py
- Service lien quan:
  - backend/services/chat/*
  - backend/services/documents/document_service.py
  - backend/services/documents/folder_service.py
  - backend/services/jobs/*
- RAG engine:
  - backend/rag_engine/chroma_manager.py
  - backend/rag_engine/ollama_ai.py
