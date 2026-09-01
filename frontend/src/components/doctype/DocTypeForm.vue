<script setup>
// Generic, meta-driven form for an arbitrary DocType. Renders each field by its
// fieldtype via the shared DocTypeFieldControl, honouring reqd / read_only /
// hidden / depends_on, plus full-width child-table grids (DocTypeChildTable) and
// Dynamic Links. For submittable DocTypes the action bar follows docstatus:
// Draft → Save / Submit / Delete; Submitted → Cancel; Cancelled → Amend / Delete.
import { computed, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useDoctypeMeta } from "@/composables/useDoctypeMeta";
import {
	getRecord,
	insertRecord,
	saveRecord,
	deleteRecord,
	submitRecord,
	cancelRecord,
	amendRecord,
} from "@/data/doctypeRecordApi";
import { getDoctypePermissions } from "@/data/workspaceSettingApi";
import { useConfirm } from "@/composables/useConfirm";
import { showToast } from "@/utils/appToast";
import StatusBadge from "@/components/StatusBadge.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DocTypeFieldControl from "@/components/doctype/DocTypeFieldControl.vue";
import DocTypeChildTable from "@/components/doctype/DocTypeChildTable.vue";

const props = defineProps({
	doctype: { type: String, required: true },
	name: { type: String, default: "" },
});

const router = useRouter();
const confirmDialog = useConfirm();
const { meta, loading: metaLoading } = useDoctypeMeta(props.doctype);

const form = reactive({ doctype: props.doctype });
const loading = ref(false);
const busy = ref(false);
const formError = ref("");
const perms = ref({ read: true, write: true, create: true, delete: true, submit: true, cancel: true });

const isEdit = computed(() => !!props.name);
const docstatus = computed(() => Number(form.docstatus || 0));
const submittable = computed(() => !!meta.value?.is_submittable);
const isDraft = computed(() => isEdit.value && docstatus.value === 0);
const isSubmitted = computed(() => isEdit.value && docstatus.value === 1);
const isCancelled = computed(() => isEdit.value && docstatus.value === 2);
// A submitted/cancelled document is not field-editable through this form.
const locked = computed(() => isSubmitted.value || isCancelled.value);
const statusLabel = computed(() =>
	docstatus.value === 1 ? "Submitted" : docstatus.value === 2 ? "Cancelled" : "Draft"
);

const SKIP = new Set([
	"Section Break",
	"Column Break",
	"Tab Break",
	"HTML",
	"Button",
	"Image",
	"Fold",
	"Heading",
	"Table MultiSelect",
]);

function evalDependsOn(expr) {
	if (!expr) return true;
	try {
		if (expr.startsWith("eval:")) {
			// eslint-disable-next-line no-new-func
			return !!Function("doc", `return (${expr.slice(5)});`)(form);
		}
		return !!form[expr];
	} catch {
		return true;
	}
}

function isRenderable(f) {
	if (SKIP.has(f.fieldtype)) return false;
	if (f.hidden) return false;
	if (f.fieldname === "naming_series" && !f.reqd) return false;
	return evalDependsOn(f.depends_on);
}

// Field layout: Tab Break → tabs, Section Break → sections within a tab, then fields.
// Fields before the first Tab Break form an implicit first tab (Frappe's "Details").
const activeTab = ref(0);

const tabs = computed(() => {
	const fields = meta.value?.fields || [];
	const mkSection = (label) => ({ label: label || "", fields: [], tables: [] });
	const mkTab = (label) => ({ label: label || "", sections: [] });
	const out = [];
	let tab = mkTab("");
	let section = mkSection("");
	tab.sections.push(section);
	out.push(tab);
	for (const f of fields) {
		if (f.fieldtype === "Tab Break") {
			tab = mkTab(f.label || "");
			section = mkSection("");
			tab.sections.push(section);
			out.push(tab);
			continue;
		}
		if (f.fieldtype === "Section Break") {
			section = mkSection(f.label || "");
			tab.sections.push(section);
			continue;
		}
		if (!isRenderable(f)) continue;
		if (f.fieldtype === "Table") section.tables.push(f);
		else section.fields.push(f);
	}
	const pruned = out
		.map((t) => ({ ...t, sections: t.sections.filter((s) => s.fields.length || s.tables.length) }))
		.filter((t) => t.sections.length);
	if (pruned.length > 1 && !pruned[0].label) pruned[0].label = "Details";
	return pruned;
});

const currentTab = computed(() => tabs.value[activeTab.value] || tabs.value[0] || { sections: [] });

// Dirty tracking: while a draft has unsaved edits, Save is the primary action;
// once clean, Submit becomes primary (Frappe's Save-then-Submit behaviour).
const pristine = ref("");
function snapshot() {
	pristine.value = JSON.stringify(form);
}
const dirty = computed(() => JSON.stringify(form) !== pristine.value);
const showSave = computed(
	() => isDraft.value && perms.value.write && !(submittable.value && !dirty.value)
);

function isReadOnly(f) {
	if (locked.value) return true;
	if (f.read_only) return true;
	return isEdit.value ? !perms.value.write : !perms.value.create;
}

// --- load --------------------------------------------------------------------
function resolveDefault(f) {
	const d = f.default;
	if (d === undefined || d === null || d === "") return undefined;
	if (f.fieldtype === "Date" && /^today$/i.test(d)) return new Date().toISOString().slice(0, 10);
	if (f.fieldtype === "Datetime" && /^(now|today)$/i.test(d))
		return new Date().toISOString().slice(0, 16);
	if (/^(user|__user)$/i.test(d)) return undefined;
	return f.fieldtype === "Check" ? (Number(d) ? 1 : 0) : d;
}

function seedNew() {
	for (const f of meta.value?.fields || []) {
		if (f.fieldtype === "Table") {
			if (!Array.isArray(form[f.fieldname])) form[f.fieldname] = [];
			continue;
		}
		if (SKIP.has(f.fieldtype)) continue;
		const dv = resolveDefault(f);
		if (dv !== undefined) form[f.fieldname] = dv;
		else if (f.fieldtype === "Check" && form[f.fieldname] === undefined) form[f.fieldname] = 0;
	}
}

async function load() {
	loading.value = true;
	formError.value = "";
	try {
		perms.value = await getDoctypePermissions(props.doctype).catch(() => perms.value);
		if (isEdit.value) {
			const doc = await getRecord(props.doctype, props.name);
			Object.keys(form).forEach((k) => delete form[k]);
			Object.assign(form, doc);
		} else if (meta.value) {
			seedNew();
		}
		snapshot();
	} catch (err) {
		formError.value = err.message || "Failed to load record.";
	} finally {
		loading.value = false;
	}
}

watch(
	() => meta.value,
	(m) => {
		if (m && !isEdit.value && !loading.value) {
			seedNew();
			snapshot();
		}
	}
);
watch(() => [props.doctype, props.name], load, { immediate: true });

// --- navigation --------------------------------------------------------------
function goList() {
	router.push({ name: "records-list", params: { doctype: props.doctype } });
}
function goEdit(name) {
	router.replace({ name: "record-edit", params: { doctype: props.doctype, name } });
}

// --- actions -----------------------------------------------------------------
function missingRequired() {
	const missing = [];
	let firstTab = null;
	const flag = (label, ti) => {
		missing.push(label);
		if (firstTab === null) firstTab = ti;
	};
	tabs.value.forEach((t, ti) => {
		for (const s of t.sections) {
			for (const f of s.fields) {
				if (!f.reqd || isReadOnly(f)) continue;
				const v = form[f.fieldname];
				if (v === undefined || v === null || v === "") flag(f.label || f.fieldname, ti);
			}
			for (const tb of s.tables) {
				if (tb.reqd && !(form[tb.fieldname] || []).length) flag(tb.label || tb.fieldname, ti);
			}
		}
	});
	return { missing, firstTab };
}

function guardRequired() {
	const { missing, firstTab } = missingRequired();
	if (missing.length) {
		if (firstTab !== null) activeTab.value = firstTab;
		formError.value = `Please fill: ${missing.join(", ")}.`;
		return false;
	}
	return true;
}

async function onSave() {
	formError.value = "";
	if (isEdit.value && !dirty.value) return; // nothing to save on a clean draft
	if (!guardRequired()) return;
	busy.value = true;
	try {
		const doc = isEdit.value ? await saveRecord({ ...form }) : await insertRecord({ ...form });
		showToast(isEdit.value ? "Saved." : "Created.");
		if (!isEdit.value && doc?.name) goEdit(doc.name);
		else await load();
	} catch (err) {
		formError.value = err.message || "Save failed.";
	} finally {
		busy.value = false;
	}
}

async function onSubmit() {
	formError.value = "";
	if (!guardRequired()) return;
	busy.value = true;
	try {
		await saveRecord({ ...form }); // persist edits before submitting
		await submitRecord(props.doctype, props.name);
		showToast("Submitted.");
		await load();
	} catch (err) {
		formError.value = err.message || "Submit failed.";
	} finally {
		busy.value = false;
	}
}

async function onCancel() {
	const ok = await confirmDialog({
		title: `Cancel ${props.name}?`,
		message: "This cancels the submitted document.",
		confirmLabel: "Cancel document",
		destructive: true,
	});
	if (!ok) return;
	busy.value = true;
	try {
		await cancelRecord(props.doctype, props.name);
		showToast("Cancelled.");
		await load();
	} catch (err) {
		formError.value = err.message || "Cancel failed.";
	} finally {
		busy.value = false;
	}
}

async function onAmend() {
	const ok = await confirmDialog({
		title: `Amend ${props.name}?`,
		message: "Creates a fresh editable draft copy; the original stays cancelled.",
		confirmLabel: "Amend",
	});
	if (!ok) return;
	busy.value = true;
	try {
		const res = await amendRecord(props.doctype, props.name);
		showToast("Amended — a draft was created.");
		goEdit(res.name);
	} catch (err) {
		formError.value = err.message || "Amend failed.";
	} finally {
		busy.value = false;
	}
}

async function onDelete() {
	const ok = await confirmDialog({
		title: `Delete ${props.name}?`,
		message: "This permanently removes the record.",
		confirmLabel: "Delete",
		destructive: true,
	});
	if (!ok) return;
	busy.value = true;
	try {
		await deleteRecord(props.doctype, props.name);
		showToast("Deleted.");
		goList();
	} catch (err) {
		formError.value = err.message || "Delete failed.";
		busy.value = false;
	}
}

const SECONDARY =
	"text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 rounded-md";
const DANGER =
	"text-xs px-3 py-1.5 border border-danger-200 bg-white hover:bg-danger-50 text-danger-700 rounded-md";
</script>

<template>
	<div>
		<div
			v-if="isEdit && submittable"
			class="mb-4 flex items-center gap-2"
		>
			<StatusBadge :status="statusLabel" />
			<span v-if="isDraft" class="text-[11px] text-ink-500">Not submitted yet.</span>
		</div>

		<div
			v-if="formError"
			class="mb-4 px-4 py-2.5 bg-danger-50 border border-danger-200 rounded-md text-xs text-danger-700 whitespace-pre-line"
		>
			{{ formError }}
		</div>

		<div v-if="metaLoading || loading" class="text-sm text-ink-500 py-10 text-center">
			Loading…
		</div>

		<form v-else @submit.prevent="onSave">
			<!-- Tabs (Tab Break fields) -->
			<div
				v-if="tabs.length > 1"
				class="flex items-center gap-1 border-b border-ink-200 mb-5 overflow-x-auto"
			>
				<button
					v-for="(t, ti) in tabs"
					:key="ti"
					type="button"
					class="px-3 py-2 text-sm whitespace-nowrap border-b-2 -mb-px transition-colors"
					:class="
						activeTab === ti
							? 'border-brand-600 text-brand-700 font-medium'
							: 'border-transparent text-ink-500 hover:text-ink-800'
					"
					@click="activeTab = ti"
				>
					{{ t.label || "Details" }}
				</button>
			</div>

			<section v-for="(s, si) in currentTab.sections" :key="si" class="mb-6">
				<h3
					v-if="s.label"
					class="text-[11px] font-semibold uppercase tracking-wider text-ink-700 mb-3 pb-1.5 border-b border-ink-200"
				>
					{{ s.label }}
				</h3>

				<div
					v-if="s.fields.length"
					class="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4 mb-4"
				>
					<DeskField
						v-for="f in s.fields"
						:key="f.fieldname"
						:label="f.label || f.fieldname"
						:required="!!f.reqd"
						:hint="f.description || ''"
					>
						<DocTypeFieldControl
							v-model="form[f.fieldname]"
							:field="f"
							:context="form"
							:disabled="isReadOnly(f)"
						/>
					</DeskField>
				</div>

				<div v-for="t in s.tables" :key="t.fieldname" class="mb-4">
					<div class="text-[11px] font-medium text-ink-700 mb-1.5">
						{{ t.label || t.fieldname }}<span v-if="t.reqd" class="text-danger-600"> *</span>
					</div>
					<DocTypeChildTable
						v-model="form[t.fieldname]"
						:doctype="t.options"
						:disabled="isReadOnly(t)"
					/>
				</div>
			</section>

			<div
				class="flex items-center gap-2 pt-2 border-t border-ink-200 sticky bottom-0 bg-white py-3"
			>
				<!-- New -->
				<button
					v-if="!isEdit && perms.create"
					type="submit"
					class="desk-save-btn"
					:disabled="busy"
				>
					{{ busy ? "Creating…" : "Create" }}
				</button>

				<!-- Draft: Save is primary while dirty; once clean, Submit takes over. -->
				<template v-else-if="isDraft">
					<button
						v-if="showSave"
						type="submit"
						class="desk-save-btn"
						:disabled="busy || !dirty"
					>
						{{ busy ? "Saving…" : "Save" }}
					</button>
					<button
						v-if="submittable && perms.submit"
						type="button"
						:class="dirty ? SECONDARY : 'desk-save-btn'"
						:disabled="busy"
						@click="onSubmit"
					>
						Submit
					</button>
					<button
						v-if="perms.delete"
						type="button"
						:class="DANGER"
						:disabled="busy"
						@click="onDelete"
					>
						Delete
					</button>
				</template>

				<!-- Submitted -->
				<template v-else-if="isSubmitted">
					<button
						v-if="perms.cancel"
						type="button"
						:class="DANGER"
						:disabled="busy"
						@click="onCancel"
					>
						Cancel
					</button>
				</template>

				<!-- Cancelled -->
				<template v-else-if="isCancelled">
					<button
						v-if="perms.create"
						type="button"
						class="desk-save-btn"
						:disabled="busy"
						@click="onAmend"
					>
						Amend
					</button>
					<button
						v-if="perms.delete"
						type="button"
						:class="DANGER"
						:disabled="busy"
						@click="onDelete"
					>
						Delete
					</button>
				</template>

				<button type="button" :class="SECONDARY" @click="goList">Back</button>
			</div>
		</form>
	</div>
</template>
