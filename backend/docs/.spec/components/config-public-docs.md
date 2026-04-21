# Component Spec: System Config and Public Documents

## 1. Scope
Phu trach cac chuc nang:
- FUNC-CFG-01: Xem danh sach cau hinh (metadata, tag dung chung).
- FUNC-CFG-02: Them / sua / xoa cau hinh.
- FUNC-PUB-01: Xem danh sach tai lieu cong ty.
- FUNC-PUB-02: Tai len tai lieu cong ty.
- FUNC-PUB-03: Sua thong tin / xoa tai lieu cong ty.

## 2. Requirements (User stories)
- US-CFG-01: La admin, toi muon quan ly metadata (loai van ban, linh vuc, trang thai).
- US-CFG-02: La admin, toi muon quan ly tag dung chung cho toan he thong.
- US-PUB-01: La admin, toi muon upload va cap nhat tai lieu cong ty.
- US-PUB-02: La admin, toi muon xoa mem tai lieu cong ty va dong bo vector index.

## 3. Technical Constraints
### 3.1 Existing API endpoints
- GET /documents/company
- GET /documents/sqp
- GET /documents/sqp/{doc_id}
- GET /admin/sqp/documents
- CRUD tags:
  - GET /tags
  - POST /tags
  - PUT /tags/{tag_id}
  - DELETE /tags/{tag_id}

### 3.2 Planned API endpoints
- GET /admin/configs
- POST /admin/configs
- PUT /admin/configs/{config_id}
- DELETE /admin/configs/{config_id}
- POST /admin/company/documents
- PUT /admin/company/documents/{doc_id}
- DELETE /admin/company/documents/{doc_id}

### 3.3 Data constraints
- Metadata nen co cau truc:
  - key: string unique
  - value: string
  - type: enum (document_type, domain, status, security_level)
- Public/company docs su dung scope = sqp hoac scope public moi (neu mo rong).
- Delete company doc la soft delete (deleted_at), khong hard delete ngay.

### 3.4 Operational constraints
- Moi update metadata dang duoc tham chieu boi tai lieu phai co check rang buoc.
- Moi xoa tai lieu cong ty phai co buoc xoa/revoke vector records lien quan.

## 4. Acceptance Criteria
- AC-CP-01:
  - Given admin login
  - When goi GET /admin/configs
  - Then tra danh sach metadata va tags dung chung.
- AC-CP-02:
  - Given payload metadata hop le
  - When goi POST /admin/configs
  - Then metadata moi duoc tao va co the dung cho tai lieu.
- AC-CP-03:
  - Given admin upload file cong ty
  - When goi POST /admin/company/documents
  - Then tao record document + enqueue/index vector.
- AC-CP-04:
  - Given admin xoa document cong ty
  - When goi DELETE /admin/company/documents/{id}
  - Then document o trang thai deleted va vector chunks bi xoa.
- AC-CP-05:
  - Given non-admin token
  - When goi endpoint /admin/configs hoac /admin/company/documents
  - Then tra HTTP 403.

## 5. Implementation Notes
- Router lien quan:
  - backend/routers/admin.py
  - backend/routers/tags.py
  - backend/routers/documents.py
- Service lien quan:
  - backend/services/document_service.py
  - backend/services/tag_service.py
- Nen tao them config_service + model ConfigItem cho metadata.
