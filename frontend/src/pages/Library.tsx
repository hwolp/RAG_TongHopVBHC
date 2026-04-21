import { useState, useEffect } from "react";
import api from "../api";
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
  uploaded_at: string;
};

export default function Library() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [search, setSearch] = useState("");
  const [uploading, setUploading] = useState(false);
  const [viewMode, setViewMode] = useState<"grid" | "tree">("grid");
  const [treeData, setTreeData] = useState<FolderTreeData | null>(null);
  const [treeLoading, setTreeLoading] = useState(false);

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

  useEffect(() => { fetchDocs(); }, []);

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
      await api.post("/employee/documents/upload", fd);
      fetchDocs();
      if (viewMode === "tree") fetchTree();
    } catch {}
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
    <div className="p-8 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Kho Tài Liệu Cá Nhân</h1>
          <p className="text-gray-500 text-sm mt-1">Tải lên, quản lý và tìm kiếm tài liệu của bạn</p>
        </div>
        <div className="flex items-center gap-2">
          {/* View toggle */}
          <button onClick={() => setViewMode("grid")}
            className={`p-2 rounded-lg border transition ${viewMode === "grid" ? "bg-blue-600 text-white border-blue-600" : "text-gray-500 hover:bg-gray-100 border-gray-200"}`}
            title="Xem dạng lưới">
            <LayoutGrid className="w-4 h-4" />
          </button>
          <button onClick={switchToTree}
            className={`p-2 rounded-lg border transition ${viewMode === "tree" ? "bg-blue-600 text-white border-blue-600" : "text-gray-500 hover:bg-gray-100 border-gray-200"}`}
            title="Xem dạng cây thư mục">
            <List className="w-4 h-4" />
          </button>

          {/* Upload */}
          <label className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 cursor-pointer shadow-sm transition">
            <Upload className="w-4 h-4" />
            {uploading ? "Đang tải..." : "Tải lên"}
            <input type="file" className="hidden" accept=".pdf,.docx,.doc,.txt" onChange={handleUpload} />
          </label>
        </div>
      </div>

      {/* Search (grid mode only) */}
      {viewMode === "grid" && (
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-3 w-4 h-4 text-gray-400" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              onKeyDown={e => e.key === "Enter" && fetchDocs()}
              className="w-full pl-10 pr-4 py-2.5 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
              placeholder="Tìm kiếm tài liệu..."
            />
          </div>
          <button onClick={fetchDocs}
            className="px-4 py-2.5 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 text-sm transition">
            Tìm
          </button>
        </div>
      )}

      {/* Grid View */}
      {viewMode === "grid" && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {docs.map((d) => (
              <div key={d.id} className="bg-white rounded-xl border shadow-sm p-5 hover:shadow-md transition group">
                <div className="flex items-start justify-between mb-3">
                  <div className="p-2 bg-blue-50 rounded-lg">
                    <FileText className="w-6 h-6 text-blue-600" />
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${d.is_indexed ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                    {d.is_indexed ? "Đã index" : "Chưa index"}
                  </span>
                </div>
                <h3 className="font-medium text-gray-900 truncate mb-1" title={d.filename}>{d.filename}</h3>
                <p className="text-xs text-gray-400 mb-4">{d.uploaded_at?.slice(0, 10)}</p>
                <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition">
                  <button onClick={() => handleDownload(d.id)}
                    className="flex-1 flex items-center justify-center gap-1 py-1.5 bg-blue-50 text-blue-600 rounded-lg text-xs hover:bg-blue-100">
                    <Download className="w-3.5 h-3.5" /> Tải xuống
                  </button>
                  <button onClick={() => handleDelete(d.id)}
                    className="flex items-center justify-center p-1.5 bg-red-50 text-red-500 rounded-lg hover:bg-red-100">
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
              hideCompany={false}
              hideDepartment={false}
              onDownload={handleDownload}
              onDelete={handleDelete}
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
