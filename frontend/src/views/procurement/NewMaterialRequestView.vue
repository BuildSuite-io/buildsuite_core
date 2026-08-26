<script setup>
// Material Request form — create + edit (draft only). One project for the whole
// request (locked while editing — the request stays on its project) plus an
// editable list of item lines. Saved via the whitelisted save_material_request
// (the child items table can't go through the generic adapter). Status is
// workflow-driven, so it is never set from this form.
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { showToast } from "@/utils/appToast";
import { getMaterialRequest, saveMaterialRequest } from "@/data/procurementApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import { usePermissions } from "@/composables/usePermissions";
import { fmtINR } from "@/utils/format";

const route = useRoute();
const router = useRouter();
const { canEdit, canCreate } = usePermissions();

const editingId = computed(() => route.params.id || null);
const isEdit = computed(() => !!editingId.value);
const canSaveForm = computed(() =>
	isEdit.value ? canEdit("materialRequest") : canCreate("materialRequest")
);

function emptyLine() {
	return { item_code: "", description: "", qty: null, uom: "", rate: null };
}
function inDays(n) {
	return new Date(Date.now() + n * 86400000).toISOString().slice(0, 10);
}

const form = ref({
	project: route.query.project || "",
	schedule_date: inDays(7),
	lines: [emptyLine()],
});
const errors = ref({});
const saving = ref(false);

watch(
	editingId,
	async (id) => {
		if (!id) return;
		try {
			const mr = await getMaterialRequest(id);
			if (mr.state !== "Draft") {
				showToast("Only a draft request can be edited.", "error");
				router.replace(`/procurement/material-requests/${id}`);
				return;
			}
			form.value = {
				project: mr.project || "",
				schedule_date: mr.schedule_date || inDays(7),
				lines: (mr.items || []).map((it) => ({
					item_code: it.item_code || "",
					description: it.description || "",
					qty: it.qty,
					uom: it.uom || "",
					rate: it.rate ?? null,
				})),
			};
			if (!form.value.lines.length) form.value.lines = [emptyLine()];
		} catch (err) {
			showToast(err.message || "Failed to load request", "error");
		}
	},
	{ immediate: true }
);

const validLines = computed(() =>
	form.value.lines.filter((l) => l.item_code && Number(l.qty) > 0)
);
const total = computed(() =>
	validLines.value.reduce((a, l) => a + Number(l.qty) * (Number(l.rate) || 0), 0)
);

function addLine() {
	form.value.lines.push(emptyLine());
}
function removeLine(idx) {
	form.value.lines.splice(idx, 1);
	if (!form.value.lines.length) addLine();
}

function validate() {
	const e = {};
	if (!form.value.project) e.project = "Pick a project for the request.";
	if (!validLines.value.length) e.lines = "Add at least one item with a quantity.";
	errors.value = e;
	return Object.keys(e).length === 0;
}

async function onSave() {
	if (!validate()) return;
	saving.value = true;
	try {
		const mr = await saveMaterialRequest({
			name: editingId.value || undefined,
			project: form.value.project,
			schedule_date: form.value.schedule_date,
			items: validLines.value.map((l) => ({
				item_code: l.item_code,
				description: l.description,
				qty: Number(l.qty),
				uom: l.uom || null,
				rate: Number(l.rate) || 0,
			})),
		});
		showToast(isEdit.value ? "Request saved." : "Request raised.");
		router.push(`/procurement/material-requests/${mr.name}`);
	} catch (err) {
		showToast(err.message || "Failed to save request", "error");
	} finally {
		saving.value = false;
	}
}
function onCancel() {
	router.back();
}

const breadcrumbs = computed(() => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Procurement", to: "/procurement" },
	{ label: "Material Requests", to: "/procurement/material-requests" },
	isEdit.value
		? { label: editingId.value, to: `/procurement/material-requests/${editingId.value}` }
		: { label: "New" },
	...(isEdit.value ? [{ label: "Edit" }] : []),
]);
const pageTitle = computed(() =>
	isEdit.value ? `Edit ${editingId.value}` : "New Material Request"
);
const saveLabel = computed(() =>
	saving.value ? "Saving…" : isEdit.value ? "Save changes" : "Raise request"
);
</script>

<template>
	<DeskPage :title="pageTitle" :breadcrumbs="breadcrumbs">
		<div
			v-if="!canSaveForm"
			class="px-3 py-2 bg-warning-50 border border-warning-100 text-xs text-warning-700 dark:bg-ink-800 dark:border-ink-700"
			style="border-radius: 6px"
		>
			You don't have permission to {{ isEdit ? "edit this" : "create a" }} material request.
		</div>
		<DeskForm v-else>
			<template #action-bar>
				<DeskActionBar
					:save-label="saveLabel"
					:saving="saving"
					@save="onSave"
					@cancel="onCancel"
				/>
			</template>

			<DeskSection title="Request" :cols="2">
				<DeskField
					label="Project"
					required
					:error="errors.project"
					:hint="
						isEdit ? 'Locked while editing — the request stays on its project.' : ''
					"
				>
					<DeskLinkPicker
						v-model="form.project"
						doctype="Project"
						label-field="project_name"
						value-field="name"
						:search-fields="['project_name', 'name']"
						:disabled="isEdit"
						placeholder="— Select project —"
					/>
				</DeskField>
				<DeskField label="Needed by">
					<DeskInput v-model="form.schedule_date" type="date" />
				</DeskField>
			</DeskSection>

			<!-- Item lines -->
			<section class="mt-6">
				<div class="flex items-center justify-between mb-2 gap-3">
					<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
						Items
					</h3>
					<button
						type="button"
						class="text-xs text-brand-700 hover:underline"
						@click="addLine"
					>
						+ Add item
					</button>
				</div>
				<div class="bg-white border border-ink-200 rounded-lg overflow-x-auto">
					<table class="w-full text-xs" style="min-width: 720px">
						<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
							<tr>
								<th class="text-left px-3 py-2" style="min-width: 200px">Item</th>
								<th class="text-left px-3 py-2">Notes</th>
								<th class="text-right px-3 py-2 w-24">Qty</th>
								<th class="text-left px-3 py-2 w-32">UOM</th>
								<th class="text-right px-3 py-2 w-28">Est. rate</th>
								<th class="text-center px-2 py-2 w-8"></th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="(line, idx) in form.lines"
								:key="idx"
								class="border-t border-ink-100"
							>
								<td class="px-3 py-2" style="min-width: 200px">
									<DeskLinkPicker
										v-model="line.item_code"
										doctype="Item"
										label-field="item_name"
										value-field="name"
										:search-fields="['item_name', 'item_code', 'name']"
										placeholder="— Item —"
									/>
								</td>
								<td class="px-3 py-2">
									<input
										v-model="line.description"
										class="w-full bg-transparent text-xs py-1.5 focus:outline-none"
										placeholder="Brand, spec, where it's needed…"
									/>
								</td>
								<td class="px-3 py-2">
									<input
										v-model.number="line.qty"
										type="number"
										min="0"
										class="w-full bg-transparent text-xs text-right tabular-nums py-1.5 focus:outline-none"
										placeholder="Qty"
									/>
								</td>
								<td class="px-3 py-2" style="min-width: 120px">
									<DeskLinkPicker
										v-model="line.uom"
										doctype="UOM"
										label-field="name"
										value-field="name"
										placeholder="—"
									/>
								</td>
								<td class="px-3 py-2">
									<input
										v-model.number="line.rate"
										type="number"
										min="0"
										step="0.01"
										class="w-full bg-transparent text-xs text-right tabular-nums py-1.5 focus:outline-none"
										placeholder="—"
									/>
								</td>
								<td class="px-2 py-2 text-center">
									<button
										type="button"
										class="text-ink-400 hover:text-danger-600"
										title="Remove"
										@click="removeLine(idx)"
									>
										✕
									</button>
								</td>
							</tr>
						</tbody>
						<tfoot>
							<tr class="border-t-2 border-ink-200 bg-ink-50">
								<td
									colspan="4"
									class="px-3 py-2 text-right text-xs font-semibold text-ink-700 uppercase tracking-wider"
								>
									Estimated value
								</td>
								<td
									class="px-3 py-2 text-right tabular-nums text-sm font-semibold text-ink-900"
								>
									{{ fmtINR(total) }}
								</td>
								<td></td>
							</tr>
						</tfoot>
					</table>
				</div>
				<p v-if="errors.lines" class="text-xs text-danger-700 mt-1">{{ errors.lines }}</p>
			</section>
		</DeskForm>
	</DeskPage>
</template>
