import * as React from "react";
import { AlertCircle, CheckCircle2, Info, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

type ToastVariant = "default" | "success" | "destructive";

type ToastInput = {
  title: string;
  description?: string;
  variant?: ToastVariant;
  duration?: number;
};

type ToastItem = ToastInput & {
  id: number;
};

type ToastContextValue = {
  toast: (input: ToastInput) => void;
};

const ToastContext = React.createContext<ToastContextValue | null>(null);
const DEFAULT_DURATION = 3000;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<ToastItem[]>([]);
  const timers = React.useRef<Map<number, number>>(new Map());

  const dismiss = React.useCallback((id: number) => {
    const timer = timers.current.get(id);
    if (timer) {
      window.clearTimeout(timer);
      timers.current.delete(id);
    }
    setToasts((items) => items.filter((item) => item.id !== id));
  }, []);

  const toast = React.useCallback((input: ToastInput) => {
    const id = Date.now() + Math.floor(Math.random() * 1000);
    const item: ToastItem = {
      id,
      variant: "default",
      duration: DEFAULT_DURATION,
      ...input,
    };

    setToasts((items) => [...items, item].slice(-4));
    const timer = window.setTimeout(() => dismiss(id), item.duration);
    timers.current.set(id, timer);
  }, [dismiss]);

  React.useEffect(() => {
    return () => {
      timers.current.forEach((timer) => window.clearTimeout(timer));
      timers.current.clear();
    };
  }, []);

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="pointer-events-none fixed right-4 top-4 z-[100] flex w-[calc(100vw-2rem)] max-w-sm flex-col gap-2">
        {toasts.map((item) => (
          <ToastCard key={item.id} toast={item} onDismiss={() => dismiss(item.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = React.useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within ToastProvider");
  }
  return context.toast;
}

function ToastCard({ toast, onDismiss }: { toast: ToastItem; onDismiss: () => void }) {
  const Icon = toast.variant === "success" ? CheckCircle2 : toast.variant === "destructive" ? AlertCircle : Info;

  return (
    <div
      className={cn(
        "pointer-events-auto flex items-start gap-3 rounded-lg border bg-card/95 p-4 text-card-foreground shadow-xl backdrop-blur-xl",
        "animate-in slide-in-from-right-4 fade-in duration-200",
        toast.variant === "success" && "border-emerald-200 bg-emerald-50/95 text-emerald-950",
        toast.variant === "destructive" && "border-destructive/30 bg-destructive/10 text-foreground",
      )}
      role="status"
      aria-live="polite"
    >
      <Icon
        className={cn(
          "mt-0.5 h-5 w-5 shrink-0",
          toast.variant === "success" && "text-emerald-600",
          toast.variant === "destructive" && "text-destructive",
          toast.variant === "default" && "text-primary",
        )}
      />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold">{toast.title}</p>
        {toast.description && (
          <p className="mt-1 text-sm text-muted-foreground">{toast.description}</p>
        )}
      </div>
      <Button type="button" variant="ghost" size="icon-sm" onClick={onDismiss} className="-mr-1 -mt-1">
        <X className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
}
