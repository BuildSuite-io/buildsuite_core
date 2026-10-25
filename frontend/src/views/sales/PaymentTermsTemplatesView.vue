<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useConfirm } from "@/composables/useConfirm";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import DeskPage from "@/components/desk/DeskPage.vue";
import PaymentScheduleEditor from "@/components/PaymentScheduleEditor.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import {
	deletePaymentTermsTemplate,
	getPaymentTermsAccess,
	listPaymentTermsTemplates,
	savePaymentTermsTemplate,
} from "@/data/paymentTermsApi";
import { getProjectTemplateSummary } from "@/data/projectTemplateApi";
import { showToast } from "@/utils/appToast";
import { __ } from "@/utils/translate";

const confirmDialog = useConfirm();
const access = ref({ can_read: false, can_create: false, can_write: false, can_delete: false });
const templates = ref([]);
const loading = ref(true);
const open = ref(false);
const saving = ref(false);
const error = ref("");
const editingId = ref("");
const stageNames = ref([]);
const stageLoadError = ref("");

const blankForm = () => ({
	name: "",
	project_category: "",
	description: "",
	enabled: true,
	rows: [],
});
const form = reactive(blankForm());

const canCreate = computed(() => access.value.can_create);
const canWrite = computed(() => access.value.can_write);
const canDelete = computed(() => access.value.can_delete);
const canEditForm = computed(() => (editingId.value ? canWrite.value : canCreate.value));
const stageOptions = computed(() =>
	stageNames.value.map((name) => ({ value: name, label: name }))
);

function total(rows) {
	return +rows.reduce((sum, row) => sum + (Number(row.percent) || 0), 0).toFixed(2);
}
const formTotal = computed(() => total(form.rows));
const hasStageWithoutCategory = computed(
	() => !form.project_category && form.rows.some((row) => row.trigger === "stage")
);

async function load() {
	loading.value = true;
	try {
		access.value = await getPaymentTermsAccess();
		templates.value = access.value.can_read ? await listPaymentTermsTemplates() : [];
	} catch (err) {
		showToast(err.message || __("Failed to load payment terms templates."), "error");
	} finally {
		loading.value = false;
	}
}

onMounted(load);

watch(
	() => form.project_category,
	async (category) => {
		stageNames.value = [];
		stageLoadError.value = "";
		if (!category) return;
		try {
			const summary = await getProjectTemplateSummary(category);
			stageNames.value = summary?.stage_names || [];
		} catch (err) {
			stageLoadError.value = err.message || __("Could not load project stages.");
		}
	}
);

function resetForm(template = null) {
	Object.assign(
		form,
		template
			? {
					name: template.name || "",
					project_category: template.project_type || "",
					description: template.description || "",
					enabled: template.enabled !== false,
					rows: JSON.parse(JSON.stringify(template.rows || [])),
			  }
			: blankForm()
	);
	error.value = "";
}

function startNew() {
	editingId.value = "";
	resetForm();
	open.value = true;
}

function startEdit(template) {
	editingId.value = template.id;
	resetForm(template);
	open.value = true;
}

function close() {
	open.value = false;
	error.value = "";
}

async function save() {
	if (!form.name.trim()) {
		error.value = __("Give the template a name.");
		return;
	}
	saving.value = true;
	error.value = "";
	try {
		await savePaymentTermsTemplate({
			name: editingId.value || undefined,
			title: form.name.trim(),
			project_category: form.project_category || null,
			description: form.description.trim(),
			enabled: form.enabled ? 1 : 0,
			milestones: form.rows,
		});
		close();
		await load();
	} catch (err) {
		error.value = err.message || __("Failed to save the template.");
	} finally {
		saving.value = false;
	}
}

async function remove() {
	const template = templates.value.find((item) => item.id === editingId.value);
	if (!template) return;
	const confirmed = await confirmDialog({
		title: __("Delete template"),
		message: __('Delete "{0}"? Existing quotations, tenders and projects are not changed.', [
			template.name,
		]),
		confirmLabel: __("Delete"),
		destructive: true,
	});
	if (!confirmed) return;
	try {
		await deletePaymentTermsTemplate(editingId.value);
		close();
		await load();
	} catch (err) {
		error.value = err.message || __("Failed to delete the template.");
	}
}

const breadcrumbs = [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: __("Sales"), to: "/sales" },
	{ label: __("Payment terms templates") },
];
</script>

<template>
	<DeskPage
		:title="__('Payment terms templates')"
		:subtitle="
			__(
				'Reusable payment schedules for quotations and tenders. Templates can be tied to a project category so stage milestones match its project stages.'
			)
		"
		:breadcrumbs="breadcrumbs"
	>
		<template #actions>
			<button v-if="canCreate" type="button" class="desk-save-btn" @click="startNew">
				{{ __("+ New template") }}
			</button>
		</template>

		<p class="text-xs text-ink-500 mb-3 max-w-3xl">
			{{
				__(
					"A template is copied into an offer when loaded, so changing one here does not alter schedules already sent."
				)
			}}
		</p>

		<div class="border border-ink-200 overflow-x-auto" style="border-radius: 8px">
			<table class="w-full text-sm min-w-[640px]">
				<thead class="bg-ink-50 border-b border-ink-200">
					<tr class="text-[11px] uppercase tracking-wider text-ink-500 text-left">
						<th class="px-3 py-2 font-medium">{{ __("Template") }}</th>
						<th class="px-3 py-2 font-medium">{{ __("Project category") }}</th>
						<th class="px-3 py-2 font-medium text-right">{{ __("Milestones") }}</th>
						<th class="px-3 py-2 font-medium text-right">{{ __("Total") }}</th>
						<th class="px-3 py-2 font-medium">{{ __("Status") }}</th>
					</tr>
				</thead>
				<tbody>
					<tr v-if="!templates.length">
						<td colspan="5" class="px-3 py-6 text-sm text-ink-500">
							{{ loading ? __("Loading templates…") : __("No templates yet.") }}
						</td>
					</tr>
					<tr
						v-for="template in templates"
						:key="template.id"
						class="border-b border-ink-100 last:border-0 hover:bg-brand-50/40"
						:class="canWrite ? 'cursor-pointer' : ''"
						@click="startEdit(template)"
					>
						<td class="px-3 py-3">
							<div class="text-ink-900 font-medium">{{ template.name }}</div>
							<div
								v-if="template.description"
								class="text-xs text-ink-500 mt-0.5 line-clamp-1"
							>
								{{ template.description }}
							</div>
						</td>
						<td class="px-3 py-3 text-ink-700">
							{{ template.project_type || __("Any project category") }}
						</td>
						<td class="px-3 py-3 text-right tabular-nums text-ink-900">
							{{ template.rows.length }}
						</td>
						<td
							class="px-3 py-3 text-right tabular-nums"
							:class="
								total(template.rows) === 100 ? 'text-ink-900' : 'text-danger-700'
							"
						>
							{{ total(template.rows) }}%
						</td>
						<td class="px-3 py-3">
							<StatusBadge :status="template.enabled ? 'Active' : 'Disabled'" />
						</td>
					</tr>
				</tbody>
			</table>
		</div>

		<Teleport to="body">
			<div
				v-if="open"
				class="fixed inset-0 bg-ink-900/40 z-[60] flex items-start justify-center p-4 overflow-y-auto"
				@click.self="close"
			>
				<div
					class="bg-white w-full max-w-4xl shadow-fp-lg my-6 flex flex-col"
					style="border-radius: 12px; max-height: calc(100vh - 3rem)"
					@click.stop
				>
					<div
						class="px-5 py-3 border-b border-ink-200 flex items-center justify-between flex-shrink-0"
					>
						<div class="text-sm font-semibold text-ink-900">
							{{ editingId ? __("Edit template") : __("New template") }}
						</div>
						<button
							type="button"
							class="text-ink-400 hover:text-ink-700 px-1"
							:aria-label="__('Close')"
							@click="close"
						>
							✕
						</button>
					</div>
					<div class="p-5 space-y-4 overflow-y-auto flex-1">
						<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
							<label class="block">
								<span class="block text-[11px] text-ink-500 mb-1">
									{{ __("Name") }} <span class="text-danger-700">*</span>
								</span>
								<input
									v-model="form.name"
									class="desk-input"
									:disabled="!canEditForm"
									:placeholder="__('e.g. Residential, stage-wise')"
								/>
							</label>
							<label class="block">
								<span class="block text-[11px] text-ink-500 mb-1">
									{{ __("Project category") }}
									<span class="text-ink-400"
										>({{ __("names the stages") }})</span
									>
								</span>
								<DeskLinkPicker
									v-model="form.project_category"
									doctype="Project Category"
									label-field="name"
									value-field="name"
									:disabled="!canEditForm"
									:placeholder="__('Any project category')"
								/>
							</label>
						</div>
						<label class="block">
							<span class="block text-[11px] text-ink-500 mb-1">{{
								__("Description")
							}}</span>
							<textarea
								v-model="form.description"
								rows="2"
								class="desk-input"
								:disabled="!canEditForm"
							></textarea>
						</label>
						<label class="inline-flex items-center gap-2">
							<input
								v-model="form.enabled"
								type="checkbox"
								class="accent-brand-600"
								:disabled="!canEditForm"
							/>
							<span class="text-sm font-medium text-ink-900">
								{{ form.enabled ? __("Enabled") : __("Disabled") }}
							</span>
						</label>

						<PaymentScheduleEditor
							v-model:rows="form.rows"
							:editable="canEditForm"
							:stage-options="stageOptions"
						/>
						<div
							v-if="form.rows.length && formTotal !== 100"
							class="text-xs text-danger-700"
						>
							{{
								__(
									"The milestones add up to {0}%. An offer using this template cannot go out until it is 100%.",
									[formTotal]
								)
							}}
						</div>
						<div v-if="hasStageWithoutCategory" class="text-xs text-warning-700">
							{{
								__(
									"Stage milestones need a project category so they can match its project stages."
								)
							}}
						</div>
						<div v-if="stageLoadError" class="text-xs text-danger-700">
							{{ stageLoadError }}
						</div>
						<div v-if="error" role="alert" class="text-xs text-danger-700">
							{{ error }}
						</div>
					</div>
					<div
						class="px-5 py-3 border-t border-ink-200 flex items-center justify-between gap-2 flex-shrink-0"
					>
						<button
							v-if="editingId && canDelete"
							type="button"
							class="text-xs px-3 py-1.5 border border-danger-200 text-danger-700 hover:bg-danger-50"
							style="border-radius: 6px"
							@click="remove"
						>
							{{ __("Delete") }}
						</button>
						<span v-else></span>
						<div class="flex gap-2">
							<button
								type="button"
								class="text-xs px-3 py-1.5 border border-ink-200 text-ink-700 hover:bg-ink-50"
								style="border-radius: 6px"
								@click="close"
							>
								{{ canEditForm ? __("Cancel") : __("Close") }}
							</button>
							<button
								v-if="canEditForm"
								type="button"
								class="text-xs desk-save-btn"
								:disabled="saving"
								@click="save"
							>
								{{ saving ? __("Saving…") : __("Save") }}
							</button>
						</div>
					</div>
				</div>
			</div>
		</Teleport>
	</DeskPage>
</template>
