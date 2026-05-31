import {
  BookOpen,
  FileText,
  FolderKanban,
  Home,
  LogOut,
  MessageSquare,
  Settings,
  Users,
  Zap,
} from "lucide-react";
import type React from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  Sidebar as ShadcnSidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar";

type SidebarProps = {
  collapsed: boolean;
  onToggleCollapsed: () => void;
};

type NavItem = {
  label: string;
  path: string;
  icon: React.ComponentType<{ className?: string }>;
};

function NavLinkItem({ item }: { item: NavItem }) {
  const location = useLocation();
  const { collapsed } = useSidebar();
  const Icon = item.icon;

  return (
    <SidebarMenuItem>
      <SidebarMenuButton asChild isActive={location.pathname === item.path} tooltip={item.label}>
        <Link to={item.path}>
          <Icon className="h-4 w-4" />
          {!collapsed && <span>{item.label}</span>}
        </Link>
      </SidebarMenuButton>
    </SidebarMenuItem>
  );
}

export default function Sidebar({ onToggleCollapsed }: SidebarProps) {
  const { user, logout } = useAuth();
  const { collapsed } = useSidebar();

  const personalItems: NavItem[] = [
    { label: "Dashboard", path: "/", icon: Home },
    { label: "Hỏi Đáp RAG", path: "/chat", icon: MessageSquare },
    { label: "Kho Cá Nhân", path: "/library", icon: FileText },
    { label: "Quy Định (SQP)", path: "/sqp", icon: BookOpen },
  ];

  const managerItems: NavItem[] = [
    { label: "Thư Mục Chung", path: "/manager/docs", icon: FolderKanban },
  ];

  const adminItems: NavItem[] = [
    { label: "Tài Khoản", path: "/admin/users", icon: Users },
    { label: "Tài liệu & Chia sẻ", path: "/admin/documents", icon: FolderKanban },
    { label: "Bảo Trì Hệ Thống", path: "/admin/system", icon: Settings },
  ];

  const handleLogout = () => {
    logout();
    window.location.href = "/login";
  };

  return (
    <ShadcnSidebar>
      <SidebarHeader className="border-b border-sidebar-border">
        <div className={`flex items-center gap-3 ${collapsed ? "justify-center" : ""}`}>
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
            <Zap className="h-5 w-5" />
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <p className="truncate text-sm font-bold tracking-wide">RAG.Gov</p>
              <p className="truncate text-xs text-muted-foreground">AI hành chính</p>
            </div>
          )}
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Cá nhân</SidebarGroupLabel>
          <SidebarMenu>
            {personalItems.map((item) => <NavLinkItem key={item.path} item={item} />)}
          </SidebarMenu>
        </SidebarGroup>

        {user?.role === "manager" && (
          <SidebarGroup>
            <SidebarGroupLabel>Phòng ban</SidebarGroupLabel>
            <SidebarMenu>
              {managerItems.map((item) => <NavLinkItem key={item.path} item={item} />)}
            </SidebarMenu>
          </SidebarGroup>
        )}

        {user?.role === "admin" && (
          <SidebarGroup>
            <SidebarGroupLabel>Hệ thống</SidebarGroupLabel>
            <SidebarMenu>
              {adminItems.map((item) => <NavLinkItem key={item.path} item={item} />)}
            </SidebarMenu>
          </SidebarGroup>
        )}
      </SidebarContent>

      <SidebarFooter>
        <SidebarTrigger
          className="mb-3 w-full"
          onClick={onToggleCollapsed}
          title={collapsed ? "Mở rộng menu" : "Thu nhỏ menu"}
        />
        <div className={`flex items-center gap-3 ${collapsed ? "justify-center" : "justify-between"}`}>
          <div className={`flex min-w-0 items-center ${collapsed ? "justify-center" : "gap-2"}`}>
            <Avatar className="h-9 w-9">
              <AvatarFallback className="bg-primary/10 text-primary">
                {user?.sub?.charAt(0).toUpperCase()}
              </AvatarFallback>
            </Avatar>
            {!collapsed && (
              <div className="min-w-0">
                <p className="truncate text-xs font-semibold">{user?.sub}</p>
                <p className="truncate text-[11px] capitalize text-muted-foreground">{user?.role}</p>
              </div>
            )}
          </div>
          {!collapsed && (
            <Button type="button" variant="ghost" size="icon-sm" onClick={handleLogout} title="Đăng xuất">
              <LogOut className="h-4 w-4" />
            </Button>
          )}
        </div>
      </SidebarFooter>
    </ShadcnSidebar>
  );
}
