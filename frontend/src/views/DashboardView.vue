<script setup lang="ts">
import { onMounted } from 'vue'
import { useIncidentsStore } from '@/stores/incidents'
import { useWebSocket } from '@/composables/useWebSocket'
import NavBar from '@/components/NavBar.vue'
import QueuePanel from '@/components/QueuePanel.vue'
import SchedulerCountdown from '@/components/SchedulerCountdown.vue'
import AppFooter from '@/components/AppFooter.vue'

const incidents = useIncidentsStore()

const { connected, connect } = useWebSocket((msg) => {
  if (msg.type === 'incidents_updated' || msg.type === 'scheduler_tick') {
    incidents.fetchIncidents()
  }
})

onMounted(async () => {
  await incidents.fetchIncidents()
  connect()
})
</script>

<template>
  <div class="min-h-screen bg-gray-950 text-white">
    <NavBar />

    <main class="max-w-6xl mx-auto px-6 py-6 space-y-4">
      <div v-if="incidents.loading && Object.keys(incidents.incidents).length === 0" class="text-gray-500 text-center py-12">
        Loading…
      </div>

      <div v-else-if="incidents.error" class="text-red-400 text-center py-12">
        {{ incidents.error }}
      </div>

      <template v-else>
        <div class="flex items-center justify-between mb-2">
          <div class="flex items-center gap-4">
            <div class="flex items-center gap-2">
              <span
                class="w-2 h-2 rounded-full"
                :class="connected ? 'bg-green-500' : 'bg-yellow-500'"
                :title="connected ? 'Live' : 'Reconnecting…'"
              />
              <p class="text-gray-500 text-xs">{{ connected ? 'Live' : 'Reconnecting…' }}</p>
            </div>
            <SchedulerCountdown :next-run-iso="incidents.nextSchedulerRun" />
          </div>
          <button
            class="text-xs text-gray-400 hover:text-white transition-colors underline underline-offset-2"
            @click="incidents.fetchIncidents()"
          >
            Refresh
          </button>
        </div>

        <QueuePanel
          v-for="(queueIncidents, queueName) in incidents.incidents"
          :key="queueName"
          :name="String(queueName)"
          :incidents="queueIncidents"
          :mute-ttl-seconds="incidents.mutes[String(queueName)] ?? 0"
          :subscribers="incidents.subscribers[String(queueName)] ?? []"
          :takeover="incidents.takeovers[String(queueName)] ?? null"
          :oncall="incidents.oncall[String(queueName)] ?? null"
          :flush-after-minutes="incidents.flushAfter[String(queueName)] ?? 0"
          @acknowledge="(id, q) => incidents.acknowledge(id, q)"
          @flush="incidents.flush($event)"
          @send="incidents.send($event)"
          @mute="(q, m) => incidents.mute(q, m)"
          @unmute="incidents.unmute($event)"
          @takeover="(q, m) => incidents.takeover(q, m)"
          @clear-takeover="incidents.clearTakeover($event)"
          @set-oncall="(q, u, d) => incidents.setOncall(q, u, d)"
          @clear-oncall="incidents.clearOncall($event)"
        />

        <p v-if="Object.keys(incidents.incidents).length === 0" class="text-gray-600 text-center py-12">
          No queues configured.
        </p>
      </template>
    </main>
    <AppFooter />
  </div>
</template>
