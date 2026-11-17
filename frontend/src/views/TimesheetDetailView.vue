<script setup>
// Timesheet detail — read-only once submitted. A draft can be edited, submitted or deleted; a submitted
// timesheet can be cancelled (its rows leave the registers and the cost leaves the estimate).

import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import DeskPage from "@/components/desk/DeskPage.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import AccessDenied from "@/components/AccessDenied.vue";
import { useConfirm } from "@/composables/useConfirm";
import { usePermissions } from "@/composables/usePermissions";
import { getTimesheet, submitTimesheet, cancelTimesheet } from "@/data/timesheetApi";
import { DOCSTATUS_LABELS } from "@/utils/workforceForms";
import { isPermissionDenied } from "@/utils/frappeError";
import { showToast } from "@/utils/appToast";
import { fmtDate, fmtINR } from "@/utils/format";
import { __ } from "@/utils/translate";

const props = defineProps({ id: String });
const router = useRouter();
const confirmDialog = useConfirm();
const { canEdit, canSubmit } = usePermissions();

const doc = ref(null);
const loading = ref(true);
const loadError = ref(null);
const busy = ref(false);
const accessDenied = computed(() => isPermissionDenied(loadError.value));

async function load() {
	loading.value = true;
	loadError.value = null;
	try {
		doc.value = await getTimesheet(props.id);
	} catch (err) {
		doc.value = null;
		loadError.value = err;
	} finally {
		loading.value = false;
	}
}
watch(() => props.id, load, { immediate: true });

const isDraft = computed(() => doc.value?.docstatus === 0);
const isSubmitted = computed(() => doc.value?.docstatus === 1);
const statusLabel = computed(() => DOCSTATUS_LABELS[doc.value?.docstatus] || "Draft");
const overtimeHours = computed(() =>
	(doc.value?.rows || []).filter((r) => r.is_overtime).reduce((a, r) => a + r.hours, 0)
);

async function act(fn, done) {
	busy.value = true;
	try {
		doc.value = await fn(props.id);
		showToast(done);
	} catch (err) {
		showToast(err.message || __("That did not work."), "error");
	} finally {
		busy.value = false;
	}
}
const onSubmit = () => act(submitTimesheet, __("Timesheet submitted"));
async function onCancel() {
	const ok = await confirmDialog({
		title: __("Cancel timesheet"),
		message: __(
			"Cancel {0}? Its rows leave the labour registers and its cost leaves the estimate.",
			[props.id]
		),
		confirmLabel: __("Cancel timesheet"),
		destructive: true,
	});
	if (ok) act(cancelTimesheet, __("Timesheet cancelled"));
}

const breadcrumbs = computed(() => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: __("Workforce"), to: "/workforce" },
	{ label: __("Timesheets"), to: "/timesheets" },
	{ label: props.id },
]);
const cards = computed(() => {
	const d = doc.value;
	if (!d) return [];
	return [
		{ label: __("Worker"), value: d.employee_name || d.employee },
		{ label: __("Date"), value: fmtDate(d.date) || "—" },
		{
			label: __("Hours"),
			value: overtimeHours.value
				? `${d.total_hours} (${overtimeHours.value} OT)`
				: d.total_hours,
		},
		{ label: __("Labour cost"), value: fmtINR(d.total_costing_amount) },
	];
});
</script>

<template>
	<DeskPage v-if="doc" :title="doc.name" :breadcrumbs="breadcrumbs" :status="statusLabel">
		<template #actions>
			<button
				v-if="isDraft && canEdit('fieldAttendance')"
				type="button"
				class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
				style="border-radius: 6px"
				@click="router.push(`/timesheets/${doc.name}/edit`)"
			>
				{{ __("Edit") }}
			</button>
			<button
				v-if="isDraft && canSubmit('fieldAttendance')"
				type="button"
				class="desk-save-btn !text-xs"
				:disabled="busy"
				@click="onSubmit"
			>
				{{ __("Submit") }}
			</button>
			<button
				v-if="isSubmitted && canSubmit('fieldAttendance')"
				type="button"
				class="text-xs px-2.5 py-1 border border-danger-200 bg-white hover:bg-danger-50 text-danger-700"
				style="border-radius: 6px"
				:disabled="busy"
				@click="onCancel"
			>
				{{ __("Cancel") }}
			</button>
		</template>

		<div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
			<div
				v-for="c in cards"
				:key="c.label"
				class="border border-ink-200 bg-white p-3"
				style="border-radius: 8px"
			>
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ c.label }}
				</div>
				<div class="text-sm font-semibold text-ink-900 tabular-nums mt-1">
					{{ c.value }}
				</div>
			</div>
		</div>

		<div class="bg-white border border-ink-200 rounded-lg overflow-x-auto">
			<table class="w-full text-xs" style="min-width: 900px">
				<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
					<tr>
						<th class="text-left px-3 py-2 w-8">#</th>
						<th class="text-left px-3 py-2">{{ __("Project") }}</th>
						<th class="text-left px-3 py-2">{{ __("Cost code") }}</th>
						<th class="text-right px-3 py-2">{{ __("Hours") }}</th>
						<th class="text-center px-3 py-2">{{ __("OT") }}</th>
						<th class="text-left px-3 py-2">{{ __("Description") }}</th>
						<th class="text-right px-3 py-2">{{ __("Full day") }}</th>
						<th class="text-right px-3 py-2">{{ __("Rate / hr") }}</th>
						<th class="text-right px-3 py-2">{{ __("Amount") }}</th>
					</tr>
				</thead>
				<tbody>
					<tr
						v-for="(r, i) in doc.rows"
						:key="r.name"
						class="border-t border-ink-100 align-top"
					>
						<td class="px-3 py-2 text-ink-500 tabular-nums">{{ i + 1 }}</td>
						<td class="px-3 py-2 text-ink-900">{{ r.project_name || r.project }}</td>
						<td class="px-3 py-2 text-ink-700">
							<span v-if="r.cost_code">{{ r.cost_code.label }}</span>
							<span v-else class="text-ink-400 italic">{{ __("Not coded") }}</span>
						</td>
						<td class="px-3 py-2 text-right tabular-nums">{{ r.hours }}</td>
						<td class="px-3 py-2 text-center">{{ r.is_overtime ? "OT" : "" }}</td>
						<td class="px-3 py-2 text-ink-600">{{ r.description || "—" }}</td>
						<td class="px-3 py-2 text-right tabular-nums text-ink-600">
							{{ r.full_day_hours }} h
						</td>
						<td class="px-3 py-2 text-right tabular-nums text-ink-600">
							{{ fmtINR(r.costing_rate) }}
						</td>
						<td class="px-3 py-2 text-right tabular-nums font-medium text-ink-900">
							{{ fmtINR(r.costing_amount) }}
						</td>
					</tr>
				</tbody>
				<tfoot class="border-t border-ink-200 bg-ink-50">
					<tr>
						<td colspan="3" class="px-3 py-2 text-right text-ink-500">
							{{ __("Total") }}
						</td>
						<td class="px-3 py-2 text-right tabular-nums font-semibold">
							{{ doc.total_hours }}
						</td>
						<td colspan="4"></td>
						<td class="px-3 py-2 text-right tabular-nums font-semibold">
							{{ fmtINR(doc.total_costing_amount) }}
						</td>
					</tr>
				</tfoot>
			</table>
		</div>
		<p v-if="doc.note" class="text-xs text-ink-600 mt-4">{{ doc.note }}</p>
	</DeskPage>

	<AccessDenied v-else-if="accessDenied" />
	<div v-else-if="loading" class="px-3 py-2 text-sm text-ink-500">
		{{ __("Loading timesheet…") }}
	</div>
	<div v-else class="px-3 py-2 text-sm text-danger-700">
		{{ loadError?.message || __("Timesheet not found.") }}
	</div>
</template>
