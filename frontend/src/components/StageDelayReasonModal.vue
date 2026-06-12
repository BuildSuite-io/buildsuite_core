<script setup>
// Stage delay reason entry modal. Opens before Stage Review when the stage is
// detected as delayed and no reasons are on file yet (gate mode), or from a
// "+ Add" inside the review dashboard. Shape mirrors an ERPNext-style Delay Log:
//   - Reason: preset dropdown + "Custom…" → free text (stored as plain text).
//   - Responsible Party: Select enum (Own / Subcontractor / Client / External / Consultant).
//   - Days Delayed: optional number (blank = ongoing / unknown duration).
//   - Notes: optional.
// Persists via the whitelisted add_stage_delay_reason backend method.

import { reactive, ref, watch, computed } from 'vue'
import DeskSection from '@/components/desk/DeskSection.vue'
import DeskField from '@/components/desk/DeskField.vue'
import DeskInput from '@/components/desk/DeskInput.vue'
import DeskSelect from '@/components/desk/DeskSelect.vue'
import DeskTextarea from '@/components/desk/DeskTextarea.vue'

const REASON_PRESETS = [
  'Payment delay',
  'Material shortage',
  'Equipment unavailability',
  'Subcontractor underperformance',
  'Design / drawing not ready',
  'Inspection / approval pending',
  'Site access issue',
  'Weather (rain / storm / heat)',
  'Pressure test not finished',
  'Waiting for water leakage test',
]
const CUSTOM_SENTINEL = '__custom__'
const RESPONSIBLE_PARTIES = ['Own', 'Subcontractor', 'Client', 'External', 'Consultant']

const props = defineProps({
  open: { type: Boolean, default: false },
  stageId: { type: String, default: '' },
  stageName: { type: String, default: '' },
  isGate: { type: Boolean, default: true },
})
const emit = defineEmits(['update:open', 'saved', 'cancel'])

const form = reactive({
  reasonSelect: '',
  reasonCustom: '',
  responsibleParty: '',
  daysDelayed: '',
  note: '',
})
const errors = ref({})
const saving = ref(false)

watch(() => props.open, (isOpen) => {
  if (!isOpen) return
  form.reasonSelect = ''
  form.reasonCustom = ''
  form.responsibleParty = ''
  form.daysDelayed = ''
  form.note = ''
  errors.value = {}
  saving.value = false
})

const isCustomReason = computed(() => form.reasonSelect === CUSTOM_SENTINEL)
const finalReason = computed(() =>
  isCustomReason.value ? form.reasonCustom.trim() : form.reasonSelect.trim(),
)

function close() { emit('update:open', false) }
function cancel() {
  if (saving.value) return
  emit('cancel')
  close()
}

async function save() {
  const e = {}
  if (!finalReason.value) {
    e.reason = isCustomReason.value ? 'Enter the custom reason.' : 'Pick a reason or choose "Custom…".'
  }
  if (!form.responsibleParty) e.responsibleParty = 'Select the responsible party.'
  if (form.daysDelayed !== '' && form.daysDelayed !== null) {
    const n = Number(form.daysDelayed)
    if (!Number.isFinite(n) || n < 0) e.daysDelayed = 'Enter a non-negative number, or leave blank.'
  }
  errors.value = e
  if (Object.keys(e).length) return

  const daysParsed = form.daysDelayed === '' || form.daysDelayed === null
    ? ''
    : String(Math.max(0, Math.floor(Number(form.daysDelayed))))

  saving.value = true
  try {
    const body = new URLSearchParams({
      stage: props.stageId,
      reason: finalReason.value,
      responsible_party: form.responsibleParty,
      days_delayed: daysParsed,
      note: form.note || '',
    })
    const response = await fetch(
      '/api/method/buildsuite_core.buildsuite_core.doctype.stage_planning.stage_planning.add_stage_delay_reason',
      {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-Frappe-CSRF-Token': window.csrf_token || '',
        },
        body: body.toString(),
      },
    )
    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(data?.exception || data?.exc_type || `HTTP ${response.status}`)
    }
    const payload = await response.json().catch(() => ({}))
    emit('saved', payload?.message || null)
    close()
  } catch (err) {
    errors.value = { reason: err.message || 'Could not save the delay reason.' }
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 bg-ink-900/40 z-[60] flex items-center justify-center p-6"
      @click.self="cancel"
    >
      <div
        class="bg-white border border-ink-200 w-full max-w-lg shadow-fp-lg flex flex-col dark:bg-[#242424] dark:border-ink-700"
        style="border-radius: 12px; max-height: calc(100vh - 3rem);"
        @click.stop
      >
        <header class="px-5 py-3 border-b border-ink-200 flex items-center justify-between flex-shrink-0 dark:border-ink-700" style="border-radius: 12px 12px 0 0;">
          <div class="min-w-0 flex-1">
            <h2 class="text-sm font-semibold text-ink-900 dark:text-[#F5F5F5]">
              {{ isGate ? 'Record delay reason' : 'Add delay reason' }}
            </h2>
            <p class="text-[11px] text-ink-500 mt-0.5 truncate">
              <template v-if="isGate">This stage appears to be delayed. Record the reason before opening Stage Review.</template>
              <template v-else>{{ stageName }}</template>
            </p>
          </div>
          <button
            type="button"
            class="text-ink-500 hover:text-ink-900 text-lg leading-none flex-shrink-0 ml-3 dark:text-ink-400 dark:hover:text-ink-200"
            aria-label="Close"
            @click="cancel"
          >×</button>
        </header>

        <div class="p-5 overflow-y-auto flex-1">
          <DeskSection title="Why is this stage delayed?">
            <DeskField label="Reason" required :error="errors.reason" hint="Pick a common reason or choose Custom to enter your own.">
              <DeskSelect v-model="form.reasonSelect">
                <option value="">— Select reason —</option>
                <option v-for="r in REASON_PRESETS" :key="r" :value="r">{{ r }}</option>
                <option disabled>──────────</option>
                <option :value="CUSTOM_SENTINEL">Custom…</option>
              </DeskSelect>
              <DeskInput
                v-if="isCustomReason"
                v-model="form.reasonCustom"
                class="mt-2"
                placeholder="Describe the delay"
              />
            </DeskField>
            <DeskField label="Responsible party" required :error="errors.responsibleParty" hint="Who is accountable for this delay — own team, subcontractor, client, etc.">
              <DeskSelect v-model="form.responsibleParty">
                <option value="">— Select —</option>
                <option v-for="p in RESPONSIBLE_PARTIES" :key="p" :value="p">{{ p }}</option>
              </DeskSelect>
            </DeskField>
            <DeskField label="No. of days delayed" :error="errors.daysDelayed" hint="Optional — leave blank for ongoing delays where duration is not yet known.">
              <DeskInput v-model="form.daysDelayed" type="number" min="0" step="1" placeholder="e.g. 3" />
            </DeskField>
            <DeskField label="Additional notes" hint="Optional context — what happened, what's the plan, by when.">
              <DeskTextarea v-model="form.note" :rows="3" placeholder="Optional context" />
            </DeskField>
          </DeskSection>
        </div>

        <footer class="px-5 py-3 border-t border-ink-200 flex items-center justify-end gap-2 flex-shrink-0 dark:border-ink-700" style="border-radius: 0 0 12px 12px;">
          <button
            type="button"
            class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 dark:bg-ink-800 dark:border-ink-700 dark:text-ink-100 dark:hover:bg-ink-700"
            style="border-radius: 6px;"
            :disabled="saving"
            @click="cancel"
          >Cancel</button>
          <button
            type="button"
            class="desk-save-btn"
            :disabled="saving"
            @click="save"
          >{{ saving ? 'Saving…' : 'Save reason' }}</button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>
