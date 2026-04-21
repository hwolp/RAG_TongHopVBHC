# Component Spec: Auth Flow

## 1. Scope
Phu trach cac chuc nang:
- FUNC-AUTH-01: Dang nhap he thong.
- FUNC-AUTH-02: Dang xuat he thong.

## 2. Requirements (User stories)
- US-AUTH-01: La nguoi dung hop le, toi muon dang nhap de nhan token va vao he thong.
- US-AUTH-02: La nguoi dung bi khoa, toi khong duoc phep dang nhap.
- US-AUTH-03: La nguoi dung da dang nhap, toi muon dang xuat de ket thuc phien lam viec.

## 3. Technical Constraints
### 3.1 API endpoints
- POST /auth/login
  - Body:
    - username: string (required)
    - password: string (required)
  - Success 200:
    - access_token: string
    - token_type: "bearer"
    - role: "admin" | "manager" | "employee"
    - username: string
  - Error:
    - 401: sai username/password
    - 403: tai khoan bi khoa

### 3.2 Auth runtime rules
- Token phai la JWT va chua claims toi thieu: sub, role, id.
- Endpoint duoc bao ve phai dung middleware get_current_user/require_admin/require_manager.
- Dang xuat hien tai chu yeu xoa token phia client; neu implement server-side revoke can co blacklist/session table.

### 3.3 Files ownership
- Router: backend/routers/auth.py
- Service: backend/services/auth_service.py
- Middleware gate: backend/middleware/auth_middleware.py

## 4. Data Constraints
- User.role su dung enum RoleEnum.
- User.is_locked = true thi login bi chan (403).

## 5. Acceptance Criteria
- AC-AUTH-01:
  - Given user ton tai va dung mat khau
  - When goi POST /auth/login
  - Then tra 200 va payload co access_token, role, username.
- AC-AUTH-02:
  - Given user sai mat khau
  - When goi POST /auth/login
  - Then tra 401 voi detail ro rang.
- AC-AUTH-03:
  - Given user bi khoa
  - When goi POST /auth/login
  - Then tra 403.
- AC-AUTH-04:
  - Given token hop le
  - When goi endpoint can auth
  - Then cho phep truy cap theo role.
- AC-AUTH-05:
  - Given token khong hop le hoac het han
  - When goi endpoint can auth
  - Then tra 401.

## 6. Open tasks
- T1: Bo sung endpoint logout chinh thuc (POST /auth/logout) neu can revoke token server-side.
- T2: Them audit log login/logout.
- T3: Bo sung refresh token neu can session dai han.
