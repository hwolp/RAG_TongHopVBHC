# Component Spec: Chat RAG, SQP, and Prompts

## 1. Scope
Phu trach cac chuc nang:
- FUNC-AI-01..03: Scope chat, hoi dap AI, citations.
- FUNC-CHAT-01..02: Quan ly phien hoi thoai.
- FUNC-SQP-01..03: Duyet va tra cuu van ban SQP.
- FUNC-PROMPT-01..02: Luu va quan ly prompts.

## 2. Requirements (User stories)
- US-AI-01: Nguoi dung chon scope tim kiem truoc khi hoi.
- US-AI-02: Nguoi dung nhan cau tra loi AI kem danh sach nguon.
- US-CHAT-01: Nguoi dung xem lich su session, doi ten, xoa session.
- US-SQP-01: Nguoi dung tra cuu van ban SQP theo keyword va xem chi tiet.
- US-PROMPT-01: Nguoi dung luu prompt mau de tai su dung.

## 3. Technical Constraints
### 3.1 Existing API endpoints
- POST /chat/ask
- GET /chat/sessions
- GET /chat/sessions/{session_id}/messages
- PUT /chat/sessions/{session_id}
- DELETE /chat/sessions/{session_id}
- GET /chat/prompts
- POST /chat/prompts
- DELETE /chat/prompts/{prompt_id}
- GET /chat/documents/tree
- POST /chat/sessions/{session_id}/attach
- DELETE /chat/sessions/{session_id}/attach/{doc_id}
- GET /chat/sessions/{session_id}/attachments
- POST /chat/sessions/{session_id}/documents
- GET /chat/sessions/{session_id}/documents
- DELETE /chat/sessions/{session_id}/documents/{doc_id}
- GET /documents/sqp
- GET /documents/sqp/{doc_id}

### 3.2 Payload constraints
- POST /chat/ask body toi thieu:
  - question: string
  - scope: personal | department | company
  - session_id: optional int
- Prompt model hien tai chi luu content text.
- ChatMessage.sources hien tai dang Text (JSON string) trong DB.

### 3.3 Retrieval constraints
- Scope phai duoc enforce khi query vector:
  - personal -> owner cua user
  - department -> cung department
  - company -> sqp/public sources
- Attachments cua session duoc phep bo sung context khi ask.

### 3.4 Planned API endpoints
- GET /chat/sessions/{session_id}/search
- POST /chat/prompts/{prompt_id}/execute
- GET /documents/sqp/categories

## 4. Acceptance Criteria
- AC-CR-01:
  - Given user token
  - When goi POST /chat/ask voi scope hop le
  - Then tao message user + ai trong session va tra answer text.
- AC-CR-02:
  - Given AI response
  - When response tra ve
  - Then co sources/citations de frontend hien thi.
- AC-CR-03:
  - Given user so huu session
  - When goi PUT /chat/sessions/{id}
  - Then title session duoc cap nhat.
- AC-CR-04:
  - Given user goi DELETE /chat/sessions/{id}
  - Then session va messages lien quan bi xoa.
- AC-CR-05:
  - Given user luu prompt
  - When goi POST /chat/prompts
  - Then prompt moi ton tai va list ra duoc.
- AC-CR-06:
  - Given user tra cuu SQP
  - When goi GET /documents/sqp?search=...
  - Then tra danh sach van ban phu hop.

## 5. Implementation Notes
- Router lien quan:
  - backend/routers/chat.py
  - backend/routers/documents.py
- Service lien quan:
  - backend/services/chat_service.py
  - backend/services/document_service.py
  - backend/services/folder_service.py
- RAG engine:
  - backend/rag_engine/chroma_manager.py
  - backend/rag_engine/ollama_ai.py
