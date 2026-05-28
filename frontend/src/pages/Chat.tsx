import { useState, useEffect, useRef, useCallback } from "react";
import api, { waitForJob } from "../api";
import {
  Send, Bot, User, Plus, Trash2, MessageSquare,
  FolderOpen, X, Upload, RefreshCw, Pencil, Check,
} from "lucide-react";
import FolderTree, { type FolderDoc, type FolderTreeData } from "../components/FolderTree";

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
  const [scope, setScope] = useState("personal");
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

  // Rename session
  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [renameInput, setRenameInput] = useState("");

  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const waitingJobsRef = useRef<Set<number>>(new Set());

  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });

  // ── Sessions ────────────────────────────────────────────────────────────────
  const fetchSessions = useCallback(async () => {
    try { const r = await api.get("/employee/sessions"); setSessions(r.data); } catch {}
  }, []);

  useEffect(() => { fetchSessions(); }, [fetchSessions]);

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
        question, scope,
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
  const handleUploadForSession = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (!activeSession) {
      alert("Vui lòng chọn hoặc tạo session trước khi tải file.");
      return;
    }
    const formData = new FormData();
    formData.append("file", file);
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
      alert("Vui lòng chọn hoặc tạo session trước.");
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
      alert("Lỗi đính kèm: " + (err.response?.data?.detail || err.message));
    }
  };

  const handleDetach = async (docId: number) => {
    if (!activeSession) return;
    try {
      await api.delete(`/chat/sessions/${activeSession}/attach/${docId}`);
      // Refetch attachments to ensure data is in sync
      await fetchAttachments(activeSession);
    } catch (err: any) {
      alert("Lỗi gỡ đính kèm: " + (err.response?.data?.detail || err.message));
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
      alert("Không thể tạo phiên mới: " + (err.response?.data?.detail || err.message));
    }
  };

  const handleDeleteSession = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    if (!confirm("Xóa phiên hội thoại này?")) return;
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
    <div className="flex h-full">
      {/* ── Sidebar Sessions ───────────────────────────────────────────────── */}
      <div className="w-64 bg-[#e7e5e4] border-r border-white/60 flex flex-col flex-shrink-0">
        <div className="p-3 border-b border-white/60">
          <button onClick={handleNewSession} className="neo-button neo-button-primary w-full">
            <Plus className="w-4 h-4" /> Phiên hội thoại mới
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {sessions.length === 0 && <p className="text-xs text-gray-400 text-center py-4">Chưa có phiên nào</p>}
          {sessions.map((s: any) => (
            <div key={s.id}
              className={`flex items-center px-2 py-1.5 rounded-lg cursor-pointer text-sm group transition
                ${activeSession === s.id ? "neo-inset text-[#006666]" : "hover:shadow-[inset_3px_3px_8px_rgba(159,154,148,0.34),inset_-3px_-3px_8px_rgba(255,255,255,0.75)]"}`}
              onClick={() => loadSession(s.id)}
            >
              <MessageSquare className="w-3.5 h-3.5 flex-shrink-0 mr-2 mt-0.5" />
              {renamingId === s.id ? (
                <div className="flex-1 flex gap-1" onClick={e => e.stopPropagation()}>
                  <input
                    value={renameInput} autoFocus
                    onChange={e => setRenameInput(e.target.value)}
                    onKeyDown={e => { if (e.key === "Enter") commitRename(s.id); if (e.key === "Escape") setRenamingId(null); }}
                    className="neo-input flex-1 min-w-0 !py-0.5 !px-1 text-xs"
                  />
                  <button onClick={() => commitRename(s.id)} className="text-blue-500"><Check className="w-3 h-3" /></button>
                </div>
              ) : (
                <span className="truncate flex-1 min-w-0 text-xs">{s.title}</span>
              )}
              <div className="flex gap-0.5 opacity-0 group-hover:opacity-100 flex-shrink-0 ml-1">
                <button onClick={(e) => startRename(e, s)} className="p-0.5 text-gray-400 hover:text-blue-500">
                  <Pencil className="w-3 h-3" />
                </button>
                <button onClick={(e) => handleDeleteSession(e, s.id)} className="p-0.5 text-gray-400 hover:text-red-500">
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Main Chat Area ─────────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Toolbar */}
        <div className="p-3 border-b border-white/60 bg-[#e7e5e4]/80 flex items-center gap-3 flex-wrap">
          <span className="text-xs font-semibold text-slate-500">Phạm vi:</span>
          {[
            { key: "personal", label: "Cá nhân" },
            { key: "department", label: "Phòng ban" },
            { key: "company", label: "Toàn công ty" },
          ].map(s => (
            <button key={s.key} onClick={() => setScope(s.key)}
              className={`neo-button !min-h-0 rounded-full px-3 py-1.5 text-xs
                ${scope === s.key ? "neo-button-primary" : ""}`}>
              {s.label}
            </button>
          ))}

          {activeSession && <span className="ml-auto text-xs text-slate-500">Session #{activeSession}</span>}

          {/* Hidden file input for upload */}
          <input ref={fileInputRef} type="file" className="hidden" onChange={handleUploadForSession} />

          {/* Upload mới */}
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={!activeSession || uploading}
            title="Tải file mới lên session"
            className="neo-button !min-h-0 px-3 py-1.5 text-xs text-emerald-700"
          >
            <Upload className="w-3.5 h-3.5" />
            {uploading ? "Đang tải..." : "Upload file"}
          </button>

          {/* Chọn từ thư viện */}
          <button
            onClick={showPicker ? () => setShowPicker(false) : openPicker}
            disabled={!activeSession}
            title="Chọn file từ thư viện"
            className={`neo-button !min-h-0 px-3 py-1.5 text-xs disabled:opacity-50
              ${showPicker
                ? "neo-button-primary"
                : "text-[#006666]"
              }`}
          >
            <FolderOpen className="w-3.5 h-3.5" />
            Chọn từ thư viện
            {attachedDocs.length > 0 && (
              <span className="ml-1 bg-blue-600 text-white text-[10px] px-1.5 py-0.5 rounded-full min-w-[18px] text-center">
                {attachedDocs.length}
              </span>
            )}
          </button>
        </div>

        {/* Attached docs chips */}
        {attachedDocs.length > 0 && (
          <div className="px-4 py-2 bg-emerald-50/50 border-b border-white/60 flex flex-wrap gap-2 items-center">
            <span className="text-xs text-emerald-700 font-semibold flex-shrink-0">📎 Đính kèm:</span>
            {attachedDocs.map(a => (
              <span key={a.doc_id} className="neo-chip text-emerald-700">
                {a.filename.length > 22 ? a.filename.slice(0, 20) + "…" : a.filename}
                <span className="text-[10px] text-emerald-400 border-l border-emerald-100 pl-1">
                  {sessionDocStatusLabel(a)}
                </span>
                <button onClick={() => handleDetach(a.doc_id)} className="text-emerald-400 hover:text-red-500 ml-0.5">
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
          </div>
        )}

        {/* Session uploaded documents */}
        {sessionDocs.length > 0 && (
          <div className="px-4 py-2 bg-sky-50/50 border-b border-white/60 flex flex-wrap gap-2 items-center">
            <span className="text-xs text-blue-700 font-semibold flex-shrink-0">📄 File trong session:</span>
            {sessionDocs.map((d: any) => (
              <span key={d.id} className="neo-chip text-[#006666]">
                {d.filename.length > 20 ? d.filename.slice(0, 18) + "…" : d.filename}
                <span className="text-[10px] text-blue-400 border-l border-blue-100 pl-1">
                  {sessionDocStatusLabel(d)}
                </span>
                <button 
                  onClick={async () => {
                    if (!activeSession) return;
                    if (!confirm(`Xóa file "${d.filename}"?`)) return;
                    try {
                      await api.delete(`/chat/sessions/${activeSession}/documents/${d.id}`);
                      // Refetch session documents to keep in sync
                      await fetchSessionDocs(activeSession);
                    } catch (err: any) {
                      alert("Lỗi xóa file: " + (err.response?.data?.detail || err.message));
                    }
                  }} 
                  className="text-blue-400 hover:text-red-500 ml-0.5"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
          </div>
        )}

        {/* Body: messages or picker */}
        <div className="flex-1 flex min-h-0">
          {/* Messages */}
          <div ref={messagesContainerRef} onScroll={handleMessagesScroll}
            className={`overflow-y-auto p-6 space-y-4 bg-transparent transition-all ${showPicker ? "flex-[3]" : "flex-1"}`}>
            {loadingOlder && <div className="text-center text-xs text-gray-400">Đang tải thêm hội thoại cũ...</div>}
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-gray-400">
                <Bot className="w-16 h-16 mb-4 opacity-20" />
                <p className="text-lg font-medium">Trợ lý AI Hành Chính</p>
                <p className="text-sm mt-1">Chọn phạm vi quét dữ liệu và đặt câu hỏi</p>
                <p className="text-xs mt-3 text-gray-300">AI nhớ 10 câu hỏi gần nhất • Đính kèm tài liệu bằng nút "Chọn từ thư viện"</p>
              </div>
            )}
            {messages.map((m: ChatMessage) => (
              <div key={m.id} className={`flex ${m.sender === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`flex gap-3 max-w-[78%] ${m.sender === "user" ? "flex-row-reverse" : ""}`}>
                  <div className={`w-9 h-9 rounded-full flex-shrink-0 flex items-center justify-center ${m.sender === "user" ? "bg-[#006666]" : "bg-slate-700"} text-white shadow-[6px_6px_14px_rgba(159,154,148,0.45),-6px_-6px_14px_rgba(255,255,255,0.78)]`}>
                    {m.sender === "user" ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                  </div>
                  <div className={`p-4 rounded-2xl ${m.sender === "user" ? "bg-[#006666] text-white rounded-tr-sm shadow-[7px_7px_16px_rgba(0,62,62,0.20),-7px_-7px_16px_rgba(255,255,255,0.55)]" : "neo-panel-compact text-gray-800 rounded-tl-sm"}`}>
                    <p className="whitespace-pre-wrap leading-relaxed text-sm">{m.content}</p>
                    {m.sender === "ai" && m.sources && (() => {
                      try {
                        const s = JSON.parse(m.sources);
                        if (s.length === 0) return null;
                        return (
                          <div className="mt-3 pt-2 border-t border-gray-100 text-xs text-gray-400">
                            📎 Nguồn: {s.join(", ")}
                          </div>
                        );
                      } catch { return null; }
                    })()}
                  </div>
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="flex gap-3">
                  <div className="w-9 h-9 rounded-full bg-slate-700 flex items-center justify-center text-white"><Bot className="w-4 h-4" /></div>
                  <div className="neo-panel-compact p-4 rounded-2xl rounded-tl-sm flex gap-1.5">
                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0.15s]" />
                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0.3s]" />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* File Picker Panel */}
          {showPicker && (
            <div className="flex-[2] border-l border-white/60 bg-[#e7e5e4] flex flex-col min-w-0 max-w-xs">
              <div className="flex items-center justify-between px-4 py-3 border-b border-white/60">
                <span className="text-sm font-semibold text-gray-700">📂 Chọn tài liệu từ thư viện</span>
                <div className="flex items-center gap-1">
                  <button onClick={refreshTree} disabled={treeLoading} className="p-1 text-gray-400 hover:text-blue-500" title="Làm mới">
                    <RefreshCw className={`w-3.5 h-3.5 ${treeLoading ? "animate-spin" : ""}`} />
                  </button>
                  <button onClick={() => setShowPicker(false)} className="p-1 text-gray-400 hover:text-red-500">
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto p-3">
                {treeLoading && (
                  <div className="flex items-center justify-center h-32 text-gray-400 text-sm gap-2">
                    <RefreshCw className="w-4 h-4 animate-spin" /> Đang tải...
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
                  <p className="text-center text-sm text-gray-400 py-8">Không thể tải dữ liệu</p>
                )}
              </div>

              <div className="p-3 border-t border-white/60 text-xs text-slate-500">
                Nhấn 📎 trên tài liệu để đính kèm vào phiên chat hiện tại.
                AI sẽ sử dụng nội dung các file đính kèm khi trả lời.
              </div>
            </div>
          )}
        </div>

        {/* Input */}
        <div className="p-4 bg-[#e7e5e4]/90 border-t border-white/60">
          <div className="flex gap-2">
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
              className="neo-input flex-1 px-4 py-3"
              placeholder="Nhập câu hỏi về văn bản hành chính..."
              disabled={loading}
            />
            <button onClick={handleSend} disabled={!input.trim() || loading}
              className="neo-button neo-button-primary px-5 py-3">
              <Send className="w-5 h-5" />
            </button>
          </div>
          <p className="text-center text-[10px] text-gray-300 mt-2">
            AI nhớ 10 câu hỏi gần nhất trong phiên • Chọn scope phù hợp để có kết quả chính xác
          </p>
        </div>
      </div>
    </div>
  );
}
