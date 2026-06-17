import { useState, useEffect } from "react";
import api, { waitForJob } from "../api";
import {
  Upload, Search, Send, RefreshCw, LayoutGrid, List,
  FileText, Trash2, BadgeCheck, Share2, Users, UserPlus, X, PencilLine,
} from "lucide-react";
import FolderTree, { type FolderDoc, type FolderTreeData } from "../components/FolderTree";
import { useConfirmDialog } from "../components/ConfirmDialog";
import TagSelector, { TagList, appendTagIds, type DocumentTag } from "../components/TagSelector";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";

type Department = {
  id: number;
  name: string;
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
  created_at: string;
};

type Doc = {
  id: number;
  filename: string;
  uploaded_at: string;
  owner_id: number;
  is_indexed?: boolean;
  index_status?: "indexed" | "not_indexed" | "queued" | "running" | "failed";
  tags?: DocumentTag[];
};

type Proposal = {
  id: number;
  document_id: number;
  status: string;
};

type JobResponse = {
  id: number;
  status: "queued" | "running" | "success" | "failed";
  error?: string | null;
};

export default function ManagerDocs() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [search, setSearch] = useState("");
  const [uploading, setUploading] = useState(false);
  const [showUploadDialog, setShowUploadDialog] = useState(false);
  const [selectedUploadFile, setSelectedUploadFile] = useState<File | null>(null);
  const [viewMode, setViewMode] = useState<"table" | "tree">("table");
  const [treeData, setTreeData] = useState<FolderTreeData | null>(null);
  const [treeLoading, setTreeLoading] = useState(false);
  const [indexingId, setIndexingId] = useState<number | null>(null);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [shares, setShares] = useState<ShareRecord[]>([]);
  const [shareDocId, setShareDocId] = useState<string>("");
  const [shareTargetDeptId, setShareTargetDeptId] = useState<string>("");
  const [shareTargetUsername, setShareTargetUsername] = useState("");
  const [shareMode, setShareMode] = useState<"department" | "user">("department");
  const [sharing, setSharing] = useState(false);
  const [jobMessage, setJobMessage] = useState("");
  const [selectedTagIds, setSelectedTagIds] = useState<number[]>([]);
  const [editingDoc, setEditingDoc] = useState<Doc | null>(null);
  const [editFilename, setEditFilename] = useState("");
  const [editTagIds, setEditTagIds] = useState<number[]>([]);
  const [savingEdit, setSavingEdit] = useState(false);
  const { confirm, confirmDialog } = useConfirmDialog();
  const toast = useToast();

  const refreshShares = async () => {
    try {
      const r = await api.get("/manager/shares");
      setShares(r.data);
    } catch {}
  };

  const fetchDepartments = async () => {
    try {
      const r = await api.get("/manager/departments");
      setDepartments(r.data);
      if (!shareTargetDeptId && r.data.length > 0) {
        setShareTargetDeptId(String(r.data[0].id));
      }
    } catch {}
  };

  const fetchDocs = async () => {
    try {
      const r = await api.get(`/manager/department/documents?search=${encodeURIComponent(search)}`);
      setDocs(r.data);
      if (!shareDocId && r.data.length > 0) {
        setShareDocId(String(r.data[0].id));
      }
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

  useEffect(() => {
    fetchDocs();
    fetchProposals();
    fetchDepartments();
    refreshShares();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const switchToTree = () => {
    setViewMode("tree");
    fetchTree();
  };

  const waitIndexJob = async (jobId: number) => {
    setJobMessage("Tài liệu đã được đưa vào hàng đợi index...");
    try {
      const job = await waitForJob<JobResponse>(jobId);
      if (job.status === "success") {
        setJobMessage("Index tài liệu phòng ban hoàn tất.");
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

  const handleUpload = async () => {
    if (!selectedUploadFile) return;
    setUploading(true);
    setJobMessage("");
    const fd = new FormData();
    fd.append("file", selectedUploadFile);
    appendTagIds(fd, selectedTagIds);
    try {
      const r = await api.post("/manager/department/documents/upload", fd);
      setSelectedUploadFile(null);
      setSelectedTagIds([]);
      setShowUploadDialog(false);
      await fetchDocs();
      if (viewMode === "tree") fetchTree();
      if (r.data.job_id) {
        void waitIndexJob(r.data.job_id);
      } else {
        setJobMessage("Tải lên hoàn tất. File này chưa cần index nền.");
      }
    } catch {}
    setUploading(false);
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
      const response = await api.put(`/manager/department/documents/${editingDoc.id}`, {
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

  const handleDelete = async (id: number, _scope?: string) => {
    const ok = await confirm({
      title: "Xóa tài liệu?",
      description: "Tài liệu phòng ban sẽ bị xóa khỏi hệ thống.",
      confirmText: "Xóa tài liệu",
    });
    if (!ok) return;
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
      toast({ title: "Đã gửi đề xuất lên Admin", variant: "success" });
    } catch (err: any) {
      toast({
        title: "Lỗi gửi đề xuất",
        description: err.response?.data?.detail || err.message,
        variant: "destructive",
      });
    }
  };

  const handleCancelProposal = async (id: number) => {
    try { await api.delete(`/manager/sqp/proposals/${id}`); fetchProposals(); } catch {}
  };

  // Index (trigger RAG indexing) cho tài liệu phòng ban
  const handleIndex = async (docId: number) => {
    setIndexingId(docId);
    setJobMessage("");
    try {
      const r = await api.post(`/manager/department/documents/${docId}/index`);
      await fetchDocs();
      if (viewMode === "tree") fetchTree();
      if (r.data.job_id) {
        void waitIndexJob(r.data.job_id);
      } else {
        setJobMessage(r.data.status === "already_indexed" ? "Tài liệu đã được index trước đó." : "Đã gửi yêu cầu index.");
      }
    } catch (err: any) {
      toast({
        title: "Lỗi index",
        description: err.response?.data?.detail || err.message,
        variant: "destructive",
      });
    }
    setIndexingId(null);
  };

  const handleShare = async () => {
    if (!shareDocId) return;
    if (shareMode === "department" && !shareTargetDeptId) return;
    if (shareMode === "user" && !shareTargetUsername.trim()) return;

    setSharing(true);
    try {
      if (shareMode === "department") {
        await api.post(`/manager/share/document/${shareDocId}/to-dept/${shareTargetDeptId}`);
      } else {
        await api.post(`/manager/share/document/${shareDocId}/to-user/${encodeURIComponent(shareTargetUsername.trim())}`);
      }
      await refreshShares();
      toast({ title: "Đã chia sẻ tài liệu", variant: "success" });
    } catch (err: any) {
      toast({
        title: "Lỗi chia sẻ",
        description: err.response?.data?.detail || err.message,
        variant: "destructive",
      });
    }
    setSharing(false);
  };

  const handleRevokeShare = async (shareId: number) => {
    const ok = await confirm({
      title: "Hủy chia sẻ tài liệu này?",
      description: "Người nhận sẽ không còn thấy tài liệu qua lượt chia sẻ này.",
      confirmText: "Hủy chia sẻ",
      variant: "warning",
    });
    if (!ok) return;
    try {
      await api.delete(`/manager/share/${shareId}`);
      await refreshShares();
    } catch (err: any) {
      toast({
        title: "Lỗi hủy chia sẻ",
        description: err.response?.data?.detail || err.message,
        variant: "destructive",
      });
    }
  };

  const proposedDocIds = new Set(proposals.map(p => p.document_id));

  const renderIndexBadge = (doc: Doc) => {
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

  // Tree attach handler used as "propose" in FolderTree context
  const handleTreePropose = (doc: FolderDoc) => handlePropose(doc.id);
  const fieldClass = "w-full rounded-lg border border-input bg-background/80 px-3 py-2.5 text-sm shadow-sm outline-none focus:ring-2 focus:ring-ring";

  return (
    <div className="app-page max-w-6xl">
      {confirmDialog}
      <Dialog
        open={showUploadDialog}
        onOpenChange={(open) => {
          setShowUploadDialog(open);
          if (!open && !uploading) {
            setSelectedUploadFile(null);
            setSelectedTagIds([]);
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Tải lên tài liệu phòng ban</DialogTitle>
            <DialogDescription>Chọn file và gắn tag trước khi đưa vào kho phòng ban.</DialogDescription>
          </DialogHeader>
          <label className="soft-panel flex cursor-pointer items-center justify-between gap-3 p-4 text-sm">
            <span className="truncate text-muted-foreground">{selectedUploadFile ? selectedUploadFile.name : "Chọn file..."}</span>
            <span className="text-xs font-medium text-primary">Browse</span>
            <input
              type="file"
              className="hidden"
              onChange={(event) => setSelectedUploadFile(event.target.files?.[0] ?? null)}
            />
          </label>
          <TagSelector value={selectedTagIds} onChange={setSelectedTagIds} />
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setShowUploadDialog(false)} disabled={uploading}>
              Hủy
            </Button>
            <Button type="button" onClick={() => void handleUpload()} disabled={!selectedUploadFile || uploading}>
              <Upload className="h-4 w-4" />
              {uploading ? "Đang tải..." : "Tải lên"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
      <Dialog open={Boolean(editingDoc)} onOpenChange={(open) => !open && setEditingDoc(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Chỉnh sửa tài liệu phòng ban</DialogTitle>
            <DialogDescription>Đổi tên file và cập nhật tag của tài liệu phòng ban.</DialogDescription>
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
      {/* Header */}
      <div className="flex flex-wrap justify-between items-center gap-3">
        <div>
          <h1 className="text-2xl font-bold">Kho Tài Liệu Phòng Ban</h1>
          <p className="mt-1 text-sm text-muted-foreground">Quản lý và đề xuất tài liệu lên kho công ty</p>
        </div>
        <div className="flex items-center gap-2">
          <Button type="button" variant={viewMode === "table" ? "default" : "outline"} size="icon"
            onClick={() => setViewMode("table")}
            title="Xem dạng bảng">
            <LayoutGrid className="w-4 h-4" />
          </Button>
          <Button type="button" variant={viewMode === "tree" ? "default" : "outline"} size="icon"
            onClick={switchToTree}
            title="Xem dạng cây thư mục">
            <List className="w-4 h-4" />
          </Button>

          <Button
            type="button"
            onClick={() => setShowUploadDialog(true)}
          >
            <Upload className="w-4 h-4" />
            {uploading ? "Đang tải..." : "Tải lên"}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <Card className="glass-panel p-6 space-y-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Share2 className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-semibold">Chia sẻ liên phòng</h2>
              <p className="mt-1 text-sm text-muted-foreground">Chọn tài liệu phòng ban của bạn rồi chia sẻ sang phòng khác hoặc một tài khoản cụ thể.</p>
            </div>
          </div>

          <div className="grid gap-3">
            <select
              value={shareDocId}
              onChange={(event) => setShareDocId(event.target.value)}
              className={fieldClass}
            >
              {docs.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  #{doc.id} - {doc.filename}
                </option>
              ))}
            </select>

            <div className="grid grid-cols-2 overflow-hidden rounded-lg border bg-background/60 text-sm">
              <Button
                type="button"
                variant={shareMode === "department" ? "default" : "ghost"}
                onClick={() => setShareMode("department")}
                className="rounded-none"
              >
                Chia sẻ phòng ban
              </Button>
              <Button
                type="button"
                variant={shareMode === "user" ? "default" : "ghost"}
                onClick={() => setShareMode("user")}
                className="rounded-none"
              >
                Chia sẻ user
              </Button>
            </div>

            {shareMode === "department" ? (
              <select
                value={shareTargetDeptId}
                onChange={(event) => setShareTargetDeptId(event.target.value)}
                className={fieldClass}
              >
                {departments.map((department) => (
                  <option key={department.id} value={department.id}>
                    {department.name}
                  </option>
                ))}
              </select>
            ) : (
              <input
                value={shareTargetUsername}
                onChange={(event) => setShareTargetUsername(event.target.value)}
                className={fieldClass}
                placeholder="Nhập username người nhận"
              />
            )}

            <Button
              type="button"
              onClick={() => void handleShare()}
              disabled={sharing || !shareDocId || (shareMode === "department" ? !shareTargetDeptId : !shareTargetUsername.trim())}
              className="w-full"
            >
              <UserPlus className="w-4 h-4" />
              {sharing ? "Đang chia sẻ..." : "Gửi chia sẻ"}
            </Button>
          </div>
        </Card>

        <Card className="glass-panel p-6 space-y-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Users className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-semibold">Chia sẻ của tôi</h2>
              <p className="mt-1 text-sm text-muted-foreground">Theo dõi các lượt chia sẻ liên phòng đã tạo từ tài liệu phòng ban của mình.</p>
            </div>
          </div>

          <div className="overflow-hidden rounded-lg border bg-background/50">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tài liệu</TableHead>
                  <TableHead>Chia sẻ tới</TableHead>
                  <TableHead className="text-right">Hành động</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {shares.map((share) => (
                  <TableRow key={share.id}>
                    <TableCell className="font-medium">{share.document_filename}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {share.shared_with_department_name ? `Phòng: ${share.shared_with_department_name}` : share.shared_with_username ? `User: ${share.shared_with_username}` : "—"}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => void handleRevokeShare(share.id)}
                        className="text-destructive"
                      >
                        <X className="w-3.5 h-3.5" />
                        Hủy
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                {shares.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={3} className="py-10 text-center text-muted-foreground">
                      Chưa có lượt chia sẻ nào
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </Card>
      </div>

      {/* Search + refresh (table mode) */}
      {jobMessage && (
        <Card className="glass-panel px-4 py-3 text-sm text-primary">
          {jobMessage}
        </Card>
      )}

      {/* Search + refresh (table mode) */}
      {viewMode === "table" && (
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-3 w-4 h-4 text-muted-foreground" />
            <Input
              value={search}
              onChange={e => setSearch(e.target.value)}
              onKeyDown={e => e.key === "Enter" && fetchDocs()}
              className="pl-10"
              placeholder="Tìm tài liệu phòng ban..."
            />
          </div>
          <Button type="button" variant="outline" onClick={fetchDocs}>
            Tìm
          </Button>
        </div>
      )}

      {/* Table View */}
      {viewMode === "table" && (
        <Card className="glass-panel overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Tên file</TableHead>
                <TableHead>Trạng thái</TableHead>
                <TableHead>Ngày tải</TableHead>
                <TableHead className="text-right">Hành động</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {docs.map((d) => (
                <TableRow key={d.id}>
                  <TableCell className="font-medium">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-primary flex-shrink-0" />
                      <div className="min-w-0">
                        <span className="block truncate max-w-xs" title={d.filename}>{d.filename}</span>
                        <TagList tags={d.tags} showEmpty className="mt-1" />
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    {renderIndexBadge(d)}
                  </TableCell>
                  <TableCell className="text-muted-foreground">{d.uploaded_at?.slice(0, 10)}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      {!d.is_indexed && (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => handleIndex(d.id)}
                          disabled={indexingId === d.id}
                          title="Index vào RAG"
                        >
                          <BadgeCheck className="w-3.5 h-3.5" />
                          {indexingId === d.id ? "Đang index..." : "Index RAG"}
                        </Button>
                      )}
                      {!proposedDocIds.has(d.id) ? (
                        <Button type="button" variant="outline" size="sm" onClick={() => handlePropose(d.id)}
                          className="text-emerald-700">
                          <Send className="w-3.5 h-3.5" /> Đề xuất SQP
                        </Button>
                      ) : (
                        <Badge variant="warning">
                          Đã đề xuất
                        </Badge>
                      )}
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => openEdit(d)}
                      >
                        <PencilLine className="w-3.5 h-3.5" /> Sửa
                      </Button>
                      <Button type="button" variant="ghost" size="icon-sm" onClick={() => handleDelete(d.id)}
                        className="text-destructive">
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {docs.length === 0 && <p className="text-center py-8 text-muted-foreground">Chưa có tài liệu phòng ban</p>}
        </Card>
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
            <div className="flex items-center justify-center py-12 text-muted-foreground gap-2">
              <RefreshCw className="w-5 h-5 animate-spin" />
              <span>Đang tải...</span>
            </div>
          )}

          {!treeLoading && treeData && (
            <FolderTree
              data={treeData}
              onDelete={handleDelete}
              canDelete={(doc) => doc.scope === "department"}
              onAttach={handleTreePropose}
              onDownload={(id) => window.open(`http://localhost:8000/employee/documents/${id}/download`, "_blank")}
            />
          )}

          {!treeLoading && !treeData && (
            <p className="text-center py-8 text-muted-foreground text-sm">Không thể tải dữ liệu</p>
          )}
        </Card>
      )}

      {/* Proposals */}
      {proposals.length > 0 && (
        <Card className="glass-panel p-6">
          <h3 className="mb-3 font-semibold">Đề Xuất Của Bạn</h3>
          <div className="space-y-2">
            {proposals.map((p) => (
              <div key={p.id} className="soft-panel flex items-center justify-between p-3">
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
                  <Button type="button" variant="ghost" size="sm" onClick={() => handleCancelProposal(p.id)}
                    className="text-destructive">
                    Hủy
                  </Button>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
