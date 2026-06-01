<script setup>
// New Stage Planning — Desk-styled (CLAUDE.md §12.4). Project is pre-selected
// via ?projectId= query param when entered from a project's Stage Planning tab.
// The child table (stagePlanningTasks) is intentionally left empty on create —
// once the stage exists, rows are added from its detail page in edit mode.

import { reactive, ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useDataStore } from '@/stores'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskForm from '@/components/desk/DeskForm.vue'
import DeskActionBar from '@/components/desk/DeskActionBar.vue'
import DeskSection from '@/components/desk/DeskSection.vue'
import DeskField from '@/components/desk/DeskField.vue'
import DeskInput from '@/components/desk/DeskInput.vue'
import DeskSelect from '@/components/desk/DeskSelect.vue'
import DeskTextarea from '@/components/desk/DeskTextarea.vue'

const router = useRouter()
const route = useRoute()
const store = useDataStore()

const form = reactive({
  stageName: '',
  project: route.query.projectId || (store.projects[0] && store.projects[0].id) || '',
  plannedStart: '',
  plannedEnd: '',
  plannedTaskCount: 0,
  plannedCompletionPct: 100,
  description: '',
  dependencies: [],
})
const errors = ref({})

// Sibling stages = existing stages on the same project, eligible as dependencies.
const siblingStages = computed(() =>
  store.stagePlannings.filter(sp => sp.project === form.project)
)
function toggleDependency(id) {
  const i = form.dependencies.indexOf(id)
  if (i === -1) form.dependencies.push(id)
  else form.dependencies.splice(i, 1)
}
// If the user changes the project, clear any sibling dependencies from the
// previous project — they're no longer valid.
function onProjectChange() {
  form.dependencies = []
}

function validate() {
  const e = {}
  if (!form.stageName.trim()) e.stageName = 'Stage name is required'
  if (!form.project)           e.project = 'Project is required'
  if (form.plannedEnd && form.plannedStart && form.plannedEnd < form.plannedStart) {
    e.plannedEnd = 'End must be on or after start'
  }
  errors.value = e
  return Object.keys(e).length === 0
}

function save() {
  if (!validate()) return
  const stage = store.addStagePlanning({ ...form })
  router.push(`/app/stage-plannings/${stage.id}`)
}
function cancel() { router.back() }

const breadcrumbs = [
  { label: 'BuildSuite Core', to: '/' },
  { label: 'Stage Planning', to: '/app/stage-plannings' },
  { label: 'New' },
]
</script>

<template>
  <DeskPage
    title="New Stage"
    subtitle="Plan a stage · task rows are added from the stage detail after create"
    :breadcrumbs="breadcrumbs"
  >
    <DeskForm>
      <template #action-bar>
        <DeskActionBar
          save-label="Create stage"
          @save="save"
          @cancel="cancel"
        />
      </template>

      <DeskSection title="Stage details">
        <DeskField label="Stage name" required :error="errors.stageName">
          <DeskInput v-model="form.stageName" placeholder="e.g. Substructure Stage" />
        </DeskField>
        <DeskField label="Project" required :error="errors.project">
          <DeskSelect v-model="form.project" @change="onProjectChange">
            <option value="">— Select project —</option>
            <option v-for="p in store.projects" :key="p.id" :value="p.id">{{ p.name }}</option>
          </DeskSelect>
        </DeskField>
        <DeskField label="Planned start">
          <DeskInput v-model="form.plannedStart" type="date" />
        </DeskField>
        <DeskField label="Planned end" :error="errors.plannedEnd">
          <DeskInput v-model="form.plannedEnd" type="date" />
        </DeskField>
        <DeskField label="Planned task count" hint="Headline count · the breakdown lives in the child table on detail.">
          <DeskInput v-model="form.plannedTaskCount" type="number" min="0" />
        </DeskField>
        <DeskField label="Planned completion %">
          <DeskInput v-model="form.plannedCompletionPct" type="number" min="0" max="100" />
        </DeskField>
        <DeskField label="Description">
          <DeskTextarea v-model="form.description" :rows="3" placeholder="Scope, gates, hand-off notes…" />
        </DeskField>
      </DeskSection>

      <DeskSection title="Dependencies" v-if="form.project">
        <div class="md:col-span-2">
          <div v-if="siblingStages.length" class="flex flex-wrap gap-2">
            <label
              v-for="sib in siblingStages"
              :key="sib.id"
              class="inline-flex items-center gap-1.5 text-xs text-ink-800 cursor-pointer px-2 py-1 border border-ink-200 hover:bg-ink-50"
              style="border-radius: 2px;"
            >
              <input
                type="checkbox"
                :checked="form.dependencies.includes(sib.id)"
                class="accent-brand-600"
                @change="toggleDependency(sib.id)"
              />
              <span class="font-mono text-[10px] text-ink-500">{{ sib.id }}</span>
              <span>{{ sib.stageName }}</span>
            </label>
          </div>
          <div v-else class="text-xs text-ink-400 italic">
            No other stages on this project yet · create them first, then come back to wire dependencies.
          </div>
          <div class="text-[11px] text-ink-500 mt-1.5">
            Optional · pick stages that must complete before this one can start.
          </div>
        </div>
      </DeskSection>
    </DeskForm>
  </DeskPage>
</template>
