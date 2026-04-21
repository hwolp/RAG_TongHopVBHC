# Engineering Rules

## 1. Muc dich
Dat ra quy tac chung de AI agent va dev team code nhat quan, an toan, test duoc.

## 2. Code Style Guide
- Backend Python:
  - Follow PEP8, type hint cho service method moi.
  - Router chi xu ly HTTP concerns; business logic dat trong services.
  - Khong duplicate logic giua canonical va legacy route, legacy route goi lai canonical handler.
- Frontend TypeScript:
  - API calls tap trung qua frontend/src/api.ts.
  - Khong hardcode role string o nhieu noi, dung central auth state.

## 3. Security Rules
- Khong expose secret key, DB password, token trong log.
- Moi endpoint nhay cam phai co auth guard ro rang.
- Validate input o schema layer (Pydantic).
- Tai lieu download phai verify ownership/scope truoc khi tra file.
- Han che CORS "*" trong moi truong production.

## 4. Testing Rules
- Muc tieu test toi thieu:
  - Unit test: service logic quan trong (auth, user, document permissions).
  - Integration test: endpoint auth, user CRUD, document upload/download, chat ask.
  - Regression test: legacy endpoints van hoat dong nhu canonical endpoint.
- Moi bug fix phai co it nhat 1 test bao ve.

## 5. API Rules
- Response loi dung format:
  - HTTP status phu hop
  - detail message de frontend hien thi.
- Khong silently swallow exception trong service.
- Endpoint moi phai khai bao trong SPEC truoc khi code.

## 6. Data Rules
- Migration uu tien additive truoc (them cot/bang moi nullable), sau do moi tighten constraints.
- Khong xoa cot cu ngay neu frontend/legacy endpoint con dung.
- Enum change phai co plan rollback.

## 7. Definition of Done
- DoD1: Requirement da map vao user story trong file component spec.
- DoD2: Co technical constraints ro endpoint, input/output, role gate.
- DoD3: Co acceptance criteria co the verify bang test hoac manual script.
- DoD4: Co changelog ngan ghi pham vi thay doi.
- DoD5: Khong tao regression cho luong dang nhap, upload tai lieu, chat.

## 8. PR Checklist
- [ ] Da update file SPEC lien quan.
- [ ] Da them/sua test cho behavior moi.
- [ ] Da test role boundary (admin/manager/employee).
- [ ] Da check backward compatibility voi endpoint legacy.
- [ ] Da review security risks (token, file access, input validation).
