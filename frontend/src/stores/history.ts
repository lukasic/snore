import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api/client'

export interface HistoryNotification {
  username: string
  notifier_type: string
}

export interface HistoryIncident {
  id: string
  title: string
  source: string
  host: string | null
  service: string | null
  received_at: string
}

export interface HistoryEntry {
  id: string
  queue: string
  action: 'sent' | 'flushed' | 'auto_sent' | 'acknowledged' | 'muted_skip'
  incidents: HistoryIncident[]
  notifications: HistoryNotification[]
  takeover_user: string | null
  triggered_by: string | null
  created_at: string
}

export const useHistoryStore = defineStore('history', () => {
  const entries = ref<HistoryEntry[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const hasMore = ref(true)

  async function fetchHistory(reset = false): Promise<void> {
    if (reset) {
      entries.value = []
      hasMore.value = true
    }
    loading.value = true
    error.value = null
    try {
      const offset = reset ? 0 : entries.value.length
      const res = await api.get<{ entries: HistoryEntry[] }>('/history/', {
        params: { limit: 50, offset },
      })
      const newEntries = res.data.entries
      if (reset) {
        entries.value = newEntries
      } else {
        entries.value.push(...newEntries)
      }
      hasMore.value = newEntries.length === 50
    } catch {
      error.value = 'Failed to load history'
    } finally {
      loading.value = false
    }
  }

  return { entries, loading, error, hasMore, fetchHistory }
})
