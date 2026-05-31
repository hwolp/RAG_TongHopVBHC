import { useState, useEffect } from "react";
import api, { waitForJob } from "../api";
import { Database, RefreshCw, Trash2 } from "lucide-react";
import { useConfirmDialog } from "../components/ConfirmDialog";

export default function AdminSystem() {
  const [vectorStatus, setVectorStatus] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [proposals, setProposals] = useState<any[]>([]);
  const [tags, setTags] = useState<any[]>([]);
  const [newTag, setNewTag] = useState("");
  const [jobMessage, setJobMessage] = useState("");
  const { confirm, confirmDialog } = useConfirmDialog();

  const fetchStatus = async () => { try { const r = await api.get("/admin/vector/status"); setVectorStatus(r.data); } catch {} };
  const fetchProposals = async () => { const r = await api.get("/admin/sqp/proposals"); setProposals(r.data); };
  const fetchTags = async () => { const r = await api.get("/admin/tags"); setTags(r.data); };

  useEffect(() => { fetchStatus(); fetchProposals(); fetchTags(); }, []);

  const handleReindex = async () => { setLoading(true); await api.post("/admin/vector/reindex"); await fetchStatus(); setLoading(false); };
  const handleClear = async () => {
    const ok = await confirm({
      title: "Xóa Collection?",
      description: "Thao tác này sẽ xóa toàn bộ vector index, tài liệu đã upload, hội thoại, tin nhắn chat và job nền. Không thể hoàn tác.",
      confirmText: "Xóa Collection",
    });
    if (!ok) return;
    setLoading(true);
    try {
      await api.post("/admin/vector/clear");
      await fetchStatus();
      await fetchProposals();
    } finally {
      setLoading(false);
    }
  };
  const waitIndexJob = async (jobId: number) => {
    setJobMessage("Tài liệu SQP đã được duyệt, đang chờ re-index...");
    try {
      const job = await waitForJob(jobId);
      if (job.status === "success") {
        setJobMessage("Re-index tài liệu SQP hoàn tất.");
        await fetchStatus();
        return;
      }
      if (job.status === "failed") {
        setJobMessage("Re-index thất bại: " + (job.error || "Không rõ lỗi."));
        return;
      }
      setJobMessage("Tài liệu vẫn đang chờ worker xử lý. Hãy kiểm tra backend worker.");
    } catch {
      setJobMessage("Không thể chờ trạng thái job index.");
    }
  };
  const handleApprove = async (id: number) => {
    const r = await api.post(`/admin/sqp/approve/${id}`);
    await fetchProposals();
    if (r.data.job_id) void waitIndexJob(r.data.job_id);
  };
  const handleReject = async (id: number) => { await api.post(`/admin/sqp/reject/${id}`); fetchProposals(); };
  const handleAddTag = async () => { if (!newTag) return; await api.post(`/admin/tags?name=${newTag}`); setNewTag(""); fetchTags(); };
  const handleDeleteTag = async (id: number) => {
    const ok = await confirm({
      title: "Xóa thẻ này?",
      description: "Thẻ sẽ bị xóa khỏi hệ thống.",
      confirmText: "Xóa thẻ",
    });
    if (!ok) return;
    await api.delete(`/admin/tags/${id}`);
    fetchTags();
  };

  const statusColors: any = { pending: "bg-yellow-100 text-yellow-700", approved: "bg-green-100 text-green-700", rejected: "bg-red-100 text-red-700" };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      {confirmDialog}
      <h1 className="text-2xl font-bold text-gray-900">Bảo Trì & Cấu Hình Hệ Thống</h1>

      {/* Vector DB Status */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-4"><Database className="w-5 h-5 text-blue-600" /><h3 className="font-semibold">Trạng thái Vector DB</h3></div>
          <p className="text-3xl font-bold text-blue-600">{vectorStatus?.total_vectors ?? "—"}</p>
          <p className="text-xs text-gray-400 mt-1">vectors đã lưu trữ</p>
        </div>
        <button onClick={handleReindex} disabled={loading} className="bg-white rounded-xl border p-6 shadow-sm hover:border-blue-300 transition text-left">
          <div className="flex items-center gap-3 mb-2"><RefreshCw className={`w-5 h-5 text-amber-600 ${loading ? "animate-spin" : ""}`} /><h3 className="font-semibold">Re-index</h3></div>
          <p className="text-sm text-gray-500">{loading ? "Đang quét lại..." : "Quét lại toàn bộ tài liệu chưa index"}</p>
        </button>
        <button onClick={handleClear} disabled={loading} className="bg-white rounded-xl border p-6 shadow-sm hover:border-red-300 transition text-left disabled:opacity-60">
          <div className="flex items-center gap-3 mb-2"><Trash2 className="w-5 h-5 text-red-600" /><h3 className="font-semibold text-red-600">Xóa Collection</h3></div>
          <p className="text-sm text-gray-500">Xóa vector, hội thoại, tin nhắn, tài liệu upload và file lưu trữ</p>
        </button>
      </div>

      {/* Tags */}
      {jobMessage && (
        <div className="rounded-lg border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-700">
          {jobMessage}
        </div>
      )}

      {/* Tags */}
      <div className="bg-white rounded-xl border shadow-sm p-6">
        <h3 className="font-semibold text-gray-900 mb-4">Quản Lý Thẻ/Nhãn (Tags)</h3>
        <div className="flex gap-2 mb-4">
          <input value={newTag} onChange={e => setNewTag(e.target.value)} className="flex-1 border rounded-lg px-3 py-2 text-sm" placeholder="Tên thẻ mới..." />
          <button onClick={handleAddTag} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">Thêm</button>
        </div>
        <div className="flex flex-wrap gap-2">
          {tags.map((t: any) => (
            <span key={t.id} className="inline-flex items-center gap-1 px-3 py-1.5 bg-gray-100 rounded-full text-sm">
              {t.name}
              <button onClick={() => handleDeleteTag(t.id)} className="text-gray-400 hover:text-red-500"><Trash2 className="w-3 h-3" /></button>
            </span>
          ))}
        </div>
      </div>

      {/* SQP Proposals */}
      <div className="bg-white rounded-xl border shadow-sm p-6">
        <h3 className="font-semibold text-gray-900 mb-4">Đề Xuất SQP Chờ Duyệt</h3>
        {proposals.length === 0 ? <p className="text-gray-400 text-sm">Không có đề xuất nào</p> : (
          <div className="space-y-3">
            {proposals.map((p: any) => (
              <div key={p.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border">
                <div>
                  <p className="font-medium">Tài liệu #{p.document_id}</p>
                  <p className="text-xs text-gray-400">Đề xuất bởi User #{p.proposed_by} • {p.created_at}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${statusColors[p.status]}`}>{p.status}</span>
                  {p.status === "pending" && (
                    <>
                      <button onClick={() => handleApprove(p.id)} className="px-3 py-1.5 bg-green-600 text-white rounded-lg text-xs hover:bg-green-700">Duyệt</button>
                      <button onClick={() => handleReject(p.id)} className="px-3 py-1.5 bg-red-100 text-red-600 rounded-lg text-xs hover:bg-red-200">Từ chối</button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
