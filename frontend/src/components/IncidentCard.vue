<script setup lang="ts">
import type { Incident } from '@/stores/incidents'

defineProps<{
  incident: Incident
}>()

const emit = defineEmits<{
  acknowledge: [id: string, queue: string]
}>()

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString()
}

const sourceColors: Record<string, string> = {
  icinga2: 'bg-blue-900 text-blue-300',
  uptime_kuma: 'bg-purple-900 text-purple-300',
  nodeping: 'bg-yellow-900 text-yellow-300',
  manual: 'bg-gray-700 text-gray-300',
}
</script>

<template>
  <div class="bg-gray-800 border border-gray-700 rounded-lg p-4 space-y-2">
    <div class="flex items-start justify-between gap-3">
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 flex-wrap">
          <span
            class="text-xs font-medium px-2 py-0.5 rounded-full"
            :class="sourceColors[incident.source] ?? 'bg-gray-700 text-gray-300'"
          >
            {{ incident.source }}
          </span>
          <span v-if="incident.host" class="text-xs text-gray-400 font-mono">{{ incident.host }}</span>
          <span v-if="incident.service" class="text-xs text-gray-500 font-mono">/ {{ incident.service }}</span>
        </div>
        <p class="text-white font-semibold mt-1 text-sm leading-snug">{{ incident.title }}</p>
        <p v-if="incident.description" class="text-gray-400 text-xs mt-0.5">{{ incident.description }}</p>
      </div>

      <button
        class="shrink-0 text-xs bg-green-700 hover:bg-green-600 text-white font-medium px-3 py-1.5 rounded-lg transition-colors"
        title="Acknowledge — remove from queue"
        @click="emit('acknowledge', incident.id, incident.queue)"
      >
        ACK
      </button>
    </div>

    <p class="text-gray-600 text-xs">{{ formatTime(incident.received_at) }}</p>
  </div>
</template>
