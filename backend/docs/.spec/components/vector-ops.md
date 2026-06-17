# Component Spec: Vector Operations

## 1. Scope
Phu trach cac chuc nang:
- FUNC-VEC-01: Xem trang thai du lieu vector.
- FUNC-VEC-02: Re-index du lieu vector.
- FUNC-VEC-03: Xoa collection vector va du lieu lien quan de bao tri.
- FUNC-JOB-01: Theo doi background job index/chat.

## 2. Requirements (User stories)
- US-VEC-01: La admin, toi muon xem tong so vectors va thong tin luu tru.
- US-VEC-02: La admin, toi muon chay reindex de dong bo vector sau khi cap nhat noi dung/scope tai lieu.
- US-VEC-03: La admin, toi muon clear vector DB co canh bao de khoi phuc index lai.
- US-JOB-01: Nguoi dung/admin co the poll job de biet tien trinh index/chat.

## 3. Technical Constraints
### 3.1 Existing API endpoints
- GET /admin/vector/status
- POST /admin/vector/reindex
- POST /admin/vector/clear
- GET /jobs
- GET /jobs/{job_id}
- GET /jobs/{job_id}/wait

### 3.2 Execution constraints
- Chi admin duoc goi cac endpoint vector ops.
- Index tai lieu thuong duoc enqueue qua background job `index_document` khi:
  - Upload file moi.
  - Upload version moi.
  - Attach/session document chua index can dung cho chat.
  - Approve SQP lam thay doi scope/access cua document.
- Sua filename hoac tag khong re-index.
- Tag khong duoc dua vao vector metadata hien tai; tag la relational metadata trong DB.
- Clear la thao tac destructive, frontend phai co confirm ro rang truoc khi goi.

### 3.3 Reindex behavior
- /admin/vector/reindex dung cho admin dong bo lai vector store.
- Code hien tai clear ChromaDB truoc, sau do lay `DocumentRepository.list_unindexed()`.
- Chi document PDF trong danh sach chua indexed duoc process bang ChromaDBManager va dat `is_indexed = true`.
- `documents.is_indexed` phan anh trang thai noi dung trong vector store, khong phan anh tag.
- /admin/vector/clear xoa vector DB, du lieu RAG lien quan, chat/job va file upload theo maintenance service.

### 3.4 Planned improvements
- Reindex theo scope, department hoac doc_id thay vi full operation.
- Lock tranh chay 2 reindex song song.
- Retry policy neu embedding/IO bi loi.
- Index status chi tiet hon: pending/indexed/failed theo latest background job.

## 4. Acceptance Criteria
- AC-VEC-01:
  - Given admin token hop le
  - When goi GET /admin/vector/status
  - Then tra total_vectors va persist_dir.
- AC-VEC-02:
  - Given co document active can index
  - When goi POST /admin/vector/reindex
  - Then vector store duoc dong bo theo workflow hien tai.
- AC-VEC-03:
  - Given admin token
  - When goi POST /admin/vector/clear
  - Then vector DB va du lieu lien quan duoc clear theo maintenance service.
- AC-VEC-04:
  - Given non-admin token
  - When goi /admin/vector/*
  - Then tra HTTP 403.
- AC-VEC-05:
  - Given user doi tag cua document
  - When update thanh cong
  - Then khong co job index moi chi vi tag thay doi.

## 5. Implementation Notes
- Router:
  - backend/routers/admin.py
  - backend/routers/jobs.py
- Services:
  - backend/services/admin/vector_service.py
  - backend/services/admin/maintenance_service.py
  - backend/services/jobs/*
- RAG manager:
  - backend/rag_engine/chroma_manager.py
