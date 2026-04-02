<script setup lang="ts">
import { onMounted } from 'vue'
import NavBar from '@/components/NavBar.vue'
import AppFooter from '@/components/AppFooter.vue'
import { useHistoryStore } from '@/stores/history'
import type { HistoryEntry } from '@/stores/history'

const history = useHistoryStore()

onMounted(() => history.fetchHistory(true))

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString()
}

const actionLabel: Record<HistoryEntry['action'], string> = {
  sent: 'Sent',
  flushed: 'Flushed',
  auto_sent: 'Auto-sent',
  acknowledged: 'Acknowledged',
  muted_skip: 'Muted skip',
}

const actionClass: Record<HistoryEntry['action'], string> = {
  sent: 'bg-red-900 text-red-300',
  flushed: 'bg-gray-700 text-gray-300',
  auto_sent: 'bg-orange-900 text-orange-300',
  acknowledged: 'bg-green-900 text-green-300',
  muted_skip: 'bg-yellow-900 text-yellow-300',
}

const notifierIcon: Record<string, string> = {
  slack_webhook: 'Slack',
  pushover: 'Pushover',
  pagerduty: 'PagerDuty',
  global: 'Slack (global)',
}

function notifierLabel(type: string, username: string): string {
  if (username === 'global') return notifierIcon['global']
  return `${username} / ${notifierIcon[type] ?? type}`
}
</script>

<template>
  <div class="min-h-screen bg-gray-950 text-white">
    <NavBar />

    <main class="max-w-5xl mx-auto px-6 py-6 space-y-3">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-white font-semibold">Notification History</h2>
        <button
          class="text-xs text-gray-400 hover:text-white underline underline-offset-2 transition-colors"
          @click="history.fetchHistory(true)"
        >
          Refresh
        </button>
      </div>

      <div v-if="history.loading && history.entries.length === 0" class="text-gray-500 text-center py-12">
        Loading…
      </div>

      <div v-else-if="history.error" class="text-red-400 text-center py-12">
        {{ history.error }}
      </div>

      <template v-else>
        <p v-if="history.entries.length === 0" class="text-gray-600 text-center py-12">
          No history yet.
        </p>

        <div
          v-for="entry in history.entries"
          :key="entry.id"
          class="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden"
        >
          <!-- Entry header -->
          <div class="flex items-center gap-3 px-4 py-3 bg-gray-800 border-b border-gray-700 flex-wrap">
            <span
              class="text-xs font-semibold px-2 py-0.5 rounded-full"
              :class="actionClass[entry.action]"
            >
              {{ actionLabel[entry.action] }}
            </span>
            <span class="text-white text-sm font-medium uppercase tracking-wide">{{ entry.queue }}</span>
            <span class="text-gray-400 text-xs">
              {{ entry.incidents.length }} incident{{ entry.incidents.length !== 1 ? 's' : '' }}
            </span>

            <span v-if="entry.takeover_user" class="text-xs bg-blue-900 text-blue-300 px-2 py-0.5 rounded-full">
              takeover: {{ entry.takeover_user }}
            </span>

            <div class="ml-auto flex items-center gap-3">
              <span v-if="entry.triggered_by" class="text-gray-500 text-xs">
                by <span class="text-gray-300">{{ entry.triggered_by }}</span>
              </span>
              <span v-else class="text-gray-500 text-xs italic">scheduler</span>
              <span class="text-gray-600 text-xs">{{ formatTime(entry.created_at) }}</span>
            </div>
          </div>

          <div class="px-4 py-3 grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- Incidents -->
            <div>
              <p class="text-gray-500 text-xs font-medium uppercase tracking-wide mb-2">Incidents</p>
              <ul class="space-y-1.5">
                <li
                  v-for="inc in entry.incidents"
                  :key="inc.id"
                  class="flex items-start gap-2"
                >
                  <span class="text-xs text-gray-600 font-mono shrink-0 mt-0.5">[{{ inc.source }}]</span>
                  <div class="min-w-0">
                    <p class="text-gray-300 text-xs leading-snug">{{ inc.title }}</p>
                    <p v-if="inc.host" class="text-gray-600 text-xs font-mono">{{ inc.host }}<span v-if="inc.service"> / {{ inc.service }}</span></p>
                  </div>
                </li>
              </ul>
            </div>

            <!-- Notifications -->
            <div>
              <p class="text-gray-500 text-xs font-medium uppercase tracking-wide mb-2">Notified</p>
              <div v-if="entry.notifications.length === 0" class="text-gray-600 text-xs italic">
                No notifications sent
              </div>
              <ul v-else class="space-y-1">
                <li
                  v-for="(notif, i) in entry.notifications"
                  :key="i"
                  class="flex items-center gap-2"
                >
                  <span class="w-1.5 h-1.5 rounded-full bg-green-500 shrink-0"></span>
                  <span class="text-gray-300 text-xs">{{ notifierLabel(notif.notifier_type, notif.username) }}</span>
                </li>
              </ul>
            </div>
          </div>
        </div>

        <!-- Load more -->
        <div v-if="history.hasMore" class="text-center pt-2">
          <button
            :disabled="history.loading"
            class="text-sm text-gray-400 hover:text-white disabled:opacity-50 transition-colors underline underline-offset-2"
            @click="history.fetchHistory(false)"
          >
            {{ history.loading ? 'Loading…' : 'Load more' }}
          </button>
        </div>
      </template>
    </main>
    <AppFooter />
  </div>
</template>
