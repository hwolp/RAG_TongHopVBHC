# Component Spec: Sharing, Delegation, and Proposal

## 1. Scope
Phu trach cac chuc nang:
- FUNC-SHARE-01: Chia se tai lieu lien phong.
- FUNC-SHARE-02: Thu hoi quyen chia se.
- FUNC-DELEGATE-01..03: Quan ly uy quyen dong gop.
- FUNC-PROPOSE-01..03: De xuat tai lieu len kho cong ty.

## 2. Requirements (User stories)
- US-SDP-01: Truong phong chia se tai lieu cho phong khac.
- US-SDP-02: Truong phong thu hoi quyen truy cap da cap.
- US-SDP-03: Truong phong uy quyen nhan vien dong gop tai lieu.
- US-SDP-04: Truong phong hoac nguoi duoc uy quyen de xuat tai lieu len SQP.
- US-SDP-05: Admin phe duyet hoac tu choi de xuat.

## 3. Technical Constraints
### 3.1 Existing API endpoints
- Manager side:
  - GET /manager/sqp/proposals
  - POST /manager/sqp/propose/{document_id}
  - DELETE /manager/sqp/proposals/{proposal_id}
  - POST /manager/share/document/{doc_id}/to-dept/{dept_id}
  - DELETE /manager/share/{share_id}
  - GET /manager/contributors
  - POST /manager/contributors/{user_id}
  - DELETE /manager/contributors/{contrib_id}
- Admin side:
  - GET /admin/sqp/proposals
  - POST /admin/sqp/approve/{proposal_id}
  - POST /admin/sqp/reject/{proposal_id}

### 3.2 Data constraints
- shared_documents hien tai chia theo department (shared_with_dept_id).
- contributors lien ket user duoc uy quyen voi manager grant.
- sqp_proposals status: pending | approved | rejected.

### 3.3 Planned constraints
- Bo sung share theo user-level voi permission view/view-download.
- Bo sung ly do de xuat va ly do tu choi.
- Bo sung audit trail cho revoke/approve/reject.

### 3.4 Authorization constraints
- Endpoint /manager/* bat buoc manager role.
- Endpoint /admin/sqp/* bat buoc admin role.
- Manager chi duoc share/de xuat tai lieu thuoc department cua minh.

## 4. Acceptance Criteria
- AC-SDP-01:
  - Given manager token va doc hop le
  - When goi POST /manager/share/document/{doc_id}/to-dept/{dept_id}
  - Then tao share record va phong duoc share co the thay doc.
- AC-SDP-02:
  - Given manager token
  - When goi DELETE /manager/share/{share_id}
  - Then share record bi xoa.
- AC-SDP-03:
  - Given manager token
  - When goi POST /manager/contributors/{user_id}
  - Then tao contributor record.
- AC-SDP-04:
  - Given manager hoac contributor hop le
  - When goi POST /manager/sqp/propose/{document_id}
  - Then tao proposal status pending.
- AC-SDP-05:
  - Given admin token
  - When goi POST /admin/sqp/approve/{proposal_id}
  - Then proposal status approved va document scope cap nhat theo quy tac.
- AC-SDP-06:
  - Given non-manager/non-admin token
  - When goi endpoint quan tri tuong ung
  - Then tra HTTP 403.

## 5. Implementation Notes
- Router lien quan:
  - backend/routers/manager.py
  - backend/routers/admin.py
- Service lien quan:
  - backend/services/share_service.py
  - backend/services/sqp_service.py
- Model lien quan:
  - backend/database/models.py (SharedDocument, Contributor, SQPProposal)
