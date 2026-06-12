<script setup>
// Companies — Settings sub-page. Desk-styled list. Lists every company in the
// store with its project count, color badge, and short description. CRUD is
// admin-only (route is gated below); non-admins who hit /app/settings/companies
// directly land on the empty-state redirect.

import { computed, ref } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { useDataStore } from '@/stores'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskList from '@/components/desk/DeskList.vue'
import DeskLink from '@/components/desk/DeskLink.vue'

const store = useDataStore()
const router = useRouter()

const search = ref('')

const items = computed(() => {
  const term = search.value.trim().toLowerCase()
  return store.companies.map(c => ({
    ...c,
    projectCount: store.projectsByCompany(c.id).length,
  })).filter(c => {
    if (!term) return true
    return `${c.id} ${c.name} ${c.shortName} ${c.description || ''}`.toLowerCase().includes(term)
  })
})

const columns = [
  { key: 'id',          label: 'ID' },
  { key: 'name',        label: 'Company' },
  { key: 'description', label: 'Description' },
  { key: 'projects',    label: 'Projects', align: 'right' },
  { key: 'active',      label: 'Active' },
]

const breadcrumbs = [
  { label: 'BuildSuite Core', to: '/' },
  { label: 'Settings', to: '/settings' },
  { label: 'Companies' },
]

const subtitle = computed(() =>
  `${items.value.length} of ${store.companies.length} · multi-company per CLAUDE.md §14`
)

function onRowClick(row) { router.push(`/settings/companies/${row.id}`) }
</script>

<template>
  <DeskPage title="Company" :subtitle="subtitle" :breadcrumbs="breadcrumbs">
    <template #actions>
      <RouterLink
        v-if="store.isAdmin"
        to="/settings/companies/new"
        class="desk-save-btn"
      >+ New Company</RouterLink>
    </template>

    <!-- Non-admin guard — direct URL access still works but the New CTA hides
         and the page reads as informational only. -->
    <div v-if="!store.isAdmin" class="mb-3 px-3 py-2 bg-warning-50 border border-warning-100 text-xs text-warning-700" style="border-radius: 2px;">
      Read-only view. Creating / editing / deleting companies requires the System Manager role.
    </div>

    <DeskList
      v-model="search"
      :rows="items"
      :columns="columns"
      row-key="id"
      search-placeholder="Search by id, name, description…"
      @row-click="onRowClick"
    >
      <template #cell-id="{ row }">
        <DeskLink :to="`/settings/companies/${row.id}`" @click.stop class="font-mono text-xs">{{ row.id }}</DeskLink>
      </template>
      <template #cell-name="{ row }">
        <div class="flex items-center gap-2">
          <span :class="row.color" class="w-3 h-3 flex-shrink-0" style="border-radius: 2px;"></span>
          <div>
            <div class="text-sm font-medium text-ink-900">{{ row.name }}</div>
            <div class="text-[11px] text-ink-500">{{ row.shortName }}</div>
          </div>
        </div>
      </template>
      <template #cell-description="{ row }">
        <span class="text-xs text-ink-600">{{ row.description || '—' }}</span>
      </template>
      <template #cell-projects="{ row }">
        <span class="text-xs tabular-nums" :class="row.projectCount ? 'text-ink-900 font-medium' : 'text-ink-400'">
          {{ row.projectCount }}
        </span>
      </template>
      <template #cell-active="{ row }">
        <span
          v-if="row.id === store.activeCompany"
          class="text-[10px] px-1.5 py-0.5 bg-brand-50 text-brand-700 font-medium"
          style="border-radius: 2px;"
        >Active</span>
        <span v-else class="text-[10px] text-ink-400">—</span>
      </template>

      <template #empty>
        <div class="text-sm text-ink-500">
          No companies match this search.
          <RouterLink v-if="store.isAdmin" to="/settings/companies/new" class="desk-link">Create a company →</RouterLink>
        </div>
      </template>
    </DeskList>
  </DeskPage>
</template>
