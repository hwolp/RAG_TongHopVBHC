import { useEffect, useMemo, useState } from "react";
import api, { waitForJob } from "../api";
import { BookOpen, Search, Download, FileText, RefreshCw, Upload, PencilLine, Trash2 } from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import { useConfirmDialog } from "../components/ConfirmDialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

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
  const { confirm, confirmDialog } = useConfirmDialog();

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
    const ok = await confirm({
      title: "Xóa tài liệu SQP này?",
      description: "Tài liệu SQP sẽ bị xóa khỏi kho quy định.",
      confirmText: "Xóa tài liệu",
    });
    if (!ok) return;
    await api.delete(`/documents/sqp/${docId}`);
    await fetchDocs();
  };

  return (
    <div className="app-page max-w-6xl">
      {confirmDialog}
      <div className="flex flex-wrap justify-between items-center gap-3">
        <div>
          <h1 className="text-2xl font-bold">Quy Định & Biểu Mẫu Công Ty (SQP)</h1>
          <p className="text-muted-foreground text-sm mt-1">
            {isAdmin ? "Quản lý CRUD tài liệu SQP" : "Tra cứu các tài liệu dùng chung đã được phê duyệt"}
          </p>
        </div>
        <Button
          type="button"
          variant="outline"
          onClick={() => void fetchDocs()}
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Làm mới
        </Button>
      </div>

      {isAdmin && (
        <Card className="glass-panel p-5 space-y-4">
          <div className="flex items-center gap-3">
            <Upload className="w-5 h-5 text-blue-600" />
            <h2 className="font-semibold text-gray-900">Tải lên tài liệu SQP</h2>
          </div>
          <div className="flex flex-wrap gap-3 items-center">
            <label className="flex-1 min-w-64 border rounded-lg px-3 py-2.5 text-sm bg-gray-50 cursor-pointer flex items-center justify-between gap-3">
              <span className="truncate text-gray-600">{selectedFile ? selectedFile.name : "Chọn file..."}</span>
              <span className="text-xs text-blue-600 font-medium whitespace-nowrap">Browse</span>
              <input type="file" className="hidden" onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)} />
            </label>
            <Button
              type="button"
              onClick={() => void handleUpload()}
              disabled={!selectedFile || uploading}
            >
              <Upload className="w-4 h-4" />
              {uploading ? "Đang tải lên..." : "Tải lên"}
            </Button>
          </div>
          {uploading && <Progress value={65} />}
        </Card>
      )}

      {jobMessage && (
        <Card className="glass-panel px-4 py-3 text-sm text-primary">
          {jobMessage}
        </Card>
      )}

      <div className="relative">
        <Search className="absolute left-3 top-3 w-4 h-4 text-gray-400" />
        <Input
          value={search} 
          onChange={e => setSearch(e.target.value)} 
          onKeyDown={e => e.key === "Enter" && fetchDocs()}
          className="pl-10" 
          placeholder="Tìm kiếm quy định, chính sách, biểu mẫu..." 
        />
      </div>

      <Card className="glass-panel overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Tên tài liệu</TableHead>
              <TableHead>Index</TableHead>
              <TableHead>Ngày ban hành (Upload)</TableHead>
              <TableHead className="text-right">Hành động</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredDocs.map((d) => (
              <TableRow key={d.id}>
                <TableCell className="font-medium">
                  <div className="flex items-center gap-3">
                  <div className="p-2 bg-amber-50 rounded-lg"><BookOpen className="w-5 h-5 text-amber-600" /></div>
                  <span>{d.filename}</span>
                  </div>
                </TableCell>
                <TableCell>{renderIndexBadge(d)}</TableCell>
                <TableCell className="text-muted-foreground">{d.uploaded_at?.slice(0, 10)}</TableCell>
                <TableCell className="text-right">
                  <div className="flex items-center justify-end gap-2">
                    <Button type="button" variant="outline" size="sm" onClick={() => handleDownload(d.id)}>
                      <Download className="w-3.5 h-3.5" /> Tải về
                    </Button>
                    {isAdmin && (
                      <>
                        <Button type="button" variant="outline" size="sm" onClick={() => openEdit(d)}>
                          <PencilLine className="w-3.5 h-3.5" /> Sửa
                        </Button>
                        <Button type="button" variant="ghost" size="icon-sm" onClick={() => void handleDelete(d.id)} className="text-destructive" title="Xóa">
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {docs.length === 0 && (
          <div className="text-center py-16 text-gray-400">
            <FileText className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p>Không tìm thấy quy định nào.</p>
          </div>
        )}
      </Card>

      <Dialog open={Boolean(editingDoc && isAdmin)} onOpenChange={(open) => !open && setEditingDoc(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Chỉnh sửa tài liệu SQP</DialogTitle>
            <DialogDescription>Đổi tên file SQP.</DialogDescription>
          </DialogHeader>
            <Input
              value={editFilename}
              onChange={(event) => setEditFilename(event.target.value)}
              placeholder="Tên file"
            />
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setEditingDoc(null)}>
                Hủy
              </Button>
              <Button type="button" onClick={() => void handleSaveEdit()}>
                Lưu thay đổi
              </Button>
            </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
