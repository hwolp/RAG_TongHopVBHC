# Component Spec: Vector Operations

## 1. Scope
Phu trach cac chuc nang:
- FUNC-VEC-01: Xem trang thai du lieu vector.
- FUNC-VEC-02: Re-index du lieu vector.
- FUNC-VEC-03: Xoa collection vector de bao tri.

## 2. Requirements (User stories)
- US-VEC-01: La admin, toi muon xem tong so vectors va thong tin luu tru.
- US-VEC-02: La admin, toi muon chay reindex de dong bo vector sau khi cap nhat tai lieu.
- US-VEC-03: La admin, toi muon clear vector DB co canh bao de khoi phuc index lai.

## 3. Technical Constraints
### 3.1 Existing API endpoints
- GET /admin/vector/status
- POST /admin/vector/reindex
- POST /admin/vector/clear

### 3.2 Execution constraints
- Chi admin duoc goi cac endpoint vector ops.
- Reindex hien tai:
  - clear vector DB truoc
  - query Document.is_indexed == false
  - index lai cac file PDF
- Clear la thao tac destructive, can xac nhan o frontend truoc khi goi.

### 3.3 Planned improvements
- Reindex theo scope hoac theo department thay vi full clear.
- Theo doi progress/background job id de monitor tien trinh.
- Luu thong tin index status theo document (pending/indexed/failed).

## 4. Acceptance Criteria
- AC-VEC-01:
  - Given admin token hop le
  - When goi GET /admin/vector/status
  - Then tra total_vectors va persist_dir.
- AC-VEC-02:
  - Given co document chua index
  - When goi POST /admin/vector/reindex
  - Then tra status success va so chunks > 0 (neu co PDF).
- AC-VEC-03:
  - Given admin token
  - When goi POST /admin/vector/clear
  - Then vector DB duoc xoa va endpoint tra success.
- AC-VEC-04:
  - Given non-admin token
  - When goi /admin/vector/*
  - Then tra HTTP 403.

## 5. Implementation Notes
- Router: backend/routers/admin.py
- RAG manager: backend/rag_engine/chroma_manager.py
- Future hardening:
  - idempotent jobs
  - lock tranh chay 2 reindex song song
  - retry policy neu embedding/IO bi loi
