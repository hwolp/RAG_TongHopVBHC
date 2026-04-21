# Component Spec: Document Lifecycle

## 1. Scope
Phu trach cac chuc nang:
- FUNC-DOC-PRI-01..05: Tai lieu ca nhan.
- FUNC-DOC-DEPT-01..02: Tai lieu phong ban.
- FUNC-TAG-01..03: Quan ly tags.

## 2. Requirements (User stories)
- US-DOC-01: Nhan vien xem, tim kiem, upload, download tai lieu ca nhan.
- US-DOC-02: Truong phong upload/xoa tai lieu phong ban, nhan vien cung phong co the xem.
- US-DOC-03: Nguoi dung gan tag vao tai lieu va tim theo tag.
- US-DOC-04: Nhan vien cap nhat version tai lieu va xem lich su version.
- US-DOC-05: Xoa tai lieu vao thung rac va co the khoi phuc trong 30 ngay.

## 3. Technical Constraints
### 3.1 Existing canonical API endpoints
- GET /documents/tree
- GET /documents/personal
- POST /documents/personal
- DELETE /documents/personal/{doc_id}
- GET /documents/department
- POST /documents/department
- DELETE /documents/department/{doc_id}
- GET /documents/{doc_id}/download
- GET /tags
- POST /tags
- PUT /tags/{tag_id}
- DELETE /tags/{tag_id}
- POST /documents/{doc_id}/tags/{tag_id}

### 3.2 Existing legacy compatibility endpoints
- /employee/documents*
- /manager/department/documents*
- /employee/department/documents

### 3.3 Planned API endpoints
- GET /documents/{doc_id}/preview
- GET /documents/{doc_id}/versions
- POST /documents/{doc_id}/versions
- GET /documents/trash
- POST /documents/{doc_id}/restore

### 3.4 Data constraints
- ScopeEnum cho documents: personal | department | sqp.
- personal doc bat buoc owner_id.
- department doc bat buoc department_id.
- upload tao is_indexed false truoc, sau do process index.
- Tag name unique toan he thong.

### 3.5 Authorization constraints
- Upload department/doc delete department bat buoc manager.
- Download chi hop le neu user co quyen owner/dept/share/sqp.
- Attach tag can check user co quyen truy cap document.

## 4. Acceptance Criteria
- AC-DOC-01:
  - Given employee token
  - When goi POST /documents/personal
  - Then tao document moi scope personal va co the list lai.
- AC-DOC-02:
  - Given manager token
  - When goi POST /documents/department
  - Then tao document scope department cua phong manager.
- AC-DOC-03:
  - Given employee token khong phai manager
  - When goi POST /documents/department
  - Then tra HTTP 403.
- AC-DOC-04:
  - Given doc co quyen truy cap
  - When goi GET /documents/{doc_id}/download
  - Then tra file hop le.
- AC-DOC-05:
  - Given tag da ton tai
  - When goi POST /documents/{doc_id}/tags/{tag_id}
  - Then tao lien ket trong document_tags.
- AC-DOC-06:
  - Given versioning API duoc implement
  - When upload version moi
  - Then version_number tang va version cu duoc giu lai.
- AC-DOC-07:
  - Given soft delete API duoc implement
  - When xoa tai lieu
  - Then tai lieu vao trash va co the restore truoc 30 ngay.

## 5. Implementation Notes
- Router lien quan:
  - backend/routers/documents.py
  - backend/routers/tags.py
- Service lien quan:
  - backend/services/document_service.py
  - backend/services/tag_service.py
  - backend/services/folder_service.py
- Can bo sung migration cho deleted_at/version fields truoc khi mo feature UI.
