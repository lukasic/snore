<script setup lang="ts">
import { ref } from 'vue'
import type { Incident, TakeoverInfo, OncallInfo } from '@/stores/incidents'
import IncidentCard from './IncidentCard.vue'

defineProps<{
  name: string
  incidents: Incident[]
  muteTtlSeconds: number
  subscribers: string[]
  takeover: TakeoverInfo | null
  oncall: OncallInfo | null
  flushAfterMinutes: number
}>()

const emit = defineEmits<{
  acknowledge: [id: string, queue: string]
  flush: [queue: string]
  send: [queue: string]
  mute: [queue: string, minutes: number]
  unmute: [queue: string]
  takeover: [queue: string, minutes: number]
  clearTakeover: [queue: string]
  setOncall: [queue: string, usernames: string[], durationMinutes: number | null]
  clearOncall: [queue: string]
}>()

const customMuteMinutes = ref(60)
const showMuteInput = ref(false)
const customTakeoverMinutes = ref(60)
const showTakeoverInput = ref(false)
const showOncallInput = ref(false)
const oncallUsernamesRaw = ref('')
const oncallDurationMinutes = ref<number | null>(null)

function ttlLabel(seconds: number): string {
  if (seconds <= 0) return ''
  const m = Math.ceil(seconds / 60)
  return m >= 60 ? `${Math.floor(m / 60)}h ${m % 60}m` : `${m}m`
}

function applyOncall(queue: string): void {
  const usernames = oncallUsernamesRaw.value
    .split(',')
    .map((u) => u.trim())
    .filter((u) => u.length > 0)
  emit('setOncall', queue, usernames, oncallDurationMinutes.value)
  showOncallInput.value = false
  oncallUsernamesRaw.value = ''
  oncallDurationMinutes.value = null
}
</script>

<template>
  <div class="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
    <!-- Queue header -->
    <div class="flex items-center justify-between px-4 py-3 bg-gray-800 border-b border-gray-700">
      <div class="flex items-center gap-2 flex-wrap">
        <h2 class="text-white font-semibold text-sm uppercase tracking-wide">{{ name }}</h2>
        <span
          class="text-xs font-bold px-2 py-0.5 rounded-full"
          :class="incidents.length > 0 ? 'bg-red-600 text-white' : 'bg-gray-700 text-gray-400'"
        >
          {{ incidents.length }}
        </span>
        <span class="text-xs text-gray-600" title="Auto-flush threshold">
          {{ flushAfterMinutes }}m
        </span>
        <span
          v-if="muteTtlSeconds > 0"
          class="text-xs bg-yellow-800 text-yellow-300 font-medium px-2 py-0.5 rounded-full"
        >
          MUTED {{ ttlLabel(muteTtlSeconds) }}
        </span>
        <span
          v-if="takeover"
          class="text-xs bg-blue-800 text-blue-200 font-medium px-2 py-0.5 rounded-full"
          :title="`Expires at ${takeover.expires_at}`"
        >
          TAKEOVER: {{ takeover.username }} ({{ ttlLabel(takeover.ttl_seconds) }})
        </span>
        <span
          v-if="oncall"
          class="text-xs bg-green-800 text-green-200 font-medium px-2 py-0.5 rounded-full"
          :title="oncall.ttl_seconds != null ? `Expires in ${ttlLabel(oncall.ttl_seconds)}` : 'Permanent until cleared'"
        >
          ON-CALL: {{ oncall.usernames.join(', ') }}
          <template v-if="oncall.ttl_seconds != null"> ({{ ttlLabel(oncall.ttl_seconds) }})</template>
        </span>
      </div>

      <!-- Subscribers -->
      <div v-if="subscribers.length > 0" class="flex items-center gap-1.5 mx-3">
        <svg class="w-3.5 h-3.5 text-gray-500 shrink-0" fill="currentColor" viewBox="0 0 20 20">
          <path d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" />
        </svg>
        <span
          v-for="user in subscribers"
          :key="user"
          class="text-xs px-2 py-0.5 rounded-full"
          :class="takeover && takeover.username !== user
            ? 'text-gray-600 bg-gray-800 line-through'
            : 'text-gray-400 bg-gray-700'"
          :title="takeover && takeover.username !== user ? 'Bypassed by takeover' : ''"
        >
          {{ user }}
        </span>
        <span
          v-if="takeover && !subscribers.includes(takeover.username)"
          class="text-xs text-blue-300 bg-blue-900 px-2 py-0.5 rounded-full"
        >
          {{ takeover.username }} ★
        </span>
      </div>

      <div class="flex items-center gap-2 flex-wrap justify-end">
        <!-- Takeover controls -->
        <template v-if="takeover">
          <button
            class="text-xs bg-blue-700 hover:bg-blue-600 text-white px-2.5 py-1 rounded-lg transition-colors"
            @click="emit('clearTakeover', name)"
          >
            End takeover
          </button>
        </template>
        <template v-else>
          <button
            v-if="!showTakeoverInput"
            class="text-xs bg-blue-700 hover:bg-blue-600 text-white px-2.5 py-1 rounded-lg transition-colors"
            title="Temporarily take over this queue — you receive all notifications"
            @click="showTakeoverInput = true"
          >
            Takeover
          </button>
          <template v-else>
            <input
              v-model.number="customTakeoverMinutes"
              type="number"
              min="1"
              max="480"
              class="w-16 text-xs bg-gray-800 border-gray-700 text-white rounded-lg px-2 py-1"
            />
            <span class="text-gray-400 text-xs">min</span>
            <button
              class="text-xs bg-blue-700 hover:bg-blue-600 text-white px-2.5 py-1 rounded-lg transition-colors"
              @click="emit('takeover', name, customTakeoverMinutes); showTakeoverInput = false"
            >
              Apply
            </button>
            <button
              class="text-xs text-gray-400 hover:text-gray-200 px-1"
              @click="showTakeoverInput = false"
            >
              ✕
            </button>
          </template>
        </template>

        <!-- On-call controls -->
        <template v-if="oncall">
          <button
            class="text-xs bg-green-700 hover:bg-green-600 text-white px-2.5 py-1 rounded-lg transition-colors"
            title="Revert to config-defined subscribers"
            @click="emit('clearOncall', name)"
          >
            Clear on-call
          </button>
        </template>
        <template v-else>
          <button
            v-if="!showOncallInput"
            class="text-xs bg-green-700 hover:bg-green-600 text-white px-2.5 py-1 rounded-lg transition-colors"
            title="Set dynamic on-call users for this queue"
            @click="showOncallInput = true"
          >
            On-call
          </button>
          <template v-else>
            <input
              v-model="oncallUsernamesRaw"
              type="text"
              placeholder="alice, bob"
              class="w-28 text-xs bg-gray-800 border-gray-700 text-white rounded-lg px-2 py-1"
            />
            <input
              v-model.number="oncallDurationMinutes"
              type="number"
              min="1"
              max="1440"
              placeholder="∞ min"
              class="w-16 text-xs bg-gray-800 border-gray-700 text-white rounded-lg px-2 py-1"
            />
            <button
              class="text-xs bg-green-700 hover:bg-green-600 text-white px-2.5 py-1 rounded-lg transition-colors"
              @click="applyOncall(name)"
            >
              Apply
            </button>
            <button
              class="text-xs text-gray-400 hover:text-gray-200 px-1"
              @click="showOncallInput = false"
            >
              ✕
            </button>
          </template>
        </template>

        <!-- Mute controls -->
        <template v-if="muteTtlSeconds > 0">
          <button
            class="text-xs bg-gray-700 hover:bg-gray-600 text-gray-200 px-2.5 py-1 rounded-lg transition-colors"
            @click="emit('unmute', name)"
          >
            Unmute
          </button>
        </template>
        <template v-else>
          <button
            v-if="!showMuteInput"
            class="text-xs bg-yellow-700 hover:bg-yellow-600 text-white px-2.5 py-1 rounded-lg transition-colors"
            @click="showMuteInput = true"
          >
            Mute
          </button>
          <template v-else>
            <input
              v-model.number="customMuteMinutes"
              type="number"
              min="1"
              max="480"
              class="w-16 text-xs bg-gray-800 border-gray-700 text-white rounded-lg px-2 py-1"
            />
            <span class="text-gray-400 text-xs">min</span>
            <button
              class="text-xs bg-yellow-700 hover:bg-yellow-600 text-white px-2.5 py-1 rounded-lg transition-colors"
              @click="emit('mute', name, customMuteMinutes); showMuteInput = false"
            >
              Apply
            </button>
            <button
              class="text-xs text-gray-400 hover:text-gray-200 px-1"
              @click="showMuteInput = false"
            >
              ✕
            </button>
          </template>
        </template>

        <!-- Flush (ack all) -->
        <button
          :disabled="incidents.length === 0"
          class="text-xs bg-gray-600 hover:bg-gray-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium px-2.5 py-1 rounded-lg transition-colors"
          title="Flush — acknowledge all, remove from queue without sending notifications"
          @click="emit('flush', name)"
        >
          Flush
        </button>

        <!-- Send (notify + clear) -->
        <button
          :disabled="incidents.length === 0"
          class="text-xs bg-red-700 hover:bg-red-600 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium px-2.5 py-1 rounded-lg transition-colors"
          title="Send — dispatch all incidents to notification backends and remove from queue"
          @click="emit('send', name)"
        >
          Send
        </button>
      </div>
    </div>

    <!-- Incidents list -->
    <div class="p-3 space-y-2 max-h-[600px] overflow-y-auto">
      <p v-if="incidents.length === 0" class="text-gray-600 text-sm text-center py-6">No incidents</p>
      <IncidentCard
        v-for="incident in incidents"
        :key="incident.id"
        :incident="incident"
        @acknowledge="emit('acknowledge', $event, incident.queue)"
      />
    </div>
  </div>
</template>
