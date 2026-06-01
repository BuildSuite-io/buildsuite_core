<script setup>
// Workspace Structure Settings — Single DocType with nested child tables.
// BSA-only. Session 34, the architecturally significant Settings DocType:
// the Site Execution workspace landing renders its shortcut grid from this
// DocType (NOT from hardcoded router.js config). A BSA at a customer org
// can reorder shortcuts, hide some per role, add new ones, all without
// developer involvement.
//
// Schema:
//   workspace_definitions (parent rows)
//     ↓
//   shortcuts (child rows, embedded on each definition)
//
// M1 ships with one seeded workspace_definitions row (Site Execution); the
// other workspaces from §12.2 become addable rows as their modules ship.

import { ref, computed, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { useDataStore } from '@/stores'
import { ROLES } from '@/data/roles'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskForm from '@/components/desk/DeskForm.vue'
import DeskActionBar from '@/components/desk/DeskActionBar.vue'
import DeskSection from '@/components/desk/DeskSection.vue'
import DeskField from '@/components/desk/DeskField.vue'
import DeskInput from '@/components/desk/DeskInput.vue'

const store = useDataStore()

// View-mode vs edit-mode toggle. Workspace + shortcut editing happens inline
// in edit mode; cancel reverts to the store snapshot.
const editing = ref(false)
const form = ref({ workspace_definitions: [] })
const saving = ref(false)

watch(() => store.workspaceStructure, (ws) => {
  if (ws) form.value = JSON.parse(JSON.stringify(ws))
}, { immediate: true, deep: true })

function startEdit() {
  form.value = JSON.parse(JSON.stringify(store.workspaceStructure))
  editing.value = true
}
function cancelEdit() {
  form.value = JSON.parse(JSON.stringify(store.workspaceStructure))
  editing.value = false
}
function saveEdit() {
  if (!store.isBSA && !store.isAdmin) return
  saving.value = true
  // Replace whole shape — we treat this like a Single DocType save (full record
  // round-trip). Drops empty shortcuts (label blank).
  const clean = {
    workspace_definitions: form.value.workspace_definitions.map(def => ({
      ...def,
      shortcuts: (def.shortcuts || []).filter(s => s && s.label && s.label.trim()),
    })),
  }
  store.workspaceStructure = clean
  // Reuse persist via a dummy update (no granular action for whole-structure save).
  store._persist()
  saving.value = false
  editing.value = false
}
function onPrimary() { editing.value ? saveEdit() : startEdit() }

// Child-table ops on the form's local copy. Saved together on saveEdit.
function addShortcut(defIdx) {
  const def = form.value.workspace_definitions[defIdx]
  const nextOrder = (def.shortcuts || []).reduce((m, s) => Math.max(m, s.sort_order || 0), 0) + 1
  def.shortcuts = [...(def.shortcuts || []), {
    id: 'WSST-NEW-' + Date.now().toString().slice(-6) + '-' + Math.floor(Math.random() * 1000),
    label: '',
    icon: '🔗',
    route_path: '/',
    visible_to_roles: null,
    sort_order: nextOrder,
  }]
}
function removeShortcut(defIdx, shortcutIdx) {
  form.value.workspace_definitions[defIdx].shortcuts.splice(shortcutIdx, 1)
}
function moveShortcut(defIdx, shortcutIdx, dir) {
  const shortcuts = form.value.workspace_definitions[defIdx].shortcuts
  const target = shortcutIdx + dir
  if (target < 0 || target >= shortcuts.length) return
  const tmp = shortcuts[shortcutIdx]
  shortcuts[shortcutIdx] = shortcuts[target]
  shortcuts[target] = tmp
  // Re-stamp sort_order from position.
  shortcuts.forEach((s, i) => { s.sort_order = i + 1 })
}
function toggleRole(target, roleId) {
  // target.visible_to_roles: null = inherit / all; array = explicit allow-list.
  const cur = target.visible_to_roles
  if (cur === null) {
    // Materialise from "all" → explicit minus the toggled one. Use all role ids
    // EXCEPT the one being toggled.
    target.visible_to_roles = ROLES.map(r => r.id).filter(id => id !== roleId)
  } else {
    const next = cur.includes(roleId) ? cur.filter(id => id !== roleId) : [...cur, roleId]
    // If next covers all roles, collapse back to null (the inherit signal).
    target.visible_to_roles = next.length === ROLES.length ? null : next
  }
}

const breadcrumbs = [
  { label: 'BuildSuite Core', to: '/' },
  { label: 'Settings', to: '/app/settings' },
  { label: 'Workspace Structure' },
]

const totalShortcuts = computed(() =>
  form.value.workspace_definitions.reduce((sum, d) => sum + (d.shortcuts?.length || 0), 0)
)
</script>

<template>
  <DeskPage
    title="Workspace Structure"
    subtitle="Configure workspace shortcut grids"
    :breadcrumbs="breadcrumbs"
  >
    <DeskForm>
      <template #action-bar>
        <DeskActionBar
          v-if="store.isBSA || store.isAdmin"
          :save-label="editing ? (saving ? 'Saving…' : 'Save') : 'Edit'"
          :show-cancel="editing"
          :saving="saving"
          cancel-label="Cancel"
          @save="onPrimary"
          @cancel="cancelEdit"
        >
          <template #left>
            <span class="text-[11px] text-ink-500">
              {{ form.workspace_definitions.length }} workspace{{ form.workspace_definitions.length === 1 ? '' : 's' }} · {{ totalShortcuts }} shortcuts
            </span>
          </template>
        </DeskActionBar>
        <div v-else class="px-3 py-2 bg-warning-50 border-b border-warning-100 text-xs text-warning-700">
          Read-only. Editing requires the BuildSuite Administrator role.
        </div>
      </template>

      <div class="max-w-4xl mx-auto">

      <DeskSection
        v-for="(def, defIdx) in (editing ? form.workspace_definitions : store.workspaceStructure.workspace_definitions)"
        :key="def.id"
        :title="def.display_name || 'Untitled workspace'"
      >
        <div class="md:col-span-2">
          <!-- Workspace definition meta row -->
          <div class="grid border border-ink-200 bg-ink-50 px-3 py-2 mb-3" style="grid-template-columns: 1fr 1fr 120px 100px; gap: 8px; border-radius: 2px;">
            <div>
              <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Slug</div>
              <div class="text-xs font-mono text-ink-700">{{ def.workspace_slug }}</div>
            </div>
            <div>
              <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Display name</div>
              <DeskInput v-if="editing" v-model="def.display_name" class="!text-xs" />
              <div v-else class="text-xs text-ink-900">{{ def.display_name }}</div>
            </div>
            <div>
              <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Enabled</div>
              <div v-if="editing" class="py-1">
                <input type="checkbox" v-model="def.enabled" class="accent-brand-600" />
              </div>
              <div v-else class="text-xs">
                <span :class="def.enabled ? 'text-success-700' : 'text-ink-500'">{{ def.enabled ? 'On' : 'Off' }}</span>
              </div>
            </div>
            <div>
              <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Shortcuts</div>
              <div class="text-xs tabular-nums text-ink-700">{{ def.shortcuts?.length || 0 }}</div>
            </div>
          </div>

          <!-- Shortcuts table -->
          <div v-if="(def.shortcuts || []).length" class="border border-ink-200" style="border-radius: 2px;">
            <div class="grid bg-ink-50 border-b border-ink-200 text-[10px] uppercase tracking-wider text-ink-500 font-medium"
                 :style="editing ? 'grid-template-columns: 32px 40px minmax(140px, 1fr) minmax(180px, 1.4fr) minmax(160px, 1.2fr) 70px;' : 'grid-template-columns: 40px minmax(140px, 1fr) minmax(180px, 1.4fr) minmax(160px, 1.2fr);'">
              <div v-if="editing"></div>
              <div class="px-2 py-1.5">Icon</div>
              <div class="px-2 py-1.5">Label</div>
              <div class="px-2 py-1.5">Route</div>
              <div class="px-2 py-1.5">Visible to</div>
              <div v-if="editing" class="px-2 py-1.5"></div>
            </div>
            <div
              v-for="(sc, scIdx) in def.shortcuts"
              :key="sc.id"
              class="grid desk-row-stripe border-b border-ink-100 last:border-b-0 items-center text-sm"
              :style="editing ? 'grid-template-columns: 32px 40px minmax(140px, 1fr) minmax(180px, 1.4fr) minmax(160px, 1.2fr) 70px;' : 'grid-template-columns: 40px minmax(140px, 1fr) minmax(180px, 1.4fr) minmax(160px, 1.2fr);'"
            >
              <!-- Reorder up/down (edit mode only) -->
              <div v-if="editing" class="px-1 py-1 flex flex-col items-center gap-0.5">
                <button
                  type="button"
                  class="text-[9px] px-1 py-0 border border-ink-200 bg-white hover:bg-ink-50 leading-tight"
                  style="border-radius: 2px;"
                  :disabled="scIdx === 0"
                  :class="scIdx === 0 ? 'opacity-30 cursor-not-allowed' : ''"
                  @click="moveShortcut(defIdx, scIdx, -1)"
                  title="Move up"
                >▲</button>
                <button
                  type="button"
                  class="text-[9px] px-1 py-0 border border-ink-200 bg-white hover:bg-ink-50 leading-tight"
                  style="border-radius: 2px;"
                  :disabled="scIdx === def.shortcuts.length - 1"
                  :class="scIdx === def.shortcuts.length - 1 ? 'opacity-30 cursor-not-allowed' : ''"
                  @click="moveShortcut(defIdx, scIdx, +1)"
                  title="Move down"
                >▼</button>
              </div>

              <!-- Icon -->
              <div class="px-2 py-1.5">
                <DeskInput v-if="editing" v-model="sc.icon" class="!text-base !w-10 !text-center" />
                <div v-else class="text-base leading-none">{{ sc.icon }}</div>
              </div>

              <!-- Label -->
              <div class="px-2 py-1.5">
                <DeskInput v-if="editing" v-model="sc.label" placeholder="e.g. Projects" class="!text-xs" />
                <div v-else class="text-sm text-ink-900">{{ sc.label }}</div>
              </div>

              <!-- Route -->
              <div class="px-2 py-1.5">
                <DeskInput v-if="editing" v-model="sc.route_path" placeholder="/app/…" class="!text-xs font-mono" />
                <div v-else class="text-xs font-mono text-ink-600">{{ sc.route_path }}</div>
              </div>

              <!-- Visible to (role allow-list) -->
              <div class="px-2 py-1.5">
                <div v-if="!editing" class="text-[10px] text-ink-600">
                  <span v-if="!sc.visible_to_roles" class="italic text-ink-400">All roles</span>
                  <span v-else>{{ sc.visible_to_roles.length }} of {{ ROLES.length }} roles</span>
                </div>
                <details v-else class="text-[10px] text-ink-700">
                  <summary class="cursor-pointer hover:text-ink-900">
                    <span v-if="!sc.visible_to_roles" class="italic">All roles</span>
                    <span v-else>{{ sc.visible_to_roles.length }} of {{ ROLES.length }} roles ▾</span>
                  </summary>
                  <div class="mt-1 grid grid-cols-2 gap-x-2 gap-y-0.5">
                    <label v-for="r in ROLES" :key="r.id" class="flex items-center gap-1 cursor-pointer">
                      <input
                        type="checkbox"
                        :checked="!sc.visible_to_roles || sc.visible_to_roles.includes(r.id)"
                        class="accent-brand-600 w-3 h-3"
                        @change="toggleRole(sc, r.id)"
                      />
                      <span class="truncate">{{ r.shortName }}</span>
                    </label>
                  </div>
                </details>
              </div>

              <!-- Remove (edit mode) -->
              <div v-if="editing" class="px-2 py-1.5 flex justify-center">
                <button
                  type="button"
                  class="text-xs px-1.5 py-0.5 border border-ink-200 bg-white hover:bg-ink-50"
                  style="border-radius: 2px; color: #B91C1C;"
                  @click="removeShortcut(defIdx, scIdx)"
                  title="Remove shortcut"
                >✕</button>
              </div>
            </div>
          </div>
          <div v-else class="text-xs text-ink-400 italic py-2">No shortcuts on this workspace yet.</div>

          <button
            v-if="editing"
            type="button"
            class="mt-2 text-xs px-2 py-1 border border-ink-200 bg-white hover:bg-ink-50"
            style="border-radius: 2px;"
            @click="addShortcut(defIdx)"
          >+ Add shortcut</button>
        </div>
      </DeskSection>

      </div>
    </DeskForm>
  </DeskPage>
</template>
