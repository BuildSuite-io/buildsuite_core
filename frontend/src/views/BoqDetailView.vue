<script setup>
// BOQ Detail — Desk-styled (CLAUDE.md §12.4) with one deliberate exception:
// the "Compare to R<n>" toggle and the inline Δ delta chips on item rows are
// LEFT AS-IS (brand-green styling) because they are the seed of the standalone
// Vue-styled "Revision Compare" page in §12.4's 9-page Vue allowlist (Phase 5).
// Everything else — page chrome, action bar, KPI strip, 3-level tree, planned/
// actual bars, sub-item rate analysis — is rebuilt in Desk style.
//
// All store calls, computed properties, and workflow actions (submit / approve /
// recalc / createRevision / delete / compareMode toggle) are preserved verbatim.

import { computed, ref } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { useDataStore } from '@/stores'
import { useConfirm } from '@/composables/useConfirm'
import StatusBadge from '@/components/StatusBadge.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskForm from '@/components/desk/DeskForm.vue'
import DeskActionBar from '@/components/desk/DeskActionBar.vue'
import DeskLink from '@/components/desk/DeskLink.vue'
import DeskField from '@/components/desk/DeskField.vue'
import DeskInput from '@/components/desk/DeskInput.vue'
import DeskSelect from '@/components/desk/DeskSelect.vue'
import DeskTextarea from '@/components/desk/DeskTextarea.vue'
import { fmtINR, fmtCompactINR, fmtDate } from '@/utils/format'
import { getWorkspaceIconPath } from '@/utils/workspaceIcons'

const props = defineProps({ id: { type: String, required: true } })
const router = useRouter()
const store = useDataStore()
const confirmDialog = useConfirm()

const boq = computed(() => store.boqById(props.id))
const project = computed(() => boq.value ? store.projectById(boq.value.projectId) : null)
const baseBoq = computed(() => boq.value?.baseRevisionId ? store.boqById(boq.value.baseRevisionId) : null)
const sourceSco = computed(() => boq.value?.sourceScoId ? store.scos.find(s => s.id === boq.value.sourceScoId) : null)
const groups = computed(() => boq.value ? store.boqGroupsByBoq(boq.value.id) : [])
const totals = computed(() => boq.value ? store.boqTotals(boq.value.id) : { planned:0, actual:0, variance:0, variancePct:0, itemCount:0 })

const expandedGroups = ref({})
const expandedItems = ref({})
const compareMode = ref(false)

function toggleGroup(id) { expandedGroups.value[id] = !expandedGroups.value[id] }
function toggleItem(id)  { expandedItems.value[id]  = !expandedItems.value[id]  }
function expandAll() {
  groups.value.forEach(g => { expandedGroups.value[g.id] = true })
  store.boqItemsByBoq(boq.value.id).forEach(i => { expandedItems.value[i.id] = true })
}
function collapseAll() { expandedGroups.value = {}; expandedItems.value = {} }

function variancePill(pct) {
  if (Math.abs(pct) < 0.5) return 'text-ink-500'
  return pct > 0 ? 'text-danger-700' : 'text-success-700'
}
function pctOf(part, whole) { return whole ? (part / whole) * 100 : 0 }

function groupTotals(groupId) {
  const items = store.boqItems.filter(i => i.groupId === groupId)
  const planned = items.reduce((a,i) => a + (i.plannedAmount || 0), 0)
  const actual  = items.reduce((a,i) => a + (i.actualAmount  || 0), 0)
  return { planned, actual, count: items.length }
}

// Diff against base revision when compareMode is on. Match by item code. Preserved
// verbatim — feeds the Δ chip rendering that stays brand-green styled per prompt.
function baseAmount(code) {
  if (!baseBoq.value) return null
  const base = store.boqItems.find(i => i.boqId === baseBoq.value.id && i.code === code)
  return base?.plannedAmount ?? null
}

// === Workflow actions ===
function recalculate() { store.recalculateActuals(boq.value.id) }
async function submit() {
  const ok = await confirmDialog({
    title: 'Submit for approval',
    message: `Submit BOQ ${boq.value.id} for approval?`,
    confirmLabel: 'Submit',
  })
  if (ok) store.submitBoq(boq.value.id)
}
async function approve() {
  const others = store.boqs.filter(b => b.projectId === boq.value.projectId && b.status === 'Approved' && b.id !== boq.value.id)
  const msg = others.length
    ? `Approve revision ${boq.value.revision}? This will supersede the currently-active revision (${others[0].id}).`
    : `Approve revision ${boq.value.revision}? It will become the live BOQ for this project.`
  if (await confirmDialog({ title: 'Approve revision', message: msg, confirmLabel: 'Approve' })) store.approveBoq(boq.value.id)
}
function createRevision() {
  const note = window.prompt('Optional: enter SCO id to link this revision to (or leave blank).', '')
  if (note === null) return
  const sco = note?.trim() ? note.trim() : null
  const newBoq = store.createBoqRevisionFrom(boq.value.id, { sourceScoId: sco })
  if (newBoq) router.push(`/boq/${newBoq.id}`)
}
async function removeBoq() {
  const ok = await confirmDialog({
    title: 'Delete BOQ',
    message: `Delete BOQ ${boq.value.id} and all its rows? This cannot be undone.`,
    confirmLabel: 'Delete',
    destructive: true,
  })
  if (!ok) return
  store.deleteBoq(boq.value.id)
  router.push('/boq')
}

const canSubmit  = computed(() => boq.value?.status === 'Draft')
const canApprove = computed(() => boq.value?.status === 'Submitted')
const isLocked   = computed(() => boq.value?.status === 'Approved' || boq.value?.status === 'Superseded')
// Add/edit/delete affordances on the tree are gated on Draft. Submitted BOQs are
// waiting for an approver and shouldn't change underneath them; Approved/Superseded
// are immutable by design (use + Revision to make changes downstream).
const isEditable = computed(() => boq.value?.status === 'Draft')

// ===== Group add/edit/delete =====
const groupModal = ref(null)  // null | { mode: 'add' | 'edit', id?: string }
const groupForm  = ref({ code: '', name: '' })

function openAddGroup() {
  groupForm.value = { code: '', name: '' }
  groupModal.value = { mode: 'add' }
}
function openEditGroup(g) {
  groupForm.value = { code: g.code, name: g.name }
  groupModal.value = { mode: 'edit', id: g.id }
}
function saveGroup() {
  if (!groupForm.value.code.trim() || !groupForm.value.name.trim()) {
    alert('Code and name are required.')
    return
  }
  if (groupModal.value.mode === 'add') {
    store.addBoqGroup({ boqId: boq.value.id, code: groupForm.value.code.trim(), name: groupForm.value.name.trim() })
  } else {
    store.updateBoqGroup(groupModal.value.id, { code: groupForm.value.code.trim(), name: groupForm.value.name.trim() })
  }
  groupModal.value = null
}
async function deleteGroupConfirm(g) {
  const items = store.boqItemsByGroup(g.id)
  const msg = items.length
    ? `Delete group "${g.code} — ${g.name}" along with ${items.length} item${items.length === 1 ? '' : 's'} and their sub-items? This cannot be undone.`
    : `Delete group "${g.code} — ${g.name}"?`
  if (await confirmDialog({ title: 'Delete group', message: msg, confirmLabel: 'Delete', destructive: true })) store.deleteBoqGroup(g.id)
}

// ===== Item add/edit/delete =====
const itemModal = ref(null)  // null | { mode: 'add' | 'edit', groupId?, id? }
const itemForm  = ref({ code: '', description: '', unit: 'nos', plannedQty: 0, rate: 0, taskId: null })

const availableTasks = computed(() => project.value ? store.tasksByProject(project.value.id) : [])
const itemPlannedAmountPreview = computed(() =>
  (Number(itemForm.value.plannedQty) || 0) * (Number(itemForm.value.rate) || 0)
)

function openAddItem(groupId) {
  itemForm.value = { code: '', description: '', unit: 'nos', plannedQty: 0, rate: 0, taskId: null }
  itemModal.value = { mode: 'add', groupId }
}
function openEditItem(item) {
  itemForm.value = {
    code: item.code,
    description: item.description,
    unit: item.unit,
    plannedQty: item.plannedQty,
    rate: item.rate,
    taskId: item.taskId,
  }
  itemModal.value = { mode: 'edit', id: item.id }
}
function saveItem() {
  const f = itemForm.value
  if (!f.code.trim() || !f.description.trim() || !f.unit.trim()) {
    alert('Code, description, and unit are required.')
    return
  }
  const data = {
    code: f.code.trim(),
    description: f.description.trim(),
    unit: f.unit.trim(),
    plannedQty: Number(f.plannedQty) || 0,
    rate: Number(f.rate) || 0,
    taskId: f.taskId || null,
  }
  if (itemModal.value.mode === 'add') {
    store.addBoqItem({ boqId: boq.value.id, groupId: itemModal.value.groupId, ...data })
  } else {
    store.updateBoqItem(itemModal.value.id, data)
  }
  itemModal.value = null
}
async function deleteItemConfirm(item) {
  const subs = store.boqSubItemsByItem(item.id)
  const msg = subs.length
    ? `Delete item "${item.code} — ${item.description}" along with ${subs.length} sub-item${subs.length === 1 ? '' : 's'}? This cannot be undone.`
    : `Delete item "${item.code} — ${item.description}"?`
  if (await confirmDialog({ title: 'Delete item', message: msg, confirmLabel: 'Delete', destructive: true })) store.deleteBoqItem(item.id)
}

// ===== Sub-item add/edit/delete =====
const subItemModal = ref(null)  // null | { mode: 'add' | 'edit', itemId?, id?, parentUnit? }
const subItemForm  = ref({ rateMasterId: null, description: '', qtyPerUnit: 0, rate: 0 })

const rateMasterOptions = computed(() => store.rateMaster.slice().sort((a, b) => a.code.localeCompare(b.code)))

function openAddSubItem(item) {
  subItemForm.value = { rateMasterId: null, description: '', qtyPerUnit: 0, rate: 0 }
  subItemModal.value = { mode: 'add', itemId: item.id, parentUnit: item.unit }
}
function openEditSubItem(si, item) {
  subItemForm.value = {
    rateMasterId: si.rateMasterId || null,
    description: si.description,
    qtyPerUnit: si.qtyPerUnit,
    rate: si.rate,
  }
  subItemModal.value = { mode: 'edit', id: si.id, parentUnit: item.unit }
}
// When the user picks a Rate Master entry, auto-fill description + rate from it.
// Per the store's addBoqSubItem behavior, rate is anyway re-fetched from rate master
// on save when rateMasterId is set — this is just the preview while the user is in
// the modal so they can see what the final amount will be.
function onRateMasterPick(rateMasterId) {
  if (!rateMasterId) return
  const rm = store.rateMaster.find(r => r.id === rateMasterId)
  if (rm) {
    subItemForm.value.description = rm.description
    subItemForm.value.rate = rm.currentRate
  }
}
const subItemAmountPreview = computed(() =>
  (Number(subItemForm.value.qtyPerUnit) || 0) * (Number(subItemForm.value.rate) || 0)
)
function saveSubItem() {
  const f = subItemForm.value
  if (!f.description.trim() || Number(f.qtyPerUnit) <= 0) {
    alert('Description and a non-zero quantity per unit are required.')
    return
  }
  const data = {
    rateMasterId: f.rateMasterId || null,
    description: f.description.trim(),
    qtyPerUnit: Number(f.qtyPerUnit) || 0,
    rate: Number(f.rate) || 0,
  }
  if (subItemModal.value.mode === 'add') {
    store.addBoqSubItem({ boqId: boq.value.id, itemId: subItemModal.value.itemId, ...data })
  } else {
    store.updateBoqSubItem(subItemModal.value.id, data)
  }
  subItemModal.value = null
}
async function deleteSubItemConfirm(si) {
  if (await confirmDialog({ title: 'Delete sub-item', message: `Delete sub-item "${si.description}"?`, confirmLabel: 'Delete', destructive: true })) store.deleteBoqSubItem(si.id)
}

// Primary action dispatcher — Submit when Draft, Approve when Submitted, hidden when locked.
const showPrimary = computed(() => canSubmit.value || canApprove.value)
const primaryLabel = computed(() => canSubmit.value ? 'Submit for approval' : canApprove.value ? 'Approve' : '')
function onPrimary() {
  if (canSubmit.value) submit()
  else if (canApprove.value) approve()
}

const breadcrumbs = computed(() => {
  const out = [
    { label: 'BuildSuite Core', to: '/' },
    { label: 'BOQ', to: '/boq' },
  ]
  if (project.value) out.push({ label: project.value.name, to: `/projects/${project.value.id}` })
  return out
})

const subtitle = computed(() => boq.value ? `${boq.value.id} · R${boq.value.revision}` : '')

// Grid template for the tree (chevron / code / description / qty / rate / planned / actual / variance / task)
const treeGridStyle = 'grid-template-columns: 28px 80px 1fr 80px 90px 100px 110px 110px 110px 80px;'
</script>

<template>
  <div v-if="!boq" class="px-6 py-12 text-center text-ink-500">
    <div class="text-sm">BOQ <span class="font-mono">{{ id }}</span> not found.</div>
    <DeskLink to="/boq" class="text-sm mt-2 inline-block">← Back to BOQ list</DeskLink>
  </div>

  <DeskPage
    v-else
    :title="boq.title"
    :subtitle="subtitle"
    :breadcrumbs="breadcrumbs"
    :status="boq.status"
  >
    <DeskForm>
      <template #action-bar>
        <DeskActionBar
          :show-save="showPrimary"
          :save-label="primaryLabel"
          :show-cancel="false"
          @save="onPrimary"
        >
          <template #left>
            <span v-if="sourceSco" class="text-xs text-ink-500">
              from SCO
              <DeskLink to="/sco" class="font-mono">{{ sourceSco.id }}</DeskLink>
            </span>
          </template>
          <template #menu>
            <!-- Compare toggle — LEFT AS-IS per prompt (Phase-5 prelude: Revision Compare page).
                 Uses brand-green styling and rounded corners deliberately. -->
            <button
              v-if="baseBoq"
              type="button"
              class="text-xs px-2.5 py-1.5 border border-ink-200 rounded hover:bg-ink-50"
              :class="compareMode ? 'bg-brand-50 border-brand-300 text-brand-700' : ''"
              @click="compareMode = !compareMode"
            >{{ compareMode ? '✓ Comparing R' + baseBoq.revision : 'Compare to R' + baseBoq.revision }}</button>

            <button
              type="button"
              class="text-xs px-2 py-1 border border-ink-200 bg-white hover:bg-ink-50"
              style="border-radius: 2px;"
              @click="recalculate"
            >↻ Recalc actuals</button>

            <button
              type="button"
              class="text-xs px-2 py-1 border border-ink-200 bg-white hover:bg-ink-50"
              style="border-radius: 2px;"
              @click="createRevision"
            >+ Revision</button>

            <button
              v-if="!isLocked"
              type="button"
              class="text-xs px-2 py-1 border border-ink-200 bg-white hover:bg-ink-50"
              style="border-radius: 2px; color: #B91C1C;"
              @click="removeBoq"
            >Delete</button>
          </template>
        </DeskActionBar>
      </template>

      <!-- KPI strip — Desk density: 6 small cards, modest numbers -->
      <div class="grid grid-cols-2 md:grid-cols-6 gap-2 mb-4">
        <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
          <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Revision</div>
          <div class="text-base font-semibold text-ink-900 mt-0.5">R{{ boq.revision }}</div>
          <div v-if="baseBoq" class="text-[10px] text-ink-500 mt-0.5">
            from <DeskLink :to="`/boq/${baseBoq.id}`" class="font-mono">R{{ baseBoq.revision }}</DeskLink>
          </div>
          <div v-else class="text-[10px] text-ink-400 mt-0.5">original</div>
        </div>
        <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
          <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Groups · Items</div>
          <div class="text-base font-semibold text-ink-900 mt-0.5">{{ groups.length }} · {{ totals.itemCount }}</div>
          <div class="text-[10px] text-ink-500 mt-0.5">across this BOQ</div>
        </div>
        <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
          <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Planned</div>
          <div class="text-base font-semibold text-ink-900 mt-0.5 tabular-nums">{{ fmtCompactINR(totals.planned) }}</div>
          <div class="text-[10px] text-ink-500 mt-0.5 tabular-nums">{{ fmtINR(totals.planned) }}</div>
        </div>
        <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
          <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Actual</div>
          <div class="text-base font-semibold text-ink-700 mt-0.5 tabular-nums">{{ fmtCompactINR(totals.actual) }}</div>
          <div class="text-[10px] text-ink-500 mt-0.5">{{ pctOf(totals.actual, totals.planned).toFixed(1) }}% of plan</div>
        </div>
        <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
          <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Variance</div>
          <div class="text-base font-semibold mt-0.5 tabular-nums" :class="variancePill(totals.variancePct)">
            {{ totals.variancePct > 0 ? '+' : '' }}{{ totals.variancePct.toFixed(1) }}%
          </div>
          <div class="text-[10px] text-ink-500 mt-0.5 tabular-nums">{{ fmtCompactINR(totals.variance) }} delta</div>
        </div>
        <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
          <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Prepared</div>
          <div class="flex items-center gap-1 mt-1">
            <UserAvatar :user-id="boq.preparedBy" size="xs" />
            <span class="text-[11px] text-ink-500">{{ fmtDate(boq.preparedDate) }}</span>
          </div>
          <div v-if="boq.approvedBy" class="flex items-center gap-1 mt-1">
            <UserAvatar :user-id="boq.approvedBy" size="xs" />
            <span class="text-[11px] text-success-700">{{ fmtDate(boq.approvedDate) }}</span>
          </div>
          <div v-else class="text-[10px] text-ink-400 mt-1">awaiting approval</div>
        </div>
      </div>

      <!-- Toolbar above the tree -->
      <div class="flex items-center gap-2 mb-1.5">
        <button type="button" @click="expandAll" class="desk-link text-xs">Expand all</button>
        <span class="text-ink-300 text-xs">·</span>
        <button type="button" @click="collapseAll" class="desk-link text-xs">Collapse all</button>
        <div v-if="compareMode && baseBoq" class="ml-2 text-[11px] text-ink-500">
          Δ vs R{{ baseBoq.revision }} shown on each item row
        </div>
        <div class="ml-auto flex items-center gap-2">
          <span v-if="!isEditable" class="text-[11px] text-ink-400 italic">
            {{ boq.status }} — read-only · use <button type="button" @click="createRevision" class="desk-link">+ Revision</button> to make changes
          </span>
          <button
            v-if="isEditable"
            type="button"
            class="desk-save-btn"
            @click="openAddGroup"
          >+ Add Group</button>
        </div>
      </div>

      <!-- The 3-level tree — Desk styling -->
      <div class="bg-white border border-ink-200 overflow-hidden" style="border-radius: 2px;">
        <!-- Header strip -->
        <div
          class="grid items-center bg-ink-50 border-b border-ink-200 text-[11px] text-ink-500 uppercase tracking-wider font-semibold"
          :style="treeGridStyle"
        >
          <div></div>
          <div class="px-3 py-2">Code</div>
          <div class="px-3 py-2">Description</div>
          <div class="px-3 py-2">Unit</div>
          <div class="px-3 py-2 text-right">Plan Qty</div>
          <div class="px-3 py-2 text-right">Rate (₹)</div>
          <div class="px-3 py-2 text-right">Planned</div>
          <div class="px-3 py-2 text-right">Actual</div>
          <div class="px-3 py-2 text-right">Variance</div>
          <div class="px-3 py-2 text-center">Task</div>
        </div>

        <template v-for="g in groups" :key="g.id">
          <!-- Group row — bold, light grey, slightly larger -->
          <div
            class="relative group/row grid items-center bg-ink-50 border-b border-ink-200 hover:bg-ink-100 cursor-pointer"
            :style="treeGridStyle"
            @click="toggleGroup(g.id)"
          >
            <div class="px-2 text-ink-500 text-xs">{{ expandedGroups[g.id] ? '▾' : '▸' }}</div>
            <div class="px-3 py-2 font-mono text-xs text-ink-700">{{ g.code }}</div>
            <div class="px-3 py-2 text-sm font-semibold text-ink-900">{{ g.name }}</div>
            <div></div>
            <div></div>
            <div class="px-3 py-2 text-right text-[11px] text-ink-500">{{ groupTotals(g.id).count }} items</div>
            <div class="px-3 py-2 text-right tabular-nums text-sm font-medium text-ink-900">{{ fmtCompactINR(groupTotals(g.id).planned) }}</div>
            <div class="px-3 py-2 text-right tabular-nums text-sm text-ink-700">{{ fmtCompactINR(groupTotals(g.id).actual) }}</div>
            <div
              class="px-3 py-2 text-right text-sm tabular-nums font-medium"
              :class="variancePill(((groupTotals(g.id).actual - groupTotals(g.id).planned) / (groupTotals(g.id).planned || 1)) * 100)"
            >{{ groupTotals(g.id).planned ? (((groupTotals(g.id).actual - groupTotals(g.id).planned) / groupTotals(g.id).planned) * 100).toFixed(1) : '0.0' }}%</div>
            <div></div>

            <!-- Edit / Delete (hover-visible, only when BOQ is Draft) -->
            <div
              v-if="isEditable"
              class="absolute right-1 top-1/2 -translate-y-1/2 opacity-0 group-hover/row:opacity-100 transition-opacity flex bg-white border border-ink-200 shadow-fp-sm"
              style="border-radius: 2px;"
            >
              <button type="button" @click.stop="openEditGroup(g)" class="px-1.5 py-0.5 text-xs hover:bg-ink-50" title="Edit group"><svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('pencil')" /></button>
              <button type="button" @click.stop="deleteGroupConfirm(g)" class="px-1.5 py-0.5 text-xs text-danger-700 hover:bg-danger-50" title="Delete group"><svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('trash')" /></button>
            </div>
          </div>

          <!-- Items inside group -->
          <template v-if="expandedGroups[g.id]">
            <template v-for="item in store.boqItemsByGroup(g.id)" :key="item.id">
              <div
                class="relative group/row grid items-center border-b border-ink-100 hover:bg-brand-50 cursor-pointer"
                :style="treeGridStyle"
                @click="toggleItem(item.id)"
              >
                <!-- Edit / Delete (hover-visible, only when BOQ is Draft) -->
                <div
                  v-if="isEditable"
                  class="absolute right-1 top-1/2 -translate-y-1/2 opacity-0 group-hover/row:opacity-100 transition-opacity flex bg-white border border-ink-200 shadow-fp-sm z-10"
                  style="border-radius: 2px;"
                >
                  <button type="button" @click.stop="openEditItem(item)" class="px-1.5 py-0.5 text-xs hover:bg-ink-50" title="Edit item"><svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('pencil')" /></button>
                  <button type="button" @click.stop="deleteItemConfirm(item)" class="px-1.5 py-0.5 text-xs text-danger-700 hover:bg-danger-50" title="Delete item"><svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('trash')" /></button>
                </div>
                <div class="px-2 text-ink-400 text-[10px]">
                  {{ store.boqSubItemsByItem(item.id).length ? (expandedItems[item.id] ? '▾' : '▸') : '·' }}
                </div>
                <div class="px-3 py-1.5 font-mono text-xs text-ink-700">{{ item.code }}</div>
                <div class="px-3 py-1.5 text-sm text-ink-800">
                  {{ item.description }}
                  <!-- LEFT AS-IS per prompt (Phase-5 prelude): Δ chip uses brand-tinted danger/success styling -->
                  <span
                    v-if="compareMode && baseAmount(item.code) !== null && baseAmount(item.code) !== item.plannedAmount"
                    class="ml-2 text-[10px] px-1 py-0.5 rounded font-medium"
                    :class="item.plannedAmount > baseAmount(item.code) ? 'bg-danger-50 text-danger-700' : 'bg-success-50 text-success-700'"
                  >Δ {{ item.plannedAmount > baseAmount(item.code) ? '+' : '' }}{{ fmtCompactINR(item.plannedAmount - baseAmount(item.code)) }}</span>
                </div>
                <div class="px-3 py-1.5 text-xs text-ink-600">{{ item.unit }}</div>
                <div class="px-3 py-1.5 text-right tabular-nums text-sm text-ink-700">{{ item.plannedQty.toLocaleString('en-IN') }}</div>
                <div class="px-3 py-1.5 text-right tabular-nums text-sm text-ink-700">{{ item.rate.toLocaleString('en-IN') }}</div>
                <div class="px-3 py-1.5 text-right tabular-nums text-sm text-ink-900">{{ fmtCompactINR(item.plannedAmount) }}</div>
                <div class="px-3 py-1.5">
                  <div class="flex flex-col items-end">
                    <span class="tabular-nums text-sm text-ink-700">{{ fmtCompactINR(item.actualAmount) }}</span>
                    <div class="w-full h-1 bg-ink-100 overflow-hidden mt-1" style="border-radius: 2px;">
                      <div
                        class="h-full"
                        :class="item.actualAmount > item.plannedAmount ? 'bg-danger-500' : (item.actualAmount > item.plannedAmount * 0.9 ? 'bg-warning-500' : 'bg-success-500')"
                        :style="`width: ${Math.min(100, pctOf(item.actualAmount, item.plannedAmount)).toFixed(1)}%`"
                      ></div>
                    </div>
                  </div>
                </div>
                <div
                  class="px-3 py-1.5 text-right tabular-nums text-sm"
                  :class="variancePill(((item.actualAmount - item.plannedAmount) / (item.plannedAmount || 1)) * 100)"
                >{{ item.plannedAmount ? (((item.actualAmount - item.plannedAmount) / item.plannedAmount) * 100).toFixed(1) : '0.0' }}%</div>
                <div class="px-3 py-1.5 text-center">
                  <DeskLink
                    v-if="item.taskId"
                    :to="`/tasks/${item.taskId}`"
                    @click.stop
                    class="text-[10px] font-mono"
                  >{{ item.taskId.slice(-4) }}</DeskLink>
                  <span v-else class="text-[10px] text-ink-300">—</span>
                </div>
              </div>

              <!-- Sub-items: rate analysis. Indented, smaller, Rate Master links Desk-blue. -->
              <template v-if="expandedItems[item.id]">
                <div
                  v-for="si in store.boqSubItemsByItem(item.id)"
                  :key="si.id"
                  class="relative group/row grid items-center border-b border-ink-50 bg-ink-50/40"
                  :style="treeGridStyle"
                >
                  <div></div>
                  <div></div>
                  <div class="px-3 py-1 text-xs text-ink-600 pl-10">
                    ↳ {{ si.description }}
                    <DeskLink
                      v-if="si.rateMasterId"
                      to="/rate-master"
                      @click.stop
                      class="ml-2 text-[10px] font-mono"
                    >{{ si.rateMasterId }}</DeskLink>
                  </div>
                  <div></div>
                  <div class="px-3 py-1 text-right tabular-nums text-xs text-ink-500">{{ si.qtyPerUnit }}</div>
                  <div class="px-3 py-1 text-right tabular-nums text-xs text-ink-500">{{ si.rate.toLocaleString('en-IN') }}</div>
                  <div class="px-3 py-1 text-right tabular-nums text-xs text-ink-700">{{ fmtINR(si.amount) }}</div>
                  <div class="px-3 py-1 text-right text-[10px] text-ink-400">per {{ item.unit }}</div>
                  <div></div>
                  <div></div>

                  <!-- Edit / Delete (hover-visible) -->
                  <div
                    v-if="isEditable"
                    class="absolute right-1 top-1/2 -translate-y-1/2 opacity-0 group-hover/row:opacity-100 transition-opacity flex bg-white border border-ink-200 shadow-fp-sm z-10"
                    style="border-radius: 2px;"
                  >
                      <button type="button" @click.stop="openEditSubItem(si, item)" class="px-1.5 py-0.5 text-xs hover:bg-ink-50" title="Edit sub-item"><svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('pencil')" /></button>
                      <button type="button" @click.stop="deleteSubItemConfirm(si)" class="px-1.5 py-0.5 text-xs text-danger-700 hover:bg-danger-50" title="Delete sub-item"><svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('trash')" /></button>
                  </div>
                </div>
                <div
                  v-if="!store.boqSubItemsByItem(item.id).length"
                  class="grid items-center border-b border-ink-50 bg-ink-50/40 text-[11px] text-ink-400 italic"
                  :style="treeGridStyle"
                >
                  <div></div>
                  <div></div>
                  <div class="px-3 py-1 pl-10">No rate analysis recorded for this item.</div>
                  <div></div><div></div><div></div><div></div><div></div><div></div><div></div>
                </div>

                <!-- Inline "+ Add Sub-item" affordance -->
                <div
                  v-if="isEditable"
                  class="grid items-center border-b border-dashed border-ink-200 bg-ink-50/40 cursor-pointer hover:bg-brand-50"
                  :style="treeGridStyle"
                  @click="openAddSubItem(item)"
                >
                  <div></div>
                  <div></div>
                  <div class="px-3 py-1 pl-10 text-[11px] text-brand-700 font-medium">+ Add sub-item to {{ item.code }}</div>
                  <div></div><div></div><div></div><div></div><div></div><div></div><div></div>
                </div>
              </template>
            </template>

            <!-- Inline "+ Add Item" affordance — at the bottom of the expanded group -->
            <div
              v-if="isEditable"
              class="grid items-center border-b border-dashed border-ink-200 cursor-pointer hover:bg-brand-50"
              :style="treeGridStyle"
              @click="openAddItem(g.id)"
            >
              <div></div>
              <div></div>
              <div class="px-3 py-1.5 text-xs text-brand-700 font-medium">+ Add item to {{ g.code }} — {{ g.name }}</div>
              <div></div><div></div><div></div><div></div><div></div><div></div><div></div>
            </div>
          </template>
        </template>

        <div v-if="!groups.length" class="px-4 py-12 text-center text-sm text-ink-400">
          This BOQ has no groups yet.
          <button
            v-if="isEditable"
            type="button"
            class="desk-link ml-1"
            @click="openAddGroup"
          >+ Add the first group</button>
        </div>
      </div>

      <!-- ========== Group modal (add + edit) ========== -->
      <div
        v-if="groupModal"
        class="fixed inset-0 bg-ink-900/40 z-[60] flex items-center justify-center p-4"
        @click="groupModal = null"
      >
        <div
          class="bg-white border border-ink-200 shadow-fp-lg w-full max-w-md"
          style="border-radius: 2px;"
          @click.stop
        >
          <div class="px-4 py-3 border-b border-ink-200 flex items-center">
            <h2 class="text-sm font-semibold text-ink-900">
              {{ groupModal.mode === 'add' ? 'New group' : 'Edit group' }}
            </h2>
            <button type="button" @click="groupModal = null" class="ml-auto text-ink-400 hover:text-ink-900" aria-label="Close"><svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('x')" /></button>
          </div>
          <div class="p-4 space-y-3">
            <div class="grid grid-cols-3 gap-3">
              <DeskField label="Code" required>
                <DeskInput v-model="groupForm.code" placeholder="A, B, C…" />
              </DeskField>
              <div class="col-span-2">
                <DeskField label="Name" required>
                  <DeskInput v-model="groupForm.name" placeholder="e.g. Civil Works — RCC" />
                </DeskField>
              </div>
            </div>
          </div>
          <div class="px-4 py-2 border-t border-ink-200 flex items-center justify-end gap-2">
            <button type="button" @click="groupModal = null" class="text-xs text-ink-600 hover:text-ink-900 px-2 py-1">Cancel</button>
            <button type="button" @click="saveGroup" class="desk-save-btn">
              {{ groupModal.mode === 'add' ? 'Create group' : 'Save changes' }}
            </button>
          </div>
        </div>
      </div>

      <!-- ========== Item modal (add + edit) ========== -->
      <div
        v-if="itemModal"
        class="fixed inset-0 bg-ink-900/40 z-[60] flex items-center justify-center p-4"
        @click="itemModal = null"
      >
        <div
          class="bg-white border border-ink-200 shadow-fp-lg w-full max-w-lg"
          style="border-radius: 2px;"
          @click.stop
        >
          <div class="px-4 py-3 border-b border-ink-200 flex items-center">
            <h2 class="text-sm font-semibold text-ink-900">
              {{ itemModal.mode === 'add' ? 'New item' : 'Edit item' }}
            </h2>
            <button type="button" @click="itemModal = null" class="ml-auto text-ink-400 hover:text-ink-900" aria-label="Close"><svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('x')" /></button>
          </div>
          <div class="p-4 space-y-3">
            <div class="grid grid-cols-3 gap-3">
              <DeskField label="Code" required hint="e.g. A.05, B.12">
                <DeskInput v-model="itemForm.code" />
              </DeskField>
              <div class="col-span-2">
                <DeskField label="Unit" required hint="m³, kg, m², nos, lot…">
                  <DeskInput v-model="itemForm.unit" />
                </DeskField>
              </div>
            </div>
            <DeskField label="Description" required>
              <DeskTextarea v-model="itemForm.description" :rows="2" placeholder="What does this line of work include?" />
            </DeskField>
            <div class="grid grid-cols-3 gap-3">
              <DeskField label="Planned qty">
                <DeskInput v-model="itemForm.plannedQty" type="number" />
              </DeskField>
              <DeskField label="Rate (₹)">
                <DeskInput v-model="itemForm.rate" type="number" />
              </DeskField>
              <DeskField label="Planned amount" hint="qty × rate (auto)">
                <div class="desk-input bg-ink-50 text-right tabular-nums">{{ fmtINR(itemPlannedAmountPreview) }}</div>
              </DeskField>
            </div>
            <DeskField label="Link to task" hint="Optional · drives live actuals from task progress">
              <DeskSelect v-model="itemForm.taskId">
                <option :value="null">— Not linked —</option>
                <option v-for="t in availableTasks" :key="t.id" :value="t.id">
                  {{ t.id.slice(-4) }} · {{ t.name }}
                </option>
              </DeskSelect>
            </DeskField>
          </div>
          <div class="px-4 py-2 border-t border-ink-200 flex items-center justify-end gap-2">
            <button type="button" @click="itemModal = null" class="text-xs text-ink-600 hover:text-ink-900 px-2 py-1">Cancel</button>
            <button type="button" @click="saveItem" class="desk-save-btn">
              {{ itemModal.mode === 'add' ? 'Create item' : 'Save changes' }}
            </button>
          </div>
        </div>
      </div>

      <!-- ========== Sub-item modal (add + edit) ========== -->
      <div
        v-if="subItemModal"
        class="fixed inset-0 bg-ink-900/40 z-[60] flex items-center justify-center p-4"
        @click="subItemModal = null"
      >
        <div
          class="bg-white border border-ink-200 shadow-fp-lg w-full max-w-lg"
          style="border-radius: 2px;"
          @click.stop
        >
          <div class="px-4 py-3 border-b border-ink-200 flex items-center">
            <h2 class="text-sm font-semibold text-ink-900">
              {{ subItemModal.mode === 'add' ? 'New sub-item · rate analysis' : 'Edit sub-item' }}
            </h2>
            <button type="button" @click="subItemModal = null" class="ml-auto text-ink-400 hover:text-ink-900" aria-label="Close"><svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('x')" /></button>
          </div>
          <div class="p-4 space-y-3">
            <DeskField label="From Rate Master" hint="Optional · pick to auto-fill description + rate. Updates to the rate master auto-flow to BOQs that use it.">
              <DeskSelect
                :model-value="subItemForm.rateMasterId"
                @update:model-value="v => { subItemForm.rateMasterId = v || null; onRateMasterPick(v) }"
              >
                <option :value="null">— Manual entry —</option>
                <option v-for="rm in rateMasterOptions" :key="rm.id" :value="rm.id">
                  {{ rm.code }} · {{ rm.description }} · ₹{{ rm.currentRate }} per {{ rm.unit }}
                </option>
              </DeskSelect>
            </DeskField>
            <DeskField label="Description" required>
              <DeskInput v-model="subItemForm.description" placeholder="e.g. Mason (skilled), Cement OPC 53, Vibrator needle…" />
            </DeskField>
            <div class="grid grid-cols-3 gap-3">
              <DeskField label="Qty per unit" required :hint="`per ${subItemModal.parentUnit || 'unit'}`">
                <DeskInput v-model="subItemForm.qtyPerUnit" type="number" />
              </DeskField>
              <DeskField label="Rate (₹)">
                <DeskInput v-model="subItemForm.rate" type="number" />
              </DeskField>
              <DeskField label="Amount" hint="qty × rate (auto)">
                <div class="desk-input bg-ink-50 text-right tabular-nums">{{ fmtINR(subItemAmountPreview) }}</div>
              </DeskField>
            </div>
          </div>
          <div class="px-4 py-2 border-t border-ink-200 flex items-center justify-end gap-2">
            <button type="button" @click="subItemModal = null" class="text-xs text-ink-600 hover:text-ink-900 px-2 py-1">Cancel</button>
            <button type="button" @click="saveSubItem" class="desk-save-btn">
              {{ subItemModal.mode === 'add' ? 'Create sub-item' : 'Save changes' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Comments / Attachments stub footer (Frappe Desk convention) -->
      <section class="mt-8 pt-4 border-t border-ink-200">
        <div class="flex items-center gap-6 text-xs text-ink-500 flex-wrap">
          <div class="flex items-center gap-1.5">
            <svg class="w-3.5 h-3.5 text-ink-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('message-circle')" /><span>Comments — <span class="font-medium text-ink-700">0</span></span>
            <span class="text-ink-400 italic ml-1">stub</span>
          </div>
          <div class="flex items-center gap-1.5">
            <svg class="w-3.5 h-3.5 text-ink-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('paperclip')" /><span>Attachments — <span class="font-medium text-ink-700">0</span></span>
            <span class="text-ink-400 italic ml-1">stub</span>
          </div>
          <div class="flex items-center gap-1.5">
            <svg class="w-3.5 h-3.5 text-ink-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('users')" /><span>Prepared by —</span>
            <UserAvatar :user-id="boq.preparedBy" size="xs" />
          </div>
        </div>
      </section>
    </DeskForm>
  </DeskPage>
</template>
