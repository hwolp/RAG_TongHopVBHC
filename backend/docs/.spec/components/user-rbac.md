# Component Spec: User and RBAC

## 1. Scope
Phu trach cac chuc nang:
- FUNC-USER-01: Xem danh sach user + tim kiem.
- FUNC-USER-02: Them moi tai khoan.
- FUNC-USER-03: Chinh sua thong tin tai khoan.
- FUNC-USER-04: Khoa / mo khoa / xoa tai khoan.
- FUNC-ROLE-01: Xem danh sach nhom quyen.
- FUNC-ROLE-02: Them / sua / xoa nhom quyen.

## 2. Requirements (User stories)
- US-USER-01: La admin, toi muon xem danh sach user theo search de quan tri nhanh.
- US-USER-02: La admin, toi muon tao user moi voi role va department.
- US-USER-03: La admin, toi muon cap nhat ho ten, role, department cua user.
- US-USER-04: La admin, toi muon khoa/mo khoa user de kiem soat truy cap.
- US-USER-05: La admin, toi muon xoa mem user theo quy tac an toan du lieu.
- US-ROLE-01: La admin, toi muon quan ly role group va permission matrix.

## 3. Technical Constraints
### 3.1 Existing API endpoints
- GET /admin/users?search=
- POST /admin/users
- PUT /admin/users/{user_id}
- POST /admin/users/{user_id}/lock
- DELETE /admin/users/{user_id}

### 3.2 Planned API endpoints for role groups
- GET /admin/role-groups
- POST /admin/role-groups
- PUT /admin/role-groups/{group_id}
- DELETE /admin/role-groups/{group_id}
- PUT /admin/users/{user_id}/role-group

### 3.3 Data constraints
- RoleEnum hien tai: admin | manager | employee.
- users.username unique.
- users.department_id co the nullable, nhung neu role = manager thi nen co department.
- users.role_group_id nullable, se mandatory sau khi role group complete.

### 3.4 Security constraints
- Tat ca endpoint tren bat buoc require_admin.
- Khong cho admin xoa chinh minh neu la admin cuoi cung.
- Khong cho xoa user neu user so huu tai lieu quan trong, tra ve warning/business error.

## 4. Acceptance Criteria
- AC-UR-01:
  - Given token admin hop le
  - When goi GET /admin/users
  - Then tra danh sach user co id, username, full_name, role, department, is_locked.
- AC-UR-02:
  - Given payload tao user hop le
  - When goi POST /admin/users
  - Then tra status success va user moi ton tai trong DB.
- AC-UR-03:
  - Given user da ton tai
  - When goi PUT /admin/users/{id}
  - Then field full_name/role/department duoc cap nhat.
- AC-UR-04:
  - Given admin lock user
  - When goi POST /admin/users/{id}/lock
  - Then is_locked dao trang thai.
- AC-UR-05:
  - Given non-admin token
  - When goi endpoint /admin/users/*
  - Then tra HTTP 403.
- AC-UR-06:
  - Given role-group API duoc implement
  - When tao role group voi permissions
  - Then co the gan role_group_id vao user va enforce duoc permission.

## 5. Implementation Notes
- File ownership:
  - Router: backend/routers/users.py
  - Service: backend/services/user_service.py
  - Model: backend/database/models.py (User, RoleGroup)
- Testing uu tien:
  - role boundary tests
  - duplicate username test
  - lock account login denial test
