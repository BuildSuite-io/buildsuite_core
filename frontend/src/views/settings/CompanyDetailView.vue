<script setup>
// Company detail / edit — Settings sub-page. Admin-only mutations (Edit / Save
// / Delete buttons hidden for non-admin). ID is locked after create (stripped
// from any patch in store.updateCompany, per Frappe Naming Series convention).
// Delete is reference-guarded — store.deleteCompany returns {ok:false} with the
// list of linked projects when blocked.

import { ref, computed, watch } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { useDataStore } from '@/stores'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskForm from '@/components/desk/DeskForm.vue'
import DeskActionBar from '@/components/desk/DeskActionBar.vue'
import DeskSection from '@/components/desk/DeskSection.vue'
import DeskField from '@/components/desk/DeskField.vue'
import DeskInput from '@/components/desk/DeskInput.vue'
import DeskTextarea from '@/components/desk/DeskTextarea.vue'
import DeskLink from '@/components/desk/DeskLink.vue'

const props = defineProps({ id: String })
const router = useRouter()
const store = useDataStore()

const COLOR_OPTIONS = [
  { value: 'bg-brand-600',   label: 'Green'    },
  { value: 'bg-blue-600',    label: 'Blue'     },
  { value: 'bg-violet-600',  label: 'Violet'   },
  { value: 'bg-amber-600',   label: 'Amber'    },
  { value: 'bg-emerald-600', label: 'Emerald'  },
  { value: 'bg-rose-600',    label: 'Rose'     },
  { value: 'bg-cyan-600',    label: 'Cyan'     },
  { value: 'bg-ink-600',     label: 'Slate'    },
]

const company = computed(() => store.companyById(props.id))
const linkedProjects = computed(() => store.projectsByCompany(props.id))
const editing = ref(false)
const form = ref({})

watch(company, (c) => { if (c) form.value = JSON.parse(JSON.stringify(c)) }, { immediate: true })

function startEdit() {
  if (!store.isAdmin) return
  form.value = JSON.parse(JSON.stringify(company.value))
  editing.value = true
}
function cancelEdit() {
  form.value = JSON.parse(JSON.stringify(company.value))
  editing.value = false
}
function saveEdit() {
  if (!store.isAdmin) return
  store.updateCompany(props.id, {
    name:        form.value.name,
    shortName:   form.value.shortName,
    description: form.value.description,
    color:       form.value.color,
  })
  editing.value = false
}
function onPrimary() { editing.value ? saveEdit() : startEdit() }

function deleteCompany() {
  if (!store.isAdmin) return
  if (linkedProjects.value.length) {
    // Reference guard — Frappe LinkExistsError pattern. List the offending
    // projects in the alert so the user knows what to fix first.
    const sample = linkedProjects.value.slice(0, 5).map(p => `• ${p.name} (${p.code})`).join('\n')
    const more = linkedProjects.value.length > 5 ? `\n…and ${linkedProjects.value.length - 5} more` : ''
    alert(`Cannot delete "${company.value.name}".\n\n${linkedProjects.value.length} project(s) reference this company:\n\n${sample}${more}\n\nReassign or delete those projects first.`)
    return
  }
  if (!confirm(`Delete company "${company.value.name}"?\n\nThis is permanent. No project references this company so the delete is safe.`)) return
  const result = store.deleteCompany(props.id)
  if (result.ok) {
    router.push('/app/settings/companies')
  } else {
    // Defensive — shouldn't happen since we pre-checked, but in case of a race.
    alert(`Delete refused: ${result.reason}`)
  }
}

const breadcrumbs = computed(() => [
  { label: 'BuildSuite Core', to: '/' },
  { label: 'Settings', to: '/app/settings' },
  { label: 'Companies', to: '/app/settings/companies' },
])

const titleStatus = computed(() => {
  const out = []
  if (company.value && company.value.id === store.activeCompany) out.push('Active')
  return out
})
</script>

<template>
  <DeskPage
    v-if="company"
    :title="company.name"
    :subtitle="company.id"
    :breadcrumbs="breadcrumbs"
    :status="titleStatus"
  >
    <DeskForm>
      <template #action-bar>
        <DeskActionBar
          v-if="store.isAdmin"
          :save-label="editing ? 'Save' : 'Edit'"
          :show-cancel="editing"
          cancel-label="Cancel"
          @save="onPrimary"
          @cancel="cancelEdit"
        >
          <template #left>
            <span v-if="linkedProjects.length" class="text-[11px] text-ink-500">
              {{ linkedProjects.length }} project{{ linkedProjects.length === 1 ? '' : 's' }} reference this company
            </span>
            <span v-else class="text-[11px] text-ink-400">No projects reference this company · safe to delete</span>
          </template>
          <template #menu>
            <button
              type="button"
              class="text-xs px-2 py-1 border border-ink-200 bg-white hover:bg-ink-50"
              style="border-radius: 2px; color: #B91C1C;"
              @click="deleteCompany"
            >Delete</button>
          </template>
        </DeskActionBar>
        <!-- Non-admin: no action bar; show a read-only marker instead. -->
        <div v-else class="px-3 py-2 bg-warning-50 border-b border-warning-100 text-xs text-warning-700">
          Read-only view. Editing requires the System Manager role.
        </div>
      </template>

      <div class="max-w-3xl mx-auto">

      <!-- Identity -->
      <DeskSection title="Identity" v-if="!editing">
        <DeskField label="Name">
          <div class="text-sm text-ink-900 py-1">{{ company.name }}</div>
        </DeskField>
        <DeskField label="Short name" hint="Topbar pill text.">
          <div class="text-sm text-ink-900 py-1">{{ company.shortName }}</div>
        </DeskField>
        <DeskField label="ID" hint="Stable identifier — locked after create.">
          <div class="text-sm text-ink-500 py-1 font-mono">{{ company.id }}</div>
        </DeskField>
        <DeskField label="Description">
          <div class="text-sm text-ink-700 py-1">{{ company.description || '—' }}</div>
        </DeskField>
      </DeskSection>
      <DeskSection title="Identity" v-else>
        <DeskField label="Name" required>
          <DeskInput v-model="form.name" />
        </DeskField>
        <DeskField label="Short name" required hint="Topbar pill text.">
          <DeskInput v-model="form.shortName" />
        </DeskField>
        <DeskField label="ID" hint="Locked after create per Frappe Naming Series convention.">
          <DeskInput :model-value="company.id" disabled class="font-mono" />
        </DeskField>
        <DeskField label="Description">
          <DeskTextarea v-model="form.description" :rows="2" />
        </DeskField>
      </DeskSection>

      <!-- Brand colour -->
      <DeskSection title="Brand colour" v-if="!editing" :cols="2">
        <DeskField label="Pill colour">
          <div class="flex items-center gap-2 py-1">
            <span :class="company.color" class="w-4 h-4" style="border-radius: 2px;"></span>
            <span class="text-sm text-ink-700">{{ company.color }}</span>
          </div>
        </DeskField>
      </DeskSection>
      <DeskSection title="Brand colour" v-else>
        <div class="md:col-span-2">
          <div class="flex flex-wrap gap-2">
            <label
              v-for="opt in COLOR_OPTIONS"
              :key="opt.value"
              class="inline-flex items-center gap-1.5 cursor-pointer px-2 py-1 border text-xs"
              :class="form.color === opt.value ? 'border-ink-900 bg-ink-50' : 'border-ink-200 hover:bg-ink-50'"
              style="border-radius: 2px;"
            >
              <input type="radio" v-model="form.color" :value="opt.value" class="sr-only" />
              <span :class="opt.value" class="w-3 h-3" style="border-radius: 2px;"></span>
              <span class="text-ink-700">{{ opt.label }}</span>
            </label>
          </div>
        </div>
      </DeskSection>

      <!-- Linked projects (always visible — informs delete safety) -->
      <DeskSection title="Linked projects">
        <div class="md:col-span-2">
          <div v-if="linkedProjects.length" class="border border-ink-200" style="border-radius: 2px;">
            <div class="grid bg-ink-50 border-b border-ink-200 text-[10px] uppercase tracking-wider text-ink-500 font-medium"
                 style="grid-template-columns: 140px 1fr 100px;">
              <div class="px-3 py-1.5">Code</div>
              <div class="px-3 py-1.5">Project</div>
              <div class="px-3 py-1.5">Status</div>
            </div>
            <div
              v-for="p in linkedProjects"
              :key="p.id"
              class="grid desk-row-stripe hover:bg-brand-50 border-b border-ink-100 last:border-b-0 items-center text-sm"
              style="grid-template-columns: 140px 1fr 100px;"
            >
              <div class="px-3 py-1.5 font-mono text-xs text-ink-600">{{ p.code }}</div>
              <div class="px-3 py-1.5">
                <DeskLink :to="`/app/projects/${p.id}`">{{ p.name }}</DeskLink>
              </div>
              <div class="px-3 py-1.5 text-xs text-ink-500">{{ p.status }}</div>
            </div>
          </div>
          <div v-else class="text-xs text-ink-400 italic">
            No projects reference this company. Safe to delete.
          </div>
          <div class="text-[11px] text-ink-500 mt-2">
            Delete is refused while any project links to this company (Frappe-standard LinkExistsError pattern).
          </div>
        </div>
      </DeskSection>

      </div>
    </DeskForm>
  </DeskPage>

  <div v-else class="px-6 py-20 text-center text-sm text-ink-400">
    Company not found ·
    <RouterLink to="/app/settings/companies" class="desk-link">Back to list →</RouterLink>
  </div>
</template>
