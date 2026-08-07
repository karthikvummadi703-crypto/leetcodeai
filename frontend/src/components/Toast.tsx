/* oxlint-disable react/only-export-components */
import React, { createContext, useContext, useCallback, useState } from "react";

type ToastType = "success" | "error" | "info";

interface ToastItem {
  id: number;
  message: string;
  type: ToastType;
}

interface ToastContextType {
  toast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextType>({
  toast: () => {},
});

export const useToast = () => useContext(ToastContext);

let nextId = 1;

export const ToastProvider = ({ children }: { children: React.ReactNode }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback(
    (message: string, type: ToastType = "info") => {
      const id = nextId++;
      setToasts((prev) => [...prev.slice(-3), { id, message, type }]);
      window.setTimeout(() => dismiss(id), 3500);
    },
    [dismiss],
  );

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[100] flex flex-col items-center gap-2 px-4">
        {toasts.map((t) => (
          <button
            key={t.id}
            onClick={() => dismiss(t.id)}
            className={`pointer-events-auto max-w-md text-sm rounded-full px-4 py-2 shadow-lg border backdrop-blur-xl transition-all ${
              t.type === "error"
                ? "bg-red-500/15 border-red-500/30 text-red-300"
                : t.type === "success"
                  ? "bg-emerald-500/15 border-emerald-500/30 text-emerald-300"
                  : "bg-card/90 border-border/50 text-foreground"
            }`}
          >
            {t.message}
          </button>
        ))}
      </div>
    </ToastContext.Provider>
  );
};
