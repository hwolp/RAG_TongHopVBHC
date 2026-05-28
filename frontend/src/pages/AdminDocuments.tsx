import { useEffect, useMemo, useState } from "react";
import api, { waitForJob } from "../api";
import { FileText, RefreshCw, Search, Share2, Trash2, Upload, PencilLine, X } from "lucide-react";

type Department = {
  id: number;
  name: string;
};

type DepartmentDocument = {
  id: number;
  filename: string;
  uploaded_at: string;
  owner_id: number | null;
  department_id: number | null;
  is_indexed?: boolean;
  index_status?: "indexed" | "not_indexed" | "queued" | "running" | "failed";
};

type JobResponse = {
  id: number;
  status: "queued" | "running" | "success" | "failed";
  error?: string | null;
};

type ShareRecord = {
  id: number;
  document_id: number;
  document_filename: string;
  document_department_name?: string | null;
  shared_with_dept_id?: number | null;
  shared_with_department_name?: string | null;
  shared_with_user_id?: number | null;
  shared_with_username?: string | null;
  shared_by: number;
  shared_by_username?: string | null;
  created_at: string;
};

type EditForm = {
  filename: string;
  department_id: string;
};

export default function AdminDocuments() {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [documents, setDocuments] = useState<DepartmentDocument[]>([]);
  const [shares, setShares] = useState<ShareRecord[]>([]);
  const [search, setSearch] = useState("");
  const [selectedDepartmentId, setSelectedDepartmentId] = useState<string>("");
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);
  const [editingDoc, setEditingDoc] = useState<DepartmentDocument | null>(null);
  const [editForm, setEditForm] = useState<EditForm>({ filename: "", department_id: "" });
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [jobMessage, setJobMessage] = useState("");

  const departmentNameMap = useMemo(
    () => new Map(departments.map((department) => [department.id, department.name])),
    [departments],
  );

  const loadDepartments = async () => {
    const response = await api.get("/admin/departments");
    setDepartments(response.data);
    if (!selectedDepartmentId && response.data.length > 0) {
      setSelectedDepartmentId(String(response.data[0].id));
    }
  };

  const loadDocuments = async () => {
    const response = await api.get(`/admin/documents/department?search=${encodeURIComponent(search)}`);
    setDocuments(response.data);
  };

  const loadShares = async () => {
    const response = await api.get(`/admin/shares?search=${encodeURIComponent(search)}`);
    setShares(response.data);
  };

  const refreshAll = async () => {
    setLoading(true);
    try {
      await Promise.all([loadDepartments(), loadDocuments(), loadShares()]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refreshAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSearch = async () => {
    setLoading(true);
    try {
      await Promise.all([loadDocuments(), loadShares()]);
    } finally {
      setLoading(false);
    }
  };

  const waitIndexJob = async (jobId: number) => {
    setJobMessage("Tài liệu đã tải lên, đang chờ worker index...");
    try {
      const job = await waitForJob<JobResponse>(jobId);
      if (job.status === "success") {
        setJobMessage("Index tài liệu phòng ban hoàn tất.");
      } else if (job.status === "failed") {
        setJobMessage("Index thất bại: " + (job.error || "Không rõ lỗi."));
      } else {
        setJobMessage("Tài liệu vẫn đang chờ worker xử lý. Hãy kiểm tra backend worker.");
      }
      await refreshAll();
    } catch {
      setJobMessage("Không thể chờ trạng thái job index.");
    }
  };

  const handleUpload = async () => {
    if (!selectedFile || !selectedDepartmentId) return;
    setUploading(true);
    setJobMessage("");
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      const response = await api.post("/admin/documents/department/upload", formData, {
        params: { department_id: Number(selectedDepartmentId) },
      });
      setSelectedFile(null);
      await refreshAll();
      if (response.data.job_id) {
        void waitIndexJob(response.data.job_id);
      } else {
        setJobMessage("Tải lên hoàn tất. File này chưa cần index nền.");
      }
    } finally {
      setUploading(false);
    }
  };

  const renderIndexBadge = (document: DepartmentDocument) => {
    const status = document.index_status || (document.is_indexed ? "indexed" : "not_indexed");
    const styles: Record<string, string> = {
      indexed: "bg-green-100 text-green-700",
      queued: "bg-amber-100 text-amber-700",
      running: "bg-blue-100 text-blue-700",
      failed: "bg-red-100 text-red-700",
      not_indexed: "bg-gray-100 text-gray-500",
    };
    const labels: Record<string, string> = {
      indexed: "Đã index",
      queued: "Chờ index",
      running: "Đang index",
      failed: "Index lỗi",
      not_indexed: "Chưa index",
    };
    return <span className={`text-xs px-2 py-0.5 rounded-full ${styles[status] || styles.not_indexed}`}>{labels[status] || labels.not_indexed}</span>;
  };

  const openEditModal = (doc: DepartmentDocument) => {
    setEditingDoc(doc);
    setEditForm({
      filename: doc.filename,
      department_id: doc.department_id ? String(doc.department_id) : "",
    });
  };

  const handleSaveEdit = async () => {
    if (!editingDoc) return;
    setSaving(true);
    try {
      await api.put(`/admin/documents/department/${editingDoc.id}`, {
        filename: editForm.filename || null,
        department_id: editForm.department_id ? Number(editForm.department_id) : null,
      });
      setEditingDoc(null);
      await refreshAll();
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteDocument = async (docId: number) => {
    if (!window.confirm("Xóa tài liệu này?")) return;
    await api.delete(`/admin/documents/department/${docId}`);
    await refreshAll();
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Quản Lý Tài Liệu & Chia Sẻ Liên Phòng</h1>
          <p className="text-sm text-gray-500 mt-1">Tải lên, đổi tên, gán phòng ban và chia sẻ tài liệu giữa các phòng ban.</p>
        </div>
        <button
          onClick={() => void refreshAll()}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-white border rounded-lg shadow-sm hover:border-blue-300 text-sm text-gray-700"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Làm mới
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white border rounded-xl p-5 shadow-sm">
          <p className="text-xs uppercase tracking-widest text-gray-400">Tài liệu</p>
          <p className="mt-2 text-3xl font-bold text-blue-600">{documents.length}</p>
          <p className="text-sm text-gray-500 mt-1">tài liệu phòng ban đang quản lý</p>
        </div>
        <div className="bg-white border rounded-xl p-5 shadow-sm">
          <p className="text-xs uppercase tracking-widest text-gray-400">Chia sẻ</p>
          <p className="mt-2 text-3xl font-bold text-emerald-600">{shares.length}</p>
          <p className="text-sm text-gray-500 mt-1">lượt chia sẻ đang còn hiệu lực</p>
        </div>
        <div className="bg-white border rounded-xl p-5 shadow-sm">
          <p className="text-xs uppercase tracking-widest text-gray-400">Phòng ban</p>
          <p className="mt-2 text-3xl font-bold text-amber-600">{departments.length}</p>
          <p className="text-sm text-gray-500 mt-1">đơn vị có trong hệ thống</p>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="bg-white border rounded-xl shadow-sm p-6 space-y-4">
          <div className="flex items-center gap-3">
            <Upload className="w-5 h-5 text-blue-600" />
            <h2 className="font-semibold text-gray-900">Tải lên tài liệu phòng ban</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <select
              value={selectedDepartmentId}
              onChange={(event) => setSelectedDepartmentId(event.target.value)}
              className="w-full border rounded-lg px-3 py-2.5 text-sm"
            >
              {departments.map((department) => (
                <option key={department.id} value={department.id}>
                  {department.name}
                </option>
              ))}
            </select>
            <label className="w-full border rounded-lg px-3 py-2.5 text-sm bg-gray-50 cursor-pointer flex items-center justify-between gap-3">
              <span className="truncate text-gray-600">{selectedFile ? selectedFile.name : "Chọn file..."}</span>
              <span className="text-xs text-blue-600 font-medium whitespace-nowrap">Browse</span>
              <input
                type="file"
                className="hidden"
                onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
              />
            </label>
          </div>
          <button
            onClick={() => void handleUpload()}
            disabled={!selectedFile || !selectedDepartmentId || uploading}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-blue-600 text-white text-sm hover:bg-blue-700 disabled:opacity-60"
          >
            <Upload className="w-4 h-4" />
            {uploading ? "Đang tải lên..." : "Tải lên"}
          </button>
        </div>
      </div>

      {jobMessage && (
        <div className="rounded-lg border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-700">
          {jobMessage}
        </div>
      )}

      <div className="bg-white border rounded-xl shadow-sm overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 p-5 border-b">
          <div>
            <h2 className="font-semibold text-gray-900">Danh Sách Tài Liệu Phòng Ban</h2>
            <p className="text-sm text-gray-500 mt-1">Quản lý file, đổi tên và đổi phòng ban lưu trữ.</p>
          </div>
          <div className="flex items-center gap-2 w-full md:w-auto md:min-w-80">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-3 w-4 h-4 text-gray-400" />
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                onKeyDown={(event) => event.key === "Enter" && void handleSearch()}
                className="w-full pl-10 pr-4 py-2.5 border rounded-lg text-sm"
                placeholder="Tìm file hoặc ghi chú chia sẻ..."
              />
            </div>
            <button
              onClick={() => void handleSearch()}
              className="px-4 py-2.5 rounded-lg bg-gray-100 text-gray-700 text-sm hover:bg-gray-200"
            >
              Tìm
            </button>
          </div>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-4 py-3 text-left font-semibold text-gray-600">Tài liệu</th>
              <th className="px-4 py-3 text-left font-semibold text-gray-600">Phòng ban</th>
              <th className="px-4 py-3 text-left font-semibold text-gray-600">Index</th>
              <th className="px-4 py-3 text-left font-semibold text-gray-600">Ngày tải</th>
              <th className="px-4 py-3 text-right font-semibold text-gray-600">Hành động</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((document) => (
              <tr key={document.id} className="border-b hover:bg-gray-50">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-blue-500 flex-shrink-0" />
                    <span className="font-medium truncate max-w-sm" title={document.filename}>
                      {document.filename}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3 text-gray-600">
                  {document.department_id ? departmentNameMap.get(document.department_id) ?? `#${document.department_id}` : "—"}
                </td>
                <td className="px-4 py-3">{renderIndexBadge(document)}</td>
                <td className="px-4 py-3 text-gray-500">{document.uploaded_at?.slice(0, 10)}</td>
                <td className="px-4 py-3 text-right">
                  <div className="flex justify-end gap-1">
                    <button
                      onClick={() => openEditModal(document)}
                      className="px-2 py-1.5 rounded-lg text-xs bg-blue-50 text-blue-700 hover:bg-blue-100 inline-flex items-center gap-1"
                    >
                      <PencilLine className="w-3.5 h-3.5" />
                      Sửa
                    </button>
                    <button
                      onClick={() => void handleDeleteDocument(document.id)}
                      className="p-1.5 rounded-lg text-red-500 hover:bg-red-50"
                      title="Xóa"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {documents.length === 0 && <p className="text-center py-8 text-gray-400">Không có tài liệu phòng ban</p>}
      </div>

      <div className="bg-white border rounded-xl shadow-sm overflow-hidden">
        <div className="p-5 border-b flex items-center gap-3">
          <Share2 className="w-5 h-5 text-emerald-600" />
          <div>
            <h2 className="font-semibold text-gray-900">Lượt Chia Sẻ Đang Quản Lý</h2>
            <p className="text-sm text-gray-500 mt-1">Chỉ xem danh sách; thao tác chia sẻ thực hiện ở trang của trưởng phòng.</p>
          </div>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-4 py-3 text-left font-semibold text-gray-600">Tài liệu</th>
              <th className="px-4 py-3 text-left font-semibold text-gray-600">Chia sẻ tới</th>
              <th className="px-4 py-3 text-left font-semibold text-gray-600">Người tạo</th>
              <th className="px-4 py-3 text-right font-semibold text-gray-600">Hành động</th>
            </tr>
          </thead>
          <tbody>
            {shares.map((share) => (
              <tr key={share.id} className="border-b hover:bg-gray-50">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <Share2 className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                    <div>
                      <p className="font-medium">{share.document_filename}</p>
                      <p className="text-xs text-gray-400">
                        {share.document_department_name ? `Phòng ban nguồn: ${share.document_department_name}` : `Tài liệu #${share.document_id}`}
                      </p>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3 text-gray-600">
                  {share.shared_with_department_name
                    ? `Phòng ban: ${share.shared_with_department_name}`
                    : share.shared_with_username
                      ? `User: ${share.shared_with_username}`
                      : "—"}
                </td>
                <td className="px-4 py-3 text-gray-600">
                  {share.shared_by_username ?? `#${share.shared_by}`}
                </td>
                <td className="px-4 py-3 text-right text-xs text-gray-400">
                  Chỉ xem
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {shares.length === 0 && <p className="text-center py-8 text-gray-400">Chưa có lượt chia sẻ nào</p>}
      </div>

      {editingDoc && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white w-full max-w-lg rounded-2xl shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h3 className="font-bold text-lg text-gray-900">Chỉnh sửa tài liệu</h3>
                <p className="text-sm text-gray-500">Đổi tên file hoặc gán sang phòng ban khác.</p>
              </div>
              <button onClick={() => setEditingDoc(null)} className="p-2 rounded-lg hover:bg-gray-100">
                <X className="w-5 h-5" />
              </button>
            </div>
            <input
              value={editForm.filename}
              onChange={(event) => setEditForm((current) => ({ ...current, filename: event.target.value }))}
              className="w-full border rounded-lg px-3 py-2.5 text-sm"
              placeholder="Tên file"
            />
            <select
              value={editForm.department_id}
              onChange={(event) => setEditForm((current) => ({ ...current, department_id: event.target.value }))}
              className="w-full border rounded-lg px-3 py-2.5 text-sm"
            >
              <option value="">Không đổi phòng ban</option>
              {departments.map((department) => (
                <option key={department.id} value={department.id}>
                  {department.name}
                </option>
              ))}
            </select>
            <div className="flex justify-end gap-2">
              <button onClick={() => setEditingDoc(null)} className="px-4 py-2.5 rounded-lg border text-sm text-gray-600">
                Hủy
              </button>
              <button
                onClick={() => void handleSaveEdit()}
                disabled={saving}
                className="px-4 py-2.5 rounded-lg bg-blue-600 text-white text-sm hover:bg-blue-700 disabled:opacity-60"
              >
                {saving ? "Đang lưu..." : "Lưu thay đổi"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
