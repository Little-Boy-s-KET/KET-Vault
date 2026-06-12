/**
 * KET Board - Toast Notification Component.
 *
 * Lightweight notification for connection status:
 * - info: reconnecting
 * - error: connection failed
 * - success: reconnected
 */

import type { Toast as ToastData } from "../hooks/usePipeline";

interface Props {
  toasts: ToastData[];
  onDismiss: (id: string) => void;
}

const ICON_MAP = {
  info: ">>",
  error: "!!",
  success: "OK",
};

export function ToastContainer({ toasts, onDismiss }: Props) {
  if (toasts.length === 0) return null;

  return (
    <div className="toast-container">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`toast toast-${toast.type}`}
          onClick={() => onDismiss(toast.id)}
          role="alert"
        >
          <span className="toast-icon">{ICON_MAP[toast.type]}</span>
          <span>{toast.message}</span>
        </div>
      ))}
    </div>
  );
}
