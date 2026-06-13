<script setup>
// Users — admin-only settings page. Lists the live User DocType; create
// (NewUserView), edit / enable-disable / delete write to Frappe.

import { computed, ref, reactive } from 'vue'
import { RouterLink } from 'vue-router'
import { useDataStore } from '@/stores'
import StatusBadge from '@/components/StatusBadge.vue'
import FrappeUserBadge from '@/components/FrappeUserBadge.vue'
import DeskPage from '@/components/desk/DeskPage.vue'
import DocTypeListView from '@/components/doctype/DocTypeListView.vue'
import DeskSection from '@/components/desk/DeskSection.vue'
import DeskField from '@/components/desk/DeskField.vue'
import DeskInput from '@/components/desk/DeskInput.vue'
import DeskSelect from '@/components/desk/DeskSelect.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { useDoctypeMeta } from '@/composables/useDoctypeMeta'
import { createDataAdapter } from '@/data/adapters'
import { showToast } from '@/utils/appToast'
import { parseFrappeError } from '@/utils/frappeError'

const store = useDataStore()

// listRef → reload the server-paginated list after create / edit / delete.
const listRef = ref(null)

const fieldOrder = ['full_name', 'persona', 'email', 'enabled', 'name']
const columns = [
  { key: 'avatar', label: '' },
  { key: 'full_name', label: 'Name' },
  { key: 'persona', label: 'Persona' },
  { key: 'email', label: 'Email' },
  { key: 'name', label: 'ID' },
  { key: 'enabled', label: 'Status' },
]

const breadcrumbs = [
  { label: 'BuildSuite Core', to: '/' },
  { label: 'Settings', to: '/settings' },
  { label: 'Users' },
]

// Persona dropdown options from the backend User.persona Select field.
const { selectOptions } = useDoctypeMeta('User')
const personaOptions = computed(() => selectOptions('persona'))

// ===== Edit + Delete (live Frappe) =====
const adapter = createDataAdapter(store)
const editing = ref(null)                 // .id holds the Frappe key (email)
const editForm = reactive({ name: '', email: '', persona: '', enabled: true })
const editErrors = reactive({ name: '' })
const saving = ref(false)
const confirmOpen = ref(false)
const pendingDelete = ref(null)           // { id, name } captured before the edit modal closes

function openEdit(row) {
  editErrors.name = ''
  editing.value = {
    ...row,
    id: row.name,
    name: row.full_name || row.name,
  }
  editForm.name = row.full_name || ''
  editForm.email = row.email || row.name
  editForm.persona = row.persona || ''
  editForm.enabled = row.enabled !== 0
}
function closeEdit() { editing.value = null }

async function saveEdit() {
  editErrors.name = editForm.name.trim() ? '' : 'Full name is required'
  if (editErrors.name) return
  saving.value = true
  try {
    await adapter.update('User', editing.value.id, {
      full_name: editForm.name.trim(),
      enabled: editForm.enabled ? 1 : 0,
      persona: editForm.persona,
    })
    closeEdit()
    listRef.value?.reload()
  } catch (err) {
    showToast(parseFrappeError(err).summary ?? 'Failed to save', 'error')
  } finally {
    saving.value = false
  }
}

function deleteUser() {
  if (editing.value.id === 'Administrator') { showToast('Cannot delete the Administrator account', 'error'); return }
  // Capture the target, then close the edit modal so the confirm (z-40) isn't
  // hidden behind it (z-[60]); the confirm replaces the modal.
  pendingDelete.value = { id: editing.value.id, name: editing.value.name }
  closeEdit()
  confirmOpen.value = true
}

async function confirmDelete() {
  if (!pendingDelete.value) return
  saving.value = true
  try {
    await adapter.remove('User', pendingDelete.value.id)
    confirmOpen.value = false
    pendingDelete.value = null
    listRef.value?.reload()
  } catch (err) {
    showToast(parseFrappeError(err).summary ?? 'Failed to delete user', 'error')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <DeskPage title="Users" :breadcrumbs="breadcrumbs">
    <template #actions>
      <RouterLink to="/settings/users/new" class="desk-save-btn">+ New User</RouterLink>
    </template>

    <DocTypeListView
      ref="listRef"
      doctype="User"
      :field-order="fieldOrder"
      :columns="columns"
      :search-fields="['full_name', 'name', 'persona', 'email']"
      :base-filters="[['persona', 'is', 'set']]"
      row-key="name"
      cache-key="buildsuite-user-list"
      search-placeholder="Search by name, persona, email…"
      empty-message="No users found."
      @row-click="openEdit"
    >
      <template #cell-avatar="{ row }">
        <FrappeUserBadge :user-id="row.name" :show-name="false" size="sm" />
      </template>
      <template #cell-full_name="{ row }">
        <div class="text-sm font-medium text-ink-900">{{ row.full_name || '—' }}</div>
      </template>
      <template #cell-persona="{ row }">
        <span
          class="text-[10px] px-2 py-0.5 rounded-full font-medium whitespace-nowrap bg-ink-100 text-ink-700"
        >{{ row.persona || '—' }}</span>
      </template>
      <template #cell-email="{ row }">
        <span class="text-xs text-ink-500">{{ row.email || '—' }}</span>
      </template>
      <template #cell-name="{ row }">
        <span class="font-mono text-[11px] text-ink-500">{{ row.name }}</span>
      </template>
      <template #cell-enabled="{ row }">
        <StatusBadge :status="row.enabled ? 'Active' : 'Disabled'" size="xs" />
      </template>

      <template #empty>
        <div class="text-sm text-ink-500">No users found.</div>
      </template>
    </DocTypeListView>

    <!-- ===== Edit user modal ===== -->
    <Teleport to="body">
      <div v-if="editing" class="fixed inset-0 bg-ink-900/40 z-[60] flex items-center justify-center p-6"
        @click.self="closeEdit">
        <div class="bg-white border border-ink-200 w-full max-w-2xl shadow-fp-lg flex flex-col"
          style="border-radius: 12px; max-height: calc(100vh - 3rem);" @click.stop>
          <header class="px-5 py-3 border-b border-ink-200 flex items-center justify-between flex-shrink-0 bg-white"
            style="border-radius: 12px 12px 0 0;">
            <div class="flex items-center gap-3 min-w-0 flex-1">
              <FrappeUserBadge :user-id="editing.id" :show-name="false" size="sm" />
              <div class="min-w-0">
                <h2 class="text-sm font-semibold text-ink-900 truncate">{{ editing.name }}</h2>
                <p class="text-[11px] text-ink-500 mt-0.5 truncate">
                  {{ editing.id }} · {{ editing.persona || '—' }}
                  <template v-if="!editing.enabled"> · <span class="text-danger-700">Disabled</span></template>
                </p>
              </div>
            </div>
            <button type="button" class="text-ink-500 hover:text-ink-900 text-lg leading-none flex-shrink-0 ml-3"
              aria-label="Close" @click="closeEdit">×</button>
          </header>

          <div class="p-5 overflow-y-auto flex-1">
            <DeskSection title="Account">
              <DeskField label="Full name" required :error="editErrors.name">
                <DeskInput v-model="editForm.name" />
              </DeskField>
              <DeskField label="Email" hint="Login id — locked after create (a Frappe User is keyed by email).">
                <DeskInput v-model="editForm.email" type="email" disabled />
              </DeskField>
              <DeskField label="Account status" hint="Disabled users keep their record but cannot log in.">
                <label class="inline-flex items-center gap-2 cursor-pointer select-none">
                  <input type="checkbox" v-model="editForm.enabled" class="accent-brand-600" />
                  <span class="text-sm text-ink-700">Enabled</span>
                </label>
              </DeskField>
            </DeskSection>

            <DeskSection title="Persona">
              <DeskField label="Persona" hint="Frappe Roles are auto-assigned from the persona on the production side.">
                <DeskSelect v-model="editForm.persona">
                  <option v-for="p in personaOptions" :key="p" :value="p">{{ p }}</option>
                </DeskSelect>
              </DeskField>
            </DeskSection>

          </div>

          <footer class="px-5 py-3 border-t border-ink-200 flex items-center justify-between gap-2 flex-shrink-0 bg-white"
            style="border-radius: 0 0 12px 12px;">
            <button type="button"
              class="text-xs px-2.5 py-1 border border-danger-200 bg-white hover:bg-danger-50 text-danger-700 disabled:opacity-50"
              style="border-radius: 6px;" :disabled="saving" @click="deleteUser">Delete user</button>
            <div class="flex items-center gap-2">
              <button type="button"
                class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
                style="border-radius: 6px;" @click="closeEdit">Cancel</button>
              <button type="button" class="desk-save-btn" :disabled="saving" @click="saveEdit">{{ saving ? 'Saving…' :
                'Save' }}</button>
            </div>
          </footer>
        </div>
      </div>
    </Teleport>

    <ConfirmDialog
      v-model:open="confirmOpen"
      title="Delete user"
      :message="`Delete ${pendingDelete?.name}? They can no longer log in; their entries on existing records stay.`"
      confirm-label="Delete user"
      destructive
      :loading="saving"
      @confirm="confirmDelete"
    />
  </DeskPage>
</template>
