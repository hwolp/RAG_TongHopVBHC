import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useEffect, useState } from 'react';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import Library from './pages/Library';
import Chat from './pages/Chat';
import Login from './pages/Login';
import AdminUsers from './pages/AdminUsers';
import AdminDocuments from './pages/AdminDocuments';
import AdminSystem from './pages/AdminSystem';
import ManagerDocs from './pages/ManagerDocs';
import SQPBrowser from './pages/SQPBrowser';
import { useAuth } from './hooks/useAuth';
import { SidebarProvider } from '@/components/ui/sidebar';
import { ToastProvider } from '@/components/ui/toast';

const ProtectedRoute = ({ children, allowedRoles }: { children: React.ReactNode, allowedRoles?: string[] }) => {
  const { user, loading } = useAuth();
  if (loading) return <div className="h-screen flex items-center justify-center text-slate-500">Đang tải...</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (allowedRoles && !allowedRoles.includes(user.role)) return <Navigate to="/" replace />;
  return <>{children}</>;
};

const Layout = ({ children }: { children: React.ReactNode }) => {
  const location = useLocation();
  const isChatRoute = location.pathname === "/chat";
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => (
    localStorage.getItem("ragGovSidebarCollapsed") === "true"
  ));

  useEffect(() => {
    localStorage.setItem("ragGovSidebarCollapsed", String(sidebarCollapsed));
  }, [sidebarCollapsed]);

  return (
    <SidebarProvider open={!sidebarCollapsed} onOpenChange={(open) => setSidebarCollapsed(!open)}>
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggleCollapsed={() => setSidebarCollapsed(value => !value)}
      />
      <main className={`min-h-0 flex-1 bg-transparent ${isChatRoute ? "overflow-hidden" : "overflow-y-auto"}`}>
        {children}
      </main>
    </SidebarProvider>
  );
};

export default function App() {
  return (
    <ToastProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />

          {/* Core */}
          <Route path="/" element={<ProtectedRoute><Layout><Dashboard /></Layout></ProtectedRoute>} />
          <Route path="/chat" element={<ProtectedRoute><Layout><Chat /></Layout></ProtectedRoute>} />
          <Route path="/library" element={<ProtectedRoute><Layout><Library /></Layout></ProtectedRoute>} />
          <Route path="/sqp" element={<ProtectedRoute><Layout><SQPBrowser /></Layout></ProtectedRoute>} />

          {/* Admin */}
          <Route path="/admin/users" element={<ProtectedRoute allowedRoles={['admin']}><Layout><AdminUsers /></Layout></ProtectedRoute>} />
          <Route path="/admin/documents" element={<ProtectedRoute allowedRoles={['admin']}><Layout><AdminDocuments /></Layout></ProtectedRoute>} />
          <Route path="/admin/system" element={<ProtectedRoute allowedRoles={['admin']}><Layout><AdminSystem /></Layout></ProtectedRoute>} />

          {/* Manager */}
          <Route path="/manager/docs" element={<ProtectedRoute allowedRoles={['admin','manager']}><Layout><ManagerDocs /></Layout></ProtectedRoute>} />
        </Routes>
      </Router>
    </ToastProvider>
  );
}
