/// <reference types="vite/client" />
interface Window {
  Telegram?: {
    WebApp: {
      initData: string
      colorScheme: string
      ready: () => void
      expand: () => void
      isVersionAtLeast?: (version: string) => boolean
      requestContact?: (callback: (sent: boolean) => void) => void
      setHeaderColor?: (color: string) => void
      setBackgroundColor?: (color: string) => void
      onEvent?: (event: string, callback: () => void) => void
      offEvent?: (event: string, callback: () => void) => void
      enableClosingConfirmation?: () => void
      disableClosingConfirmation?: () => void
      BackButton?: {
        show: () => void
        hide: () => void
        onClick: (callback: () => void) => void
        offClick: (callback: () => void) => void
      }
      HapticFeedback?: {
        notificationOccurred: (type: 'success' | 'error' | 'warning') => void
        selectionChanged: () => void
      }
    }
  }
}
