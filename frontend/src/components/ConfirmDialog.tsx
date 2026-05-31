import { useCallback, useState } from "react";
import { AlertTriangle, Trash2, X } from "lucide-react";

type ConfirmOptions = {
  title: string;
  description?: string;
  confirmText?: string;
  cancelText?: string;
  variant?: "danger" | "warning";
};

type PendingConfirm = ConfirmOptions & {
  resolve: (confirmed: boolean) => void;
};

export function useConfirmDialog() {
  const [pending, setPending] = useState<PendingConfirm | null>(null);

  const confirm = useCallback((options: ConfirmOptions) => {
    return new Promise<boolean>((resolve) => {
      setPending({
        cancelText: "Hủy",
        confirmText: "Xác nhận",
        variant: "danger",
        ...options,
        resolve,
      });
    });
  }, []);

  const close = (confirmed: boolean) => {
    pending?.resolve(confirmed);
    setPending(null);
  };

  const dialog = pending ? (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/45 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-dialog-title"
    >
      <div className="neo-modal w-full max-w-md overflow-hidden">
        <div className="flex items-start justify-between gap-4 border-b border-white/60 p-5">
          <div className="flex items-start gap-3">
            <div
              className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg ${
                pending.variant === "warning" ? "bg-amber-100 text-amber-700" : "bg-red-100 text-red-700"
              }`}
            >
              {pending.variant === "warning" ? <AlertTriangle className="h-5 w-5" /> : <Trash2 className="h-5 w-5" />}
            </div>
            <div>
              <h2 id="confirm-dialog-title" className="text-base font-bold text-slate-900">
                {pending.title}
              </h2>
              {pending.description && (
                <p className="mt-1 text-sm leading-6 text-slate-600">{pending.description}</p>
              )}
            </div>
          </div>
          <button
            type="button"
            onClick={() => close(false)}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-white/50 hover:text-slate-700"
            aria-label="Đóng"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex justify-end gap-2 p-5">
          <button type="button" onClick={() => close(false)} className="neo-button">
            {pending.cancelText}
          </button>
          <button
            type="button"
            onClick={() => close(true)}
            className={`neo-button ${pending.variant === "warning" ? "text-amber-700" : "neo-button-danger"}`}
          >
            {pending.confirmText}
          </button>
        </div>
      </div>
    </div>
  ) : null;

  return { confirm, confirmDialog: dialog };
}
