<script setup>
// Generic, meta-driven form for an arbitrary DocType (Phase 1: scalar fields).
//
// Reads the DocType's Frappe meta (useDoctypeMeta), renders each field by its
// fieldtype using the shared Desk controls, honouring reqd / read_only / hidden /
// depends_on, and saves via the standard frappe.client.* endpoints. Child tables
// (fieldtype "Table") are intentionally NOT rendered yet — that (and Journal
// Entry's accounts grid) lands in Phase 2. When a DocType has a mandatory child
// table the server rejects the save and the error surfaces in the banner.
import { computed, reactive, ref, watch } from "vue";
import { useDoctypeMeta } from "@/composables/useDoctypeMeta";
import { getRecord, insertRecord, saveRecord } from "@/data/doctypeRecordApi";
import { getDoctypePermissions } from "@/data/workspaceSettingApi";
import { showToast } from "@/utils/appToast";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskTextarea from "@/components/desk/DeskTextarea.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";

const props = defineProps({
	doctype: { type: String, required: true },
	// Present → edit an existing record; absent → new record.
	name: { type: String, default: "" },
});
const emit = defineEmits(["saved", "cancelled"]);

const { meta, loading: metaLoading, selectOptions } = useDoctypeMeta(props.doctype);

const form = reactive({ doctype: props.doctype });
const loading = ref(false);
const saving = ref(false);
const formError = ref("");
const perms = ref({ read: true, write: true, create: true, delete: true });

const isEdit = computed(() => !!props.name);

// --- fieldtype → control routing ---------------------------------------------
const NUMERIC = new Set(["Int", "Float", "Currency", "Percent"]);
const TEXTAREA = new Set([
	"Small Text",
	"Text",
	"Long Text",
	"Code",
	"Text Editor",
	"HTML Editor",
	"Markdown Editor",
	"JSON",
]);
// Layout / structural / not-yet-supported fieldtypes never rendered as an input.
const SKIP = new Set([
	"Section Break",
	"Column Break",
	"Tab Break",
	"HTML",
	"Button",
	"Image",
	"Fold",
	"Heading",
	"Table",
	"Table MultiSelect",
]);

function evalDependsOn(expr) {
	if (!expr) return true;
	try {
		if (expr.startsWith("eval:")) {
			// Frappe depends_on expressions are trusted (from the DocType definition).
			// eslint-disable-next-line no-new-func
			return !!Function("doc", `return (${expr.slice(5)});`)(form);
		}
		return !!form[expr];
	} catch {
		return true; // never hide a field because its expression failed to parse
	}
}

function isRenderable(f) {
	if (SKIP.has(f.fieldtype)) return false;
	if (f.hidden) return false;
	if (f.fieldname === "naming_series" && !f.reqd) return false;
	return evalDependsOn(f.depends_on);
}

// Fields grouped into sections (split on Section Break), for a tidy layout.
const sections = computed(() => {
	const fields = meta.value?.fields || [];
	const out = [{ label: "", fields: [] }];
	for (const f of fields) {
		if (f.fieldtype === "Section Break") {
			out.push({ label: f.label || "", fields: [] });
			continue;
		}
		if (isRenderable(f)) out[out.length - 1].fields.push(f);
	}
	return out.filter((s) => s.fields.length);
});

function controlFor(f) {
	if (f.fieldtype === "Link" || f.fieldtype === "Dynamic Link") return "link";
	if (f.fieldtype === "Select") return "select";
	if (f.fieldtype === "Check") return "check";
	if (f.fieldtype === "Date") return "date";
	if (f.fieldtype === "Datetime") return "datetime";
	if (TEXTAREA.has(f.fieldtype)) return "textarea";
	if (NUMERIC.has(f.fieldtype)) return "number";
	return "data";
}

// Dynamic Link: options names the field that holds the target DocType.
function linkTarget(f) {
	if (f.fieldtype === "Dynamic Link") return form[f.options] || "";
	return f.options || "DocType";
}

function isReadOnly(f) {
	return !!f.read_only || (isEdit.value && !perms.value.write) || (!isEdit.value && !perms.value.create);
}

// --- load --------------------------------------------------------------------
function seedDefaults() {
	for (const f of meta.value?.fields || []) {
		if (SKIP.has(f.fieldtype)) continue;
		if (f.default !== undefined && f.default !== null && f.default !== "") {
			form[f.fieldname] = f.fieldtype === "Check" ? Number(f.default) ? 1 : 0 : f.default;
		} else if (f.fieldtype === "Check" && form[f.fieldname] === undefined) {
			form[f.fieldname] = 0;
		}
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
			Object.assign(form, doc); // full doc incl. child tables (which ride untouched on save)
		} else {
			// wait for meta so defaults can seed
			if (!meta.value) await new Promise((r) => setTimeout(r, 0));
			seedDefaults();
		}
	} catch (err) {
		formError.value = err.message || "Failed to load record.";
	} finally {
		loading.value = false;
	}
}

// meta arrives async; seed defaults for a new record once it's here.
watch(
	() => meta.value,
	(m) => {
		if (m && !isEdit.value && !loading.value) seedDefaults();
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
			class="mb-4 px-4 py-2.5 bg-danger-50 border border-danger-200 rounded-md text-xs text-danger-700"
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
				<div class="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4">
					<DeskField
						v-for="f in s.fields"
						:key="f.fieldname"
						:label="f.label || f.fieldname"
						:required="!!f.reqd"
						:hint="f.description || ''"
					>
						<!-- Link / Dynamic Link -->
						<DeskLinkPicker
							v-if="controlFor(f) === 'link'"
							v-model="form[f.fieldname]"
							:doctype="linkTarget(f) || 'DocType'"
							value-field="name"
							:disabled="isReadOnly(f) || (f.fieldtype === 'Dynamic Link' && !linkTarget(f))"
							:placeholder="f.fieldtype === 'Dynamic Link' && !linkTarget(f) ? 'Pick the type first' : 'Search…'"
						/>

						<!-- Select -->
						<DeskSelect
							v-else-if="controlFor(f) === 'select'"
							v-model="form[f.fieldname]"
							:disabled="isReadOnly(f)"
						>
							<option value="">—</option>
							<option v-for="o in selectOptions(f.fieldname)" :key="o" :value="o">
								{{ o }}
							</option>
						</DeskSelect>

						<!-- Check -->
						<label
							v-else-if="controlFor(f) === 'check'"
							class="inline-flex items-center gap-2 text-xs text-ink-700 h-[34px]"
						>
							<input
								type="checkbox"
								:checked="!!form[f.fieldname]"
								:disabled="isReadOnly(f)"
								@change="form[f.fieldname] = $event.target.checked ? 1 : 0"
							/>
							<span>Yes</span>
						</label>

						<!-- Date / Datetime -->
						<DeskInput
							v-else-if="controlFor(f) === 'date'"
							v-model="form[f.fieldname]"
							type="date"
							:disabled="isReadOnly(f)"
						/>
						<DeskInput
							v-else-if="controlFor(f) === 'datetime'"
							v-model="form[f.fieldname]"
							type="datetime-local"
							:disabled="isReadOnly(f)"
						/>

						<!-- Textarea -->
						<DeskTextarea
							v-else-if="controlFor(f) === 'textarea'"
							v-model="form[f.fieldname]"
							:rows="3"
							:disabled="isReadOnly(f)"
						/>

						<!-- Number -->
						<DeskInput
							v-else-if="controlFor(f) === 'number'"
							v-model.number="form[f.fieldname]"
							type="number"
							:disabled="isReadOnly(f)"
						/>

						<!-- Data / fallback -->
						<DeskInput
							v-else
							v-model="form[f.fieldname]"
							:disabled="isReadOnly(f)"
						/>
					</DeskField>
				</div>
			</section>

			<div class="flex items-center gap-2 pt-2 border-t border-ink-200 sticky bottom-0 bg-white py-3">
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
