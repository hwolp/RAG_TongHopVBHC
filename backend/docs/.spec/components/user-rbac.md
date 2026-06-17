# Component Spec: User and RBAC

## 1. Scope
Phu trach cac chuc nang:
- FUNC-USER-01: Xem danh sach user + tim kiem.
- FUNC-USER-02: Them moi tai khoan.
- FUNC-USER-03: Chinh sua thong tin tai khoan.
- FUNC-USER-04: Khoa / mo khoa / xoa tai khoan.
- FUNC-DEPT-01: Quan ly phong ban.
- FUNC-ROLE-01: Xem/tao nhom quyen.
- FUNC-ROLE-02: Gan nhom quyen cho user.

## 2. Requirements (User stories)
- US-USER-01: La admin, toi muon xem danh sach user theo search de quan tri nhanh.
- US-USER-02: La admin, toi muon tao user moi voi role va department.
- US-USER-03: La admin, toi muon cap nhat ho ten, role, department va password cua user.
- US-USER-04: La admin, toi muon khoa/mo khoa user de kiem soat truy cap.
- US-USER-05: La admin, toi muon xoa user theo workflow hien tai.
- US-DEPT-01: La admin, toi muon tao/sua/xoa phong ban.
- US-ROLE-01: La admin, toi muon tao role group va gan role_group_id cho user.

## 3. Technical Constraints
### 3.1 Existing user endpoints
- GET /admin/users?search=
- POST /admin/users
- PUT /admin/users/{user_id}
- POST /admin/users/{user_id}/lock
- DELETE /admin/users/{user_id}

### 3.2 Existing department endpoints
- GET /admin/departments
- POST /admin/departments
- PUT /admin/departments/{department_id}
- DELETE /admin/departments/{department_id}
- GET /manager/departments

### 3.3 Existing role group endpoints
- GET /admin/role-groups
- POST /admin/role-groups
- PUT /admin/users/{user_id}/role-group

### 3.4 Data constraints
- RoleEnum hien tai: admin | manager | employee.
- users.username unique.
- users.department_id co the nullable, nhung role manager/employee nen co department khi dung workflow phong ban.
- users.role_group_id nullable.
- RoleGroup hien tai gom `name` va `description`; chua co permission matrix chi tiet.

### 3.5 Security constraints
- Tat ca endpoint /admin/users*, /admin/departments*, /admin/role-groups* bat buoc require_admin.
- /manager/departments bat buoc require_manager_only.
- User bi `is_locked = true` khong duoc login.
- Khong expose hashed_password trong response.

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
  - Then field full_name/role/department/password duoc cap nhat theo payload.
- AC-UR-04:
  - Given admin lock user
  - When goi POST /admin/users/{id}/lock
  - Then is_locked dao trang thai.
- AC-UR-05:
  - Given admin tao role group
  - When goi POST /admin/role-groups
  - Then role group moi co the list lai.
- AC-UR-06:
  - Given user va role group ton tai
  - When goi PUT /admin/users/{user_id}/role-group
  - Then user.role_group_id duoc cap nhat.
- AC-UR-07:
  - Given non-admin token
  - When goi endpoint /admin/users/*
  - Then tra HTTP 403.

## 5. Implementation Notes
- File ownership:
  - Router: backend/routers/users.py, backend/routers/admin.py, backend/routers/manager.py
  - Service: backend/services/admin/user_service.py, backend/services/admin/directory_service.py
  - Model: backend/database/models.py (User, Department, RoleGroup)
- Testing uu tien:
  - role boundary tests
  - duplicate username test
  - lock account login denial test
  - role_group assignment test
