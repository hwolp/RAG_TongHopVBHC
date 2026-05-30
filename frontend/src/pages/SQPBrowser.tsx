import { useEffect, useMemo, useState } from "react";
import api, { waitForJob } from "../api";
import { BookOpen, Search, Download, FileText, RefreshCw, Upload, PencilLine, Trash2, X } from "lucide-react";
import { useAuth } from "../hooks/useAuth";

type SQPDocument = {
  id: number;
  filename: string;
  uploaded_at: string;
  owner_id?: number | null;
  is_indexed?: boolean;
  index_status?: "indexed" | "not_indexed" | "queued" | "running" | "failed";
};

type JobResponse = {
  id: number;
  status: "queued" | "running" | "success" | "failed";
  error?: string | null;
};

export default function SQPBrowser() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const [docs, setDocs] = useState<SQPDocument[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [editingDoc, setEditingDoc] = useState<SQPDocument | null>(null);
  const [editFilename, setEditFilename] = useState("");
  const [jobMessage, setJobMessage] = useState("");

  const fetchDocs = async () => {
    setLoading(true);
    try {
      const r = await api.get(`/documents/sqp?search=${encodeURIComponent(search)}`);
      setDocs(r.data);
    } catch {
      setDocs([]);
    } finally {
      setLoading(false);
    }
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { fetchDocs(); }, []);

  const filteredDocs = useMemo(() => docs, [docs]);

  const handleDownload = (id: number) => {
    window.open(`http://localhost:8000/documents/${id}/download`, "_blank");
  };

  const waitIndexJob = async (jobId: number) => {
    setJobMessage("Tài liệu SQP đã tải lên, đang chờ worker index...");
    try {
      const job = await waitForJob<JobResponse>(jobId);
      if (job.status === "success") {
        setJobMessage("Index tài liệu SQP hoàn tất.");
      } else if (job.status === "failed") {
        setJobMessage("Index thất bại: " + (job.error || "Không rõ lỗi."));
      } else {
        setJobMessage("Tài liệu vẫn đang chờ worker xử lý. Hãy kiểm tra backend worker.");
      }
      await fetchDocs();
    } catch {
      setJobMessage("Không thể chờ trạng thái job index.");
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setUploading(true);
    setJobMessage("");
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      const response = await api.post("/documents/sqp", formData, { headers: { "Content-Type": "multipart/form-data" } });
      setSelectedFile(null);
      await fetchDocs();
      if (response.data.job_id) {
        void waitIndexJob(response.data.job_id);
      } else {
        setJobMessage("Tải lên hoàn tất. File này chưa cần index nền.");
      }
    } finally {
      setUploading(false);
    }
  };

  const renderIndexBadge = (doc: SQPDocument) => {
    const status = doc.index_status || (doc.is_indexed ? "indexed" : "not_indexed");
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

  const openEdit = (doc: SQPDocument) => {
    setEditingDoc(doc);
    setEditFilename(doc.filename);
  };

  const handleSaveEdit = async () => {
    if (!editingDoc) return;
    await api.put(`/documents/sqp/${editingDoc.id}`, { filename: editFilename });
    setEditingDoc(null);
    await fetchDocs();
  };

  const handleDelete = async (docId: number) => {
    if (!window.confirm("Xóa tài liệu SQP này?")) return;
    await api.delete(`/documents/sqp/${docId}`);
    await fetchDocs();
  };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6">
      <div className="flex flex-wrap justify-between items-center gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Quy Định & Biểu Mẫu Công Ty (SQP)</h1>
          <p className="text-gray-500 text-sm mt-1">
            {isAdmin ? "Quản lý CRUD tài liệu SQP" : "Tra cứu các tài liệu dùng chung đã được phê duyệt"}
          </p>
        </div>
        <button
          onClick={() => void fetchDocs()}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-white border rounded-lg shadow-sm hover:border-blue-300 text-sm text-gray-700"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Làm mới
        </button>
      </div>

      {isAdmin && (
        <div className="bg-white border rounded-xl shadow-sm p-5 space-y-4">
          <div className="flex items-center gap-3">
            <Upload className="w-5 h-5 text-blue-600" />
            <h2 className="font-semibold text-gray-900">Tải lên tài liệu SQP</h2>
          </div>
          <div className="flex flex-wrap gap-3 items-center">
            <label className="flex-1 min-w-64 border rounded-lg px-3 py-2.5 text-sm bg-gray-50 cursor-pointer flex items-center justify-between gap-3">
              <span className="truncate text-gray-600">{selectedFile ? selectedFile.name : "Chọn file..."}</span>
              <span className="text-xs text-blue-600 font-medium whitespace-nowrap">Browse</span>
              <input type="file" className="hidden" accept=".pdf,.docx" onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)} />
            </label>
            <button
              onClick={() => void handleUpload()}
              disabled={!selectedFile || uploading}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-blue-600 text-white text-sm hover:bg-blue-700 disabled:opacity-60"
            >
              <Upload className="w-4 h-4" />
              {uploading ? "Đang tải lên..." : "Tải lên"}
            </button>
          </div>
        </div>
      )}

      {jobMessage && (
        <div className="rounded-lg border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-700">
          {jobMessage}
        </div>
      )}

      <div className="relative">
        <Search className="absolute left-3 top-3 w-4 h-4 text-gray-400" />
        <input 
          value={search} 
          onChange={e => setSearch(e.target.value)} 
          onKeyDown={e => e.key === "Enter" && fetchDocs()}
          className="w-full pl-10 pr-4 py-2.5 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none" 
          placeholder="Tìm kiếm quy định, chính sách, biểu mẫu..." 
        />
      </div>

      <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-4 py-3 text-left font-semibold text-gray-600">Tên tài liệu</th>
              <th className="px-4 py-3 text-left font-semibold text-gray-600">Index</th>
              <th className="px-4 py-3 text-left font-semibold text-gray-600">Ngày ban hành (Upload)</th>
              <th className="px-4 py-3 text-right font-semibold text-gray-600">Hành động</th>
            </tr>
          </thead>
          <tbody>
            {filteredDocs.map((d) => (
              <tr key={d.id} className="border-b hover:bg-gray-50 transition">
                <td className="px-4 py-4 font-medium flex items-center gap-3">
                  <div className="p-2 bg-amber-50 rounded-lg"><BookOpen className="w-5 h-5 text-amber-600" /></div>
                  <span className="text-gray-900">{d.filename}</span>
                </td>
                <td className="px-4 py-4">{renderIndexBadge(d)}</td>
                <td className="px-4 py-4 text-gray-500">{d.uploaded_at?.slice(0, 10)}</td>
                <td className="px-4 py-4 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <button onClick={() => handleDownload(d.id)} className="flex items-center justify-center gap-1.5 px-3 py-1.5 bg-blue-50 text-blue-600 rounded-lg text-xs hover:bg-blue-100 font-medium">
                      <Download className="w-3.5 h-3.5" /> Tải về
                    </button>
                    {isAdmin && (
                      <>
                        <button onClick={() => openEdit(d)} className="flex items-center justify-center gap-1.5 px-3 py-1.5 bg-emerald-50 text-emerald-600 rounded-lg text-xs hover:bg-emerald-100 font-medium">
                          <PencilLine className="w-3.5 h-3.5" /> Sửa
                        </button>
                        <button onClick={() => void handleDelete(d.id)} className="p-1.5 rounded-lg text-red-500 hover:bg-red-50" title="Xóa">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {docs.length === 0 && (
          <div className="text-center py-16 text-gray-400">
            <FileText className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p>Không tìm thấy quy định nào.</p>
          </div>
        )}
      </div>

      {editingDoc && isAdmin && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white w-full max-w-lg rounded-2xl shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h3 className="font-bold text-lg text-gray-900">Chỉnh sửa tài liệu SQP</h3>
                <p className="text-sm text-gray-500">Đổi tên file SQP.</p>
              </div>
              <button onClick={() => setEditingDoc(null)} className="p-2 rounded-lg hover:bg-gray-100">
                <X className="w-5 h-5" />
              </button>
            </div>
            <input
              value={editFilename}
              onChange={(event) => setEditFilename(event.target.value)}
              className="w-full border rounded-lg px-3 py-2.5 text-sm"
              placeholder="Tên file"
            />
            <div className="flex justify-end gap-2">
              <button onClick={() => setEditingDoc(null)} className="px-4 py-2.5 rounded-lg border text-sm text-gray-600">
                Hủy
              </button>
              <button onClick={() => void handleSaveEdit()} className="px-4 py-2.5 rounded-lg bg-blue-600 text-white text-sm hover:bg-blue-700">
                Lưu thay đổi
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
