<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(username.value, password.value)
    router.push('/')
  } catch {
    error.value = 'Invalid username or password'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-gray-950 flex items-center justify-center px-4">
    <div class="w-full max-w-sm">
      <div class="text-center mb-8">
        <h1 class="text-3xl font-bold text-white tracking-tight">S.N.O.R.E.</h1>
        <p class="text-gray-400 text-sm mt-1">Service Notification Override &amp; Response Engine</p>
      </div>

      <form
        class="bg-gray-900 rounded-xl shadow-xl p-8 border border-gray-800 space-y-5"
        @submit.prevent="submit"
      >
        <div>
          <label class="block text-sm font-medium text-gray-300 mb-1" for="username">Username</label>
          <input
            id="username"
            v-model="username"
            type="text"
            autocomplete="username"
            required
            class="w-full rounded-lg bg-gray-800 border-gray-700 text-white placeholder-gray-500 focus:ring-red-500 focus:border-red-500"
            placeholder="admin"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-300 mb-1" for="password">Password</label>
          <input
            id="password"
            v-model="password"
            type="password"
            autocomplete="current-password"
            required
            class="w-full rounded-lg bg-gray-800 border-gray-700 text-white placeholder-gray-500 focus:ring-red-500 focus:border-red-500"
            placeholder="••••••••"
          />
        </div>

        <p v-if="error" class="text-red-400 text-sm">{{ error }}</p>

        <button
          type="submit"
          :disabled="loading"
          class="w-full bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white font-semibold py-2.5 rounded-lg transition-colors"
        >
          {{ loading ? 'Signing in…' : 'Sign in' }}
        </button>
      </form>
    </div>
  </div>
</template>
