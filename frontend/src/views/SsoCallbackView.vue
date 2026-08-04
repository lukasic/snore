<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { handleKeycloakCallback } from '@/api/oidc'

const auth = useAuthStore()
const router = useRouter()
const error = ref('')

onMounted(async () => {
  try {
    const idToken = await handleKeycloakCallback()
    await auth.loginSso(idToken)
    router.push('/')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'SSO login failed'
  }
})
</script>

<template>
  <div class="min-h-screen bg-gray-950 flex items-center justify-center px-4">
    <div class="w-full max-w-sm text-center">
      <p v-if="!error" class="text-gray-400">Signing you in…</p>
      <template v-else>
        <p class="text-red-400 text-sm mb-4">{{ error }}</p>
        <router-link to="/login" class="text-sm text-gray-400 underline">Back to login</router-link>
      </template>
    </div>
  </div>
</template>
