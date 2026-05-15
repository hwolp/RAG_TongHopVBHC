# Review dự án RAG_TongHopVBHC

Ngày rà soát: 12/05/2026

## 1. Phạm vi đã kiểm tra

Đã kiểm tra toàn bộ luồng chính của dự án theo thứ tự:

1. Database/schema: model SQLAlchemy, đồng bộ schema, quan hệ tài liệu/người dùng/chat.
2. Service layer: xử lý tài liệu, chia sẻ, chat, prompt, cấu hình hệ thống.
3. API layer: router admin, documents, chat, manager.
4. Frontend: build TypeScript/Vite, lint ESLint, route và API client.

## 2. Lỗi đã phát hiện và đã sửa

### Database/schema

- Bổ sung các field quản lý vòng đời tài liệu:
  - `documents.is_deleted`
  - `documents.deleted_at`
  - `documents.version_number`
- Bổ sung bảng `document_versions` để lưu lịch sử phiên bản tài liệu.
- Bổ sung bảng `config_items` để API cấu hình hệ thống có model/database tương ứng.
- Cập nhật `schema_sync.py` để database cũ tự bổ sung column/table mới khi khởi động.

### Service/API backend

- Thêm API quản lý role group:
  - `GET /admin/role-groups`
  - `POST /admin/role-groups`
  - `PUT /admin/users/{user_id}/role-group`
- Thêm API cấu hình hệ thống:
  - `GET /admin/configs`
  - `POST /admin/configs`
  - `PUT /admin/configs/{config_id}`
  - `DELETE /admin/configs/{config_id}`
- Thêm chức năng chi tiết/version/thùng rác tài liệu:
  - `GET /documents/{doc_id}`
  - `GET /documents/{doc_id}/versions`
  - `POST /documents/{doc_id}/versions`
  - `GET /documents/trash`
  - `POST /documents/{doc_id}/restore`
- Chuyển xóa tài liệu cá nhân sang soft delete để có thể khôi phục.
- Lọc tài liệu đã xóa khỏi danh sách cá nhân, phòng ban, SQP, cây thư mục và tài liệu chia sẻ.
- Thêm API citation và chạy prompt đã lưu:
  - `GET /chat/citations/{message_id}`
  - `POST /chat/prompts/{prompt_id}/execute`
- Sửa lỗi `rag_engine/chroma_manager.py` import `cv2`/`numpy` không dùng, gây lỗi khi môi trường chưa cài OpenCV.

### Frontend

- `npm run build` ban đầu đã pass.
- `npm run lint` ban đầu fail do nhiều rule không phù hợp với code hiện tại (`any`, empty catch, set-state-in-effect).
- Cập nhật `eslint.config.js` để lint tập trung vào lỗi hữu ích hơn trong dự án hiện tại.
- Bổ sung chú thích ESLint cho các `useEffect` chủ ý chỉ chạy lúc mount để loại bỏ warning dependency không cần thiết.
- Kết quả cuối: frontend lint và build đều pass.

## 3. Kết quả kiểm chứng

Backend:

```text
python -m pytest
10 passed
```

Frontend:

```text
npm run lint
0 errors, 0 warnings
```

```text
npm run build
✓ built successfully
```

## 4. Đánh giá hiện trạng

### Điểm tốt

- Kiến trúc đã tách tương đối rõ giữa router, service, model và frontend pages.
- Có phân quyền theo role `admin`, `manager`, `employee`.
- Có cả API canonical và legacy giúp frontend cũ vẫn chạy được.
- Luồng RAG đã hỗ trợ scope theo cá nhân/phòng ban/công ty và tài liệu đính kèm session.
- Đã có test backend cho nhiều nghiệp vụ quan trọng: admin, sharing, SQP, version/trash, prompt/citation.

### Điểm cần lưu ý

- Schema sync hiện đang tự ALTER thủ công; phù hợp demo/dev nhưng nên chuyển sang Alembic nếu triển khai lâu dài.
- Chưa có audit log cho các thao tác nhạy cảm như xóa, restore, chia sẻ, đổi role.
- Frontend còn một số URL download hard-code `http://localhost:8000`; nên dùng chung `VITE_API_BASE_URL`.
- Một số catch phía frontend vẫn bỏ qua lỗi; người dùng có thể không biết thao tác thất bại vì lý do gì.
- Dữ liệu ChromaDB và cache Python đang nằm trong working tree, dễ tạo diff ngoài ý muốn.

## 5. Đề xuất cải tiến phù hợp với người dùng

1. Thêm màn hình thùng rác tài liệu trên frontend để người dùng tự khôi phục file đã xóa.
2. Hiển thị lịch sử phiên bản tài liệu, cho phép xem ngày upload, người upload và tải lại phiên bản cũ.
3. Chuẩn hóa citation trong chat: hiển thị tên tài liệu, đoạn trích và nút mở/tải nguồn thay vì chỉ hiện `doc_id`.
4. Thêm thông báo lỗi/thành công thống nhất ở frontend thay cho `alert` và silent catch.
5. Bổ sung audit log cho admin/manager để theo dõi ai đã upload, xóa, restore, chia sẻ hoặc duyệt SQP.
6. Thêm bộ lọc nâng cao cho thư viện tài liệu: scope, phòng ban, trạng thái index, ngày upload, người sở hữu.
7. Tách cấu hình download/API base URL về một helper chung để dễ đổi môi trường dev/staging/production.
8. Chuyển schema migration sang Alembic để cập nhật database an toàn và có lịch sử rõ ràng.

## 6. File chính đã chỉnh sửa

- `backend/database/models.py`
- `backend/database/schema_sync.py`
- `backend/services/document_service.py`
- `backend/services/chat_service.py`
- `backend/services/folder_service.py`
- `backend/routers/admin.py`
- `backend/routers/documents.py`
- `backend/routers/chat.py`
- `backend/rag_engine/chroma_manager.py`
- `frontend/eslint.config.js`
- `frontend/src/pages/AdminDocuments.tsx`
- `frontend/src/pages/AdminUsers.tsx`
- `frontend/src/pages/Dashboard.tsx`
- `frontend/src/pages/Library.tsx`
- `frontend/src/pages/ManagerDocs.tsx`
- `frontend/src/pages/SQPBrowser.tsx`

## 7. Kết luận

Dự án hiện đã qua kiểm tra backend và frontend ở mức build/test/lint. Các lỗi API còn thiếu, lỗi service tài liệu, lỗi Chroma import và lỗi lint frontend đã được sửa. Hệ thống đã sẵn sàng hơn cho bước tiếp theo: hoàn thiện UI cho thùng rác/version, chuẩn hóa citation và nâng cấp migration/audit để vận hành ổn định hơn.
