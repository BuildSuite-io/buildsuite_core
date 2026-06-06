<script setup>
import DeskSection from '@/components/desk/DeskSection.vue'
import DeskField from '@/components/desk/DeskField.vue'
import DeskInput from '@/components/desk/DeskInput.vue'
import DeskSelect from '@/components/desk/DeskSelect.vue'
import DeskTextarea from '@/components/desk/DeskTextarea.vue'
import DeskLinkPicker from '@/components/desk/DeskLinkPicker.vue'

defineProps({
  open:          { type: Boolean, default: false },
  project:       { type: Object,  default: null },
  editForm:      { type: Object,  required: true },
  errors:        { type: Object,  default: () => ({}) },
  isSubproject:  { type: Boolean, default: false },
  subsCount:     { type: Number,  default: 0 },
  isMultiCompany:{ type: Boolean, default: false },
})

const emit = defineEmits(['close', 'save', 'clear-error'])
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 bg-ink-900/40 z-40 flex items-center justify-center p-6"
      @click.self="emit('close')"
    >
      <div
        class="bg-white border border-ink-200 w-full max-w-2xl shadow-fp-lg flex flex-col"
        style="border-radius: 12px; max-height: calc(100vh - 3rem);"
        @click.stop
      >
        <header class="px-5 py-3 border-b border-ink-200 flex items-center justify-between flex-shrink-0 bg-white" style="border-radius: 12px 12px 0 0;">
          <div class="min-w-0 flex-1">
            <h2 class="text-sm font-semibold text-ink-900">Edit project</h2>
            <p class="text-[11px] text-ink-500 mt-0.5 truncate">{{ project?.name }}</p>
          </div>
          <button
            type="button"
            class="text-ink-500 hover:text-ink-900 text-lg leading-none flex-shrink-0 ml-3"
            aria-label="Close"
            @click="emit('close')"
          >x</button>
        </header>

        <div class="p-5 overflow-y-auto flex-1">
          <DeskSection title="Basic information">
            <DeskField label="Project name" required :error="errors.name">
              <DeskInput v-model="editForm.name" @input="emit('clear-error', 'name')" />
            </DeskField>
            <DeskField label="Client" :error="errors.client">
              <DeskLinkPicker
                v-model="editForm.client"
                doctype="Customer"
                placeholder="Select customer"
                label-field="customer_name"
                value-field="name"
                :search-fields="['customer_name', 'name']"
                order-by="modified desc"
                :page-length="20"
                :error="errors.client"
                @change="emit('clear-error', 'client')"
              />
            </DeskField>
            <DeskField label="Type" :error="errors.type">
              <DeskLinkPicker
                v-model="editForm.type"
                doctype="Project Type"
                placeholder="Select project type"
                label-field="name"
                value-field="name"
                :search-fields="['name']"
                order-by="modified desc"
                :page-length="20"
                :error="errors.type"
                @change="emit('clear-error', 'type')"
              />
            </DeskField>
            <DeskField
              v-if="isMultiCompany"
              label="Company"
              :error="errors.company"
              :hint="errors.company ? '' : 'Legal entity this project belongs to.'"
            >
              <DeskLinkPicker
                v-model="editForm.company"
                doctype="Company"
                placeholder="Select company"
                label-field="name"
                value-field="name"
                :search-fields="['name', 'abbr']"
                order-by="modified desc"
                :page-length="20"
                :error="errors.company"
                @change="emit('clear-error', 'company')"
              />
            </DeskField>
            <DeskField label="Location">
              <DeskInput v-model="editForm.location" />
            </DeskField>
            <DeskField label="Note">
              <DeskTextarea v-model="editForm.description" :rows="3" />
            </DeskField>
            <DeskField
              v-if="!isSubproject"
              label="Subprojects"
              :hint="subsCount > 0
                ? `Locked on - this project has ${subsCount} subproject${subsCount === 1 ? '' : 's'}. Delete or move them out before turning this off.`
                : 'Turn on to break this project into subprojects (e.g. Block A / Block B / Tower 1).'
              "
            >
              <label class="inline-flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  v-model="editForm.isGroup"
                  :disabled="subsCount > 0"
                  class="accent-brand-600 disabled:cursor-not-allowed"
                />
                <span class="text-sm text-ink-700">Allow subprojects under this project</span>
              </label>
            </DeskField>
          </DeskSection>

          <DeskSection title="Schedule & cost">
            <DeskField label="Start date">
              <DeskInput v-model="editForm.startDate" type="date" />
            </DeskField>
            <DeskField label="End date">
              <DeskInput v-model="editForm.endDate" type="date" />
            </DeskField>
            <DeskField label="Budget" hint="In INR">
              <DeskInput v-model="editForm.budget" type="number" />
            </DeskField>
            <DeskField label="Progress" hint="0-100">
              <DeskInput v-model="editForm.progress" type="number" />
            </DeskField>
          </DeskSection>

          <DeskSection title="Team & status">
            <DeskField label="Project Manager">
              <DeskLinkPicker
                v-model="editForm.pm"
                doctype="Employee"
                placeholder="Select project manager"
                label-field="employee_name"
                value-field="name"
                :search-fields="['employee_name', 'name', 'company_email', 'user_id']"
                order-by="modified desc"
                :page-length="20"
              />
            </DeskField>
            <DeskField label="Status">
              <DeskSelect v-model="editForm.status">
                <option>Open</option>
                <option>Working</option>
                <option>On Hold</option>
                <option>Completed</option>
                <option>Cancelled</option>
              </DeskSelect>
            </DeskField>
            <DeskField label="Priority">
              <DeskSelect v-model="editForm.priority">
                <option>Low</option>
                <option>Medium</option>
                <option>High</option>
              </DeskSelect>
            </DeskField>
          </DeskSection>
        </div>

        <footer class="px-5 py-3 border-t border-ink-200 flex items-center justify-end gap-2 flex-shrink-0 bg-white" style="border-radius: 0 0 12px 12px;">
          <button
            type="button"
            class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
            style="border-radius: 6px;"
            @click="emit('close')"
          >Cancel</button>
          <button
            type="button"
            class="desk-save-btn"
            @click="emit('save')"
          >Save</button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>
