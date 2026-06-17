# Component Spec: Document Lifecycle

## 1. Scope
Phu trach cac chuc nang:
- FUNC-DOC-PRI-01..05: Tai lieu ca nhan.
- FUNC-DOC-DEPT-01..03: Tai lieu phong ban.
- FUNC-DOC-SQP-01..03: Tai lieu SQP/kho chung.
- FUNC-TAG-01..03: Quan ly tags va lien ket tag voi tai lieu.
- FUNC-DOC-VER-01..02: Version va trash.

## 2. Requirements (User stories)
- US-DOC-01: Nhan vien xem, tim kiem, upload, download, doi ten va gan tag tai lieu ca nhan.
- US-DOC-02: Truong phong upload/xoa/sua ten/sua tag tai lieu phong ban minh quan ly.
- US-DOC-03: Admin upload/sua/xoa tai lieu phong ban bat ky va co the doi phong ban cua tai lieu.
- US-DOC-04: Admin upload/sua/xoa tai lieu SQP.
- US-DOC-05: Nguoi dung cap nhat version tai lieu va xem lich su version.
- US-DOC-06: Nguoi dung xoa tai lieu ca nhan vao trash va co the khoi phuc.
- US-DOC-07: Folder tree tra ve tai lieu ca nhan, phong ban, chia se va SQP kem tags de frontend hien thi.

## 3. Technical Constraints
### 3.1 Canonical API endpoints
- GET /documents/tree
- GET /documents/personal
- POST /documents/personal
- PUT /documents/personal/{doc_id}
- DELETE /documents/personal/{doc_id}
- GET /documents/department
- POST /documents/department
- PUT /documents/department/{doc_id}
- DELETE /documents/department/{doc_id}
- GET /documents/shared
- GET /documents/company
- GET /documents/sqp
- POST /documents/sqp
- GET /documents/sqp/{doc_id}
- PUT /documents/sqp/{doc_id}
- DELETE /documents/sqp/{doc_id}
- GET /documents/{doc_id}
- GET /documents/{doc_id}/download
- GET /documents/{doc_id}/versions
- POST /documents/{doc_id}/versions
- GET /documents/trash
- POST /documents/{doc_id}/restore

### 3.2 Admin document endpoints
- GET /admin/documents/department
- POST /admin/documents/department/upload
- PUT /admin/documents/department/{doc_id}
- DELETE /admin/documents/department/{doc_id}
- GET /admin/sqp/documents

### 3.3 Tag endpoints
- GET /tags: any authenticated user.
- POST /tags: admin.
- PUT /tags/{tag_id}: admin.
- DELETE /tags/{tag_id}: admin.
- POST /documents/{doc_id}/tags/{tag_id}: legacy single-tag attach.
- Legacy aliases:
  - GET/POST /employee/tags
  - GET/POST/PUT/DELETE /admin/tags*
  - POST /employee/documents/{doc_id}/tag/{tag_id}

### 3.4 Legacy compatibility endpoints
- /employee/documents*
- /employee/department/documents
- /employee/sqp*
- /employee/company
- /employee/shared
- /manager/department/documents*

### 3.5 Upload and update payload
- Upload personal/department/SQP:
  - multipart `file`: UploadFile, required.
  - multipart `tag_ids`: repeated int, optional.
- Update personal/department/SQP:
  - JSON `filename`: optional string.
  - JSON `tag_ids`: optional list[int].
- Admin update department document:
  - JSON `filename`: optional string.
  - JSON `department_id`: optional int.
  - JSON `tag_ids`: optional list[int].

### 3.6 Data constraints
- ScopeEnum cho documents: personal | department | sqp.
- personal doc bat buoc owner_id.
- department doc bat buoc department_id.
- SQP doc dung scope = sqp.
- Chat-session upload la personal document co `chat_session_id`.
- Upload tao Document truoc, attach tags neu co, sau do enqueue background job `index_document` neu file ho tro.
- Tag name unique toan he thong.
- Tag chi ton tai trong `document_tags`; tag khong duoc day vao vector metadata va khong lam doi ket qua index truc tiep.
- Sua ten file hoac sua tag khong tao background index job moi.
- Tai version moi thay doi noi dung file, dat `is_indexed = false` va enqueue index job.

### 3.7 Authorization constraints
- Personal update/delete: owner hoac admin.
- Department update/delete:
  - Manager chi duoc sua tai lieu thuoc phong ban minh.
  - Admin duoc sua/xoa tai lieu phong ban bat ky qua /admin/documents/department/*.
- SQP upload/update/delete: admin.
- Download/detail chi hop le neu user co quyen owner/dept/share/sqp/admin.
- Attach tag legacy can check user co quyen truy cap document.

## 4. Workflow
### 4.1 Upload document
1. Frontend gui multipart `file` va `tag_ids`.
2. Service validate quyen, scope, department va tag ton tai.
3. Service luu file vao storage theo scope.
4. Tao Document va cac row `document_tags`.
5. Tao background job index neu dinh dang file ho tro.
6. Response tra ve document metadata kem tags va job_id/index_status neu co.

### 4.2 Update document metadata
1. Frontend gui JSON `filename` va/hoac `tag_ids`.
2. Service validate quyen cap nhat.
3. Neu co filename thi cap nhat `documents.filename`.
4. Neu co tag_ids thi replace lien ket trong `document_tags`.
5. Khong goi ChromaDB, khong xoa chunks, khong enqueue index job.

### 4.3 Upload new version
1. User upload file moi cho document co quyen.
2. Service luu version cu vao `document_versions`.
3. Cap nhat file_path/filename/version_number cua document.
4. Dat `is_indexed = false`.
5. Enqueue `index_document`.

## 5. Acceptance Criteria
- AC-DOC-01:
  - Given employee token
  - When goi POST /documents/personal kem tag_ids hop le
  - Then tao document scope personal, tao rows document_tags va enqueue index job neu file ho tro.
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
  - Given doc co quyen cap nhat va tag da ton tai
  - When goi PUT /documents/personal/{doc_id} voi tag_ids moi
  - Then document_tags duoc replace va khong co index job moi.
- AC-DOC-06:
  - Given manager cua phong ban
  - When goi PUT /documents/department/{doc_id}
  - Then filename/tag cua tai lieu phong ban duoc cap nhat.
- AC-DOC-07:
  - Given admin
  - When goi PUT /admin/documents/department/{doc_id}
  - Then co the doi filename, department_id va tag_ids.
- AC-DOC-08:
  - Given admin
  - When goi PUT /documents/sqp/{doc_id}
  - Then co the doi filename va tag_ids cua tai lieu SQP.
- AC-DOC-09:
  - Given doc co quyen truy cap
  - When upload version moi
  - Then version_number tang, version cu duoc giu lai, document can index lai.
- AC-DOC-10:
  - Given personal doc
  - When xoa tai lieu
  - Then document vao trash va co the restore.

## 6. Implementation Notes
- Router lien quan:
  - backend/routers/documents.py
  - backend/routers/tags.py
  - backend/routers/admin.py
  - backend/routers/chat.py
- Service lien quan:
  - backend/services/documents/document_service.py
  - backend/services/documents/tag_service.py
  - backend/services/documents/folder_service.py
  - backend/services/jobs/job_service.py
- Neu can search theo tag trong UI, query SQL qua `document_tags`; khong dua tag vao vector index.
