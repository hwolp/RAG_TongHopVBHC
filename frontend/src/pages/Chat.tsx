import { useState, useEffect, useRef, useCallback } from "react";
import api, { waitForJob } from "../api";
import {
  Send, Bot, User, Plus, Trash2, MessageSquare,
  FolderOpen, X, Upload, RefreshCw, Pencil, Check, ChevronsLeft, ChevronsRight, FileText,
} from "lucide-react";
import FolderTree, { type FolderDoc, type FolderTreeData } from "../components/FolderTree";
import { useConfirmDialog } from "../components/ConfirmDialog";
import TagSelector, { TagList, appendTagIds, type DocumentTag } from "../components/TagSelector";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/utils";

// ──────────────────────────────────────────────────────────────────────────────
type ChatMessage = {
  id: number;
  sender: "user" | "ai";
  content: string;
  sources?: string;
  created_at?: string;
  job_id?: number;
  job_status?: JobResponse["status"];
  job_progress?: number;
};

type MessagePage = {
  items: ChatMessage[];
  has_more: boolean;
  next_before_id: number | null;
};

type AttachedDoc = {
  doc_id: number;
  filename: string;
  scope: string;
  is_indexed: boolean;
  index_status?: "indexed" | "not_indexed" | "queued" | "running" | "failed";
  tags?: DocumentTag[];
};

type JobResponse = {
  id: number;
  status: "queued" | "running" | "success" | "failed";
  progress: number;
  result?: {
    answer?: string;
    sources?: string[];
    message_id?: number;
  } | null;
  error?: string | null;
};

// ──────────────────────────────────────────────────────────────────────────────
export default function Chat() {
  const [sessions, setSessions] = useState<any[]>([]);
  const [activeSession, setActiveSession] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const [hasMoreMessages, setHasMoreMessages] = useState(false);
  const [nextBeforeId, setNextBeforeId] = useState<number | null>(null);

  // File picker modal
  const [showPicker, setShowPicker] = useState(false);
  const [treeData, setTreeData] = useState<FolderTreeData | null>(null);
  const [treeLoading, setTreeLoading] = useState(false);

  // Attached docs
  const [attachedDocs, setAttachedDocs] = useState<AttachedDoc[]>([]);

  // Session documents (uploaded to current session)
  const [sessionDocs, setSessionDocs] = useState<any[]>([]);
  const [showUploadDialog, setShowUploadDialog] = useState(false);
  const [selectedUploadFile, setSelectedUploadFile] = useState<File | null>(null);
  const [selectedUploadTagIds, setSelectedUploadTagIds] = useState<number[]>([]);

  // Rename session
  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [renameInput, setRenameInput] = useState("");
  const [sessionsCollapsed, setSessionsCollapsed] = useState(() => (
    localStorage.getItem("ragGovSessionsCollapsed") === "true"
  ));
  const [docsPanelCollapsed, setDocsPanelCollapsed] = useState(() => (
    localStorage.getItem("ragGovDocsPanelCollapsed") === "true"
  ));

  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const waitingJobsRef = useRef<Set<number>>(new Set());
  const { confirm, confirmDialog } = useConfirmDialog();
  const toast = useToast();

  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });

  // ── Sessions ────────────────────────────────────────────────────────────────
  const fetchSessions = useCallback(async () => {
    try { const r = await api.get("/employee/sessions"); setSessions(r.data); } catch {}
  }, []);

  useEffect(() => { fetchSessions(); }, [fetchSessions]);
  useEffect(() => {
    localStorage.setItem("ragGovSessionsCollapsed", String(sessionsCollapsed));
  }, [sessionsCollapsed]);
  useEffect(() => {
    localStorage.setItem("ragGovDocsPanelCollapsed", String(docsPanelCollapsed));
  }, [docsPanelCollapsed]);

  const fetchSessionMessages = async (sessionId: number, beforeId?: number | null): Promise<MessagePage> => {
    const params: Record<string, number> = { limit: 5 };
    if (beforeId) params.before_id = beforeId;
    const r = await api.get(`/employee/sessions/${sessionId}/messages`, { params });
    return r.data;
  };

  const fetchAttachments = async (sessionId: number) => {
    try {
      const r = await api.get(`/chat/sessions/${sessionId}/attachments`);
      setAttachedDocs(r.data ?? []);
    } catch { setAttachedDocs([]); }
  };

  const fetchSessionDocs = async (sessionId: number) => {
    try {
      const r = await api.get(`/chat/sessions/${sessionId}/documents`);
      setSessionDocs(r.data ?? []);
    } catch { setSessionDocs([]); }
  };

  const loadSession = async (id: number) => {
    setActiveSession(id);
    setHasMoreMessages(false);
    setNextBeforeId(null);
    setShowPicker(false);
    try {
      const page = await fetchSessionMessages(id);
      setMessages(page.items || []);
      setHasMoreMessages(Boolean(page.has_more));
      setNextBeforeId(page.next_before_id ?? null);
      (page.items || []).forEach(message => {
        if (message.sender === "ai" && message.job_id && message.job_status !== "success" && message.job_status !== "failed") {
          void waitChatJob(message.job_id, message.id, id);
        }
      });
      requestAnimationFrame(scrollToBottom);
    } catch { setMessages([]); }
    fetchAttachments(id);
    fetchSessionDocs(id);
  };

  const loadOlderMessages = async () => {
    if (!activeSession || !hasMoreMessages || loadingOlder || nextBeforeId === null) return;
    setLoadingOlder(true);
    const container = messagesContainerRef.current;
    const prevHeight = container?.scrollHeight ?? 0;
    const prevTop = container?.scrollTop ?? 0;
    try {
      const page = await fetchSessionMessages(activeSession, nextBeforeId);
      setMessages(prev => [...(page.items || []), ...prev]);
      setHasMoreMessages(Boolean(page.has_more));
      setNextBeforeId(page.next_before_id ?? null);
      requestAnimationFrame(() => {
        if (!container) return;
        container.scrollTop = container.scrollHeight - prevHeight + prevTop;
      });
    } catch {}
    setLoadingOlder(false);
  };

  const handleMessagesScroll = () => {
    const el = messagesContainerRef.current;
    if (!el) return;
    if (el.scrollTop <= 80) loadOlderMessages();
  };

  const waitChatJob = async (jobId: number, aiMessageId: number, sessionId: number) => {
    if (waitingJobsRef.current.has(jobId)) return;
    waitingJobsRef.current.add(jobId);
    try {
      const job = await waitForJob<JobResponse>(jobId);
      if (job.status === "success") {
        setMessages(prev => prev.map(message => (
          message.id === aiMessageId
            ? {
                ...message,
                content: job.result?.answer || "Đã xử lý xong nhưng không có nội dung trả lời.",
                sources: JSON.stringify(job.result?.sources || []),
              }
            : message
        )));
        await fetchSessionDocs(sessionId);
        await fetchSessions();
        requestAnimationFrame(scrollToBottom);
        return;
      }
      if (job.status === "failed") {
        setMessages(prev => prev.map(message => (
          message.id === aiMessageId
            ? { ...message, content: `⚠️ Xử lý AI thất bại.\n\n${job.error || "Không rõ lỗi."}` }
            : message
        )));
        return;
      }
      const timeoutMessage = job.status === "running"
        ? `⏳ AI vẫn đang xử lý (${job.progress || 0}%). Vui lòng tải lại phiên sau ít phút nếu câu trả lời chưa hiện.`
        : "⏳ Job vẫn đang chờ xử lý nền. Vui lòng kiểm tra backend worker.";
      setMessages(prev => prev.map(message => (
        message.id === aiMessageId
          ? { ...message, content: timeoutMessage }
          : message
      )));
    } catch (err: any) {
      setMessages(prev => prev.map(message => (
        message.id === aiMessageId
          ? { ...message, content: "⚠️ Không thể chờ trạng thái job: " + (err.response?.data?.detail || err.message) }
          : message
      )));
    } finally {
      waitingJobsRef.current.delete(jobId);
    }
  };

  const waitIndexJob = async (jobId: number, sessionId: number) => {
    try {
      await waitForJob<JobResponse>(jobId);
      await fetchSessionDocs(sessionId);
      await fetchAttachments(sessionId);
    } catch {
      return;
    }
  };

  // ── Send Chat ───────────────────────────────────────────────────────────────
  const handleSend = async () => {
    if (!input.trim() || loading) return;
    const question = input;
    const tempUserMessageId = Date.now();
    setInput("");
    setMessages(prev => [...prev, { sender: "user", content: question, id: tempUserMessageId }]);
    setLoading(true);
    try {
      const r = await api.post("/employee/chat", {
        question,
        session_id: activeSession,
      });
      const sessionId = r.data.session_id;
      const aiMessageId = r.data.ai_message_id;
      setMessages(prev => [
        ...prev.map(message => (
          message.id === tempUserMessageId ? { ...message, id: r.data.user_message_id } : message
        )),
        {
          sender: "ai",
          content: "⏳ Đã nhận câu hỏi. AI đang tra cứu tài liệu và tạo câu trả lời...",
          sources: "[]",
          id: aiMessageId,
        },
      ]);
      requestAnimationFrame(scrollToBottom);
      if (!activeSession && sessionId) {
        setActiveSession(sessionId);
        fetchAttachments(sessionId);
        fetchSessionDocs(sessionId);
      }
      fetchSessions();
      setLoading(false);
      if (r.data.job_id) {
        void waitChatJob(r.data.job_id, aiMessageId, sessionId);
      }
    } catch (err: any) {
      setMessages(prev => [...prev, {
        sender: "ai",
        content: "⚠️ Lỗi kết nối AI.\n\n" + (err.response?.data?.detail || err.message),
        id: Date.now() + 1,
      }]);
      setLoading(false);
    }
  };

  // ── Upload file mới vào session ─────────────────────────────────────────────
  const handleUploadForSession = async () => {
    const file = selectedUploadFile;
    if (!file) return;
    if (!activeSession) {
      toast({ title: "Vui lòng chọn hoặc tạo session trước khi tải file" });
      return;
    }
    const formData = new FormData();
    formData.append("file", file);
    appendTagIds(formData, selectedUploadTagIds);
    setUploading(true);
    try {
      const r = await api.post(
        `/employee/sessions/${activeSession}/documents/upload`,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      setMessages(prev => [...prev, {
        id: Date.now(), sender: "ai",
        content: r.data.job_id
          ? `✅ Đã tải file **"${file.name}"** vào session. Tài liệu đang chờ index nền.`
          : `✅ Đã tải file **"${file.name}"** vào session.`,
      }]);
      setSelectedUploadFile(null);
      setSelectedUploadTagIds([]);
      setShowUploadDialog(false);
      // Fetch updated session documents
      if (activeSession) {
        await fetchSessionDocs(activeSession);
        if (r.data.job_id) void waitIndexJob(r.data.job_id, activeSession);
      }
      requestAnimationFrame(scrollToBottom);
    } catch (err: any) {
      setMessages(prev => [...prev, {
        id: Date.now(), sender: "ai",
        content: "⚠️ Tải file thất bại: " + (err.response?.data?.detail || err.message),
      }]);
    }
    setUploading(false);
  };

  // ── Folder Tree Picker ──────────────────────────────────────────────────────
  const openPicker = async () => {
    if (!activeSession) {
      toast({ title: "Vui lòng chọn hoặc tạo session trước" });
      return;
    }
    setShowPicker(true);
    if (!treeData) {
      setTreeLoading(true);
      try {
        const r = await api.get("/chat/documents/tree");
        setTreeData(r.data);
      } catch {}
      setTreeLoading(false);
    }
  };

  const refreshTree = async () => {
    setTreeLoading(true);
    try {
      const r = await api.get("/chat/documents/tree");
      setTreeData(r.data);
    } catch {}
    setTreeLoading(false);
  };

  const handleAttach = async (doc: FolderDoc) => {
    if (!activeSession) return;
    try {
      const r = await api.post(`/chat/sessions/${activeSession}/attach`, { doc_id: doc.id });
      // Refetch attachments to ensure data is in sync
      await fetchAttachments(activeSession);
      setMessages(prev => [...prev, {
        id: Date.now(), sender: "ai",
        content: r.data.index_job_id
          ? `📎 Đã đính kèm **"${doc.filename}"** vào phiên chat.\nTài liệu đang được index, AI sẽ dùng được nội dung sau khi trạng thái chuyển sang Đã index.`
          : `📎 Đã đính kèm **"${doc.filename}"** vào phiên chat.\nAI sẽ dùng nội dung tài liệu này khi trả lời câu hỏi.`,
      }]);
      if (r.data.index_job_id) void waitIndexJob(r.data.index_job_id, activeSession);
      requestAnimationFrame(scrollToBottom);
    } catch (err: any) {
      toast({
        title: "Lỗi đính kèm",
        description: err.response?.data?.detail || err.message,
        variant: "destructive",
      });
    }
  };

  const handleDetach = async (docId: number) => {
    if (!activeSession) return;
    const ok = await confirm({
      title: "Gỡ tài liệu khỏi phiên chat?",
      description: "Tài liệu chỉ được gỡ khỏi phiên hiện tại, không bị xóa khỏi kho.",
      confirmText: "Gỡ tài liệu",
      variant: "warning",
    });
    if (!ok) return;
    try {
      await api.delete(`/chat/sessions/${activeSession}/attach/${docId}`);
      // Refetch attachments to ensure data is in sync
      await fetchAttachments(activeSession);
    } catch (err: any) {
      toast({
        title: "Lỗi gỡ đính kèm",
        description: err.response?.data?.detail || err.message,
        variant: "destructive",
      });
    }
  };

  // ── Session Management ──────────────────────────────────────────────────────
  const handleNewSession = async () => {
    try {
      const r = await api.post("/employee/sessions");
      const newSession = r.data;
      await fetchSessions();
      setActiveSession(newSession.id);
      setMessages([]);
      setHasMoreMessages(false);
      setNextBeforeId(null);
      setAttachedDocs([]);
      setSessionDocs([]);
      setShowPicker(false);
    } catch (err: any) {
      toast({
        title: "Không thể tạo phiên mới",
        description: err.response?.data?.detail || err.message,
        variant: "destructive",
      });
    }
  };

  const handleDeleteSession = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    const ok = await confirm({
      title: "Xóa phiên hội thoại này?",
      description: "Toàn bộ tin nhắn trong phiên sẽ bị xóa.",
      confirmText: "Xóa phiên",
    });
    if (!ok) return;
    try {
      await api.delete(`/employee/sessions/${id}`);
      if (activeSession === id) { 
        setActiveSession(null); 
        setMessages([]); 
        setAttachedDocs([]);
        setSessionDocs([]);
      }
      fetchSessions();
    } catch {}
  };

  const startRename = (e: React.MouseEvent, s: any) => {
    e.stopPropagation();
    setRenamingId(s.id);
    setRenameInput(s.title);
  };

  const commitRename = async (id: number) => {
    if (!renameInput.trim()) return;
    try {
      await api.put(`/employee/sessions/${id}`, { title: renameInput.trim() });
      fetchSessions();
    } catch {}
    setRenamingId(null);
  };

  // ── Render ──────────────────────────────────────────────────────────────────
  const attachedIds = new Set(attachedDocs.map(a => a.doc_id));
  const sourceNameById = new Map<string, string>();
  const sourceTagsById = new Map<string, DocumentTag[]>();
  attachedDocs.forEach(doc => sourceNameById.set(String(doc.doc_id), doc.filename));
  attachedDocs.forEach(doc => sourceTagsById.set(String(doc.doc_id), doc.tags ?? []));
  sessionDocs.forEach((doc: any) => {
    sourceNameById.set(String(doc.id), doc.filename);
    sourceTagsById.set(String(doc.id), doc.tags ?? []);
  });

  const sourceLabel = (source: unknown) => {
    const sourceId = String(source);
    const filename = sourceNameById.get(sourceId);
    return filename || "Tài liệu";
  };

  const sessionDocStatusLabel = (doc: any) => {
    const status = doc.index_status || (doc.is_indexed ? "indexed" : "not_indexed");
    const labels: Record<string, string> = {
      indexed: "Đã index",
      queued: "Chờ index",
      running: "Đang index",
      failed: "Index lỗi",
      not_indexed: "Chưa index",
    };
    return labels[status] || labels.not_indexed;
  };

  return (
    <div className="flex h-full min-h-0 overflow-hidden bg-transparent">
      {confirmDialog}
      <Dialog
        open={showUploadDialog}
        onOpenChange={(open) => {
          setShowUploadDialog(open);
          if (!open && !uploading) {
            setSelectedUploadFile(null);
            setSelectedUploadTagIds([]);
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Upload file vào session</DialogTitle>
            <DialogDescription>Chọn file và gắn tag cho tài liệu trước khi đưa vào phiên chat.</DialogDescription>
          </DialogHeader>
          <label className="soft-panel flex cursor-pointer items-center justify-between gap-3 p-4 text-sm">
            <span className="min-w-0 truncate text-muted-foreground">
              {selectedUploadFile ? selectedUploadFile.name : "Chọn file từ máy tính"}
            </span>
            <span className="font-medium text-primary">Browse</span>
            <input
              type="file"
              className="hidden"
              accept=".pdf,.docx,.doc,.txt"
              onChange={(event) => setSelectedUploadFile(event.target.files?.[0] ?? null)}
            />
          </label>
          <TagSelector value={selectedUploadTagIds} onChange={setSelectedUploadTagIds} />
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setShowUploadDialog(false)} disabled={uploading}>
              Hủy
            </Button>
            <Button type="button" onClick={() => void handleUploadForSession()} disabled={!selectedUploadFile || uploading}>
              <Upload className="h-4 w-4" />
              {uploading ? "Đang tải..." : "Upload file"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
      <aside className={cn("glass-sidebar flex shrink-0 flex-col border-r bg-card/65 transition-[width] duration-300", sessionsCollapsed ? "w-[4.5rem]" : "w-72")}>
        <div className="space-y-2 border-b p-3">
          <Button
            type="button"
            variant="ghost"
            size={sessionsCollapsed ? "icon" : "default"}
            onClick={() => setSessionsCollapsed(value => !value)}
            className="w-full"
            title={sessionsCollapsed ? "Mở rộng phiên hội thoại" : "Thu nhỏ phiên hội thoại"}
          >
            {sessionsCollapsed ? <ChevronsRight className="h-4 w-4" /> : <ChevronsLeft className="h-4 w-4" />}
            {!sessionsCollapsed && <span>Phiên chat</span>}
          </Button>
          <Button
            type="button"
            onClick={handleNewSession}
            size={sessionsCollapsed ? "icon" : "default"}
            className="w-full"
            title="Phiên hội thoại mới"
          >
            <Plus className="h-4 w-4" />
            {!sessionsCollapsed && "Phiên hội thoại mới"}
          </Button>
        </div>

        <ScrollArea className="min-h-0 flex-1">
          <div className={cn("space-y-1", sessionsCollapsed ? "p-3" : "p-2")}>
            {sessions.length === 0 && !sessionsCollapsed && (
              <p className="py-6 text-center text-xs text-muted-foreground">Chưa có phiên nào</p>
            )}
            {sessions.map((s: any) => (
              <div
                key={s.id}
                title={sessionsCollapsed ? s.title : undefined}
                className={cn(
                  "group flex cursor-pointer items-center rounded-md text-sm transition-colors",
                  sessionsCollapsed ? "justify-center px-0 py-2" : "px-2 py-1.5",
                  activeSession === s.id ? "bg-primary/10 text-primary" : "hover:bg-muted/70",
                )}
                onClick={() => loadSession(s.id)}
              >
                <MessageSquare className={cn("h-3.5 w-3.5 shrink-0", !sessionsCollapsed && "mr-2 mt-0.5")} />
                {!sessionsCollapsed && renamingId === s.id ? (
                  <div className="flex flex-1 gap-1" onClick={e => e.stopPropagation()}>
                    <Input
                      value={renameInput}
                      autoFocus
                      onChange={e => setRenameInput(e.target.value)}
                      onKeyDown={e => { if (e.key === "Enter") commitRename(s.id); if (e.key === "Escape") setRenamingId(null); }}
                      className="h-7 min-w-0 flex-1 px-2 text-xs"
                    />
                    <Button type="button" variant="ghost" size="icon-sm" onClick={() => commitRename(s.id)}>
                      <Check className="h-3 w-3" />
                    </Button>
                  </div>
                ) : !sessionsCollapsed && (
                  <span className="min-w-0 flex-1 truncate text-xs">{s.title}</span>
                )}
                {!sessionsCollapsed && (
                  <div className="ml-1 flex shrink-0 gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
                    <Button type="button" variant="ghost" size="icon-sm" onClick={(e) => startRename(e, s)}>
                      <Pencil className="h-3 w-3" />
                    </Button>
                    <Button type="button" variant="ghost" size="icon-sm" onClick={(e) => handleDeleteSession(e, s.id)} className="text-destructive">
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </ScrollArea>
      </aside>

      <section className="flex h-full min-w-0 flex-1 flex-col overflow-hidden">
        <div className="flex flex-wrap items-center gap-3 border-b bg-card/55 p-3 backdrop-blur-xl">
          <div className="min-w-40 flex-1">
            <p className="truncate text-sm font-semibold">Trợ lý AI Hành Chính</p>
            <p className="truncate text-xs text-muted-foreground">{activeSession ? `Session #${activeSession}` : "Chọn hoặc tạo phiên để bắt đầu"}</p>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setShowUploadDialog(true)}
            disabled={!activeSession || uploading}
            title="Tải file mới lên session"
            className="shrink-0"
          >
            <Upload className="h-3.5 w-3.5" />
            {uploading ? "Đang tải..." : "Upload file"}
          </Button>
          <Button
            type="button"
            variant={showPicker ? "default" : "outline"}
            size="sm"
            onClick={showPicker ? () => setShowPicker(false) : () => {
              setDocsPanelCollapsed(false);
              void openPicker();
            }}
            disabled={!activeSession}
            className="shrink-0"
          >
            <FolderOpen className="h-3.5 w-3.5" />
            Chọn từ thư viện
            {attachedDocs.length > 0 && <Badge variant="secondary">{attachedDocs.length}</Badge>}
          </Button>
        </div>

        <div className="flex min-h-0 flex-1 overflow-hidden">
          <div ref={messagesContainerRef} onScroll={handleMessagesScroll} className="min-w-0 flex-1 space-y-4 overflow-y-auto p-4 sm:p-6">
            {loadingOlder && <div className="text-center text-xs text-muted-foreground">Đang tải thêm hội thoại cũ...</div>}
            {messages.length === 0 && (
              <div className="flex h-full flex-col items-center justify-center text-center text-muted-foreground">
                <Bot className="mb-4 h-16 w-16 opacity-20" />
                <p className="text-lg font-semibold text-foreground">Trợ lý AI Hành Chính</p>
                <p className="mt-1 text-sm">Đặt câu hỏi theo tài liệu trong phiên hiện tại</p>
                <p className="mt-3 text-xs">AI nhớ 3 đoạn hội thoại gần nhất và ưu tiên tài liệu đã đính kèm.</p>
              </div>
            )}
            {messages.map((m: ChatMessage) => (
              <div key={m.id} className={cn("flex", m.sender === "user" ? "justify-end" : "justify-start")}>
                <div className={cn("flex max-w-[82%] gap-3", m.sender === "user" && "flex-row-reverse")}>
                  <div className={cn("flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-white shadow-sm", m.sender === "user" ? "bg-primary" : "bg-slate-700")}>
                    {m.sender === "user" ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                  </div>
                  <Card className={cn("chat-bubble", m.sender === "user" ? "chat-bubble-user rounded-tr-sm" : "chat-bubble-ai rounded-tl-sm")}>
                    <p className="whitespace-pre-wrap">{m.content}</p>
                    {m.sender === "ai" && m.sources && (() => {
                      try {
                        const sources: unknown[] = JSON.parse(m.sources);
                        if (sources.length === 0) return null;
                        return (
                          <div className="mt-3 flex flex-wrap gap-1.5 border-t pt-3">
                            {sources.map((source, index) => {
                              const sourceId = String(source);
                              return (
                                <div key={`${sourceId}-${index}`} className="flex flex-wrap items-center gap-1.5">
                                  <Badge variant="outline" className="bg-background/60">
                                    {sourceLabel(source)}
                                  </Badge>
                                  <TagList tags={sourceTagsById.get(sourceId)} />
                                </div>
                              );
                            })}
                          </div>
                        );
                      } catch { return null; }
                    })()}
                  </Card>
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="flex max-w-md gap-3">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-700 text-white">
                    <Bot className="h-4 w-4" />
                  </div>
                  <Card className="chat-bubble chat-bubble-ai w-72 space-y-2 rounded-tl-sm">
                    <Skeleton className="h-3 w-5/6" />
                    <Skeleton className="h-3 w-3/4" />
                    <Skeleton className="h-3 w-1/2" />
                  </Card>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {docsPanelCollapsed ? (
            <aside className="hidden w-14 shrink-0 flex-col items-center border-l bg-card/55 py-3 backdrop-blur-xl xl:flex">
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                onClick={() => setDocsPanelCollapsed(false)}
                title="Mở panel tài liệu"
              >
                <FolderOpen className="h-4 w-4" />
              </Button>
            </aside>
          ) : (
          <aside className={cn(
            "hidden shrink-0 flex-col border-l bg-card/55 backdrop-blur-xl transition-[width] duration-200 xl:flex",
            showPicker ? "w-[30rem] max-w-[42vw]" : "w-80",
          )}>
            <div className="border-b p-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold">Tài liệu phiên</p>
                  <p className="text-xs text-muted-foreground">Nguồn sẽ được ưu tiên khi trả lời</p>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon-sm"
                  onClick={() => setDocsPanelCollapsed(true)}
                  title="Thu gọn panel tài liệu"
                >
                  <ChevronsRight className="h-4 w-4" />
                </Button>
              </div>
            </div>

            <ScrollArea className="min-h-0 flex-1">
              <div className="space-y-4 p-4">
                <div className="space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Đính kèm</p>
                  {attachedDocs.length === 0 && <p className="text-xs text-muted-foreground">Chưa có tài liệu đính kèm.</p>}
                  {attachedDocs.map(a => (
                    <div key={a.doc_id} className="soft-panel flex items-center gap-2 p-2">
                      <FileText className="h-4 w-4 shrink-0 text-emerald-600" />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-xs font-medium">{a.filename}</p>
                        <p className="text-[11px] text-muted-foreground">{sessionDocStatusLabel(a)}</p>
                        <TagList tags={a.tags} showEmpty className="mt-1" />
                      </div>
                      <Button type="button" variant="ghost" size="icon-sm" onClick={() => handleDetach(a.doc_id)} className="text-destructive">
                        <X className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  ))}
                </div>

                <div className="space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Upload trong session</p>
                  {sessionDocs.length === 0 && <p className="text-xs text-muted-foreground">Chưa có file upload riêng.</p>}
                  {sessionDocs.map((d: any) => (
                    <div key={d.id} className="soft-panel flex items-center gap-2 p-2">
                      <FileText className="h-4 w-4 shrink-0 text-primary" />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-xs font-medium">{d.filename}</p>
                        <p className="text-[11px] text-muted-foreground">{sessionDocStatusLabel(d)}</p>
                        <TagList tags={d.tags} showEmpty className="mt-1" />
                      </div>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon-sm"
                        className="text-destructive"
                        onClick={async () => {
                          if (!activeSession) return;
                          const ok = await confirm({
                            title: `Xóa file "${d.filename}"?`,
                            description: "File upload trong phiên chat này sẽ bị xóa.",
                            confirmText: "Xóa file",
                          });
                          if (!ok) return;
                          try {
                            await api.delete(`/chat/sessions/${activeSession}/documents/${d.id}`);
                            await fetchSessionDocs(activeSession);
                          } catch (err: any) {
                            toast({
                              title: "Lỗi xóa file",
                              description: err.response?.data?.detail || err.message,
                              variant: "destructive",
                            });
                          }
                        }}
                      >
                        <X className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  ))}
                </div>

                {showPicker && (
                  <div className="space-y-3 border-t pt-4">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Thư viện</p>
                      <div className="flex items-center gap-1">
                      <Button type="button" variant="ghost" size="icon-sm" onClick={refreshTree} disabled={treeLoading} title="Làm mới">
                        <RefreshCw className={cn("h-3.5 w-3.5", treeLoading && "animate-spin")} />
                      </Button>
                      <Button type="button" variant="ghost" size="icon-sm" onClick={() => setShowPicker(false)} title="Đóng thư viện">
                        <X className="h-3.5 w-3.5" />
                      </Button>
                      </div>
                    </div>
                    {treeLoading && (
                      <div className="space-y-2">
                        <Skeleton className="h-10 w-full" />
                        <Skeleton className="h-10 w-full" />
                        <Skeleton className="h-10 w-5/6" />
                      </div>
                    )}
                    {!treeLoading && treeData && (
                      <FolderTree
                        data={treeData}
                        attachedIds={attachedIds}
                        onAttach={handleAttach}
                        onDownload={(id) => window.open(`http://localhost:8000/employee/documents/${id}/download`, "_blank")}
                      />
                    )}
                    {!treeLoading && !treeData && (
                      <p className="py-8 text-center text-sm text-muted-foreground">Không thể tải dữ liệu</p>
                    )}
                  </div>
                )}
              </div>
            </ScrollArea>
          </aside>
          )}
        </div>

        <div className="border-t bg-card/70 p-4 backdrop-blur-xl">
          <div className="flex w-full items-end gap-2">
            <Textarea
              value={input}
              onChange={e => {
                setInput(e.target.value);
                e.currentTarget.style.height = "auto";
                e.currentTarget.style.height = `${Math.min(e.currentTarget.scrollHeight, 180)}px`;
              }}
              onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
              className="max-h-44 min-h-12 resize-none rounded-2xl bg-background/80 px-4 py-3"
              placeholder="Nhập câu hỏi về văn bản hành chính..."
              disabled={loading}
              rows={1}
            />
            <Button type="button" onClick={handleSend} disabled={!input.trim() || loading} size="icon" className="h-12 w-12 rounded-2xl">
              <Send className="h-5 w-5" />
            </Button>
          </div>
          <p className="mt-2 text-center text-[11px] text-muted-foreground">
            AI nhớ 3 đoạn hội thoại gần nhất trong phiên và ưu tiên tài liệu đã upload hoặc đính kèm.
          </p>
        </div>
      </section>
    </div>
  );
}
