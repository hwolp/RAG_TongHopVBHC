import { Home, MessageSquare, FileText, Users, Settings, FolderKanban, LogOut, BookOpen, Zap } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { Link, useLocation } from 'react-router-dom';

export default function Sidebar() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const isActive = (path: string) => location.pathname === path
    ? "bg-[#006666] text-white shadow-[inset_3px_3px_8px_rgba(0,45,45,0.32),inset_-3px_-3px_8px_rgba(255,255,255,0.16)]"
    : "text-slate-600 hover:text-[#006666] hover:shadow-[inset_3px_3px_8px_rgba(159,154,148,0.38),inset_-3px_-3px_8px_rgba(255,255,255,0.82)]";

  return (
    <div className="w-64 bg-[#e7e5e4] border-r border-white/60 flex flex-col shadow-[10px_0_24px_rgba(159,154,148,0.28)]">
      <div className="p-4 flex items-center gap-3 border-b border-white/60 mb-2">
        <div className="w-10 h-10 rounded-lg bg-[#006666] flex items-center justify-center text-white shadow-[7px_7px_16px_rgba(0,62,62,0.24),-7px_-7px_16px_rgba(255,255,255,0.72)]">
          <Zap className="w-5 h-5" />
        </div>
        <div>
          <span className="font-display font-bold text-slate-900 tracking-wide text-sm">RAG.Gov</span>
          <p className="text-[10px] text-slate-500">AI hành chính</p>
        </div>
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

      <div className="p-3 border-t border-white/60">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-full bg-[#e7e5e4] flex items-center justify-center text-[#006666] text-sm font-bold shadow-[inset_4px_4px_10px_rgba(159,154,148,0.48),inset_-4px_-4px_10px_rgba(255,255,255,0.86)]">{user?.sub?.charAt(0).toUpperCase()}</div>
            <div><p className="text-xs font-semibold text-slate-800">{user?.sub}</p><p className="text-[10px] text-slate-500 capitalize">{user?.role}</p></div>
          </div>
          <button onClick={() => { logout(); window.location.href = "/login"; }} className="p-2 text-slate-500 hover:text-[#ff2157] rounded-lg transition" title="Đăng xuất"><LogOut className="w-4 h-4" /></button>
        </div>
      </div>
    </div>
  );
}
