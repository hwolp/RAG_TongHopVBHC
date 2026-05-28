import { useState, useEffect } from "react";
import api, { waitForJob } from "../api";
import {
  FileText, Upload, Trash2, Download, Search,
  LayoutGrid, List, RefreshCw,
} from "lucide-react";
import FolderTree, { type FolderTreeData } from "../components/FolderTree";

type Doc = {
  id: number;
  filename: string;
  scope: string;
  is_indexed: boolean;
  index_status?: "indexed" | "not_indexed" | "queued" | "running" | "failed";
  uploaded_at: string;
};

type JobResponse = {
  id: number;
  status: "queued" | "running" | "success" | "failed";
  error?: string | null;
};

export default function Library() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [search, setSearch] = useState("");
  const [uploading, setUploading] = useState(false);
  const [viewMode, setViewMode] = useState<"grid" | "tree">("grid");
  const [treeData, setTreeData] = useState<FolderTreeData | null>(null);
  const [treeLoading, setTreeLoading] = useState(false);
  const [jobMessage, setJobMessage] = useState("");

  const fetchDocs = async () => {
    try {
      const r = await api.get(`/employee/documents?search=${encodeURIComponent(search)}`);
      setDocs(r.data);
    } catch {}
  };

  const fetchTree = async () => {
    setTreeLoading(true);
    try {
      const r = await api.get("/documents/tree");
      setTreeData(r.data);
    } catch {}
    setTreeLoading(false);
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { fetchDocs(); }, []);

  const switchToTree = () => {
    setViewMode("tree");
    fetchTree();
  };

  const waitIndexJob = async (jobId: number) => {
    setJobMessage("Tài liệu đã tải lên, đang chờ worker index...");
    try {
      const job = await waitForJob<JobResponse>(jobId);
      if (job.status === "success") {
        setJobMessage("Index tài liệu hoàn tất.");
      } else if (job.status === "failed") {
        setJobMessage("Index thất bại: " + (job.error || "Không rõ lỗi."));
      } else {
        setJobMessage("Tài liệu vẫn đang chờ worker xử lý. Hãy kiểm tra backend worker.");
      }
      await fetchDocs();
      if (viewMode === "tree") await fetchTree();
    } catch {
      setJobMessage("Không thể chờ trạng thái job index.");
    }
  };

  const indexBadge = (doc: Doc) => {
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
    return (
      <span className={`text-xs px-2 py-0.5 rounded-full ${styles[status] || styles.not_indexed}`}>
        {labels[status] || labels.not_indexed}
      </span>
    );
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.[0]) return;
    setJobMessage("");
    setUploading(true);
    const fd = new FormData();
    fd.append("file", e.target.files[0]);
    try {
      const r = await api.post("/employee/documents/upload", fd);
      await fetchDocs();
      if (viewMode === "tree") fetchTree();
      if (r.data.job_id) {
        void waitIndexJob(r.data.job_id);
      } else {
        setJobMessage("Tải lên hoàn tất. File này chưa cần index nền.");
      }
    } catch (err: any) {
      setJobMessage("Tải lên thất bại: " + (err.response?.data?.detail || err.message));
    }
    setUploading(false);
  };

  const handleDelete = async (id: number, _scope?: string) => {
    if (!confirm("Xóa tài liệu này?")) return;
    try {
      await api.delete(`/employee/documents/${id}`);
      fetchDocs();
      if (viewMode === "tree") fetchTree();
    } catch {}
  };

  const handleDownload = (id: number) => {
    window.open(`http://localhost:8000/employee/documents/${id}/download`, "_blank");
  };

  return (
    <div className="neo-page max-w-6xl">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Kho Tài Liệu Cá Nhân</h1>
          <p className="text-slate-500 text-sm mt-1">Tải lên, quản lý và tìm kiếm tài liệu của bạn</p>
        </div>
        <div className="flex items-center gap-2">
          {/* View toggle */}
          <button onClick={() => setViewMode("grid")}
            className={`neo-icon-button ${viewMode === "grid" ? "text-white !bg-[#006666]" : "text-slate-500"}`}
            title="Xem dạng lưới">
            <LayoutGrid className="w-4 h-4" />
          </button>
          <button onClick={switchToTree}
            className={`neo-icon-button ${viewMode === "tree" ? "text-white !bg-[#006666]" : "text-slate-500"}`}
            title="Xem dạng cây thư mục">
            <List className="w-4 h-4" />
          </button>

          {/* Upload */}
          <label className="neo-button neo-button-primary cursor-pointer">
            <Upload className="w-4 h-4" />
            {uploading ? "Đang tải..." : "Tải lên"}
            <input type="file" className="hidden" accept=".pdf,.docx,.doc,.txt" onChange={handleUpload} />
          </label>
        </div>
      </div>

      {/* Search (grid mode only) */}
      {jobMessage && (
        <div className="neo-panel-compact px-4 py-3 text-sm text-[#006666]">
          {jobMessage}
        </div>
      )}

      {/* Search (grid mode only) */}
      {viewMode === "grid" && (
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-3 w-4 h-4 text-gray-400" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              onKeyDown={e => e.key === "Enter" && fetchDocs()}
              className="neo-input pl-10 pr-4"
              placeholder="Tìm kiếm tài liệu..."
            />
          </div>
          <button onClick={fetchDocs}
            className="neo-button">
            Tìm
          </button>
        </div>
      )}

      {/* Grid View */}
      {viewMode === "grid" && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {docs.map((d) => (
              <div key={d.id} className="neo-panel p-5 transition group hover:-translate-y-0.5">
                <div className="flex items-start justify-between mb-3">
                  <div className="neo-stat-icon">
                    <FileText className="w-6 h-6 text-[#006666]" />
                  </div>
                  {indexBadge(d)}
                </div>
                <h3 className="font-medium text-gray-900 truncate mb-1" title={d.filename}>{d.filename}</h3>
                <p className="text-xs text-gray-400 mb-4">{d.uploaded_at?.slice(0, 10)}</p>
                <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition">
                  <button onClick={() => handleDownload(d.id)}
                    className="neo-button flex-1 !min-h-0 py-1.5 text-xs text-[#006666]">
                    <Download className="w-3.5 h-3.5" /> Tải xuống
                  </button>
                  <button onClick={() => handleDelete(d.id)}
                    className="neo-icon-button !h-8 !w-8 text-red-500">
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
          {docs.length === 0 && (
            <div className="text-center py-16 text-gray-400">
              <FileText className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p>Chưa có tài liệu nào. Hãy tải lên file PDF!</p>
            </div>
          )}
        </>
      )}

      {/* Tree View */}
      {viewMode === "tree" && (
        <div className="neo-panel p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-700">Cây thư mục tài liệu</h2>
            <button onClick={fetchTree} disabled={treeLoading}
              className="flex items-center gap-1 text-xs text-gray-500 hover:text-blue-600 transition">
              <RefreshCw className={`w-3.5 h-3.5 ${treeLoading ? "animate-spin" : ""}`} />
              Làm mới
            </button>
          </div>

          {treeLoading && (
            <div className="flex items-center justify-center py-12 text-gray-400 gap-2">
              <RefreshCw className="w-5 h-5 animate-spin" />
              <span>Đang tải...</span>
            </div>
          )}

          {!treeLoading && treeData && (
            <FolderTree
              data={treeData}
              hideCompany={false}
              hideDepartment={false}
              onDownload={handleDownload}
              onDelete={handleDelete}
              canDelete={(doc) => doc.scope === "personal"}
            />
          )}

          {!treeLoading && !treeData && (
            <p className="text-center py-8 text-gray-400 text-sm">Không thể tải dữ liệu</p>
          )}
        </div>
      )}
    </div>
  );
}
