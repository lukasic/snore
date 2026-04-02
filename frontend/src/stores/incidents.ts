import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api/client'

export interface Incident {
  id: string
  source: string
  title: string
  description: string
  queue: string
  host: string | null
  service: string | null
  received_at: string
  raw_payload: Record<string, unknown>
}

export interface TakeoverInfo {
  username: string
  expires_at: string
  ttl_seconds: number
}

export interface OncallInfo {
  usernames: string[]
  ttl_seconds: number | null  // null = permanent (no expiry)
}

export const useIncidentsStore = defineStore('incidents', () => {
  const incidents = ref<Record<string, Incident[]>>({})
  const mutes = ref<Record<string, number>>({})
  const subscribers = ref<Record<string, string[]>>({})
  const takeovers = ref<Record<string, TakeoverInfo>>({})
  const oncall = ref<Record<string, OncallInfo>>({})
  const flushAfter = ref<Record<string, number>>({})
  const nextSchedulerRun = ref<string | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchIncidents(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const res = await api.get<{
        incidents: Record<string, Incident[]>
        mutes: Record<string, number>
        subscribers: Record<string, string[]>
        takeovers: Record<string, TakeoverInfo>
        oncall: Record<string, OncallInfo>
        flush_after: Record<string, number>
        next_scheduler_run: string | null
      }>('/incidents/')
      incidents.value = res.data.incidents
      mutes.value = res.data.mutes
      subscribers.value = res.data.subscribers
      takeovers.value = res.data.takeovers
      oncall.value = res.data.oncall
      flushAfter.value = res.data.flush_after
      nextSchedulerRun.value = res.data.next_scheduler_run
    } catch {
      error.value = 'Failed to load incidents'
    } finally {
      loading.value = false
    }
  }

  async function acknowledge(incidentId: string, queue: string): Promise<void> {
    await api.post('/incidents/acknowledge', { incident_id: incidentId, queue })
    if (incidents.value[queue]) {
      incidents.value[queue] = incidents.value[queue].filter((i) => i.id !== incidentId)
    }
  }

  async function flush(queue: string): Promise<void> {
    await api.post('/incidents/flush', { queue })
    incidents.value[queue] = []
  }

  async function send(queue: string): Promise<void> {
    await api.post('/incidents/send', { queue })
    incidents.value[queue] = []
  }

  async function mute(queue: string, durationMinutes: number): Promise<void> {
    await api.post('/incidents/mute', { queue, duration_minutes: durationMinutes })
    mutes.value[queue] = durationMinutes * 60
  }

  async function unmute(queue: string): Promise<void> {
    await api.post('/incidents/unmute', { queue })
    mutes.value[queue] = 0
  }

  async function takeover(queue: string, durationMinutes: number): Promise<void> {
    const res = await api.post<{ username: string; expires_at: string }>('/incidents/takeover', {
      queue,
      duration_minutes: durationMinutes,
    })
    takeovers.value[queue] = {
      username: res.data.username,
      expires_at: res.data.expires_at,
      ttl_seconds: durationMinutes * 60,
    }
  }

  async function clearTakeover(queue: string): Promise<void> {
    await api.post('/incidents/takeover/clear', { queue })
    delete takeovers.value[queue]
  }

  async function setOncall(queue: string, usernames: string[], durationMinutes: number | null): Promise<void> {
    await api.put(`/queues/${queue}/oncall`, { usernames, duration_minutes: durationMinutes })
    await fetchIncidents()
  }

  async function clearOncall(queue: string): Promise<void> {
    await api.delete(`/queues/${queue}/oncall`)
    delete oncall.value[queue]
    await fetchIncidents()
  }

  return {
    incidents, mutes, subscribers, takeovers, oncall, flushAfter, nextSchedulerRun, loading, error,
    fetchIncidents, acknowledge, flush, send, mute, unmute, takeover, clearTakeover,
    setOncall, clearOncall,
  }
})
