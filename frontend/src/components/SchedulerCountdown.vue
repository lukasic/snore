<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'

const props = defineProps<{
  nextRunIso: string | null
}>()

const secondsLeft = ref<number | null>(null)
let timer: ReturnType<typeof setInterval> | null = null

function recalculate() {
  if (!props.nextRunIso) {
    secondsLeft.value = null
    return
  }
  const diff = Math.round((new Date(props.nextRunIso).getTime() - Date.now()) / 1000)
  secondsLeft.value = Math.max(0, diff)
}

function startTimer() {
  if (timer) clearInterval(timer)
  recalculate()
  timer = setInterval(recalculate, 1000)
}

watch(() => props.nextRunIso, startTimer)
onMounted(startTimer)
onUnmounted(() => { if (timer) clearInterval(timer) })

const label = computed(() => {
  if (secondsLeft.value === null) return null
  if (secondsLeft.value <= 0) return 'now'
  const m = Math.floor(secondsLeft.value / 60)
  const s = secondsLeft.value % 60
  return m > 0 ? `${m}m ${s}s` : `${s}s`
})

const urgency = computed(() => {
  if (secondsLeft.value === null) return 'text-gray-600'
  if (secondsLeft.value <= 10) return 'text-orange-400'
  return 'text-gray-400'
})
</script>

<template>
  <div v-if="label !== null" class="flex items-center gap-1.5 text-xs" :title="`Next scheduler run: ${nextRunIso}`">
    <svg class="w-3 h-3 text-gray-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
      <circle cx="12" cy="12" r="10" />
      <path stroke-linecap="round" d="M12 6v6l4 2" />
    </svg>
    <span class="text-gray-600">next check in</span>
    <span class="font-mono font-medium tabular-nums" :class="urgency">{{ label }}</span>
  </div>
</template>
