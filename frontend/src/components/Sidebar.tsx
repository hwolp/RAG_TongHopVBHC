import { useState } from 'react';
import { Home, MessageSquare, FileText, Users, Settings, FolderKanban, LogOut, BookOpen, Zap, SlidersHorizontal, ChevronDown, PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { Link, useLocation } from 'react-router-dom';

export default function Sidebar() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [collapsedSections, setCollapsedSections] = useState<Record<string, boolean>>({});
  const isActive = (path: string) => location.pathname === path
    ? "bg-[#006666] text-white shadow-[inset_3px_3px_8px_rgba(0,45,45,0.32),inset_-3px_-3px_8px_rgba(255,255,255,0.16)]"
    : "text-slate-600 hover:text-[#006666] hover:shadow-[inset_3px_3px_8px_rgba(159,154,148,0.38),inset_-3px_-3px_8px_rgba(255,255,255,0.82)]";

  const toggleSection = (key: string) => {
    setCollapsedSections(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const sectionHeaderClass = "w-full flex items-center justify-between px-3 py-2 text-[10px] font-bold text-slate-500 tracking-widest uppercase rounded-lg hover:text-[#006666] hover:shadow-[inset_3px_3px_8px_rgba(159,154,148,0.30),inset_-3px_-3px_8px_rgba(255,255,255,0.72)] transition";
  const navLinkClass = (path: string) => `flex items-center rounded-lg transition-all text-sm ${sidebarCollapsed ? "justify-center px-0 py-2.5" : "gap-3 px-3 py-2"} ${isActive(path)}`;

  return (
    <div className={`${sidebarCollapsed ? "w-16" : "w-64"} bg-[#e7e5e4] border-r border-white/60 flex flex-col shadow-[10px_0_24px_rgba(159,154,148,0.28)] transition-[width] duration-200 flex-shrink-0`}>
      <div className={`${sidebarCollapsed ? "p-3 flex-col" : "p-4"} flex items-center gap-3 border-b border-white/60 mb-2`}>
        <div className="w-10 h-10 rounded-lg bg-[#006666] flex items-center justify-center text-white shadow-[7px_7px_16px_rgba(0,62,62,0.24),-7px_-7px_16px_rgba(255,255,255,0.72)]">
          <Zap className="w-5 h-5" />
        </div>
        {!sidebarCollapsed && <div className="min-w-0">
          <span className="font-display font-bold text-slate-900 tracking-wide text-sm">RAG.Gov</span>
          <p className="text-[10px] text-slate-500">AI hành chính</p>
        </div>}
        <button
          type="button"
          onClick={() => setSidebarCollapsed(prev => !prev)}
          className={`${sidebarCollapsed ? "mt-2" : "ml-auto"} p-1.5 rounded-lg text-slate-500 hover:text-[#006666] hover:shadow-[inset_3px_3px_8px_rgba(159,154,148,0.32),inset_-3px_-3px_8px_rgba(255,255,255,0.78)] transition`}
          title={sidebarCollapsed ? "Mở rộng menu" : "Thu gọn menu"}
          aria-label={sidebarCollapsed ? "Mở rộng menu" : "Thu gọn menu"}
        >
          {sidebarCollapsed ? <PanelLeftOpen className="w-4 h-4" /> : <PanelLeftClose className="w-4 h-4" />}
        </button>
      </div>

      <nav className={`${sidebarCollapsed ? "px-2" : "px-3"} flex-1 space-y-0.5 overflow-y-auto`}>
        {!sidebarCollapsed && (
          <button type="button" onClick={() => toggleSection('personal')} className={sectionHeaderClass} aria-expanded={!collapsedSections.personal}>
            <span>Cá nhân</span>
            <ChevronDown className={`w-3.5 h-3.5 transition-transform ${collapsedSections.personal ? "-rotate-90" : ""}`} />
          </button>
        )}
        {(sidebarCollapsed || !collapsedSections.personal) && (
          <div className="space-y-0.5 pb-3">
            <Link to="/" className={navLinkClass('/')} title="Dashboard"><Home className="w-4 h-4 flex-shrink-0" />{!sidebarCollapsed && "Dashboard"}</Link>
            <Link to="/chat" className={navLinkClass('/chat')} title="Hỏi Đáp RAG"><MessageSquare className="w-4 h-4 flex-shrink-0" />{!sidebarCollapsed && "Hỏi Đáp RAG"}</Link>
            <Link to="/library" className={navLinkClass('/library')} title="Kho Cá Nhân"><FileText className="w-4 h-4 flex-shrink-0" />{!sidebarCollapsed && "Kho Cá Nhân"}</Link>
            <Link to="/sqp" className={navLinkClass('/sqp')} title="Quy Định (SQP)"><BookOpen className="w-4 h-4 flex-shrink-0" />{!sidebarCollapsed && "Quy Định (SQP)"}</Link>
          </div>
        )}

        {user?.role === 'manager' && (<>
          {!sidebarCollapsed && (
            <button type="button" onClick={() => toggleSection('department')} className={`${sectionHeaderClass} mt-2`} aria-expanded={!collapsedSections.department}>
              <span>Phòng ban</span>
              <ChevronDown className={`w-3.5 h-3.5 transition-transform ${collapsedSections.department ? "-rotate-90" : ""}`} />
            </button>
          )}
          {(sidebarCollapsed || !collapsedSections.department) && (
            <div className="space-y-0.5 pb-3">
              <Link to="/manager/docs" className={navLinkClass('/manager/docs')} title="Thư Mục Chung"><FolderKanban className="w-4 h-4 flex-shrink-0" />{!sidebarCollapsed && "Thư Mục Chung"}</Link>
            </div>
          )}
        </>)}

        {user?.role === 'admin' && (<>
          {!sidebarCollapsed && (
            <button type="button" onClick={() => toggleSection('system')} className={`${sectionHeaderClass} mt-2`} aria-expanded={!collapsedSections.system}>
              <span>Hệ thống</span>
              <ChevronDown className={`w-3.5 h-3.5 transition-transform ${collapsedSections.system ? "-rotate-90" : ""}`} />
            </button>
          )}
          {(sidebarCollapsed || !collapsedSections.system) && (
            <div className="space-y-0.5 pb-3">
              <Link to="/admin/users" className={navLinkClass('/admin/users')} title="Tài Khoản"><Users className="w-4 h-4 flex-shrink-0" />{!sidebarCollapsed && "Tài Khoản"}</Link>
              <Link to="/admin/documents" className={navLinkClass('/admin/documents')} title="Tài liệu & Chia sẻ"><FolderKanban className="w-4 h-4 flex-shrink-0" />{!sidebarCollapsed && "Tài liệu & Chia sẻ"}</Link>
              <Link to="/admin/configs" className={navLinkClass('/admin/configs')} title="Cấu Hình"><SlidersHorizontal className="w-4 h-4 flex-shrink-0" />{!sidebarCollapsed && "Cấu Hình"}</Link>
              <Link to="/admin/system" className={navLinkClass('/admin/system')} title="Bảo Trì"><Settings className="w-4 h-4 flex-shrink-0" />{!sidebarCollapsed && "Bảo Trì"}</Link>
            </div>
          )}
        </>)}
      </nav>

      <div className={`${sidebarCollapsed ? "p-2" : "p-3"} border-t border-white/60`}>
        <div className={`flex items-center ${sidebarCollapsed ? "flex-col gap-2" : "justify-between"}`}>
          <div className={`flex items-center ${sidebarCollapsed ? "" : "gap-2"}`}>
            <div className="w-9 h-9 rounded-full bg-[#e7e5e4] flex items-center justify-center text-[#006666] text-sm font-bold shadow-[inset_4px_4px_10px_rgba(159,154,148,0.48),inset_-4px_-4px_10px_rgba(255,255,255,0.86)]">{user?.sub?.charAt(0).toUpperCase()}</div>
            {!sidebarCollapsed && <div><p className="text-xs font-semibold text-slate-800">{user?.sub}</p><p className="text-[10px] text-slate-500 capitalize">{user?.role}</p></div>}
          </div>
          <button onClick={() => { logout(); window.location.href = "/login"; }} className="p-2 text-slate-500 hover:text-[#ff2157] rounded-lg transition" title="Đăng xuất"><LogOut className="w-4 h-4" /></button>
        </div>
      </div>
    </div>
  );
}
