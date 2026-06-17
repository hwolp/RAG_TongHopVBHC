# Component Spec: Sharing, Delegation, and Proposal

## 1. Scope
Phu trach cac chuc nang:
- FUNC-SHARE-01: Chia se tai lieu lien phong.
- FUNC-SHARE-02: Chia se tai lieu den user cu the.
- FUNC-SHARE-03: Thu hoi quyen chia se.
- FUNC-DELEGATE-01..03: Quan ly uy quyen dong gop.
- FUNC-PROPOSE-01..03: De xuat tai lieu len kho SQP/kho chung.

## 2. Requirements (User stories)
- US-SDP-01: Truong phong chia se tai lieu phong ban cho phong khac.
- US-SDP-02: Truong phong chia se tai lieu phong ban cho mot user cu the.
- US-SDP-03: Truong phong thu hoi quyen truy cap da cap.
- US-SDP-04: Truong phong uy quyen nhan vien dong gop tai lieu.
- US-SDP-05: Truong phong hoac nguoi co quyen de xuat tai lieu len SQP.
- US-SDP-06: Admin phe duyet hoac tu choi de xuat SQP.
- US-SDP-07: Admin co the xem va thu hoi tat ca share.

## 3. Technical Constraints
### 3.1 Existing manager endpoints
- GET /manager/sqp/proposals
- POST /manager/sqp/propose/{document_id}
- DELETE /manager/sqp/proposals/{proposal_id}
- GET /manager/departments
- POST /manager/share/document/{doc_id}/to-dept/{dept_id}
- POST /manager/share/document/{doc_id}/to-user/{username}
- DELETE /manager/share/{share_id}
- GET /manager/shares
- GET /manager/contributors
- POST /manager/contributors/{user_id}
- DELETE /manager/contributors/{contrib_id}
- POST /manager/department/documents/{doc_id}/index

### 3.2 Existing admin endpoints
- GET /admin/sqp/proposals
- POST /admin/sqp/approve/{proposal_id}
- POST /admin/sqp/reject/{proposal_id}
- GET /admin/shares
- POST /admin/documents/{doc_id}/share/department/{dept_id}
- POST /admin/documents/{doc_id}/share/user
- DELETE /admin/shares/{share_id}

### 3.3 Data constraints
- shared_documents ho tro share theo department qua `shared_with_dept_id`.
- shared_documents ho tro share theo user qua `shared_with_user_id`.
- contributors lien ket user duoc uy quyen voi manager grant va department.
- sqp_proposals status: pending | approved | rejected.

### 3.4 Authorization constraints
- Endpoint share/contributor manager dung require_manager_only.
- Endpoint proposal manager dung require_manager.
- Endpoint /admin/sqp/* va /admin/shares* bat buoc admin.
- Manager chi duoc share/de xuat tai lieu thuoc department cua minh.
- Employee chi thay tai lieu phong ban khi co share hoac co quyen department theo workflow.

## 4. Workflow
### 4.1 Share document
1. Manager chon department document thuoc phong ban minh.
2. Manager share den department hoac username.
3. Service tao row `shared_documents`.
4. Nguoi nhan thay tai lieu qua list shared/folder tree/chat document tree.
5. Revoke share xoa row, khong doi document va khong re-index.

### 4.2 Propose to SQP
1. Manager goi POST /manager/sqp/propose/{document_id}.
2. Service tao SQPProposal pending.
3. Admin approve hoac reject.
4. Khi approve, document chuyen sang scope=sqp, duoc dat can index lai va enqueue index job vi scope truy cap thay doi.
5. Khi reject, proposal doi status rejected, document khong doi scope.

### 4.3 Contributor delegation
1. Manager them contributor trong phong ban.
2. Contributor duoc ghi nhan trong bang contributors.
3. Workflow hien tai chu yeu phuc vu hien thi/phan quyen mo rong; moi endpoint can check service cu the truoc khi mo them UI.

## 5. Acceptance Criteria
- AC-SDP-01:
  - Given manager token va doc hop le
  - When goi POST /manager/share/document/{doc_id}/to-dept/{dept_id}
  - Then tao share record va phong duoc share co the thay doc.
- AC-SDP-02:
  - Given manager token va username hop le
  - When goi POST /manager/share/document/{doc_id}/to-user/{username}
  - Then tao share record user-level.
- AC-SDP-03:
  - Given manager token
  - When goi DELETE /manager/share/{share_id}
  - Then share record bi xoa va khong re-index document.
- AC-SDP-04:
  - Given manager token
  - When goi POST /manager/contributors/{user_id}
  - Then tao contributor record.
- AC-SDP-05:
  - Given manager hop le
  - When goi POST /manager/sqp/propose/{document_id}
  - Then tao proposal status pending.
- AC-SDP-06:
  - Given admin token
  - When goi POST /admin/sqp/approve/{proposal_id}
  - Then proposal status approved, document scope=sqp va enqueue index job.
- AC-SDP-07:
  - Given non-manager/non-admin token
  - When goi endpoint quan tri tuong ung
  - Then tra HTTP 403.

## 6. Implementation Notes
- Router lien quan:
  - backend/routers/manager.py
  - backend/routers/admin.py
- Service lien quan:
  - backend/services/sharing/share_service.py
  - backend/services/sharing/sqp_service.py
- Model lien quan:
  - backend/database/models.py (SharedDocument, Contributor, SQPProposal)
