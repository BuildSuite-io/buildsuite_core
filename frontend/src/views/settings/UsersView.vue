<script setup>
// Users — Settings sub-page. Admin-only. Lists the seed team (USR-001..007)
// as Frappe's User DocType would render them. Read-only in the prototype —
// real user CRUD requires the auth layer that the prototype deliberately doesn't
// build (no passwords / no 2FA / no Frappe Role assignment).
//
// The "role" column shows each team member's persona role from seed.team. Note
// that the prototype's *active* role (the topbar switcher) is decoupled — it's
// a demo affordance per §12.1, not real auth.

import { computed, ref } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { useDataStore } from '@/stores'
import StatusBadge from '@/components/StatusBadge.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskList from '@/components/desk/DeskList.vue'

const store = useDataStore()
const router = useRouter()

const search = ref('')

const items = computed(() => {
  const term = search.value.trim().toLowerCase()
  return store.team.filter(u => {
    if (!term) return true
    return `${u.id} ${u.name} ${u.role}`.toLowerCase().includes(term)
  })
})

const columns = [
  { key: 'avatar',  label: '',         class: 'w-10' },
  { key: 'name',    label: 'Name' },
  { key: 'role',    label: 'Role' },
  { key: 'email',   label: 'Email' },
  { key: 'id',      label: 'ID' },
  { key: 'enabled', label: 'Enabled' },
]

const breadcrumbs = [
  { label: 'BuildSuite Core', to: '/' },
  { label: 'Settings', to: '/settings' },
  { label: 'Users' },
]

const subtitle = computed(() =>
  `${items.value.length} of ${store.team.length} · Frappe: User DocType + Role Profile`
)
</script>

<template>
  <DeskPage title="Users" :subtitle="subtitle" :breadcrumbs="breadcrumbs">
    <template #actions>
      <RouterLink to="/settings" class="text-xs text-ink-600 hover:text-ink-900">← Back to Settings</RouterLink>
    </template>

    <!-- Non-admin guard — direct URL access. -->
    <div v-if="!store.isAdmin" class="mb-3 px-3 py-2 bg-warning-50 border border-warning-100 text-xs text-warning-700" style="border-radius: 2px;">
      Users management is restricted to the System Manager role. You can still view the team list but cannot enable / disable accounts or change role assignments.
    </div>

    <!-- Read-only disclaimer — surface the prototype scope upfront. -->
    <div class="mb-3 px-3 py-2 bg-info-50 border border-info-100 text-xs text-info-700" style="border-radius: 2px;">
      Read-only view. Real user CRUD (invite / disable / password reset / 2FA / Role Profile assignment) is part of the Frappe auth layer and is out of prototype scope. The active demo persona is set via the topbar Role switcher per §12.1.
    </div>

    <DeskList
      v-model="search"
      :rows="items"
      :columns="columns"
      row-key="id"
      search-placeholder="Search by name, role…"
    >
      <template #cell-avatar="{ row }">
        <UserAvatar :user-id="row.id" size="sm" />
      </template>
      <template #cell-name="{ row }">
        <div class="text-sm font-medium text-ink-900">{{ row.name }}</div>
      </template>
      <template #cell-role="{ row }">
        <span class="text-xs text-ink-700">{{ row.role }}</span>
      </template>
      <template #cell-email="{ row }">
        <span class="text-xs text-ink-500">{{ row.email || '—' }}</span>
      </template>
      <template #cell-id="{ row }">
        <span class="font-mono text-[11px] text-ink-500">{{ row.id }}</span>
      </template>
      <template #cell-enabled="{ row }">
        <!-- Every seed user is treated as enabled — the prototype has no
             disable mechanism. Shown as a badge so the column has meaning when
             the auth layer eventually lands. -->
        <StatusBadge status="Active" size="xs" />
      </template>

      <template #empty>
        <div class="text-sm text-ink-500">No users match this search.</div>
      </template>
    </DeskList>
  </DeskPage>
</template>
