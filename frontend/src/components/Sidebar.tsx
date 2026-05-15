import { Home, MessageSquare, FileText, Users, Settings, FolderKanban, LogOut, BookOpen } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { Link, useLocation } from 'react-router-dom';

export default function Sidebar() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const isActive = (path: string) => location.pathname === path ? "bg-blue-600 text-white shadow-md shadow-blue-500/20" : "text-slate-400 hover:bg-slate-800 hover:text-white";

  return (
    <div className="w-60 bg-slate-900 border-r border-slate-800 flex flex-col">
      <div className="p-4 flex items-center gap-3 border-b border-slate-800/60 mb-2">
        <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center shadow-lg shadow-blue-600/30">
          <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
        </div>
        <span className="font-semibold text-white tracking-wide text-sm">RAG.Gov</span>
      </div>

      <nav className="flex-1 px-3 space-y-0.5 overflow-y-auto">
        <p className="text-[10px] font-bold text-slate-500 tracking-widest mb-2 px-3 uppercase">Cá nhân</p>
        <Link to="/" className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-all text-sm ${isActive('/')}`}><Home className="w-4 h-4" />Dashboard</Link>
        <Link to="/chat" className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-all text-sm ${isActive('/chat')}`}><MessageSquare className="w-4 h-4" />Hỏi Đáp RAG</Link>
        <Link to="/library" className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-all text-sm ${isActive('/library')}`}><FileText className="w-4 h-4" />Kho Cá Nhân</Link>
        <Link to="/sqp" className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-all text-sm ${isActive('/sqp')}`}><BookOpen className="w-4 h-4" />Quy Định (SQP)</Link>

        {user?.role === 'manager' && (<>
          <p className="text-[10px] font-bold text-slate-500 tracking-widest mb-2 px-3 uppercase mt-6">Phòng ban</p>
          <Link to="/manager/docs" className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-all text-sm ${isActive('/manager/docs')}`}><FolderKanban className="w-4 h-4" />Thư Mục Chung</Link>
        </>)}

        {user?.role === 'admin' && (<>
          <p className="text-[10px] font-bold text-slate-500 tracking-widest mb-2 px-3 uppercase mt-6">Hệ thống</p>
          <Link to="/admin/users" className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-all text-sm ${isActive('/admin/users')}`}><Users className="w-4 h-4" />Tài Khoản</Link>
          <Link to="/admin/documents" className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-all text-sm ${isActive('/admin/documents')}`}><FolderKanban className="w-4 h-4" />Tài liệu & Chia sẻ</Link>
          <Link to="/admin/system" className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-all text-sm ${isActive('/admin/system')}`}><Settings className="w-4 h-4" />Bảo Trì Hệ Thống</Link>
        </>)}
      </nav>

      <div className="p-3 border-t border-slate-800">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center text-white text-sm font-medium">{user?.sub?.charAt(0).toUpperCase()}</div>
            <div><p className="text-xs font-medium text-white">{user?.sub}</p><p className="text-[10px] text-slate-400 capitalize">{user?.role}</p></div>
          </div>
          <button onClick={() => { logout(); window.location.href = "/login"; }} className="p-1.5 text-slate-400 hover:text-red-400 rounded-lg transition" title="Đăng xuất"><LogOut className="w-4 h-4" /></button>
        </div>
      </div>
    </div>
  );
}
