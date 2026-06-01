<script setup>
// New Company — Settings sub-page. Admin-only (route is allowlisted at the
// Settings hub tile level; non-admins who hit the URL still see the form but
// the save action checks isAdmin and refuses).
//
// ID is auto-derived from shortName on first keystroke (e.g. "Acme Realty" →
// ACME-REA) so the user can override before save. Once saved, ID is locked
// per Frappe Naming Series convention — see updateCompany in store.

import { reactive, ref, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useDataStore } from '@/stores'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskForm from '@/components/desk/DeskForm.vue'
import DeskActionBar from '@/components/desk/DeskActionBar.vue'
import DeskSection from '@/components/desk/DeskSection.vue'
import DeskField from '@/components/desk/DeskField.vue'
import DeskInput from '@/components/desk/DeskInput.vue'
import DeskTextarea from '@/components/desk/DeskTextarea.vue'

const router = useRouter()
const store = useDataStore()

// Palette options for the company switcher pill. Same Tailwind classes used by
// roles.js and the existing seed companies — keeps the topbar pill consistent.
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

const form = reactive({
  id: '',
  name: '',
  shortName: '',
  description: '',
  color: COLOR_OPTIONS[0].value,
})
const errors = ref({})
const saving = ref(false)
// Did the user manually edit the id? If so, stop auto-deriving from shortName.
const idTouched = ref(false)

// Auto-derive id from shortName (e.g. "Acme Realty" → ACME-REA). User can edit
// manually; once they do, idTouched stops the auto-pipe.
watch(() => form.shortName, (v) => {
  if (idTouched.value) return
  const cleaned = (v || '').trim().toUpperCase().replace(/[^A-Z0-9 ]/g, '')
  const parts = cleaned.split(/\s+/).filter(Boolean)
  if (!parts.length) { form.id = ''; return }
  const head = parts[0].slice(0, 4)
  const tail = parts[1] ? parts[1].slice(0, 3) : ''
  form.id = tail ? `${head}-${tail}` : head
})

const idCollision = computed(() =>
  form.id && store.companies.some(c => c.id === form.id.toUpperCase())
)

function validate() {
  const e = {}
  if (!form.name.trim()) e.name = 'Company name is required'
  if (!form.shortName.trim()) e.shortName = 'Short name is required (shown in topbar switcher pill)'
  if (!form.id.trim()) e.id = 'ID is required'
  errors.value = e
  return Object.keys(e).length === 0
}

function save() {
  if (!store.isAdmin) {
    alert('Only the System Manager role can create companies.')
    return
  }
  if (!validate()) return
  saving.value = true
  const created = store.addCompany({ ...form })
  saving.value = false
  router.push(`/app/settings/companies/${created.id}`)
}
function cancel() { router.back() }

const breadcrumbs = [
  { label: 'BuildSuite Core', to: '/' },
  { label: 'Settings', to: '/app/settings' },
  { label: 'Companies', to: '/app/settings/companies' },
  { label: 'New' },
]
</script>

<template>
  <DeskPage title="New Company" subtitle="Legal entity for project / accounting segregation (§14)" :breadcrumbs="breadcrumbs">
    <DeskForm>
      <template #action-bar>
        <DeskActionBar
          :save-label="saving ? 'Creating…' : 'Create company'"
          :saving="saving"
          @save="save"
          @cancel="cancel"
        />
      </template>

      <div class="max-w-3xl mx-auto">

      <!-- Non-admin guard. -->
      <div v-if="!store.isAdmin" class="mb-3 px-3 py-2 bg-warning-50 border border-warning-100 text-xs text-warning-700" style="border-radius: 2px;">
        You're viewing this form as <span class="font-medium">{{ store.currentRole?.name }}</span>. Saving requires the System Manager role.
      </div>

      <DeskSection title="Identity">
        <DeskField label="Company name" required :error="errors.name" hint="Legal entity name. Will appear on invoices / contracts in production.">
          <DeskInput v-model="form.name" placeholder="e.g. Acme Realty Pvt Ltd" />
        </DeskField>
        <DeskField label="Short name" required :error="errors.shortName" hint="Displayed in the topbar company switcher and lists. Keep it under ~16 characters.">
          <DeskInput v-model="form.shortName" placeholder="e.g. Acme Realty" />
        </DeskField>
        <DeskField
          label="ID"
          required
          :error="errors.id"
          :hint="idCollision ? 'An existing company already uses this ID — addCompany() will append a numeric suffix on save.' : 'Auto-derived from short name. Stable identifier — locked after create (Frappe Naming Series convention).'"
        >
          <DeskInput
            v-model="form.id"
            placeholder="ACME-REA"
            class="font-mono"
            @input="idTouched = true"
          />
        </DeskField>
        <DeskField label="Description" hint="What this entity builds — used as a hint in the company switcher dropdown.">
          <DeskTextarea v-model="form.description" :rows="2" placeholder="e.g. Residential towers · apartments · gated communities" />
        </DeskField>
      </DeskSection>

      <DeskSection title="Brand colour">
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
          <div class="text-[11px] text-ink-500 mt-2">
            Used for the topbar switcher pill, the Projects-list Company column badge, and any future per-company tag.
          </div>
        </div>
      </DeskSection>

      </div>
    </DeskForm>
  </DeskPage>
</template>
