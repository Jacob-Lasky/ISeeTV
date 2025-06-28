// Define toast types
export type ToastType = "success" | "info" | "warn" | "error"

// Define toast message structure
export interface ToastMessage {
    severity: ToastType
    summary: string
    detail?: string
    life?: number
    closable?: boolean
}

// Global event emitter for toast messages
class ToastEventEmitter {
    private listeners: Array<(message: ToastMessage) => void> = []

    emit(message: ToastMessage) {
        this.listeners.forEach((listener) => listener(message))
    }

    subscribe(listener: (message: ToastMessage) => void) {
        this.listeners.push(listener)
        return () => {
            const index = this.listeners.indexOf(listener)
            if (index > -1) {
                this.listeners.splice(index, 1)
            }
        }
    }
}

const toastEmitter = new ToastEventEmitter()

/**
 * Global toast service that can be used anywhere in the application
 */
export const toastService = {
    /**
     * Show a toast notification
     * @param severity - Type of toast (success, info, warn, error)
     * @param summary - Main message text
     * @param detail - Optional detailed message
     * @param life - Optional duration in milliseconds
     */
    showToast(
        severity: ToastType,
        summary: string,
        detail?: string,
        life: number = 3000
    ) {
        toastEmitter.emit({
            severity,
            summary,
            detail,
            life,
            closable: true,
        })
    },

    /**
     * Show a success toast notification
     * @param summary - Main message text
     * @param detail - Optional detailed message
     */
    showSuccess(summary: string, detail?: string) {
        this.showToast("success", summary, detail)
    },

    /**
     * Show an info toast notification
     * @param summary - Main message text
     * @param detail - Optional detailed message
     */
    showInfo(summary: string, detail?: string) {
        this.showToast("info", summary, detail)
    },

    /**
     * Show a warning toast notification
     * @param summary - Main message text
     * @param detail - Optional detailed message
     */
    showWarn(summary: string, detail?: string) {
        this.showToast("warn", summary, detail)
    },

    /**
     * Show an error toast notification
     * @param summary - Main message text
     * @param detail - Optional detailed message
     */
    showError(summary: string, detail?: string) {
        this.showToast("error", summary, detail)
    },
}

/**
 * Composable for components to listen to toast events
 * This should be used in component setup functions
 */
export function useToastListener() {
    const subscribe = (listener: (message: ToastMessage) => void) => {
        return toastEmitter.subscribe(listener)
    }

    return {
        subscribe,
    }
}
