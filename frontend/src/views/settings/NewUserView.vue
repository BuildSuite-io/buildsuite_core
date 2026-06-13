<script setup>
// New User — admin-only. Creates a Frappe User; the validate hook maps the
// chosen persona (a Select storing the role name) to the matching Frappe Role.

import { reactive, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useDataStore } from '@/stores'
import { showToast } from '@/utils/appToast'
import { useFormErrors } from '@/composables/useFormErrors'
import { useDoctypeMeta } from '@/composables/useDoctypeMeta'
import { createDataAdapter } from '@/data/adapters'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskForm from '@/components/desk/DeskForm.vue'
import DeskActionBar from '@/components/desk/DeskActionBar.vue'
import DeskSection from '@/components/desk/DeskSection.vue'
import DeskField from '@/components/desk/DeskField.vue'
import DeskInput from '@/components/desk/DeskInput.vue'
import DeskSelect from '@/components/desk/DeskSelect.vue'

const router = useRouter()
const store = useDataStore()
const adapter = createDataAdapter(store)

const form = reactive({
  name: '',
  email: '',
  persona: '',
  enabled: true,
  sendWelcome: true,
})

const { errors, applyServerErrors, setErrors, clearError } = useFormErrors({
  email: 'email',
  first_name: 'name',
})
const saving = ref(false)

// Persona options sourced from the backend User.persona Select field.
const { selectOptions } = useDoctypeMeta('User')
const personas = computed(() => selectOptions('persona'))

const breadcrumbs = [
  { label: 'BuildSuite Core', to: '/' },
  { label: 'Settings', to: '/settings' },
  { label: 'Users', to: '/settings/users' },
  { label: 'New User' },
]

function validate() {
  const e = {}
  if (!form.name.trim()) e.name = 'Full name is required.'
  if (!form.email.trim()) {
    e.email = 'Email is required — it is the login id and where the welcome email is sent.'
  } else if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email.trim())) {
    e.email = 'Enter a valid email address.'
  }
  if (!form.persona) e.persona = 'Pick a persona.'
  setErrors(e)
  return Object.keys(e).length === 0
}

async function save() {
  if (!validate()) return
  saving.value = true
  try {
    await adapter.create('User', {
      email: form.email,
      first_name: form.name,
      enabled: form.enabled ? 1 : 0,
      persona: form.persona,
      send_welcome_email: form.sendWelcome ? 1 : 0,
    })
    showToast('User created')
    router.push('/settings/users')
  } catch (err) {
    const summary = applyServerErrors(err)
    // Duplicate email (User is keyed by email) — surface it on the Email field.
    const isDuplicate = err?.exc_type === 'DuplicateEntryError' || /already exists|duplicate entry/i.test(summary || '')
    if (isDuplicate) {
      setErrors({ ...errors.value, email: 'A user with this email already exists.' })
    }
    showToast(isDuplicate ? 'A user with this email already exists.' : (summary ?? 'Failed to create user'), 'error')
  } finally {
    saving.value = false
  }
}

function cancel() { router.back() }
</script>

<template>
  <DeskPage title="New User" :breadcrumbs="breadcrumbs">
    <DeskForm>
      <template #action-bar>
        <DeskActionBar :save-label="saving ? 'Creating…' : 'Create user'" :saving="saving" @save="save"
          @cancel="cancel" />
      </template>

      <div class="max-w-3xl mx-auto">
        <DeskSection title="Account">
          <DeskField label="Full name" required :error="errors.name">
            <DeskInput v-model="form.name" placeholder="e.g. Rajesh K." />
          </DeskField>
          <DeskField label="Email" required :error="errors.email"
            hint="Used as the login id and where the welcome email is sent.">
            <DeskInput v-model="form.email" type="email" placeholder="rajesh@buildsuite.io" />
          </DeskField>
          <DeskField label="Account status" hint="Disabled users keep their record but cannot log in.">
            <label class="inline-flex items-center gap-2 cursor-pointer select-none">
              <input type="checkbox" v-model="form.enabled" class="accent-brand-600" />
              <span class="text-sm text-ink-700">Enabled — user can log in immediately</span>
            </label>
          </DeskField>
        </DeskSection>

        <DeskSection title="Persona">
          <DeskField label="Persona" required :error="errors.persona"
            hint="Frappe Roles are auto-assigned from the persona on the production side. Pick the one that matches the user's day-to-day work.">
            <DeskSelect v-model="form.persona" @change="clearError('persona')">
              <option value="" disabled>Select persona</option>
              <option v-for="p in personas" :key="p" :value="p">{{ p }}</option>
            </DeskSelect>
          </DeskField>
        </DeskSection>

        <DeskSection title="Onboarding">
          <div class="md:col-span-2 space-y-3">
            <label class="flex items-start gap-2 cursor-pointer select-none">
              <input type="checkbox" v-model="form.sendWelcome" class="accent-brand-600 mt-0.5" />
              <div>
                <div class="text-sm text-ink-900">Send welcome email</div>
                <div class="text-[11px] text-ink-500">Emails the user a link to set their password and get started.
                </div>
              </div>
            </label>
          </div>
        </DeskSection>
      </div>
    </DeskForm>
  </DeskPage>
</template>
