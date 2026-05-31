import * as React from "react";
import { PanelLeft } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

type SidebarContextValue = {
  collapsed: boolean;
  setCollapsed: (collapsed: boolean) => void;
  toggleSidebar: () => void;
};

const SidebarContext = React.createContext<SidebarContextValue | null>(null);

function useSidebar() {
  const context = React.useContext(SidebarContext);
  if (!context) throw new Error("useSidebar must be used inside SidebarProvider");
  return context;
}

type SidebarProviderProps = React.HTMLAttributes<HTMLDivElement> & {
  open?: boolean;
  defaultOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
};

function SidebarProvider({
  open,
  defaultOpen = true,
  onOpenChange,
  className,
  children,
  ...props
}: SidebarProviderProps) {
  const [internalOpen, setInternalOpen] = React.useState(defaultOpen);
  const actualOpen = open ?? internalOpen;
  const setOpen = React.useCallback(
    (nextOpen: boolean) => {
      onOpenChange?.(nextOpen);
      if (open === undefined) setInternalOpen(nextOpen);
    },
    [onOpenChange, open],
  );
  const value = React.useMemo(
    () => ({
      collapsed: !actualOpen,
      setCollapsed: (collapsed: boolean) => setOpen(!collapsed),
      toggleSidebar: () => setOpen(!actualOpen),
    }),
    [actualOpen, setOpen],
  );

  return (
    <SidebarContext.Provider value={value}>
      <div
        data-sidebar-state={actualOpen ? "expanded" : "collapsed"}
        className={cn("group/sidebar-wrapper flex h-screen w-full overflow-hidden", className)}
        {...props}
      >
        {children}
      </div>
    </SidebarContext.Provider>
  );
}

function Sidebar({ className, ...props }: React.HTMLAttributes<HTMLElement>) {
  const { collapsed } = useSidebar();
  return (
    <aside
      className={cn(
        "glass-sidebar flex h-screen shrink-0 flex-col border-r border-sidebar-border bg-sidebar/80 text-sidebar-foreground transition-[width] duration-300",
        collapsed ? "w-[4.75rem]" : "w-72",
        className,
      )}
      {...props}
    />
  );
}

function SidebarTrigger({ className, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const { toggleSidebar } = useSidebar();
  return (
    <Button type="button" variant="ghost" size="icon-sm" className={className} onClick={toggleSidebar} {...props}>
      <PanelLeft className="h-4 w-4" />
      <span className="sr-only">Thu gọn menu</span>
    </Button>
  );
}

function SidebarHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-col gap-2 p-3", className)} {...props} />;
}

function SidebarContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("min-h-0 flex-1 overflow-y-auto p-3", className)} {...props} />;
}

function SidebarFooter({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("border-t border-sidebar-border p-3", className)} {...props} />;
}

function SidebarGroup({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("space-y-1 py-2", className)} {...props} />;
}

function SidebarGroupLabel({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  const { collapsed } = useSidebar();
  if (collapsed) return null;
  return <p className={cn("px-3 pb-1 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground", className)} {...props} />;
}

function SidebarMenu({ className, ...props }: React.HTMLAttributes<HTMLUListElement>) {
  return <ul className={cn("space-y-1", className)} {...props} />;
}

function SidebarMenuItem({ className, ...props }: React.HTMLAttributes<HTMLLIElement>) {
  return <li className={cn("relative", className)} {...props} />;
}

type SidebarMenuButtonProps = React.AnchorHTMLAttributes<HTMLAnchorElement> & {
  isActive?: boolean;
  tooltip?: string;
  asChild?: boolean;
};

function SidebarMenuButton({ className, isActive, tooltip, children, asChild = false, ...props }: SidebarMenuButtonProps) {
  const { collapsed } = useSidebar();
  const itemClassName = cn(
    "flex h-10 items-center gap-3 rounded-md px-3 text-sm font-medium transition-colors",
    collapsed && "justify-center px-0",
    isActive
      ? "bg-sidebar-accent text-sidebar-accent-foreground shadow-sm"
      : "text-sidebar-foreground/75 hover:bg-sidebar-accent/70 hover:text-sidebar-accent-foreground",
    className,
  );

  if (asChild && React.isValidElement<{ className?: string; title?: string }>(children)) {
    return React.cloneElement(children, {
      className: cn(itemClassName, children.props.className),
      title: collapsed ? tooltip : children.props.title,
    });
  }

  return (
    <a
      title={collapsed ? tooltip : undefined}
      className={itemClassName}
      {...props}
    >
      {children}
    </a>
  );
}

export {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
  useSidebar,
};
