import { useState, useEffect } from "react";
import api from "../api";
import { useAuth } from "../hooks/useAuth";
import { FileText, MessageSquare, Users, Database } from "lucide-react";

export default function Dashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState({ docs: 0, sessions: 0, users: 0, vectors: 0 });

  useEffect(() => {
    if (!user) return;

    const load = async () => {
      try {
        const [docsR, sessionsR] = await Promise.all([
          api.get("/employee/documents"),
          api.get("/employee/sessions"),
        ]);
        let usersCount = 0, vectorCount = 0;
        if (user?.role === "admin") {
          try {
            const u = await api.get("/admin/users");
            usersCount = Array.isArray(u.data) ? u.data.length : 0;
          } catch {}
          try { const v = await api.get("/admin/vector/status"); vectorCount = v.data.total_vectors; } catch {}
        }
        setStats({
          docs: Array.isArray(docsR.data) ? docsR.data.length : 0,
          sessions: Array.isArray(sessionsR.data) ? sessionsR.data.length : 0,
          users: usersCount,
          vectors: vectorCount,
        });
      } catch {}
    };
    load();
  }, [user]);

  const cards = [
    { title: "Tài liệu của tôi", value: stats.docs, icon: <FileText className="w-6 h-6" />, color: "text-[#006666]" },
    { title: "Phiên hội thoại", value: stats.sessions, icon: <MessageSquare className="w-6 h-6" />, color: "text-emerald-600" },
    ...(user?.role === "admin" ? [
      { title: "Tổng người dùng", value: stats.users, icon: <Users className="w-6 h-6" />, color: "text-amber-600" },
      { title: "Vectors trong DB", value: stats.vectors, icon: <Database className="w-6 h-6" />, color: "text-indigo-600" },
    ] : []),
  ];

  return (
    <div className="neo-page max-w-6xl space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Xin chào, {user?.sub || "User"} 👋</h1>
        <p className="text-slate-500 text-sm mt-1">Vai trò: <span className="font-medium capitalize">{user?.role}</span></p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        {cards.map((c, i) => (
          <div key={i} className="neo-panel p-6 transition-transform hover:-translate-y-0.5">
            <div className="flex justify-between items-start">
              <div><p className="text-sm text-slate-500 mb-1">{c.title}</p><h3 className={`text-3xl font-bold ${c.color}`}>{c.value}</h3></div>
              <div className={`neo-stat-icon ${c.color}`}>{c.icon}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="neo-panel p-6">
        <h2 className="text-lg font-bold text-slate-900 mb-4">Hướng dẫn nhanh</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-slate-600">
          <div className="neo-inset p-4">
            <p className="font-semibold text-[#006666] mb-1">📄 Tải tài liệu</p>
            <p>Vào "Kho Cá Nhân" → Tải lên file PDF → Hệ thống tự động vector hoá</p>
          </div>
          <div className="neo-inset p-4">
            <p className="font-semibold text-emerald-700 mb-1">🤖 Hỏi AI</p>
            <p>Vào "Hỏi Đáp RAG" → Chọn phạm vi quét → Đặt câu hỏi bằng tiếng Việt</p>
          </div>
          <div className="neo-inset p-4">
            <p className="font-semibold text-amber-700 mb-1">📋 Tra cứu SQP</p>
            <p>Các quy định công ty đã được duyệt có thể tìm trong mục "Quy Định"</p>
          </div>
        </div>
      </div>
    </div>
  );
}
