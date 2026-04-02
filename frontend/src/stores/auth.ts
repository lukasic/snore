import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api/client'

interface Me {
  username: string
  queues: string[]
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('snore_token'))
  const user = ref<Me | null>(null)

  async function login(username: string, password: string): Promise<void> {
    const res = await api.post<{ access_token: string }>('/auth/login', { username, password })
    token.value = res.data.access_token
    localStorage.setItem('snore_token', token.value)
    await fetchMe()
  }

  async function fetchMe(): Promise<void> {
    const res = await api.get<Me>('/auth/me')
    user.value = res.data
  }

  function logout(): void {
    token.value = null
    user.value = null
    localStorage.removeItem('snore_token')
  }

  return { token, user, login, fetchMe, logout }
})
