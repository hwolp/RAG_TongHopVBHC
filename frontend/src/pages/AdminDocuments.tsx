import { useEffect, useMemo, useState } from "react";
import api, { waitForJob } from "../api";
import { FileText, RefreshCw, Search, Share2, Trash2, Upload, PencilLine } from "lucide-react";
import { useConfirmDialog } from "../components/ConfirmDialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

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
  const { confirm, confirmDialog } = useConfirmDialog();

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
    const ok = await confirm({
      title: "Xóa tài liệu này?",
      description: "Tài liệu phòng ban sẽ bị xóa khỏi hệ thống.",
      confirmText: "Xóa tài liệu",
    });
    if (!ok) return;
    await api.delete(`/admin/documents/department/${docId}`);
    await refreshAll();
  };

  return (
    <div className="app-page">
      {confirmDialog}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Quản Lý Tài Liệu & Chia Sẻ Liên Phòng</h1>
          <p className="text-sm text-muted-foreground mt-1">Tải lên, đổi tên, gán phòng ban và chia sẻ tài liệu giữa các phòng ban.</p>
        </div>
        <Button
          type="button"
          variant="outline"
          onClick={() => void refreshAll()}
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Làm mới
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="glass-panel p-5">
          <p className="text-xs uppercase tracking-widest text-gray-400">Tài liệu</p>
          <p className="mt-2 text-3xl font-bold text-blue-600">{documents.length}</p>
          <p className="text-sm text-gray-500 mt-1">tài liệu phòng ban đang quản lý</p>
        </Card>
        <Card className="glass-panel p-5">
          <p className="text-xs uppercase tracking-widest text-gray-400">Chia sẻ</p>
          <p className="mt-2 text-3xl font-bold text-emerald-600">{shares.length}</p>
          <p className="text-sm text-gray-500 mt-1">lượt chia sẻ đang còn hiệu lực</p>
        </Card>
        <Card className="glass-panel p-5">
          <p className="text-xs uppercase tracking-widest text-gray-400">Phòng ban</p>
          <p className="mt-2 text-3xl font-bold text-amber-600">{departments.length}</p>
          <p className="text-sm text-gray-500 mt-1">đơn vị có trong hệ thống</p>
        </Card>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <Card className="glass-panel p-6 space-y-4">
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
          <Button
            type="button"
            onClick={() => void handleUpload()}
            disabled={!selectedFile || !selectedDepartmentId || uploading}
          >
            <Upload className="w-4 h-4" />
            {uploading ? "Đang tải lên..." : "Tải lên"}
          </Button>
          {uploading && <Progress value={65} />}
        </Card>
      </div>

      {jobMessage && (
        <Card className="glass-panel px-4 py-3 text-sm text-primary">
          {jobMessage}
        </Card>
      )}

      <Card className="glass-panel overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 p-5 border-b">
          <div>
            <h2 className="font-semibold text-gray-900">Danh Sách Tài Liệu Phòng Ban</h2>
            <p className="text-sm text-gray-500 mt-1">Quản lý file, đổi tên và đổi phòng ban lưu trữ.</p>
          </div>
          <div className="flex items-center gap-2 w-full md:w-auto md:min-w-80">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-3 w-4 h-4 text-gray-400" />
              <Input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                onKeyDown={(event) => event.key === "Enter" && void handleSearch()}
                className="pl-10"
                placeholder="Tìm file hoặc ghi chú chia sẻ..."
              />
            </div>
            <Button
              type="button"
              variant="outline"
              onClick={() => void handleSearch()}
            >
              Tìm
            </Button>
          </div>
        </div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Tài liệu</TableHead>
              <TableHead>Phòng ban</TableHead>
              <TableHead>Index</TableHead>
              <TableHead>Ngày tải</TableHead>
              <TableHead className="text-right">Hành động</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {documents.map((document) => (
              <TableRow key={document.id}>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-blue-500 flex-shrink-0" />
                    <span className="font-medium truncate max-w-sm" title={document.filename}>
                      {document.filename}
                    </span>
                  </div>
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {document.department_id ? departmentNameMap.get(document.department_id) ?? `#${document.department_id}` : "—"}
                </TableCell>
                <TableCell>{renderIndexBadge(document)}</TableCell>
                <TableCell className="text-muted-foreground">{document.uploaded_at?.slice(0, 10)}</TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end gap-1">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => openEditModal(document)}
                    >
                      <PencilLine className="w-3.5 h-3.5" />
                      Sửa
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => void handleDeleteDocument(document.id)}
                      className="text-destructive"
                      title="Xóa"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {documents.length === 0 && <p className="text-center py-8 text-gray-400">Không có tài liệu phòng ban</p>}
      </Card>

      <Card className="glass-panel overflow-hidden">
        <div className="p-5 border-b flex items-center gap-3">
          <Share2 className="w-5 h-5 text-emerald-600" />
          <div>
            <h2 className="font-semibold text-gray-900">Lượt Chia Sẻ Đang Quản Lý</h2>
            <p className="text-sm text-gray-500 mt-1">Chỉ xem danh sách; thao tác chia sẻ thực hiện ở trang của trưởng phòng.</p>
          </div>
        </div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Tài liệu</TableHead>
              <TableHead>Chia sẻ tới</TableHead>
              <TableHead>Người tạo</TableHead>
              <TableHead className="text-right">Hành động</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {shares.map((share) => (
              <TableRow key={share.id}>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Share2 className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                    <div>
                      <p className="font-medium">{share.document_filename}</p>
                      <p className="text-xs text-gray-400">
                        {share.document_department_name ? `Phòng ban nguồn: ${share.document_department_name}` : `Tài liệu #${share.document_id}`}
                      </p>
                    </div>
                  </div>
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {share.shared_with_department_name
                    ? `Phòng ban: ${share.shared_with_department_name}`
                    : share.shared_with_username
                      ? `User: ${share.shared_with_username}`
                      : "—"}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {share.shared_by_username ?? `#${share.shared_by}`}
                </TableCell>
                <TableCell className="text-right text-xs text-muted-foreground">
                  Chỉ xem
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {shares.length === 0 && <p className="text-center py-8 text-gray-400">Chưa có lượt chia sẻ nào</p>}
      </Card>

      <Dialog open={Boolean(editingDoc)} onOpenChange={(open) => !open && setEditingDoc(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Chỉnh sửa tài liệu</DialogTitle>
            <DialogDescription>Đổi tên file hoặc gán sang phòng ban khác.</DialogDescription>
          </DialogHeader>
            <Input
              value={editForm.filename}
              onChange={(event) => setEditForm((current) => ({ ...current, filename: event.target.value }))}
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
              <Button type="button" variant="outline" onClick={() => setEditingDoc(null)}>
                Hủy
              </Button>
              <Button
                type="button"
                onClick={() => void handleSaveEdit()}
                disabled={saving}
              >
                {saving ? "Đang lưu..." : "Lưu thay đổi"}
              </Button>
            </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
