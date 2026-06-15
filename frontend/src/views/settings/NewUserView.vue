<script setup>
// New User — create a real Frappe User with a BuildSuite persona. The persona
// drives the BuildSuite role via the server-side sync hook. Optional welcome /
// password-reset emails use Frappe's native flows.

import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useDataStore } from '@/stores'
import { ROLES } from '@/data/roles'
import { createBuildsuiteUser, sendUserWelcome, sendUserPasswordReset } from '@/data/usersApi'
import { showToast } from '@/utils/appToast'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskForm from '@/components/desk/DeskForm.vue'
import DeskActionBar from '@/components/desk/DeskActionBar.vue'
import DeskSection from '@/components/desk/DeskSection.vue'
import DeskField from '@/components/desk/DeskField.vue'
import DeskInput from '@/components/desk/DeskInput.vue'
import DeskSelect from '@/components/desk/DeskSelect.vue'

const router = useRouter()
const store = useDataStore()

const form = reactive({
  fullName: '',
  email: '',
  persona: '',
  enabled: true,
  sendWelcome: true,
  sendReset: false,
})
const errors = ref({})
const saving = ref(false)

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

const breadcrumbs = [
  { label: 'BuildSuite Core', to: '/' },
  { label: 'Settings', to: '/settings' },
  { label: 'Users', to: '/settings/users' },
  { label: 'New User' },
]

function validate() {
  const e = {}
  if (!form.fullName.trim()) e.fullName = 'Full name is required.'
  if (!form.email.trim()) e.email = 'Email is required.'
  else if (!EMAIL_RE.test(form.email.trim())) e.email = 'Enter a valid email address.'
  if (!form.persona) e.persona = 'Pick a persona.'
  errors.value = e
  return Object.keys(e).length === 0
}

async function save() {
  if (!validate()) return
  saving.value = true
  try {
    const user = await createBuildsuiteUser({
      full_name: form.fullName.trim(),
      email: form.email.trim().toLowerCase(),
      persona: form.persona,
      enabled: form.enabled ? 1 : 0,
      send_welcome: form.sendWelcome ? 1 : 0,
    })
    // Optional separate password-reset link (welcome was handled on create).
    if (form.sendReset) {
      try { await sendUserPasswordReset(user.name) } catch { /* email queue handles it */ }
    }
    showToast(`User ${user.full_name} created`)
    router.push({ path: '/settings/users', query: { created: user.name } })
  } catch (err) {
    errors.value = { email: err.message || 'Could not create the user.' }
    saving.value = false
  }
}
</script>

<template>
  <DeskPage title="New User" :breadcrumbs="breadcrumbs">
    <div v-if="!store.isAdmin" class="mb-3 px-3 py-2 bg-warning-50 border border-warning-100 text-xs text-warning-700 dark:bg-ink-800 dark:border-ink-700" style="border-radius: 6px;">
      Creating users is restricted to administrators.
    </div>

    <DeskForm v-else>
      <template #action-bar>
        <DeskActionBar
          :saving="saving"
          save-label="Create user"
          saving-label="Creating…"
          @save="save"
          @cancel="router.push('/settings/users')"
        />
      </template>

      <DeskSection title="Account">
        <DeskField label="Full name" required :error="errors.fullName">
          <DeskInput v-model="form.fullName" placeholder="e.g. Asha Menon" @input="errors.fullName = ''" />
        </DeskField>
        <DeskField label="Email" required :error="errors.email" hint="Becomes the login id. The welcome email goes here.">
          <DeskInput v-model="form.email" type="email" placeholder="name@company.com" @input="errors.email = ''" />
        </DeskField>
        <DeskField label="Account status">
          <label class="inline-flex items-center gap-2 text-sm text-ink-700 dark:text-ink-200">
            <input v-model="form.enabled" type="checkbox" class="accent-brand-600" />
            Enabled
          </label>
        </DeskField>
      </DeskSection>

      <DeskSection title="Persona">
        <DeskField label="Persona" required :error="errors.persona" hint="Drives the user's BuildSuite role and access.">
          <DeskSelect v-model="form.persona" @change="errors.persona = ''">
            <option value="">— Select persona —</option>
            <option v-for="r in ROLES" :key="r.id" :value="r.name">{{ r.name }}</option>
          </DeskSelect>
        </DeskField>
      </DeskSection>

      <DeskSection title="Onboarding">
        <DeskField label="Emails">
          <label class="flex items-center gap-2 text-sm text-ink-700 dark:text-ink-200">
            <input v-model="form.sendWelcome" type="checkbox" class="accent-brand-600" />
            Send welcome email (account setup link)
          </label>
          <label class="flex items-center gap-2 text-sm text-ink-700 mt-2 dark:text-ink-200">
            <input v-model="form.sendReset" type="checkbox" class="accent-brand-600" />
            Also send a password-reset link
          </label>
          <div class="text-[11px] text-ink-500 mt-1.5">
            Emails use the site's mail settings. If mail isn't configured they wait in the Email Queue.
          </div>
        </DeskField>
      </DeskSection>
    </DeskForm>
  </DeskPage>
</template>
