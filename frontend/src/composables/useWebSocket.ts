import { ref, onUnmounted } from 'vue'

type MessageHandler = (data: Record<string, unknown>) => void

const BASE_DELAY = 1_000
const MAX_DELAY = 30_000

export function useWebSocket(onMessage: MessageHandler) {
  const connected = ref(false)
  let ws: WebSocket | null = null
  let retryDelay = BASE_DELAY
  let stopped = false
  let retryTimer: ReturnType<typeof setTimeout> | null = null

  function getToken(): string | null {
    return localStorage.getItem('snore_token')
  }

  function connect() {
    if (stopped) return
    const token = getToken()
    if (!token) return

    const protocol = location.protocol === 'https:' ? 'wss' : 'ws'
    const url = `${protocol}://${location.host}/ws?token=${encodeURIComponent(token)}`
    ws = new WebSocket(url)

    ws.onopen = () => {
      connected.value = true
      retryDelay = BASE_DELAY
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        onMessage(data)
      } catch {
        // ignore malformed messages
      }
    }

    ws.onclose = (event) => {
      connected.value = false
      ws = null
      // 4001 = auth failure, don't retry
      if (event.code === 4001 || stopped) return
      retryTimer = setTimeout(() => {
        retryDelay = Math.min(retryDelay * 2, MAX_DELAY)
        connect()
      }, retryDelay)
    }

    ws.onerror = () => {
      ws?.close()
    }
  }

  function disconnect() {
    stopped = true
    if (retryTimer) clearTimeout(retryTimer)
    ws?.close()
    ws = null
  }

  onUnmounted(disconnect)

  return { connected, connect, disconnect }
}
