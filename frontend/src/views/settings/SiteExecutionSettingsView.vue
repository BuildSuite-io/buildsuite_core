<script setup>
// Site Execution Settings — the reports shown in the Site Execution workspace.
// Each row is a Frappe report + icon + description; row order = display order.
// Admin / BSA only.

import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import { showToast } from "@/utils/appToast";
import { getSiteExecutionSettings, setSiteExecutionReports } from "@/data/siteExecutionApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";

const store = useDataStore();
const router = useRouter();

const reports = ref([]);
const saving = ref(false);
const loading = ref(true);

async function load() {
	loading.value = true;
	try {
		const res = await getSiteExecutionSettings();
		reports.value = (res?.reports || []).map((r) => ({ ...r }));
	} catch (err) {
		showToast(err.message || "Failed to load settings", "error");
	} finally {
		loading.value = false;
	}
}

function addReport() {
	reports.value.push({ report: "", icon: "file-text", description: "" });
}
function removeReport(i) {
	reports.value.splice(i, 1);
}
function move(i, delta) {
	const j = i + delta;
	if (j < 0 || j >= reports.value.length) return;
	const [row] = reports.value.splice(i, 1);
	reports.value.splice(j, 0, row);
}

async function save() {
	if (saving.value) return;
	const bad = reports.value.find((r) => !r.report);
	if (bad) {
		showToast("Every row needs a report selected.", "error");
		return;
	}
	saving.value = true;
	try {
		const res = await setSiteExecutionReports(reports.value);
		reports.value = (res?.reports || []).map((r) => ({ ...r }));
		showToast("Site Execution reports saved");
	} catch (err) {
		showToast(err.message || "Failed to save", "error");
	} finally {
		saving.value = false;
	}
}

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Settings", to: "/settings" },
	{ label: "Site Execution Settings" },
];

onMounted(() => {
	if (!store.isAdmin && !store.isBSA) {
		router.replace("/settings");
		return;
	}
	load();
});
</script>

<template>
	<DeskPage
		title="Site Execution Settings"
		subtitle="Reports shown in the Site Execution workspace"
		:breadcrumbs="breadcrumbs"
	>
		<DeskForm>
			<template #action-bar>
				<DeskActionBar
					:save-label="saving ? 'Saving…' : 'Save reports'"
					:saving="saving"
					@save="save"
					@cancel="load"
				/>
			</template>

			<div v-if="loading" class="py-12 text-center text-sm text-ink-500">Loading…</div>

			<DeskSection v-else title="Workspace reports" :cols="1">
				<p class="text-sm text-ink-500 -mt-1">
					Each report opens in the Site Execution workspace, in the order below. Pick a
					Frappe report, an icon slug (e.g. chart-line, file-text, calendar), and a short
					description.
				</p>
				<div class="overflow-x-auto">
					<table class="w-full text-sm">
						<thead>
							<tr class="text-left text-ink-500 border-b border-ink-100">
								<th class="py-1.5 pr-2 font-medium w-8">#</th>
								<th class="py-1.5 pr-2 font-medium w-64">Report</th>
								<th class="py-1.5 pr-2 font-medium w-32">Icon</th>
								<th class="py-1.5 pr-2 font-medium">Description</th>
								<th class="w-20"></th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="(r, i) in reports" :key="i" class="border-b border-ink-50">
								<td class="py-1 pr-2 text-ink-400 tabular-nums">{{ i + 1 }}</td>
								<td class="py-1 pr-2">
									<DeskLinkPicker
										v-model="r.report"
										doctype="Report"
										placeholder="Select report"
										label-field="report_name"
										value-field="name"
										:search-fields="['report_name', 'name']"
										:page-length="20"
									/>
								</td>
								<td class="py-1 pr-2">
									<DeskInput v-model="r.icon" placeholder="file-text" />
								</td>
								<td class="py-1 pr-2">
									<DeskInput
										v-model="r.description"
										placeholder="Short description"
									/>
								</td>
								<td class="py-1 text-center whitespace-nowrap">
									<button
										class="text-ink-400 hover:text-ink-700 px-1 disabled:opacity-30"
										:disabled="i === 0"
										title="Move up"
										@click="move(i, -1)"
									>
										↑
									</button>
									<button
										class="text-ink-400 hover:text-ink-700 px-1 disabled:opacity-30"
										:disabled="i === reports.length - 1"
										title="Move down"
										@click="move(i, 1)"
									>
										↓
									</button>
									<button
										class="text-ink-400 hover:text-danger-600 px-1"
										title="Remove"
										@click="removeReport(i)"
									>
										×
									</button>
								</td>
							</tr>
							<tr v-if="!reports.length">
								<td colspan="5" class="py-3 text-center text-ink-400">
									No reports configured yet.
								</td>
							</tr>
						</tbody>
					</table>
				</div>
				<button class="mt-2 text-sm text-brand-600 hover:underline" @click="addReport">
					+ Add report
				</button>
			</DeskSection>
		</DeskForm>
	</DeskPage>
</template>
