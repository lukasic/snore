<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

onMounted(async () => {
  if (auth.token) {
    try {
      await auth.fetchMe()
    } catch {
      auth.logout()
      router.push('/login')
    }
  }
})
</script>

<template>
  <RouterView />
</template>
