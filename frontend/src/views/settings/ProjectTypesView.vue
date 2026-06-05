<script setup>
// Project Type Settings — list page. Session 39 (exploratory).
//
// Promotes Project Type from JSON fixture (§13.3 item 19 "Light") to a
// configurable record set keyed on the same `name` field. Editable surface
// here is the human Work Package label per type (Block / Tower / Chainage
// Segment / …) and which template the type's new projects get seeded from.
// Per Session 39 framing this is exploratory — see §10 entry.
//
// Admin / BSA gated. Non-admins are sent back to the Settings hub.

import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useDataStore } from '@/stores'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskList from '@/components/desk/DeskList.vue'
import DeskLink from '@/components/desk/DeskLink.vue'

const store = useDataStore()
const router = useRouter()

const search = ref('')

const rows = computed(() => {
  const term = search.value.trim().toLowerCase()
  return store.projectTypes.slice()
    .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))
    .filter(pt =>
      !term ||
      pt.name.toLowerCase().includes(term) ||
      (pt.workPackageLabel || '').toLowerCase().includes(term) ||
      (pt.defaultTemplate || '').toLowerCase().includes(term)
    )
})

const columns = [
  { key: 'name',                   label: 'Project Type' },
  { key: 'workPackageLabel',       label: 'Work Package label' },
  { key: 'workPackageLabelPlural', label: 'Plural' },
  { key: 'defaultTemplate',        label: 'Default template' },
  { key: 'projectCount',           label: 'Projects', align: 'right' },
  { key: 'enabled',                label: 'Status' },
]

function projectCountFor(typeName) {
  return store.projects.filter(p => p.type === typeName).length
}

const breadcrumbs = [
  { label: 'BuildSuite Core', to: '/' },
  { label: 'Settings', to: '/settings' },
  { label: 'Project Types' },
]

const subtitle = computed(() => `${rows.value.length} of ${store.projectTypes.length}`)

function onRowClick(row) {
  router.push(`/settings/project-types/${row.id}`)
}

// Admin/BSA guard — non-admins bounce back to settings hub
onMounted(() => {
  if (!store.isAdmin) router.replace('/settings')
})
</script>

<template>
  <DeskPage title="Project Types" :subtitle="subtitle" :breadcrumbs="breadcrumbs">
    <template #actions>
      <RouterLink to="/settings/project-types/new" class="desk-save-btn">+ New</RouterLink>
    </template>

    <DeskList
      v-model="search"
      :rows="rows"
      :columns="columns"
      row-key="id"
      search-placeholder="Search by name, label, template…"
      @row-click="onRowClick"
    >
      <template #cell-name="{ row }">
        <DeskLink :to="`/settings/project-types/${row.id}`" @click.stop class="font-medium">{{ row.name }}</DeskLink>
      </template>

      <template #cell-workPackageLabel="{ row }">
        <span class="text-ink-700">{{ row.workPackageLabel || '—' }}</span>
      </template>

      <template #cell-workPackageLabelPlural="{ row }">
        <span class="text-ink-500 text-xs">{{ row.workPackageLabelPlural || '—' }}</span>
      </template>

      <template #cell-defaultTemplate="{ row }">
        <span v-if="row.defaultTemplate" class="text-xs px-2 py-0.5 bg-ink-100 text-ink-700" style="border-radius: 9999px;">{{ row.defaultTemplate }}</span>
        <span v-else class="text-xs text-ink-400 italic">none</span>
      </template>

      <template #cell-projectCount="{ row }">
        <span class="tabular-nums text-ink-700">{{ projectCountFor(row.name) }}</span>
      </template>

      <template #cell-enabled="{ row }">
        <span
          class="text-[11px] px-2 py-0.5 font-medium"
          :class="row.enabled ? 'bg-success-50 text-success-700' : 'bg-ink-100 text-ink-500'"
          style="border-radius: 9999px;"
        >{{ row.enabled ? 'Enabled' : 'Disabled' }}</span>
      </template>

      <template #empty>
        <div class="text-sm text-ink-500">
          No Project Types yet ·
          <DeskLink to="/settings/project-types/new">Create one →</DeskLink>
        </div>
      </template>
    </DeskList>
  </DeskPage>
</template>
