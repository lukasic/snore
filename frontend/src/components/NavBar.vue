<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <header class="bg-gray-900 border-b border-gray-800 px-6 py-3 flex items-center justify-between">
    <div class="flex items-center gap-6">
      <h1 class="text-lg font-bold tracking-tight text-white">S.N.O.R.E.</h1>
      <nav class="flex items-center gap-1">
        <RouterLink
          to="/"
          class="text-sm px-3 py-1.5 rounded-lg transition-colors"
          :class="route.path === '/' ? 'bg-gray-700 text-white' : 'text-gray-400 hover:text-white'"
        >
          Dashboard
        </RouterLink>
        <RouterLink
          to="/history"
          class="text-sm px-3 py-1.5 rounded-lg transition-colors"
          :class="route.path === '/history' ? 'bg-gray-700 text-white' : 'text-gray-400 hover:text-white'"
        >
          History
        </RouterLink>
      </nav>
    </div>
    <div class="flex items-center gap-4">
      <span class="text-gray-400 text-sm">{{ auth.user?.username }}</span>
      <button
        class="text-sm text-gray-400 hover:text-white transition-colors"
        @click="logout"
      >
        Sign out
      </button>
    </div>
  </header>
</template>
