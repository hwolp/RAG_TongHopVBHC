# Component Spec: System Config and SQP/Public Documents

## 1. Scope
Phu trach cac chuc nang:
- FUNC-CFG-01: Xem danh sach cau hinh metadata.
- FUNC-CFG-02: Them / sua / xoa cau hinh metadata.
- FUNC-TAG-01: Quan ly tag dung chung toan he thong.
- FUNC-SQP-01: Xem danh sach tai lieu SQP/kho chung.
- FUNC-SQP-02: Admin tai len tai lieu SQP.
- FUNC-SQP-03: Admin sua thong tin/tag/xoa tai lieu SQP.
- FUNC-DEPT-ADMIN-01: Admin quan ly tai lieu phong ban.

## 2. Requirements (User stories)
- US-CFG-01: La admin, toi muon quan ly metadata he thong (key/value/type).
- US-CFG-02: La admin, toi muon quan ly tag dung chung cho toan he thong.
- US-SQP-01: La nguoi dung, toi muon tra cuu tai lieu SQP/kho chung.
- US-SQP-02: La admin, toi muon upload, doi ten, gan tag va xoa tai lieu SQP.
- US-DEPT-ADMIN-01: La admin, toi muon upload va cap nhat tai lieu phong ban bat ky.

## 3. Technical Constraints
### 3.1 Existing config endpoints
- GET /admin/configs
- POST /admin/configs
- PUT /admin/configs/{config_id}
- DELETE /admin/configs/{config_id}

### 3.2 Existing tag endpoints
- GET /tags
- POST /tags
- PUT /tags/{tag_id}
- DELETE /tags/{tag_id}
- Legacy admin aliases:
  - GET /admin/tags
  - POST /admin/tags
  - PUT /admin/tags/{tag_id}
  - DELETE /admin/tags/{tag_id}

### 3.3 Existing SQP/public endpoints
- GET /documents/sqp
- GET /documents/company
- GET /documents/sqp/{doc_id}
- GET /documents/{doc_id}/download
- GET /admin/sqp/documents
- POST /documents/sqp
- PUT /documents/sqp/{doc_id}
- DELETE /documents/sqp/{doc_id}

### 3.4 Existing admin department document endpoints
- GET /admin/documents/department
- POST /admin/documents/department/upload
- PUT /admin/documents/department/{doc_id}
- DELETE /admin/documents/department/{doc_id}

### 3.5 Data constraints
- ConfigItem:
  - key: string
  - value: string
  - type: string, default metadata
- Tags:
  - name unique toan he thong.
  - Tag assignment luu bang `document_tags`.
  - Tag khong anh huong truc tiep den vector index.
- SQP/public docs dung `documents.scope = sqp`.
- Endpoint `/documents/company` la alias browse cho SQP/public docs hien tai.
- Khong ton tai workflow `/admin/company/documents*`; admin quan ly SQP bang `/documents/sqp*`.

### 3.6 Operational constraints
- Sua tag cua document chi cap nhat DB relational metadata, khong re-index.
- Xoa tag global can tranh lam mat lien ket khong mong muon; service hien tai xoa tag va cascade theo DB neu duoc cau hinh.
- Xoa SQP document can xoa file/record theo service hien tai va dam bao vector data khong duoc frontend tin la con active.
- Neu approve SQP tu proposal thi document doi scope sang sqp va can index lai vi access scope thay doi.

## 4. Acceptance Criteria
- AC-CP-01:
  - Given admin login
  - When goi GET /admin/configs
  - Then tra danh sach metadata.
- AC-CP-02:
  - Given payload metadata hop le
  - When goi POST /admin/configs
  - Then metadata moi duoc tao va co the list lai.
- AC-CP-03:
  - Given admin upload file SQP kem tag_ids
  - When goi POST /documents/sqp
  - Then tao record document scope=sqp, tao document_tags va enqueue index neu file ho tro.
- AC-CP-04:
  - Given admin sua tai lieu SQP
  - When goi PUT /documents/sqp/{id} voi filename/tag_ids
  - Then cap nhat metadata/document_tags va khong re-index.
- AC-CP-05:
  - Given admin upload tai lieu phong ban
  - When goi POST /admin/documents/department/upload?department_id=...
  - Then tao tai lieu scope=department cho phong ban duoc chon.
- AC-CP-06:
  - Given non-admin token
  - When goi endpoint /admin/configs, /documents/sqp mutating endpoint hoac /admin/documents/department
  - Then tra HTTP 403.

## 5. Implementation Notes
- Router lien quan:
  - backend/routers/admin.py
  - backend/routers/tags.py
  - backend/routers/documents.py
- Service lien quan:
  - backend/services/admin/config_service.py
  - backend/services/documents/document_service.py
  - backend/services/documents/tag_service.py
