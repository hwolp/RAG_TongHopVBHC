import { useState, useEffect } from "react";
import api, { waitForJob } from "../api";
import {
  FileText, Upload, Trash2, Download, Search,
  LayoutGrid, List, RefreshCw, PencilLine,
} from "lucide-react";
import FolderTree, { type FolderTreeData } from "../components/FolderTree";
import { useConfirmDialog } from "../components/ConfirmDialog";
import TagSelector, { TagList, appendTagIds, type DocumentTag } from "../components/TagSelector";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";

type Doc = {
  id: number;
  filename: string;
  scope: string;
  is_indexed: boolean;
  index_status?: "indexed" | "not_indexed" | "queued" | "running" | "failed";
  uploaded_at: string;
  tags?: DocumentTag[];
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
  const [selectedTagIds, setSelectedTagIds] = useState<number[]>([]);
  const [editingDoc, setEditingDoc] = useState<Doc | null>(null);
  const [editFilename, setEditFilename] = useState("");
  const [editTagIds, setEditTagIds] = useState<number[]>([]);
  const [savingEdit, setSavingEdit] = useState(false);
  const { confirm, confirmDialog } = useConfirmDialog();

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
    const labels: Record<string, string> = {
      indexed: "Đã index",
      queued: "Chờ index",
      running: "Đang index",
      failed: "Index lỗi",
      not_indexed: "Chưa index",
    };
    const variant = status === "indexed" ? "success" : status === "queued" || status === "running" ? "warning" : status === "failed" ? "destructive" : "secondary";
    return <Badge variant={variant}>{labels[status] || labels.not_indexed}</Badge>;
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.[0]) return;
    setJobMessage("");
    setUploading(true);
    const fd = new FormData();
    fd.append("file", e.target.files[0]);
    appendTagIds(fd, selectedTagIds);
    try {
      const r = await api.post("/employee/documents/upload", fd);
      setSelectedTagIds([]);
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
    const ok = await confirm({
      title: "Xóa tài liệu này?",
      description: "Tài liệu sẽ bị xóa khỏi kho cá nhân.",
      confirmText: "Xóa tài liệu",
    });
    if (!ok) return;
    try {
      await api.delete(`/employee/documents/${id}`);
      fetchDocs();
      if (viewMode === "tree") fetchTree();
    } catch {}
  };

  const handleDownload = (id: number) => {
    window.open(`http://localhost:8000/employee/documents/${id}/download`, "_blank");
  };

  const openEdit = (doc: Doc) => {
    setEditingDoc(doc);
    setEditFilename(doc.filename);
    setEditTagIds((doc.tags ?? []).map((tag) => tag.id));
  };

  const handleSaveEdit = async () => {
    if (!editingDoc) return;
    setSavingEdit(true);
    try {
      const response = await api.put(`/employee/documents/${editingDoc.id}`, {
        filename: editFilename,
        tag_ids: editTagIds,
      });
      setEditingDoc(null);
      await fetchDocs();
      if (viewMode === "tree") await fetchTree();
      if (response.data.job_id) {
        void waitIndexJob(response.data.job_id);
      }
    } finally {
      setSavingEdit(false);
    }
  };

  return (
    <div className="app-page max-w-6xl">
      {confirmDialog}
      <Dialog open={Boolean(editingDoc)} onOpenChange={(open) => !open && setEditingDoc(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Chỉnh sửa tài liệu cá nhân</DialogTitle>
            <DialogDescription>Đổi tên file và cập nhật tag cho tài liệu.</DialogDescription>
          </DialogHeader>
          <Input
            value={editFilename}
            onChange={(event) => setEditFilename(event.target.value)}
            placeholder="Tên file"
          />
          <TagSelector value={editTagIds} onChange={setEditTagIds} />
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setEditingDoc(null)}>
              Hủy
            </Button>
            <Button type="button" onClick={() => void handleSaveEdit()} disabled={savingEdit}>
              {savingEdit ? "Đang lưu..." : "Lưu thay đổi"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Kho Tài Liệu Cá Nhân</h1>
          <p className="mt-1 text-sm text-muted-foreground">Tải lên, quản lý và tìm kiếm tài liệu của bạn</p>
        </div>
        <div className="flex items-center gap-2">
          <Button type="button" variant={viewMode === "grid" ? "default" : "outline"} size="icon"
            onClick={() => setViewMode("grid")}
            title="Xem dạng lưới">
            <LayoutGrid className="w-4 h-4" />
          </Button>
          <Button type="button" variant={viewMode === "tree" ? "default" : "outline"} size="icon"
            onClick={switchToTree}
            title="Xem dạng cây thư mục">
            <List className="w-4 h-4" />
          </Button>

          <Dialog>
            <DialogTrigger>
              <Button type="button">
                <Upload className="w-4 h-4" />
                Tải lên
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Tải lên tài liệu</DialogTitle>
                <DialogDescription>Chọn file PDF, Word hoặc TXT để thêm vào kho cá nhân.</DialogDescription>
              </DialogHeader>
              <label className="soft-panel flex cursor-pointer items-center justify-between gap-3 p-4 text-sm">
                <span className="text-muted-foreground">Chọn file từ máy tính</span>
                <span className="font-medium text-primary">Browse</span>
                <input type="file" className="hidden" accept=".pdf,.docx,.doc,.txt" onChange={handleUpload} />
              </label>
              <TagSelector value={selectedTagIds} onChange={setSelectedTagIds} />
              {uploading && <Progress value={65} className="mt-1" />}
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {jobMessage && (
        <Card className="glass-panel px-4 py-3 text-sm text-primary">
          {jobMessage}
        </Card>
      )}

      {viewMode === "grid" && (
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-3 w-4 h-4 text-gray-400" />
            <Input
              value={search}
              onChange={e => setSearch(e.target.value)}
              onKeyDown={e => e.key === "Enter" && fetchDocs()}
              className="pl-10"
              placeholder="Tìm kiếm tài liệu..."
            />
          </div>
          <Button type="button" variant="outline" onClick={fetchDocs}>
            Tìm
          </Button>
        </div>
      )}

      {/* Grid View */}
      {viewMode === "grid" && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {docs.map((d) => (
              <Card key={d.id} className="glass-panel group transition hover:-translate-y-0.5">
                <CardHeader className="pb-3">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-primary/10">
                    <FileText className="w-6 h-6 text-[#006666]" />
                  </div>
                  {indexBadge(d)}
                </div>
                  <CardTitle className="truncate text-base" title={d.filename}>{d.filename}</CardTitle>
                  <CardDescription>{d.uploaded_at?.slice(0, 10)}</CardDescription>
                  <TagList tags={d.tags} showEmpty className="pt-1" />
                </CardHeader>
                <CardContent>
                <div className="flex gap-2 opacity-0 transition group-hover:opacity-100">
                  <Button type="button" variant="outline" size="sm" onClick={() => handleDownload(d.id)}
                    className="flex-1">
                    <Download className="w-3.5 h-3.5" /> Tải xuống
                  </Button>
                  <Button type="button" variant="outline" size="icon-sm" onClick={() => openEdit(d)}
                    title="Sửa tên và tag">
                    <PencilLine className="w-3.5 h-3.5" />
                  </Button>
                  <Button type="button" variant="ghost" size="icon-sm" onClick={() => handleDelete(d.id)}
                    className="text-destructive">
                    <Trash2 className="w-3.5 h-3.5" />
                  </Button>
                </div>
                </CardContent>
              </Card>
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
        <Card className="glass-panel p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold">Cây thư mục tài liệu</h2>
            <Button type="button" variant="ghost" size="sm" onClick={fetchTree} disabled={treeLoading}>
              <RefreshCw className={`w-3.5 h-3.5 ${treeLoading ? "animate-spin" : ""}`} />
              Làm mới
            </Button>
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
        </Card>
      )}
    </div>
  );
}
