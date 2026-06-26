<script setup>
import { usePageTitle } from "@/composables/usePageTitle";
// BOQ Detail — backend-backed (data adapter + boqApi). The Desk template is kept
// verbatim; only the data layer changed: the local store became adapter reads of
// BOQ + its Group/Item/Sub-Item children (transformed back to the prototype's
// camelCase shape), CRUD became adapter.create/update/remove, and the workflow /
// revision / explode / clone / import / recalc actions call the whitelisted boqApi.

import { computed, ref, watch } from "vue";
import { useRouter, RouterLink } from "vue-router";
import { useDataStore } from "@/stores";
import { createDataAdapter } from "@/data/adapters";
import { useDocTypeList } from "@/composables/useDocTypeList";
import { useConfirm } from "@/composables/useConfirm";
import { showToast } from "@/utils/appToast";
import { parseFrappeError } from "@/utils/frappeError";
import * as boqApi from "@/utils/boqApi";
import StatusBadge from "@/components/StatusBadge.vue";
import UserAvatar from "@/components/UserAvatar.vue";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskTextarea from "@/components/desk/DeskTextarea.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import { fmtINR, fmtCompactINR, fmtDate } from "@/utils/format";
import { getWorkspaceIconPath } from "@/utils/workspaceIcons";

const props = defineProps({ id: { type: String, required: true } });
const router = useRouter();
const adapter = createDataAdapter(useDataStore());
const confirmDialog = useConfirm();

// === Data load: BOQ header + the three child levels ===
const boqResource = adapter.read("BOQ", props.id, { fields: ["*"] });
function childList(doctype, orderBy) {
	return adapter.list(doctype, {
		filters: [["boq", "=", props.id]],
		fields: ["*"],
		pageLength: 0,
		orderBy,
	});
}
const groupsRes = childList("BOQ Group", "idx_order asc");
const itemsRes = childList("BOQ Item", "code asc");
const subsRes = childList("BOQ Sub Item", "creation asc");
function reloadTree() {
	boqResource?.reload?.();
	groupsRes?.reload?.();
	itemsRes?.reload?.();
	subsRes?.reload?.();
}
const rowsOf = (res) => res?.data || [];

const boqDoc = computed(() => boqResource?.doc || null);
const boq = computed(() => {
	const d = boqDoc.value;
	if (!d) return null;
	return {
		id: d.name,
		status: d.status,
		revision: d.revision,
		title: d.title,
		projectId: d.project,
		preparedBy: d.prepared_by,
		preparedDate: d.prepared_date,
		approvedBy: d.approved_by,
		approvedDate: d.approved_date,
		baseRevisionId: d.base_revision,
		sourceScoId: d.source_sco,
	};
});

usePageTitle(() => boq.value?.id);

const projectsRes = useDocTypeList("Project", {
	fields: ["name", "project_name", "custom_project_id"],
	pageLength: 0,
	cache: "buildsuite-boq-projects",
});
const project = computed(() => {
	const pid = boq.value?.projectId;
	if (!pid) return null;
	const p = (projectsRes.data || []).find((x) => x.name === pid);
	return p ? { id: p.name, name: p.project_name || p.name } : { id: pid, name: pid };
});

// Sibling revisions (for baseBoq label) + base-revision items (for compare mode).
const projectBoqsRes = useDocTypeList("BOQ", {
	filters: [["project", "=", props.id ? undefined : ""]],
	fields: ["name", "revision"],
	pageLength: 0,
	auto: false,
});
watch(
	() => boq.value?.projectId,
	(pid) => {
		if (pid) {
			projectBoqsRes.filters = [["project", "=", pid]];
			projectBoqsRes.reload?.();
		}
	},
	{ immediate: true }
);
const baseBoq = computed(() => {
	const bid = boq.value?.baseRevisionId;
	if (!bid) return null;
	const b = (projectBoqsRes.data || []).find((x) => x.name === bid);
	return b ? { id: b.name, revision: b.revision } : { id: bid, revision: "?" };
});
const sourceSco = computed(() => (boq.value?.sourceScoId ? { id: boq.value.sourceScoId } : null));

// Lazily load base-revision items when compare is on.
const baseItems = ref([]);
async function loadBaseItems() {
	const bid = boq.value?.baseRevisionId;
	if (!bid) {
		baseItems.value = [];
		return;
	}
	try {
		const res = adapter.list("BOQ Item", {
			filters: [["boq", "=", bid]],
			fields: ["code", "planned_amount"],
			pageLength: 0,
			auto: false,
		});
		await res.reload?.();
		baseItems.value = res.data || [];
	} catch {
		baseItems.value = [];
	}
}

// === Tree shape (camelCase, matching the template) ===
const groups = computed(() =>
	rowsOf(groupsRes).map((g) => ({
		id: g.name,
		code: g.code,
		name: g.group_name,
		order: g.idx_order,
	}))
);
const allItems = computed(() =>
	rowsOf(itemsRes).map((i) => ({
		id: i.name,
		groupId: i.boq_group,
		code: i.code,
		description: i.description,
		unit: i.unit,
		plannedQty: i.planned_qty,
		rate: i.rate,
		plannedAmount: i.planned_amount,
		actualQty: i.actual_qty,
		actualAmount: i.actual_amount,
		taskId: i.task,
		workPackageId: i.work_package,
		costHead: i.cost_head,
		assemblyId: i.assembly,
		drivingQty: i.driving_qty,
	}))
);
const allSubs = computed(() =>
	rowsOf(subsRes).map((s) => ({
		id: s.name,
		itemId: s.boq_item,
		rateMasterId: s.rate_master,
		description: s.description,
		qtyPerUnit: s.qty_per_unit,
		rate: s.rate,
		amount: s.amount,
	}))
);
function boqItemsByGroup(groupId) {
	return allItems.value.filter((i) => i.groupId === groupId);
}
function boqSubItemsByItem(itemId) {
	return allSubs.value.filter((s) => s.itemId === itemId);
}
const boqItemsByBoq = computed(() => allItems.value);

const totals = computed(() => {
	const planned = allItems.value.reduce((a, i) => a + (i.plannedAmount || 0), 0);
	const actual = allItems.value.reduce((a, i) => a + (i.actualAmount || 0), 0);
	const variance = actual - planned;
	return {
		planned,
		actual,
		variance,
		variancePct: planned ? (variance / planned) * 100 : 0,
		itemCount: allItems.value.length,
	};
});

const expandedGroups = ref({});
const expandedItems = ref({});
const compareMode = ref(false);
watch(compareMode, (on) => {
	if (on) loadBaseItems();
});

function toggleGroup(id) {
	expandedGroups.value[id] = !expandedGroups.value[id];
}
function toggleItem(id) {
	expandedItems.value[id] = !expandedItems.value[id];
}
function expandAll() {
	groups.value.forEach((g) => (expandedGroups.value[g.id] = true));
	allItems.value.forEach((i) => (expandedItems.value[i.id] = true));
}
function collapseAll() {
	expandedGroups.value = {};
	expandedItems.value = {};
}

function variancePill(pct) {
	if (Math.abs(pct) < 0.5) return "text-ink-500";
	return pct > 0 ? "text-danger-700" : "text-success-700";
}
function pctOf(part, whole) {
	return whole ? (part / whole) * 100 : 0;
}
function groupTotals(groupId) {
	const items = boqItemsByGroup(groupId);
	const planned = items.reduce((a, i) => a + (i.plannedAmount || 0), 0);
	const actual = items.reduce((a, i) => a + (i.actualAmount || 0), 0);
	return { planned, actual, count: items.length };
}
function baseAmount(code) {
	if (!baseBoq.value) return null;
	const base = baseItems.value.find((i) => i.code === code);
	return base?.planned_amount ?? null;
}

// === Workflow / advanced actions (boqApi) ===
async function recalculate() {
	try {
		await boqApi.recalculateActuals(boq.value.id);
		reloadTree();
		showToast("Actuals recalculated");
	} catch (err) {
		showToast(parseFrappeError(err).summary ?? "Failed to recalculate", "error");
	}
}
async function submit() {
	const ok = await confirmDialog({
		title: "Submit for approval",
		message: `Submit BOQ ${boq.value.id} for approval?`,
		confirmLabel: "Submit",
	});
	if (!ok) return;
	try {
		await boqApi.submitBoq(boq.value.id);
		reloadTree();
	} catch (err) {
		showToast(parseFrappeError(err).summary ?? "Failed to submit", "error");
	}
}
async function approve() {
	const others = (projectBoqsRes.data || []).filter(
		(b) => b.name !== boq.value.id && b.revision !== boq.value.revision
	);
	void others;
	const ok = await confirmDialog({
		title: "Approve revision",
		message: `Approve revision ${boq.value.revision}? Any other approved revision on this project is superseded.`,
		confirmLabel: "Approve",
	});
	if (!ok) return;
	try {
		await boqApi.approveBoq(boq.value.id);
		reloadTree();
	} catch (err) {
		showToast(parseFrappeError(err).summary ?? "Failed to approve", "error");
	}
}
async function createRevision() {
	const note = window.prompt("Optional: SCO id to link this revision to (or leave blank).", "");
	if (note === null) return;
	try {
		const name = await boqApi.createRevision(boq.value.id, note?.trim() || null);
		if (name) router.push(`/boq/${name}`);
	} catch (err) {
		showToast(parseFrappeError(err).summary ?? "Failed to create revision", "error");
	}
}
async function removeBoq() {
	const ok = await confirmDialog({
		title: "Delete BOQ",
		message: `Delete BOQ ${boq.value.id} and all its rows? This cannot be undone.`,
		confirmLabel: "Delete",
		destructive: true,
	});
	if (!ok) return;
	try {
		await adapter.remove("BOQ", boq.value.id);
		router.push("/boq");
	} catch (err) {
		showToast(parseFrappeError(err).summary ?? "Failed to delete BOQ", "error");
	}
}
async function explode(item) {
	if (!item.assemblyId) {
		showToast("Link an Assembly to this item first.", "error");
		return;
	}
	try {
		await boqApi.explodeItem(item.id);
		reloadTree();
		showToast("Exploded from assembly");
	} catch (err) {
		showToast(parseFrappeError(err).summary ?? "Failed to explode", "error");
	}
}

// === CSV export (client-side, flat tree dump) ===
function csvCell(v) {
	const s = String(v ?? "");
	return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}
function exportCsv() {
	const lines = [];
	lines.push(
		["BOQ", boq.value.id, "Rev", boq.value.revision, "Status", boq.value.status]
			.map(csvCell)
			.join(",")
	);
	lines.push(
		[
			"Type",
			"Code",
			"Description",
			"Unit",
			"Planned Qty",
			"Rate",
			"Planned Amount",
			"Actual Qty",
			"Actual Amount",
			"Work Package",
			"Cost Head",
		]
			.map(csvCell)
			.join(",")
	);
	for (const g of groups.value) {
		lines.push(["Group", g.code, g.name].map(csvCell).join(","));
		for (const it of boqItemsByGroup(g.id)) {
			lines.push(
				[
					"Item",
					it.code,
					it.description,
					it.unit,
					it.plannedQty,
					it.rate,
					it.plannedAmount,
					it.actualQty,
					it.actualAmount,
					it.workPackageId || "",
					it.costHead || "",
				]
					.map(csvCell)
					.join(",")
			);
			for (const si of boqSubItemsByItem(it.id)) {
				lines.push(
					["Sub", "↳", si.description, "", si.qtyPerUnit, si.rate, si.amount]
						.map(csvCell)
						.join(",")
				);
			}
		}
	}
	const blob = new Blob(["﻿" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
	const url = URL.createObjectURL(blob);
	const a = document.createElement("a");
	a.href = url;
	a.download = `${boq.value.id}.csv`;
	a.click();
	URL.revokeObjectURL(url);
}

// === Import Estimate Template ===
const importModal = ref(false);
const importForm = ref({ template: "" });
function openImport() {
	importForm.value = { template: "" };
	importModal.value = true;
}
async function doImport() {
	if (!importForm.value.template) return;
	try {
		await boqApi.importTemplate(boq.value.id, importForm.value.template);
		importModal.value = false;
		reloadTree();
		showToast("Template imported");
	} catch (err) {
		showToast(parseFrappeError(err).summary ?? "Failed to import template", "error");
	}
}

// === Clone (project->project or WP->WP) ===
const cloneModal = ref(false);
const cloneForm = ref({ toProject: "", toWorkPackage: "", fromWorkPackage: "", title: "" });
function openClone() {
	cloneForm.value = { toProject: "", toWorkPackage: "", fromWorkPackage: "", title: "" };
	cloneModal.value = true;
}
async function doClone() {
	const f = cloneForm.value;
	const sameProject = !f.toProject || f.toProject === boq.value.projectId;
	const payload = sameProject
		? {
				from_project: boq.value.projectId,
				to_project: boq.value.projectId,
				from_work_package: f.fromWorkPackage,
				to_work_package: f.toWorkPackage,
		  }
		: {
				from_project: boq.value.projectId,
				to_project: f.toProject,
				to_work_package: f.toWorkPackage || null,
				title: f.title || null,
		  };
	try {
		const res = await boqApi.cloneBoq(payload);
		cloneModal.value = false;
		if (res?.boq && res.boq !== boq.value.id) router.push(`/boq/${res.boq}`);
		else reloadTree();
		showToast("Cloned");
	} catch (err) {
		showToast(parseFrappeError(err).summary ?? "Failed to clone", "error");
	}
}

const canSubmit = computed(() => boq.value?.status === "Draft");
const canApprove = computed(() => boq.value?.status === "Submitted");
const isLocked = computed(
	() => boq.value?.status === "Approved" || boq.value?.status === "Superseded"
);
const isEditable = computed(() => boq.value?.status === "Draft");

// ===== Group add/edit/delete =====
const groupModal = ref(null);
const groupForm = ref({ code: "", name: "" });
function openAddGroup() {
	groupForm.value = { code: "", name: "" };
	groupModal.value = { mode: "add" };
}
function openEditGroup(g) {
	groupForm.value = { code: g.code, name: g.name };
	groupModal.value = { mode: "edit", id: g.id };
}
async function saveGroup() {
	if (!groupForm.value.code.trim() || !groupForm.value.name.trim()) {
		showToast("Code and name are required.", "error");
		return;
	}
	const payload = { code: groupForm.value.code.trim(), group_name: groupForm.value.name.trim() };
	try {
		if (groupModal.value.mode === "add") {
			await adapter.create("BOQ Group", { boq: boq.value.id, ...payload });
		} else {
			await adapter.update("BOQ Group", groupModal.value.id, payload);
		}
		groupModal.value = null;
		reloadTree();
	} catch (err) {
		showToast(parseFrappeError(err).summary ?? "Failed to save group", "error");
	}
}
async function deleteGroupConfirm(g) {
	const items = boqItemsByGroup(g.id);
	const msg = items.length
		? `Delete group "${g.code} — ${g.name}" with ${items.length} item${
				items.length === 1 ? "" : "s"
		  } and their sub-items?`
		: `Delete group "${g.code} — ${g.name}"?`;
	if (
		!(await confirmDialog({
			title: "Delete group",
			message: msg,
			confirmLabel: "Delete",
			destructive: true,
		}))
	)
		return;
	try {
		await adapter.remove("BOQ Group", g.id);
		reloadTree();
	} catch (err) {
		showToast(parseFrappeError(err).summary ?? "Failed to delete group", "error");
	}
}

// ===== Item add/edit/delete =====
const itemModal = ref(null);
const itemForm = ref({
	code: "",
	description: "",
	unit: "",
	plannedQty: 0,
	rate: 0,
	taskId: null,
	workPackageId: null,
	costHead: "",
	assemblyId: null,
});
const availableTasks = computed(() => {
	const pid = boq.value?.projectId;
	return pid
		? (tasksRes.data || []).map((t) => ({ id: t.name, name: t.subject || t.name }))
		: [];
});
const tasksRes = useDocTypeList("Task", {
	filters: [["project", "=", props.id ? undefined : ""]],
	fields: ["name", "subject"],
	pageLength: 0,
	auto: false,
});
watch(
	() => boq.value?.projectId,
	(pid) => {
		if (pid) {
			tasksRes.filters = [["project", "=", pid]];
			tasksRes.reload?.();
		}
	},
	{ immediate: true }
);
const itemPlannedAmountPreview = computed(
	() => (Number(itemForm.value.plannedQty) || 0) * (Number(itemForm.value.rate) || 0)
);
function blankItemForm() {
	return {
		code: "",
		description: "",
		unit: "",
		plannedQty: 0,
		rate: 0,
		taskId: null,
		workPackageId: null,
		costHead: "",
		assemblyId: null,
	};
}
function openAddItem(groupId) {
	itemForm.value = blankItemForm();
	itemModal.value = { mode: "add", groupId };
}
function openEditItem(item) {
	itemForm.value = {
		code: item.code,
		description: item.description,
		unit: item.unit,
		plannedQty: item.plannedQty,
		rate: item.rate,
		taskId: item.taskId,
		workPackageId: item.workPackageId,
		costHead: item.costHead || "",
		assemblyId: item.assemblyId,
	};
	itemModal.value = { mode: "edit", id: item.id };
}
async function saveItem() {
	const f = itemForm.value;
	if (!f.code.trim() || !f.description.trim() || !f.unit) {
		showToast("Code, description, and unit are required.", "error");
		return;
	}
	const payload = {
		code: f.code.trim(),
		description: f.description.trim(),
		unit: f.unit,
		planned_qty: Number(f.plannedQty) || 0,
		rate: Number(f.rate) || 0,
		task: f.taskId || null,
		work_package: f.workPackageId || null,
		cost_head: f.costHead || null,
		assembly: f.assemblyId || null,
	};
	try {
		if (itemModal.value.mode === "add") {
			await adapter.create("BOQ Item", {
				boq: boq.value.id,
				boq_group: itemModal.value.groupId,
				...payload,
			});
		} else {
			await adapter.update("BOQ Item", itemModal.value.id, payload);
		}
		itemModal.value = null;
		reloadTree();
	} catch (err) {
		showToast(parseFrappeError(err).summary ?? "Failed to save item", "error");
	}
}
async function deleteItemConfirm(item) {
	const subs = boqSubItemsByItem(item.id);
	const msg = subs.length
		? `Delete item "${item.code} — ${item.description}" with ${subs.length} sub-item${
				subs.length === 1 ? "" : "s"
		  }?`
		: `Delete item "${item.code} — ${item.description}"?`;
	if (
		!(await confirmDialog({
			title: "Delete item",
			message: msg,
			confirmLabel: "Delete",
			destructive: true,
		}))
	)
		return;
	try {
		await adapter.remove("BOQ Item", item.id);
		reloadTree();
	} catch (err) {
		showToast(parseFrappeError(err).summary ?? "Failed to delete item", "error");
	}
}

// ===== Sub-item add/edit/delete =====
const subItemModal = ref(null);
const subItemForm = ref({ rateMasterId: null, description: "", qtyPerUnit: 0, rate: 0 });
const rateMasterRes = useDocTypeList("Construction Rate Master", {
	fields: ["name", "rate_code", "rate_name", "current_rate", "category"],
	orderBy: "rate_code asc",
	pageLength: 0,
	cache: "buildsuite-boq-rate-master",
});
const rateMasterOptions = computed(() =>
	(rateMasterRes.data || []).map((r) => ({
		id: r.name,
		code: r.rate_code,
		description: r.rate_name,
		currentRate: r.current_rate,
		category: r.category,
	}))
);
function openAddSubItem(item) {
	subItemForm.value = { rateMasterId: null, description: "", qtyPerUnit: 0, rate: 0 };
	subItemModal.value = { mode: "add", itemId: item.id, parentUnit: item.unit };
}
function openEditSubItem(si, item) {
	subItemForm.value = {
		rateMasterId: si.rateMasterId || null,
		description: si.description,
		qtyPerUnit: si.qtyPerUnit,
		rate: si.rate,
	};
	subItemModal.value = { mode: "edit", id: si.id, parentUnit: item.unit };
}
function onRateMasterPick(rateMasterId) {
	if (!rateMasterId) return;
	const rm = rateMasterOptions.value.find((r) => r.id === rateMasterId);
	if (rm) {
		subItemForm.value.description = rm.description;
		subItemForm.value.rate = rm.currentRate;
	}
}
const subItemAmountPreview = computed(
	() => (Number(subItemForm.value.qtyPerUnit) || 0) * (Number(subItemForm.value.rate) || 0)
);
async function saveSubItem() {
	const f = subItemForm.value;
	if (!f.description.trim() || Number(f.qtyPerUnit) <= 0) {
		showToast("Description and a non-zero quantity per unit are required.", "error");
		return;
	}
	const payload = {
		rate_master: f.rateMasterId || null,
		description: f.description.trim(),
		qty_per_unit: Number(f.qtyPerUnit) || 0,
		rate: Number(f.rate) || 0,
	};
	try {
		if (subItemModal.value.mode === "add") {
			await adapter.create("BOQ Sub Item", {
				boq: boq.value.id,
				boq_item: subItemModal.value.itemId,
				...payload,
			});
		} else {
			await adapter.update("BOQ Sub Item", subItemModal.value.id, payload);
		}
		subItemModal.value = null;
		reloadTree();
	} catch (err) {
		showToast(parseFrappeError(err).summary ?? "Failed to save sub-item", "error");
	}
}
async function deleteSubItemConfirm(si) {
	if (
		!(await confirmDialog({
			title: "Delete sub-item",
			message: `Delete sub-item "${si.description}"?`,
			confirmLabel: "Delete",
			destructive: true,
		}))
	)
		return;
	try {
		await adapter.remove("BOQ Sub Item", si.id);
		reloadTree();
	} catch (err) {
		showToast(parseFrappeError(err).summary ?? "Failed to delete sub-item", "error");
	}
}

// Primary action dispatcher — Submit when Draft, Approve when Submitted.
const showPrimary = computed(() => canSubmit.value || canApprove.value);
const primaryLabel = computed(() =>
	canSubmit.value ? "Submit for approval" : canApprove.value ? "Approve" : ""
);
function primaryAction() {
	if (canSubmit.value) submit();
	else if (canApprove.value) approve();
}

const breadcrumbs = computed(() => {
	const out = [
		{ label: "BuildSuite Core", to: "/" },
		{ label: "BOQ", to: "/boq" },
	];
	if (project.value)
		out.push({ label: project.value.name, to: `/projects/${project.value.id}` });
	out.push({ label: boq.value?.id || props.id });
	return out;
});
</script>

<template>
	<div v-if="!boq" class="px-6 py-12 text-center text-ink-500">
		<div class="text-sm">
			BOQ <span class="font-mono">{{ id }}</span> not found.
		</div>
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
							:class="
								compareMode ? 'bg-brand-50 border-brand-300 text-brand-700' : ''
							"
							@click="compareMode = !compareMode"
						>
							{{
								compareMode
									? "✓ Comparing R" + baseBoq.revision
									: "Compare to R" + baseBoq.revision
							}}
						</button>

						<button
							type="button"
							class="text-xs px-2 py-1 border border-ink-200 bg-white hover:bg-ink-50"
							style="border-radius: 2px"
							@click="recalculate"
						>
							↻ Recalc actuals
						</button>

						<button
							type="button"
							class="text-xs px-2 py-1 border border-ink-200 bg-white hover:bg-ink-50"
							style="border-radius: 2px"
							@click="createRevision"
						>
							+ Revision
						</button>

						<button
							type="button"
							class="text-xs px-2 py-1 border border-ink-200 bg-white hover:bg-ink-50"
							style="border-radius: 2px"
							@click="exportCsv"
						>
							⬇ Export CSV
						</button>

						<button
							v-if="isEditable"
							type="button"
							class="text-xs px-2 py-1 border border-ink-200 bg-white hover:bg-ink-50"
							style="border-radius: 2px"
							@click="openImport"
						>
							Import Template…
						</button>

						<button
							type="button"
							class="text-xs px-2 py-1 border border-ink-200 bg-white hover:bg-ink-50"
							style="border-radius: 2px"
							@click="openClone"
						>
							Clone…
						</button>

						<button
							v-if="!isLocked"
							type="button"
							class="text-xs px-2 py-1 border border-ink-200 bg-white hover:bg-ink-50"
							style="border-radius: 2px; color: #b91c1c"
							@click="removeBoq"
						>
							Delete
						</button>
					</template>
				</DeskActionBar>
			</template>

			<!-- KPI strip — Desk density: 6 small cards, modest numbers -->
			<div class="grid grid-cols-2 md:grid-cols-6 gap-2 mb-4">
				<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
						Revision
					</div>
					<div class="text-base font-semibold text-ink-900 mt-0.5">
						R{{ boq.revision }}
					</div>
					<div v-if="baseBoq" class="text-[10px] text-ink-500 mt-0.5">
						from
						<DeskLink :to="`/boq/${baseBoq.id}`" class="font-mono"
							>R{{ baseBoq.revision }}</DeskLink
						>
					</div>
					<div v-else class="text-[10px] text-ink-400 mt-0.5">original</div>
				</div>
				<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
						Groups · Items
					</div>
					<div class="text-base font-semibold text-ink-900 mt-0.5">
						{{ groups.length }} · {{ totals.itemCount }}
					</div>
					<div class="text-[10px] text-ink-500 mt-0.5">across this BOQ</div>
				</div>
				<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
						Planned
					</div>
					<div class="text-base font-semibold text-ink-900 mt-0.5 tabular-nums">
						{{ fmtCompactINR(totals.planned) }}
					</div>
					<div class="text-[10px] text-ink-500 mt-0.5 tabular-nums">
						{{ fmtINR(totals.planned) }}
					</div>
				</div>
				<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
						Actual
					</div>
					<div class="text-base font-semibold text-ink-700 mt-0.5 tabular-nums">
						{{ fmtCompactINR(totals.actual) }}
					</div>
					<div class="text-[10px] text-ink-500 mt-0.5">
						{{ pctOf(totals.actual, totals.planned).toFixed(1) }}% of plan
					</div>
				</div>
				<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
						Variance
					</div>
					<div
						class="text-base font-semibold mt-0.5 tabular-nums"
						:class="variancePill(totals.variancePct)"
					>
						{{ totals.variancePct > 0 ? "+" : "" }}{{ totals.variancePct.toFixed(1) }}%
					</div>
					<div class="text-[10px] text-ink-500 mt-0.5 tabular-nums">
						{{ fmtCompactINR(totals.variance) }} delta
					</div>
				</div>
				<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
						Prepared
					</div>
					<div class="flex items-center gap-1 mt-1">
						<UserAvatar :user-id="boq.preparedBy" size="xs" />
						<span class="text-[11px] text-ink-500">{{
							fmtDate(boq.preparedDate)
						}}</span>
					</div>
					<div v-if="boq.approvedBy" class="flex items-center gap-1 mt-1">
						<UserAvatar :user-id="boq.approvedBy" size="xs" />
						<span class="text-[11px] text-success-700">{{
							fmtDate(boq.approvedDate)
						}}</span>
					</div>
					<div v-else class="text-[10px] text-ink-400 mt-1">awaiting approval</div>
				</div>
			</div>

			<!-- Toolbar above the tree -->
			<div class="flex items-center gap-2 mb-1.5">
				<button type="button" @click="expandAll" class="desk-link text-xs">
					Expand all
				</button>
				<span class="text-ink-300 text-xs">·</span>
				<button type="button" @click="collapseAll" class="desk-link text-xs">
					Collapse all
				</button>
				<div v-if="compareMode && baseBoq" class="ml-2 text-[11px] text-ink-500">
					Δ vs R{{ baseBoq.revision }} shown on each item row
				</div>
				<div class="ml-auto flex items-center gap-2">
					<span v-if="!isEditable" class="text-[11px] text-ink-400 italic">
						{{ boq.status }} — read-only · use
						<button type="button" @click="createRevision" class="desk-link">
							+ Revision
						</button>
						to make changes
					</span>
					<button
						v-if="isEditable"
						type="button"
						class="desk-save-btn"
						@click="openAddGroup"
					>
						+ Add Group
					</button>
				</div>
			</div>

			<!-- The 3-level tree — Desk styling -->
			<div class="bg-white border border-ink-200 overflow-hidden" style="border-radius: 2px">
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
						<div class="px-2 text-ink-500 text-xs">
							{{ expandedGroups[g.id] ? "▾" : "▸" }}
						</div>
						<div class="px-3 py-2 font-mono text-xs text-ink-700">{{ g.code }}</div>
						<div class="px-3 py-2 text-sm font-semibold text-ink-900">
							{{ g.name }}
						</div>
						<div></div>
						<div></div>
						<div class="px-3 py-2 text-right text-[11px] text-ink-500">
							{{ groupTotals(g.id).count }} items
						</div>
						<div
							class="px-3 py-2 text-right tabular-nums text-sm font-medium text-ink-900"
						>
							{{ fmtCompactINR(groupTotals(g.id).planned) }}
						</div>
						<div class="px-3 py-2 text-right tabular-nums text-sm text-ink-700">
							{{ fmtCompactINR(groupTotals(g.id).actual) }}
						</div>
						<div
							class="px-3 py-2 text-right text-sm tabular-nums font-medium"
							:class="
								variancePill(
									((groupTotals(g.id).actual - groupTotals(g.id).planned) /
										(groupTotals(g.id).planned || 1)) *
										100
								)
							"
						>
							{{
								groupTotals(g.id).planned
									? (
											((groupTotals(g.id).actual -
												groupTotals(g.id).planned) /
												groupTotals(g.id).planned) *
											100
									  ).toFixed(1)
									: "0.0"
							}}%
						</div>
						<div></div>

						<!-- Edit / Delete (hover-visible, only when BOQ is Draft) -->
						<div
							v-if="isEditable"
							class="absolute right-1 top-1/2 -translate-y-1/2 opacity-0 group-hover/row:opacity-100 transition-opacity flex bg-white border border-ink-200 shadow-fp-sm"
							style="border-radius: 2px"
						>
							<button
								type="button"
								@click.stop="openEditGroup(g)"
								class="px-1.5 py-0.5 text-xs hover:bg-ink-50"
								title="Edit group"
							>
								<svg
									class="w-3.5 h-3.5"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="1.8"
									stroke-linecap="round"
									stroke-linejoin="round"
									aria-hidden="true"
									v-html="getWorkspaceIconPath('pencil')"
								/>
							</button>
							<button
								type="button"
								@click.stop="deleteGroupConfirm(g)"
								class="px-1.5 py-0.5 text-xs text-danger-700 hover:bg-danger-50"
								title="Delete group"
							>
								<svg
									class="w-3.5 h-3.5"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="1.8"
									stroke-linecap="round"
									stroke-linejoin="round"
									aria-hidden="true"
									v-html="getWorkspaceIconPath('trash')"
								/>
							</button>
						</div>
					</div>

					<!-- Items inside group -->
					<template v-if="expandedGroups[g.id]">
						<template v-for="item in boqItemsByGroup(g.id)" :key="item.id">
							<div
								class="relative group/row grid items-center border-b border-ink-100 hover:bg-brand-50 cursor-pointer"
								:style="treeGridStyle"
								@click="toggleItem(item.id)"
							>
								<!-- Edit / Delete (hover-visible, only when BOQ is Draft) -->
								<div
									v-if="isEditable"
									class="absolute right-1 top-1/2 -translate-y-1/2 opacity-0 group-hover/row:opacity-100 transition-opacity flex bg-white border border-ink-200 shadow-fp-sm z-10"
									style="border-radius: 2px"
								>
									<button
										v-if="item.assemblyId"
										type="button"
										@click.stop="explode(item)"
										class="px-1.5 py-0.5 text-xs text-brand-700 hover:bg-brand-50"
										title="Explode from assembly into sub-items"
									>
										⚡
									</button>
									<button
										type="button"
										@click.stop="openEditItem(item)"
										class="px-1.5 py-0.5 text-xs hover:bg-ink-50"
										title="Edit item"
									>
										<svg
											class="w-3.5 h-3.5"
											viewBox="0 0 24 24"
											fill="none"
											stroke="currentColor"
											stroke-width="1.8"
											stroke-linecap="round"
											stroke-linejoin="round"
											aria-hidden="true"
											v-html="getWorkspaceIconPath('pencil')"
										/>
									</button>
									<button
										type="button"
										@click.stop="deleteItemConfirm(item)"
										class="px-1.5 py-0.5 text-xs text-danger-700 hover:bg-danger-50"
										title="Delete item"
									>
										<svg
											class="w-3.5 h-3.5"
											viewBox="0 0 24 24"
											fill="none"
											stroke="currentColor"
											stroke-width="1.8"
											stroke-linecap="round"
											stroke-linejoin="round"
											aria-hidden="true"
											v-html="getWorkspaceIconPath('trash')"
										/>
									</button>
								</div>
								<div class="px-2 text-ink-400 text-[10px]">
									{{
										boqSubItemsByItem(item.id).length
											? expandedItems[item.id]
												? "▾"
												: "▸"
											: "·"
									}}
								</div>
								<div class="px-3 py-1.5 font-mono text-xs text-ink-700">
									{{ item.code }}
								</div>
								<div class="px-3 py-1.5 text-sm text-ink-800">
									{{ item.description }}
									<!-- LEFT AS-IS per prompt (Phase-5 prelude): Δ chip uses brand-tinted danger/success styling -->
									<span
										v-if="
											compareMode &&
											baseAmount(item.code) !== null &&
											baseAmount(item.code) !== item.plannedAmount
										"
										class="ml-2 text-[10px] px-1 py-0.5 rounded font-medium"
										:class="
											item.plannedAmount > baseAmount(item.code)
												? 'bg-danger-50 text-danger-700'
												: 'bg-success-50 text-success-700'
										"
										>Δ
										{{ item.plannedAmount > baseAmount(item.code) ? "+" : ""
										}}{{
											fmtCompactINR(
												item.plannedAmount - baseAmount(item.code)
											)
										}}</span
									>
								</div>
								<div class="px-3 py-1.5 text-xs text-ink-600">{{ item.unit }}</div>
								<div
									class="px-3 py-1.5 text-right tabular-nums text-sm text-ink-700"
								>
									{{ item.plannedQty.toLocaleString("en-IN") }}
								</div>
								<div
									class="px-3 py-1.5 text-right tabular-nums text-sm text-ink-700"
								>
									{{ item.rate.toLocaleString("en-IN") }}
								</div>
								<div
									class="px-3 py-1.5 text-right tabular-nums text-sm text-ink-900"
								>
									{{ fmtCompactINR(item.plannedAmount) }}
								</div>
								<div class="px-3 py-1.5">
									<div class="flex flex-col items-end">
										<span class="tabular-nums text-sm text-ink-700">{{
											fmtCompactINR(item.actualAmount)
										}}</span>
										<div
											class="w-full h-1 bg-ink-100 overflow-hidden mt-1"
											style="border-radius: 2px"
										>
											<div
												class="h-full"
												:class="
													item.actualAmount > item.plannedAmount
														? 'bg-danger-500'
														: item.actualAmount >
														  item.plannedAmount * 0.9
														? 'bg-warning-500'
														: 'bg-success-500'
												"
												:style="`width: ${Math.min(
													100,
													pctOf(item.actualAmount, item.plannedAmount)
												).toFixed(1)}%`"
											></div>
										</div>
									</div>
								</div>
								<div
									class="px-3 py-1.5 text-right tabular-nums text-sm"
									:class="
										variancePill(
											((item.actualAmount - item.plannedAmount) /
												(item.plannedAmount || 1)) *
												100
										)
									"
								>
									{{
										item.plannedAmount
											? (
													((item.actualAmount - item.plannedAmount) /
														item.plannedAmount) *
													100
											  ).toFixed(1)
											: "0.0"
									}}%
								</div>
								<div class="px-3 py-1.5 text-center">
									<DeskLink
										v-if="item.taskId"
										:to="`/tasks/${item.taskId}`"
										@click.stop
										class="text-[10px] font-mono"
										>{{ item.taskId.slice(-4) }}</DeskLink
									>
									<span v-else class="text-[10px] text-ink-300">—</span>
								</div>
							</div>

							<!-- Sub-items: rate analysis. Indented, smaller, Rate Master links Desk-blue. -->
							<template v-if="expandedItems[item.id]">
								<div
									v-for="si in boqSubItemsByItem(item.id)"
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
											>{{ si.rateMasterId }}</DeskLink
										>
									</div>
									<div></div>
									<div
										class="px-3 py-1 text-right tabular-nums text-xs text-ink-500"
									>
										{{ si.qtyPerUnit }}
									</div>
									<div
										class="px-3 py-1 text-right tabular-nums text-xs text-ink-500"
									>
										{{ si.rate.toLocaleString("en-IN") }}
									</div>
									<div
										class="px-3 py-1 text-right tabular-nums text-xs text-ink-700"
									>
										{{ fmtINR(si.amount) }}
									</div>
									<div class="px-3 py-1 text-right text-[10px] text-ink-400">
										per {{ item.unit }}
									</div>
									<div></div>
									<div></div>

									<!-- Edit / Delete (hover-visible) -->
									<div
										v-if="isEditable"
										class="absolute right-1 top-1/2 -translate-y-1/2 opacity-0 group-hover/row:opacity-100 transition-opacity flex bg-white border border-ink-200 shadow-fp-sm z-10"
										style="border-radius: 2px"
									>
										<button
											type="button"
											@click.stop="openEditSubItem(si, item)"
											class="px-1.5 py-0.5 text-xs hover:bg-ink-50"
											title="Edit sub-item"
										>
											<svg
												class="w-3.5 h-3.5"
												viewBox="0 0 24 24"
												fill="none"
												stroke="currentColor"
												stroke-width="1.8"
												stroke-linecap="round"
												stroke-linejoin="round"
												aria-hidden="true"
												v-html="getWorkspaceIconPath('pencil')"
											/>
										</button>
										<button
											type="button"
											@click.stop="deleteSubItemConfirm(si)"
											class="px-1.5 py-0.5 text-xs text-danger-700 hover:bg-danger-50"
											title="Delete sub-item"
										>
											<svg
												class="w-3.5 h-3.5"
												viewBox="0 0 24 24"
												fill="none"
												stroke="currentColor"
												stroke-width="1.8"
												stroke-linecap="round"
												stroke-linejoin="round"
												aria-hidden="true"
												v-html="getWorkspaceIconPath('trash')"
											/>
										</button>
									</div>
								</div>
								<div
									v-if="!boqSubItemsByItem(item.id).length"
									class="grid items-center border-b border-ink-50 bg-ink-50/40 text-[11px] text-ink-400 italic"
									:style="treeGridStyle"
								>
									<div></div>
									<div></div>
									<div class="px-3 py-1 pl-10">
										No rate analysis recorded for this item.
									</div>
									<div></div>
									<div></div>
									<div></div>
									<div></div>
									<div></div>
									<div></div>
									<div></div>
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
									<div
										class="px-3 py-1 pl-10 text-[11px] text-brand-700 font-medium"
									>
										+ Add sub-item to {{ item.code }}
									</div>
									<div></div>
									<div></div>
									<div></div>
									<div></div>
									<div></div>
									<div></div>
									<div></div>
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
							<div class="px-3 py-1.5 text-xs text-brand-700 font-medium">
								+ Add item to {{ g.code }} — {{ g.name }}
							</div>
							<div></div>
							<div></div>
							<div></div>
							<div></div>
							<div></div>
							<div></div>
							<div></div>
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
					>
						+ Add the first group
					</button>
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
					style="border-radius: 2px"
					@click.stop
				>
					<div class="px-4 py-3 border-b border-ink-200 flex items-center">
						<h2 class="text-sm font-semibold text-ink-900">
							{{ groupModal.mode === "add" ? "New group" : "Edit group" }}
						</h2>
						<button
							type="button"
							@click="groupModal = null"
							class="ml-auto text-ink-400 hover:text-ink-900"
							aria-label="Close"
						>
							<svg
								class="w-4 h-4"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="1.8"
								stroke-linecap="round"
								stroke-linejoin="round"
								aria-hidden="true"
								v-html="getWorkspaceIconPath('x')"
							/>
						</button>
					</div>
					<div class="p-4 space-y-3">
						<div class="grid grid-cols-3 gap-3">
							<DeskField label="Code" required>
								<DeskInput v-model="groupForm.code" placeholder="A, B, C…" />
							</DeskField>
							<div class="col-span-2">
								<DeskField label="Name" required>
									<DeskInput
										v-model="groupForm.name"
										placeholder="e.g. Civil Works — RCC"
									/>
								</DeskField>
							</div>
						</div>
					</div>
					<div
						class="px-4 py-2 border-t border-ink-200 flex items-center justify-end gap-2"
					>
						<button
							type="button"
							@click="groupModal = null"
							class="text-xs text-ink-600 hover:text-ink-900 px-2 py-1"
						>
							Cancel
						</button>
						<button type="button" @click="saveGroup" class="desk-save-btn">
							{{ groupModal.mode === "add" ? "Create group" : "Save changes" }}
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
					style="border-radius: 2px"
					@click.stop
				>
					<div class="px-4 py-3 border-b border-ink-200 flex items-center">
						<h2 class="text-sm font-semibold text-ink-900">
							{{ itemModal.mode === "add" ? "New item" : "Edit item" }}
						</h2>
						<button
							type="button"
							@click="itemModal = null"
							class="ml-auto text-ink-400 hover:text-ink-900"
							aria-label="Close"
						>
							<svg
								class="w-4 h-4"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="1.8"
								stroke-linecap="round"
								stroke-linejoin="round"
								aria-hidden="true"
								v-html="getWorkspaceIconPath('x')"
							/>
						</button>
					</div>
					<div class="p-4 space-y-3">
						<div class="grid grid-cols-3 gap-3">
							<DeskField label="Code" required hint="e.g. A.05, B.12">
								<DeskInput v-model="itemForm.code" />
							</DeskField>
							<div class="col-span-2">
								<DeskField label="Unit" required>
									<DeskLinkPicker
										v-model="itemForm.unit"
										doctype="UOM"
										label-field="name"
										value-field="name"
										:search-fields="['name']"
										placeholder="m³, kg, nos…"
									/>
								</DeskField>
							</div>
						</div>
						<DeskField label="Description" required>
							<DeskTextarea
								v-model="itemForm.description"
								:rows="2"
								placeholder="What does this line of work include?"
							/>
						</DeskField>
						<div class="grid grid-cols-3 gap-3">
							<DeskField label="Planned qty">
								<DeskInput v-model="itemForm.plannedQty" type="number" />
							</DeskField>
							<DeskField label="Rate (₹)">
								<DeskInput v-model="itemForm.rate" type="number" />
							</DeskField>
							<DeskField label="Planned amount" hint="qty × rate (auto)">
								<div class="desk-input bg-ink-50 text-right tabular-nums">
									{{ fmtINR(itemPlannedAmountPreview) }}
								</div>
							</DeskField>
						</div>
						<DeskField
							label="Link to task"
							hint="Optional · drives live actuals from task progress"
						>
							<DeskSelect v-model="itemForm.taskId">
								<option :value="null">— Not linked —</option>
								<option v-for="t in availableTasks" :key="t.id" :value="t.id">
									{{ t.id.slice(-4) }} · {{ t.name }}
								</option>
							</DeskSelect>
						</DeskField>
						<div class="grid grid-cols-3 gap-3">
							<DeskField label="Work Package" hint="Optional · per-WP rollup">
								<DeskLinkPicker
									v-model="itemForm.workPackageId"
									doctype="Work Package"
									label-field="work_package_name"
									value-field="name"
									:search-fields="['work_package_name', 'code', 'name']"
									placeholder="— None —"
								/>
							</DeskField>
							<DeskField label="Cost head">
								<DeskSelect v-model="itemForm.costHead">
									<option value="">— None —</option>
									<option>Material</option>
									<option>Labour</option>
									<option>Equipment</option>
									<option>Subcontract</option>
									<option>Preliminaries</option>
									<option>Other</option>
								</DeskSelect>
							</DeskField>
							<DeskField label="Assembly" hint="Then ‘Explode’ on the row">
								<DeskLinkPicker
									v-model="itemForm.assemblyId"
									doctype="Assembly"
									label-field="assembly_name"
									value-field="name"
									:search-fields="['assembly_code', 'assembly_name', 'name']"
									placeholder="— None —"
								/>
							</DeskField>
						</div>
					</div>
					<div
						class="px-4 py-2 border-t border-ink-200 flex items-center justify-end gap-2"
					>
						<button
							type="button"
							@click="itemModal = null"
							class="text-xs text-ink-600 hover:text-ink-900 px-2 py-1"
						>
							Cancel
						</button>
						<button type="button" @click="saveItem" class="desk-save-btn">
							{{ itemModal.mode === "add" ? "Create item" : "Save changes" }}
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
					style="border-radius: 2px"
					@click.stop
				>
					<div class="px-4 py-3 border-b border-ink-200 flex items-center">
						<h2 class="text-sm font-semibold text-ink-900">
							{{
								subItemModal.mode === "add"
									? "New sub-item · rate analysis"
									: "Edit sub-item"
							}}
						</h2>
						<button
							type="button"
							@click="subItemModal = null"
							class="ml-auto text-ink-400 hover:text-ink-900"
							aria-label="Close"
						>
							<svg
								class="w-4 h-4"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="1.8"
								stroke-linecap="round"
								stroke-linejoin="round"
								aria-hidden="true"
								v-html="getWorkspaceIconPath('x')"
							/>
						</button>
					</div>
					<div class="p-4 space-y-3">
						<DeskField
							label="From Rate Master"
							hint="Optional · pick to auto-fill description + rate. Updates to the rate master auto-flow to BOQs that use it."
						>
							<DeskSelect
								:model-value="subItemForm.rateMasterId"
								@update:model-value="
									(v) => {
										subItemForm.rateMasterId = v || null;
										onRateMasterPick(v);
									}
								"
							>
								<option :value="null">— Manual entry —</option>
								<option
									v-for="rm in rateMasterOptions"
									:key="rm.id"
									:value="rm.id"
								>
									{{ rm.code }} · {{ rm.description }} · ₹{{
										rm.currentRate
									}}
									per {{ rm.unit }}
								</option>
							</DeskSelect>
						</DeskField>
						<DeskField label="Description" required>
							<DeskInput
								v-model="subItemForm.description"
								placeholder="e.g. Mason (skilled), Cement OPC 53, Vibrator needle…"
							/>
						</DeskField>
						<div class="grid grid-cols-3 gap-3">
							<DeskField
								label="Qty per unit"
								required
								:hint="`per ${subItemModal.parentUnit || 'unit'}`"
							>
								<DeskInput v-model="subItemForm.qtyPerUnit" type="number" />
							</DeskField>
							<DeskField label="Rate (₹)">
								<DeskInput v-model="subItemForm.rate" type="number" />
							</DeskField>
							<DeskField label="Amount" hint="qty × rate (auto)">
								<div class="desk-input bg-ink-50 text-right tabular-nums">
									{{ fmtINR(subItemAmountPreview) }}
								</div>
							</DeskField>
						</div>
					</div>
					<div
						class="px-4 py-2 border-t border-ink-200 flex items-center justify-end gap-2"
					>
						<button
							type="button"
							@click="subItemModal = null"
							class="text-xs text-ink-600 hover:text-ink-900 px-2 py-1"
						>
							Cancel
						</button>
						<button type="button" @click="saveSubItem" class="desk-save-btn">
							{{ subItemModal.mode === "add" ? "Create sub-item" : "Save changes" }}
						</button>
					</div>
				</div>
			</div>

			<!-- ========== Import template modal ========== -->
			<div
				v-if="importModal"
				class="fixed inset-0 bg-ink-900/40 z-[60] flex items-center justify-center p-4"
				@click="importModal = false"
			>
				<div
					class="bg-white border border-ink-200 shadow-fp-lg w-full max-w-md"
					style="border-radius: 2px"
					@click.stop
				>
					<div class="px-4 py-3 border-b border-ink-200 flex items-center">
						<h2 class="text-sm font-semibold text-ink-900">Import from template</h2>
						<button
							type="button"
							@click="importModal = false"
							class="ml-auto text-ink-400 hover:text-ink-900"
						>
							✕
						</button>
					</div>
					<div class="p-4 space-y-3">
						<DeskField label="Estimate template" required>
							<DeskLinkPicker
								v-model="importForm.template"
								doctype="Estimate Template"
								label-field="template_name"
								value-field="name"
								:search-fields="['template_code', 'template_name', 'name']"
								placeholder="Pick a template"
							/>
						</DeskField>
						<p class="text-[11px] text-ink-500">
							Adds the template's rows to this BOQ. Assembly lines explode into
							sub-items.
						</p>
					</div>
					<div
						class="px-4 py-2 border-t border-ink-200 flex items-center justify-end gap-2"
					>
						<button
							type="button"
							@click="importModal = false"
							class="text-xs text-ink-600 hover:text-ink-900 px-2 py-1"
						>
							Cancel
						</button>
						<button type="button" @click="doImport" class="desk-save-btn">
							Import
						</button>
					</div>
				</div>
			</div>

			<!-- ========== Clone modal ========== -->
			<div
				v-if="cloneModal"
				class="fixed inset-0 bg-ink-900/40 z-[60] flex items-center justify-center p-4"
				@click="cloneModal = false"
			>
				<div
					class="bg-white border border-ink-200 shadow-fp-lg w-full max-w-md"
					style="border-radius: 2px"
					@click.stop
				>
					<div class="px-4 py-3 border-b border-ink-200 flex items-center">
						<h2 class="text-sm font-semibold text-ink-900">Clone BOQ</h2>
						<button
							type="button"
							@click="cloneModal = false"
							class="ml-auto text-ink-400 hover:text-ink-900"
						>
							✕
						</button>
					</div>
					<div class="p-4 space-y-3">
						<DeskField
							label="To project"
							hint="Leave blank to clone within this project (WP → WP)."
						>
							<DeskLinkPicker
								v-model="cloneForm.toProject"
								doctype="Project"
								label-field="project_name"
								value-field="name"
								:search-fields="['project_name', 'custom_project_id', 'name']"
								placeholder="— Same project —"
							/>
						</DeskField>
						<div
							v-if="!cloneForm.toProject || cloneForm.toProject === boq.projectId"
							class="grid grid-cols-2 gap-3"
						>
							<DeskField label="From WP" required>
								<DeskLinkPicker
									v-model="cloneForm.fromWorkPackage"
									doctype="Work Package"
									label-field="work_package_name"
									value-field="name"
									:search-fields="['work_package_name', 'code', 'name']"
									:filters="[['project', '=', boq.projectId]]"
									placeholder="Source WP"
								/>
							</DeskField>
							<DeskField label="To WP" required>
								<DeskLinkPicker
									v-model="cloneForm.toWorkPackage"
									doctype="Work Package"
									label-field="work_package_name"
									value-field="name"
									:search-fields="['work_package_name', 'code', 'name']"
									:filters="[['project', '=', boq.projectId]]"
									placeholder="Target WP"
								/>
							</DeskField>
						</div>
						<DeskField v-else label="Title">
							<DeskInput v-model="cloneForm.title" placeholder="Cloned BOQ title" />
						</DeskField>
					</div>
					<div
						class="px-4 py-2 border-t border-ink-200 flex items-center justify-end gap-2"
					>
						<button
							type="button"
							@click="cloneModal = false"
							class="text-xs text-ink-600 hover:text-ink-900 px-2 py-1"
						>
							Cancel
						</button>
						<button type="button" @click="doClone" class="desk-save-btn">Clone</button>
					</div>
				</div>
			</div>

			<!-- Comments / Attachments stub footer (Frappe Desk convention) -->
			<section class="mt-8 pt-4 border-t border-ink-200">
				<div class="flex items-center gap-6 text-xs text-ink-500 flex-wrap">
					<div class="flex items-center gap-1.5">
						<svg
							class="w-3.5 h-3.5 text-ink-500"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="1.8"
							stroke-linecap="round"
							stroke-linejoin="round"
							aria-hidden="true"
							v-html="getWorkspaceIconPath('message-circle')"
						/><span>Comments — <span class="font-medium text-ink-700">0</span></span>
						<span class="text-ink-400 italic ml-1">stub</span>
					</div>
					<div class="flex items-center gap-1.5">
						<svg
							class="w-3.5 h-3.5 text-ink-500"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="1.8"
							stroke-linecap="round"
							stroke-linejoin="round"
							aria-hidden="true"
							v-html="getWorkspaceIconPath('paperclip')"
						/><span
							>Attachments — <span class="font-medium text-ink-700">0</span></span
						>
						<span class="text-ink-400 italic ml-1">stub</span>
					</div>
					<div class="flex items-center gap-1.5">
						<svg
							class="w-3.5 h-3.5 text-ink-500"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="1.8"
							stroke-linecap="round"
							stroke-linejoin="round"
							aria-hidden="true"
							v-html="getWorkspaceIconPath('users')"
						/><span>Prepared by —</span>
						<UserAvatar :user-id="boq.preparedBy" size="xs" />
					</div>
				</div>
			</section>
		</DeskForm>
	</DeskPage>
</template>
