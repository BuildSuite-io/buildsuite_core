<script setup>
// Terms & Conditions settings (prototype S362, adapted).
//
// One clause library for every document that prints a terms block, segregated by the document it
// applies to (Quotation, Purchase Order, …) via the native Terms and Conditions doctype +
// custom_applicable_for. The body is the native `terms` Text Editor (rich text), edited here with
// frappe-ui's TextEditor so tables and formatting work. Access is native DocPerms: the admin /
// Accountant / Procurement Officer / Estimator manage the library (can_write); every other role
// gets select-only and never reaches this screen.
import { ref, reactive, computed, onMounted } from "vue";
import { TextEditor } from "frappe-ui";
import "frappe-ui/editor-style.css";
import { useConfirm } from "@/composables/useConfirm";
import { showToast } from "@/utils/appToast";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import { getTermsAccess, listTerms, saveTerms, deleteTerms } from "@/data/termsApi";
import { __ } from "@/utils/translate";

const confirmDialog = useConfirm();
const UNCATEGORISED = "Uncategorised";

const access = ref({ can_read: false, can_write: false, applicable_for: [] });
const clauses = ref([]);
const loading = ref(true);
const activeCat = ref("");
const search = ref("");

const canWrite = computed(() => !!access.value.can_write);

// Categories = the applicable-for documents, plus an Uncategorised bucket when a clause has none.
const categories = computed(() => {
	const list = [...(access.value.applicable_for || [])];
	if (clauses.value.some((c) => !c.custom_applicable_for)) list.push(UNCATEGORISED);
	return list;
});

function catOf(c) {
	return c.custom_applicable_for || UNCATEGORISED;
}
function countFor(cat) {
	return clauses.value.filter((c) => catOf(c) === cat).length;
}

const rows = computed(() => {
	const t = search.value.trim().toLowerCase();
	return clauses.value
		.filter((c) => catOf(c) === activeCat.value)
		.filter(
			(c) =>
				!t ||
				(c.title || "").toLowerCase().includes(t) ||
				(c.terms || "").toLowerCase().includes(t)
		);
});

async function load() {
	loading.value = true;
	try {
		access.value = await getTermsAccess();
		clauses.value = access.value.can_read ? await listTerms() : [];
		if (!activeCat.value || !categories.value.includes(activeCat.value)) {
			activeCat.value = categories.value[0] || "";
		}
	} catch (err) {
		showToast(err.message || __("Failed to load terms"), "error");
	} finally {
		loading.value = false;
	}
}
onMounted(load);

// ---- editor ----
const BLANK = { name: "", title: "", applicable_for: "", terms: "", disabled: false };
const form = reactive({ ...BLANK });
const editing = ref(false);
const error = ref("");
const saving = ref(false);
// Remount the rich-text editor when the edited clause changes, so it initialises with that body.
const editorKey = ref(0);

function startNew() {
	Object.assign(form, {
		...BLANK,
		applicable_for: activeCat.value === UNCATEGORISED ? "" : activeCat.value,
	});
	error.value = "";
	editing.value = true;
	editorKey.value += 1;
}
function startEdit(c) {
	Object.assign(form, {
		name: c.name,
		title: c.title,
		applicable_for: c.custom_applicable_for || "",
		terms: c.terms || "",
		disabled: c.disabled === 1,
	});
	error.value = "";
	editing.value = true;
	editorKey.value += 1;
}
function cancel() {
	editing.value = false;
	error.value = "";
}

async function save() {
	if (!form.title.trim()) {
		error.value = __("Give the clause a name — it's what the picker shows.");
		return;
	}
	saving.value = true;
	try {
		await saveTerms({
			name: form.name || undefined,
			title: form.title,
			applicable_for: form.applicable_for || undefined,
			terms: form.terms || "",
			disabled: form.disabled ? 1 : 0,
		});
		if (form.applicable_for) activeCat.value = form.applicable_for;
		editing.value = false;
		await load();
	} catch (err) {
		error.value = err.message || __("Failed to save the clause.");
	} finally {
		saving.value = false;
	}
}

async function remove(c) {
	const ok = await confirmDialog({
		title: __("Delete this clause"),
		message: __(
			'Delete "{0}"?\n\nDocuments that already used this wording keep their copy — a clause is copied in, never linked. Only the library loses it.',
			[c.title]
		),
		confirmLabel: __("Delete"),
		destructive: true,
	});
	if (!ok) return;
	try {
		await deleteTerms(c.name);
		await load();
	} catch (err) {
		showToast(err.message || __("Failed to delete the clause."), "error");
	}
}

const breadcrumbs = [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: __("Settings"), to: "/settings" },
	{ label: __("Terms & Conditions") },
];
</script>

<template>
	<DeskPage
		:title="__('Terms & Conditions')"
		:subtitle="
			__(
				'The clause library every printed document pulls from, grouped by the document it applies to. Pulling a clause into a document copies its wording — editing it here never changes a document already sent.'
			)
		"
		:breadcrumbs="breadcrumbs"
	>
		<template #actions>
			<button
				v-if="activeCat && canWrite"
				type="button"
				class="desk-save-btn"
				@click="startNew"
			>
				+ {{ __("New clause") }}
			</button>
		</template>

		<div v-if="loading" class="py-14 text-center text-xs text-ink-400">
			{{ __("Loading…") }}
		</div>

		<div
			v-else-if="!access.can_read"
			class="border border-dashed border-ink-200 px-4 py-10 text-center"
			style="border-radius: 8px"
		>
			<div class="text-sm text-ink-700">
				{{ __("You don't have access to the terms library.") }}
			</div>
			<div class="text-[11px] text-ink-500 mt-1">
				{{
					__(
						"Your role can pick a clause on a document, but not manage the library here."
					)
				}}
			</div>
		</div>

		<div v-else class="grid grid-cols-1 lg:grid-cols-4 gap-4">
			<!-- Categories: the documents a clause can apply to. -->
			<nav class="lg:col-span-1">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-2">
					{{ __("Used on") }}
				</div>
				<button
					v-for="cat in categories"
					:key="cat"
					type="button"
					class="w-full text-left px-3 py-2 mb-1 border transition-colors"
					style="border-radius: 6px"
					:class="
						activeCat === cat
							? 'border-brand-400 bg-brand-50'
							: 'border-ink-200 hover:bg-ink-50'
					"
					@click="
						activeCat = cat;
						editing = false;
					"
				>
					<div class="flex items-center justify-between gap-2">
						<span class="text-sm font-medium text-ink-900">{{ __(cat) }}</span>
						<span class="text-[10px] text-ink-500 tabular-nums">{{
							countFor(cat)
						}}</span>
					</div>
				</button>
			</nav>

			<section class="lg:col-span-3">
				<div v-if="activeCat" class="flex flex-wrap items-center gap-3 mb-3">
					<DeskInput
						v-model="search"
						class="!w-72"
						:placeholder="__('Search name or wording…')"
					/>
					<span class="text-xs text-ink-500 ml-auto"
						>{{ rows.length }} {{ __("of") }} {{ countFor(activeCat) }}</span
					>
				</div>

				<!-- Editor -->
				<div
					v-if="editing"
					class="border border-brand-200 bg-brand-50 p-4 mb-4"
					style="border-radius: 8px"
				>
					<div class="text-sm font-semibold text-ink-900 mb-3">
						{{ form.name ? __("Edit clause") : __("New clause") }}
					</div>
					<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
						<DeskField
							:label="__('Name')"
							required
							:hint="__('What the picker shows on a document.')"
						>
							<DeskInput
								v-model="form.title"
								:placeholder="__('e.g. Standard Validity & Payment Terms')"
							/>
						</DeskField>
						<DeskField
							:label="__('Applicable for')"
							:hint="__('The document this clause belongs to.')"
						>
							<DeskSelect v-model="form.applicable_for">
								<option value="">{{ __("— Uncategorised —") }}</option>
								<option v-for="c in access.applicable_for" :key="c" :value="c">
									{{ __(c) }}
								</option>
							</DeskSelect>
						</DeskField>
					</div>
					<DeskField
						:label="__('Wording')"
						class="mt-3"
						:hint="
							__(
								'Printed as written — copied into a document when somebody picks this clause. Supports formatting and tables.'
							)
						"
					>
						<div
							class="bg-white border border-ink-200 rounded-md overflow-hidden terms-editor"
						>
							<TextEditor
								:key="editorKey"
								:content="form.terms"
								:fixed-menu="true"
								:editable="true"
								editor-class="prose-sm px-3 py-2 min-h-[12rem] focus:outline-none"
								@change="(html) => (form.terms = html)"
							/>
						</div>
					</DeskField>
					<label class="inline-flex items-center gap-2 text-xs text-ink-700 mt-3">
						<input v-model="form.disabled" type="checkbox" />
						<span>{{ __("Disabled (not offered on documents)") }}</span>
					</label>
					<p v-if="error" class="text-xs text-danger-700 mt-2">{{ error }}</p>
					<div class="flex justify-end gap-2 mt-3">
						<button
							type="button"
							class="text-xs px-2.5 py-1 border border-ink-200 bg-white text-ink-700 hover:bg-ink-50"
							style="border-radius: 6px"
							@click="cancel"
						>
							{{ __("Cancel") }}
						</button>
						<button
							type="button"
							class="desk-save-btn"
							:disabled="saving"
							@click="save"
						>
							{{
								saving
									? __("Saving…")
									: form.name
									? __("Save clause")
									: __("Add clause")
							}}
						</button>
					</div>
				</div>

				<!-- The clauses -->
				<article
					v-for="c in rows"
					:key="c.name"
					class="border border-ink-200 overflow-hidden mb-2"
					style="border-radius: 8px"
					:class="c.disabled === 1 ? 'opacity-60' : ''"
				>
					<header
						class="px-4 py-2.5 bg-gradient-to-r from-brand-50 to-white border-b border-ink-100 flex items-center justify-between gap-3"
					>
						<div class="min-w-0">
							<div class="text-sm font-medium text-ink-900 truncate">
								{{ c.title }}
							</div>
							<div class="text-[10px] text-ink-500">
								{{ __(c.custom_applicable_for || UNCATEGORISED) }}
							</div>
						</div>
						<div class="flex items-center gap-1.5 shrink-0">
							<span
								v-if="c.disabled === 1"
								class="text-[10px] px-1.5 py-0.5 bg-ink-100 text-ink-600"
								style="border-radius: 9999px"
								>{{ __("Disabled") }}</span
							>
							<template v-if="canWrite">
								<button
									type="button"
									class="text-xs px-2 py-0.5 border border-ink-200 bg-white text-ink-700 hover:bg-ink-50"
									style="border-radius: 6px"
									@click="startEdit(c)"
								>
									{{ __("Edit") }}
								</button>
								<button
									type="button"
									class="text-xs px-2 py-0.5 border border-danger-200 text-danger-700 hover:bg-danger-50"
									style="border-radius: 6px"
									@click="remove(c)"
								>
									{{ __("Delete") }}
								</button>
							</template>
						</div>
					</header>
					<!-- Admin-authored HTML (native Terms Text Editor) — rendered as-is. -->
					<div
						class="px-4 py-3 prose prose-sm max-w-none text-ink-700 terms-body"
						v-html="c.terms"
					></div>
				</article>

				<p
					v-if="activeCat && !rows.length"
					class="text-sm text-ink-500 border border-dashed border-ink-200 px-4 py-8 text-center"
					style="border-radius: 8px"
				>
					{{
						search
							? __("Nothing matches that search.")
							: __("No clauses for {0} yet.", [__(activeCat)])
					}}
				</p>
			</section>
		</div>
	</DeskPage>
</template>

<style scoped>
/* Keep tables inside a printed clause legible in the read view. */
.terms-body :deep(table) {
	border-collapse: collapse;
	width: 100%;
	margin: 0.5rem 0;
}
.terms-body :deep(th),
.terms-body :deep(td) {
	border: 1px solid var(--ink-200, #e5e7eb);
	padding: 0.35rem 0.5rem;
	text-align: left;
}
</style>
