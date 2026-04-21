import { useState, useEffect } from "react";
import api from "../api";
import {
  Upload, Search, Send, RefreshCw, LayoutGrid, List,
  FileText, Trash2, BadgeCheck,
} from "lucide-react";
import FolderTree, { type FolderDoc, type FolderTreeData } from "../components/FolderTree";

type Doc = {
  id: number;
  filename: string;
  uploaded_at: string;
  owner_id: number;
  is_indexed?: boolean;
};

type Proposal = {
  id: number;
  document_id: number;
  status: string;
};

export default function ManagerDocs() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [search, setSearch] = useState("");
  const [uploading, setUploading] = useState(false);
  const [viewMode, setViewMode] = useState<"table" | "tree">("table");
  const [treeData, setTreeData] = useState<FolderTreeData | null>(null);
  const [treeLoading, setTreeLoading] = useState(false);
  const [indexingId, setIndexingId] = useState<number | null>(null);

  const fetchDocs = async () => {
    try {
      const r = await api.get(`/manager/department/documents?search=${encodeURIComponent(search)}`);
      setDocs(r.data);
    } catch {}
  };

  const fetchProposals = async () => {
    try { const r = await api.get("/manager/sqp/proposals"); setProposals(r.data); } catch {}
  };

  const fetchTree = async () => {
    setTreeLoading(true);
    try {
      const r = await api.get("/documents/tree");
      setTreeData(r.data);
    } catch {}
    setTreeLoading(false);
  };

  useEffect(() => { fetchDocs(); fetchProposals(); }, []);

  const switchToTree = () => {
    setViewMode("tree");
    fetchTree();
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.[0]) return;
    setUploading(true);
    const fd = new FormData();
    fd.append("file", e.target.files[0]);
    try {
      await api.post("/manager/department/documents/upload", fd);
      fetchDocs();
      if (viewMode === "tree") fetchTree();
    } catch {}
    setUploading(false);
  };

  const handleDelete = async (id: number, _scope?: string) => {
    if (!confirm("Xóa tài liệu?")) return;
    try {
      await api.delete(`/manager/department/documents/${id}`);
      fetchDocs();
      if (viewMode === "tree") fetchTree();
    } catch {}
  };

  const handlePropose = async (docId: number) => {
    try {
      await api.post(`/manager/sqp/propose/${docId}`);
      fetchProposals();
      alert("Đã gửi đề xuất lên Admin!");
    } catch (err: any) {
      alert("Lỗi: " + (err.response?.data?.detail || err.message));
    }
  };

  const handleCancelProposal = async (id: number) => {
    try { await api.delete(`/manager/sqp/proposals/${id}`); fetchProposals(); } catch {}
  };

  // Index (trigger RAG indexing) cho tài liệu phòng ban
  const handleIndex = async (docId: number) => {
    setIndexingId(docId);
    try {
      await api.post(`/manager/department/documents/${docId}/index`);
      fetchDocs();
      if (viewMode === "tree") fetchTree();
    } catch (err: any) {
      alert("Lỗi index: " + (err.response?.data?.detail || err.message));
    }
    setIndexingId(null);
  };

  const proposedDocIds = new Set(proposals.map(p => p.document_id));

  // Tree attach handler used as "propose" in FolderTree context
  const handleTreePropose = (doc: FolderDoc) => handlePropose(doc.id);

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-wrap justify-between items-center gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Kho Tài Liệu Phòng Ban</h1>
          <p className="text-gray-500 text-sm mt-1">Quản lý và đề xuất tài liệu lên kho công ty</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setViewMode("table")}
            className={`p-2 rounded-lg border transition ${viewMode === "table" ? "bg-blue-600 text-white border-blue-600" : "text-gray-500 hover:bg-gray-100 border-gray-200"}`}
            title="Xem dạng bảng">
            <LayoutGrid className="w-4 h-4" />
          </button>
          <button onClick={switchToTree}
            className={`p-2 rounded-lg border transition ${viewMode === "tree" ? "bg-blue-600 text-white border-blue-600" : "text-gray-500 hover:bg-gray-100 border-gray-200"}`}
            title="Xem dạng cây thư mục">
            <List className="w-4 h-4" />
          </button>

          <label className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 cursor-pointer shadow-sm transition">
            <Upload className="w-4 h-4" />
            {uploading ? "Đang tải..." : "Tải lên"}
            <input type="file" className="hidden" onChange={handleUpload} />
          </label>
        </div>
      </div>

      {/* Search + refresh (table mode) */}
      {viewMode === "table" && (
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-3 w-4 h-4 text-gray-400" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              onKeyDown={e => e.key === "Enter" && fetchDocs()}
              className="w-full pl-10 pr-4 py-2.5 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
              placeholder="Tìm tài liệu phòng ban..."
            />
          </div>
          <button onClick={fetchDocs}
            className="px-4 py-2.5 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 text-sm transition">
            Tìm
          </button>
        </div>
      )}

      {/* Table View */}
      {viewMode === "table" && (
        <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Tên file</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Trạng thái</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Ngày tải</th>
                <th className="px-4 py-3 text-right font-semibold text-gray-600">Hành động</th>
              </tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.id} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-blue-500 flex-shrink-0" />
                      <span className="truncate max-w-xs" title={d.filename}>{d.filename}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${d.is_indexed ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {d.is_indexed ? "Đã index" : "Chưa index"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500">{d.uploaded_at?.slice(0, 10)}</td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-1">
                      {!d.is_indexed && (
                        <button
                          onClick={() => handleIndex(d.id)}
                          disabled={indexingId === d.id}
                          className="px-2 py-1.5 bg-purple-50 text-purple-700 rounded-lg text-xs hover:bg-purple-100 inline-flex items-center gap-1"
                          title="Index vào RAG"
                        >
                          <BadgeCheck className="w-3.5 h-3.5" />
                          {indexingId === d.id ? "Đang index..." : "Index RAG"}
                        </button>
                      )}
                      {!proposedDocIds.has(d.id) ? (
                        <button onClick={() => handlePropose(d.id)}
                          className="px-2 py-1.5 bg-green-50 text-green-700 rounded-lg text-xs hover:bg-green-100 inline-flex items-center gap-1">
                          <Send className="w-3.5 h-3.5" /> Đề xuất SQP
                        </button>
                      ) : (
                        <span className="px-2 py-1.5 text-xs text-amber-600 bg-amber-50 rounded-lg border border-amber-200">
                          Đã đề xuất
                        </span>
                      )}
                      <button onClick={() => handleDelete(d.id)}
                        className="p-1.5 rounded-lg hover:bg-red-50 text-red-500">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {docs.length === 0 && <p className="text-center py-8 text-gray-400">Chưa có tài liệu phòng ban</p>}
        </div>
      )}

      {/* Tree View */}
      {viewMode === "tree" && (
        <div className="bg-white rounded-xl border shadow-sm p-4">
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
              onDelete={handleDelete}
              onAttach={handleTreePropose}
              onDownload={(id) => window.open(`http://localhost:8000/employee/documents/${id}/download`, "_blank")}
            />
          )}

          {!treeLoading && !treeData && (
            <p className="text-center py-8 text-gray-400 text-sm">Không thể tải dữ liệu</p>
          )}
        </div>
      )}

      {/* Proposals */}
      {proposals.length > 0 && (
        <div className="bg-white rounded-xl border shadow-sm p-6">
          <h3 className="font-semibold mb-3 text-gray-800">Đề Xuất Của Bạn</h3>
          <div className="space-y-2">
            {proposals.map((p) => (
              <div key={p.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border">
                <span className="text-sm">
                  Tài liệu #{p.document_id} —{" "}
                  <strong className={
                    p.status === "pending" ? "text-amber-600"
                    : p.status === "approved" ? "text-green-600"
                    : "text-red-600"
                  }>
                    {p.status === "pending" ? "Chờ duyệt"
                     : p.status === "approved" ? "Đã duyệt"
                     : "Từ chối"}
                  </strong>
                </span>
                {p.status === "pending" && (
                  <button onClick={() => handleCancelProposal(p.id)}
                    className="text-xs text-red-500 hover:underline">
                    Hủy
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
