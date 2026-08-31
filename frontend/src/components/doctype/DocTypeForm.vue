<script setup>
// Generic, meta-driven form for an arbitrary DocType. Renders each field by its
// fieldtype via the shared DocTypeFieldControl, honouring reqd / read_only /
// hidden / depends_on, plus full-width child-table grids (DocTypeChildTable) and
// Dynamic Links. Loads via frappe.client.get (full doc incl. child tables) and
// saves via frappe.client.insert / save — so untouched child rows round-trip.
import { computed, reactive, ref, watch } from "vue";
import { useDoctypeMeta } from "@/composables/useDoctypeMeta";
import { getRecord, insertRecord, saveRecord } from "@/data/doctypeRecordApi";
import { getDoctypePermissions } from "@/data/workspaceSettingApi";
import { showToast } from "@/utils/appToast";
import DeskField from "@/components/desk/DeskField.vue";
import DocTypeFieldControl from "@/components/doctype/DocTypeFieldControl.vue";
import DocTypeChildTable from "@/components/doctype/DocTypeChildTable.vue";

const props = defineProps({
	doctype: { type: String, required: true },
	name: { type: String, default: "" },
});
const emit = defineEmits(["saved", "cancelled"]);

const { meta, loading: metaLoading } = useDoctypeMeta(props.doctype);

const form = reactive({ doctype: props.doctype });
const loading = ref(false);
const saving = ref(false);
const formError = ref("");
const perms = ref({ read: true, write: true, create: true, delete: true });

const isEdit = computed(() => !!props.name);

// Structural / not-yet-supported fieldtypes never rendered (Table is handled separately).
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

// Sections split on Section Break; scalars render in a 2-col grid, tables full-width.
const sections = computed(() => {
	const fields = meta.value?.fields || [];
	const out = [{ label: "", fields: [], tables: [] }];
	for (const f of fields) {
		if (f.fieldtype === "Section Break") {
			out.push({ label: f.label || "", fields: [], tables: [] });
			continue;
		}
		if (!isRenderable(f)) continue;
		if (f.fieldtype === "Table") out[out.length - 1].tables.push(f);
		else out[out.length - 1].fields.push(f);
	}
	return out.filter((s) => s.fields.length || s.tables.length);
});

function isReadOnly(f) {
	return (
		!!f.read_only ||
		(isEdit.value && !perms.value.write) ||
		(!isEdit.value && !perms.value.create)
	);
}

// --- load --------------------------------------------------------------------
function resolveDefault(f) {
	const d = f.default;
	if (d === undefined || d === null || d === "") return undefined;
	if (f.fieldtype === "Date" && /^today$/i.test(d)) return new Date().toISOString().slice(0, 10);
	if (f.fieldtype === "Datetime" && /^(now|today)$/i.test(d))
		return new Date().toISOString().slice(0, 16);
	if (/^(user|__user)$/i.test(d)) return undefined; // let the server stamp the session user
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
	} catch (err) {
		formError.value = err.message || "Failed to load record.";
	} finally {
		loading.value = false;
	}
}

watch(
	() => meta.value,
	(m) => {
		if (m && !isEdit.value && !loading.value) seedNew();
	}
);
watch(() => [props.doctype, props.name], load, { immediate: true });

// --- save --------------------------------------------------------------------
function missingRequired() {
	const missing = [];
	for (const s of sections.value) {
		for (const f of s.fields) {
			if (!f.reqd || isReadOnly(f)) continue;
			const v = form[f.fieldname];
			if (v === undefined || v === null || v === "") missing.push(f.label || f.fieldname);
		}
		for (const t of s.tables) {
			if (t.reqd && !(form[t.fieldname] || []).length) missing.push(t.label || t.fieldname);
		}
	}
	return missing;
}

async function onSave() {
	formError.value = "";
	const missing = missingRequired();
	if (missing.length) {
		formError.value = `Please fill: ${missing.join(", ")}.`;
		return;
	}
	saving.value = true;
	try {
		const doc = isEdit.value ? await saveRecord({ ...form }) : await insertRecord({ ...form });
		showToast(isEdit.value ? "Saved." : "Created.");
		emit("saved", doc);
	} catch (err) {
		formError.value = err.message || "Save failed.";
	} finally {
		saving.value = false;
	}
}

const canSave = computed(() => (isEdit.value ? perms.value.write : perms.value.create));
</script>

<template>
	<div>
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
			<section v-for="(s, si) in sections" :key="si" class="mb-6">
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
				<button
					v-if="canSave"
					type="submit"
					class="text-xs px-3 py-1.5 border border-brand-300 bg-brand-50 hover:bg-brand-100 text-brand-700 font-medium rounded-md"
					:disabled="saving"
				>
					{{ saving ? "Saving…" : isEdit ? "Save" : "Create" }}
				</button>
				<button
					type="button"
					class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 rounded-md"
					@click="emit('cancelled')"
				>
					Cancel
				</button>
			</div>
		</form>
	</div>
</template>
