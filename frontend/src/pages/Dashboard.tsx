import { useState, useEffect } from "react";
import api from "../api";
import { useAuth } from "../hooks/useAuth";
import { FileText, MessageSquare, Users, Database } from "lucide-react";

export default function Dashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState({ docs: 0, sessions: 0, users: 0, vectors: 0 });

  useEffect(() => {
    const load = async () => {
      try {
        const [docsR, sessionsR] = await Promise.all([
          api.get("/employee/documents"),
          api.get("/employee/sessions"),
        ]);
        let usersCount = 0, vectorCount = 0;
        if (user?.role === "admin") {
          try { const u = await api.get("/admin/users"); usersCount = u.data.length; } catch {}
          try { const v = await api.get("/admin/vector/status"); vectorCount = v.data.total_vectors; } catch {}
        }
        setStats({ docs: docsR.data.length, sessions: sessionsR.data.length, users: usersCount, vectors: vectorCount });
      } catch {}
    };
    load();
  }, []);

  const cards = [
    { title: "Tài liệu của tôi", value: stats.docs, icon: <FileText className="w-6 h-6" />, color: "text-blue-600", bg: "bg-blue-50 border-blue-100" },
    { title: "Phiên hội thoại", value: stats.sessions, icon: <MessageSquare className="w-6 h-6" />, color: "text-emerald-600", bg: "bg-emerald-50 border-emerald-100" },
    ...(user?.role === "admin" ? [
      { title: "Tổng người dùng", value: stats.users, icon: <Users className="w-6 h-6" />, color: "text-amber-600", bg: "bg-amber-50 border-amber-100" },
      { title: "Vectors trong DB", value: stats.vectors, icon: <Database className="w-6 h-6" />, color: "text-purple-600", bg: "bg-purple-50 border-purple-100" },
    ] : []),
  ];

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Xin chào, {user?.sub || "User"} 👋</h1>
        <p className="text-gray-500 text-sm mt-1">Vai trò: <span className="font-medium capitalize">{user?.role}</span></p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        {cards.map((c, i) => (
          <div key={i} className={`p-6 rounded-xl border shadow-sm ${c.bg} hover:-translate-y-0.5 transition-transform`}>
            <div className="flex justify-between items-start">
              <div><p className="text-sm text-gray-500 mb-1">{c.title}</p><h3 className={`text-3xl font-bold ${c.color}`}>{c.value}</h3></div>
              <div className={`p-2.5 rounded-lg ${c.color} bg-white/60`}>{c.icon}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl border shadow-sm p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-4">Hướng dẫn nhanh</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-gray-600">
          <div className="p-4 bg-blue-50 rounded-lg border border-blue-100">
            <p className="font-semibold text-blue-700 mb-1">📄 Tải tài liệu</p>
            <p>Vào "Kho Cá Nhân" → Tải lên file PDF → Hệ thống tự động vector hoá</p>
          </div>
          <div className="p-4 bg-emerald-50 rounded-lg border border-emerald-100">
            <p className="font-semibold text-emerald-700 mb-1">🤖 Hỏi AI</p>
            <p>Vào "Hỏi Đáp RAG" → Chọn phạm vi quét → Đặt câu hỏi bằng tiếng Việt</p>
          </div>
          <div className="p-4 bg-amber-50 rounded-lg border border-amber-100">
            <p className="font-semibold text-amber-700 mb-1">📋 Tra cứu SQP</p>
            <p>Các quy định công ty đã được duyệt có thể tìm trong mục "Quy Định"</p>
          </div>
        </div>
      </div>
    </div>
  );
}
