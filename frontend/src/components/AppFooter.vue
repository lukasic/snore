<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api/client'

interface BuildInfo {
  commit_hash: string
  commit_time: string
  commit_info: string
  commit_branch: string
  commit_count: string
  pipeline_id: string
  environment: string
}

const frontend: BuildInfo = {
  commit_hash: import.meta.env.VITE_GIT_COMMIT_HASH || 'dev',
  commit_time: import.meta.env.VITE_GIT_COMMIT_TIME || '',
  commit_info: import.meta.env.VITE_GIT_COMMIT_INFO || 'local development',
  commit_branch: import.meta.env.VITE_GIT_COMMIT_BRANCH || 'local',
  commit_count: import.meta.env.VITE_GIT_COMMIT_COUNT || '0',
  pipeline_id: import.meta.env.VITE_PIPELINE_ID || '',
  environment: import.meta.env.VITE_GIT_COMMIT_HASH ? 'production' : 'development',
}

const backend = ref<BuildInfo | null>(null)

onMounted(async () => {
  try {
    const res = await api.get<BuildInfo>('/version/')
    backend.value = res.data
  } catch {
    // non-critical
  }
})
</script>

<template>
  <footer class="border-t border-gray-800 mt-6 py-3 px-6">
    <div class="max-w-6xl mx-auto space-y-1">
      <p class="text-gray-700 text-xs font-mono leading-relaxed">
        <span class="text-gray-500">fe</span>
        | <span class="text-gray-500">commit:</span> {{ frontend.commit_hash }}
        <template v-if="frontend.commit_time"> | <span class="text-gray-500">at:</span> {{ frontend.commit_time }}</template>
        <template v-if="frontend.commit_info"> | <span class="text-gray-500">msg:</span> {{ frontend.commit_info }}</template>
        | <span class="text-gray-500">branch:</span> {{ frontend.commit_branch }}
        | <span class="text-gray-500">build:</span> #{{ frontend.commit_count }}
        <template v-if="frontend.pipeline_id"> | <span class="text-gray-500">pipeline:</span> {{ frontend.pipeline_id }}</template>
      </p>
      <p v-if="backend" class="text-gray-700 text-xs font-mono leading-relaxed">
        <span class="text-gray-500">be</span>
        | <span class="text-gray-500">commit:</span> {{ backend.commit_hash }}
        <template v-if="backend.commit_time"> | <span class="text-gray-500">at:</span> {{ backend.commit_time }}</template>
        <template v-if="backend.commit_info"> | <span class="text-gray-500">msg:</span> {{ backend.commit_info }}</template>
        | <span class="text-gray-500">branch:</span> {{ backend.commit_branch }}
        | <span class="text-gray-500">build:</span> #{{ backend.commit_count }}
        <template v-if="backend.pipeline_id"> | <span class="text-gray-500">pipeline:</span> {{ backend.pipeline_id }}</template>
        | <span class="text-gray-500">env:</span> {{ backend.environment }}
      </p>
    </div>
  </footer>
</template>
