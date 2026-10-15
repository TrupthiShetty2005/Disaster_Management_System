import type { ReactNode } from "react";

export function LoadingState() {
  return (
    <p className="animate-pulse text-sm text-slate-500" role="status" aria-live="polite">
      Loading operations picture…
    </p>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <p className="rounded border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-300" role="alert">
      {message}
    </p>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <p className="rounded border border-line bg-panel p-3 text-sm text-slate-500" role="status">
      {message}
    </p>
  );
}

export function Toast({ message }: { message: string }) {
  return (
    <div className="fixed bottom-4 right-4 rounded border border-amber-500/40 bg-panel px-4 py-2 text-sm text-amber-200">
      {message}
    </div>
  );
}

export function Modal({
  open,
  title,
  children,
  onClose,
}: {
  open: boolean;
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="w-full max-w-lg rounded border border-line bg-panel p-4">
        <div className="mb-3 flex justify-between">
          <h2 className="font-display text-xl">{title}</h2>
          <button onClick={onClose} className="text-slate-400">
            Close
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Drawer({
  open,
  title,
  children,
  onClose,
}: {
  open: boolean;
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-y-0 right-0 z-40 w-80 border-l border-line bg-panel p-4 shadow-xl">
      <div className="mb-3 flex justify-between">
        <h2 className="font-display text-xl">{title}</h2>
        <button onClick={onClose}>Close</button>
      </div>
      {children}
    </div>
  );
}
