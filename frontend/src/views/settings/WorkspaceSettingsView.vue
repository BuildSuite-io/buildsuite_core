<script setup>
// Workspace Setting — the report-style shortcut tiles shown in each live BuildSuite
// workspace. One tab per workspace; each row is a tile (label + destination + icon +
// description), row order = display order. Destination is a linked Frappe Report OR an
// explicit route (in-app path or Desk URL). Admin / BSA only.

import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import { showToast } from "@/utils/appToast";
import { __ } from "@/utils/translate";
import {
	getWorkspaceSettings,
	setWorkspaceReports,
	setWorkspaceDoctypes,
} from "@/data/workspaceSettingApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";

const store = useDataStore();
const router = useRouter();

const workspaces = ref([]); // [{ slug, label }]
const byWorkspace = ref({}); // { slug: [report row, …] }
const docByWorkspace = ref({}); // { slug: [doctype row, …] }
const activeSlug = ref("");
const saving = ref(false);
const loading = ref(true);

const rows = computed(() => byWorkspace.value[activeSlug.value] || []);
const docRows = computed(() => docByWorkspace.value[activeSlug.value] || []);

// Rebuild the per-workspace report + doctype maps from an authoritative response.
function hydrate(res) {
	const rmap = {};
	const dmap = {};
	for (const w of workspaces.value) {
		rmap[w.slug] = (res?.reports?.[w.slug] || []).map((r) => ({ ...r }));
		dmap[w.slug] = (res?.doctypes?.[w.slug] || []).map((r) => ({ ...r }));
	}
	byWorkspace.value = rmap;
	docByWorkspace.value = dmap;
}

async function load() {
	loading.value = true;
	try {
		const res = await getWorkspaceSettings();
		workspaces.value = res?.workspaces || [];
		hydrate(res);
		if (!activeSlug.value && workspaces.value.length)
			activeSlug.value = workspaces.value[0].slug;
	} catch (err) {
		showToast(err.message || __("Failed to load settings"), "error");
	} finally {
		loading.value = false;
	}
}

function move(arr, i, delta) {
	const j = i + delta;
	if (j < 0 || j >= arr.length) return;
	const [row] = arr.splice(i, 1);
	arr.splice(j, 0, row);
}

function addReport() {
	rows.value.push({ label: "", report: "", route: "", icon: "file-text", description: "" });
}
function removeReport(i) {
	rows.value.splice(i, 1);
}
function addRecord() {
	docRows.value.push({ label: "", doctype: "", icon: "file-text", description: "" });
}
function removeRecord(i) {
	docRows.value.splice(i, 1);
}

async function save() {
	if (saving.value) return;
	if (rows.value.find((r) => !r.report && !(r.route || "").trim())) {
		showToast(__("Every report row needs a report or a route."), "error");
		return;
	}
	if (docRows.value.find((r) => !(r.doctype || "").trim())) {
		showToast(__("Every record row needs a DocType."), "error");
		return;
	}
	saving.value = true;
	try {
		await setWorkspaceReports(activeSlug.value, rows.value);
		const res = await setWorkspaceDoctypes(activeSlug.value, docRows.value);
		hydrate(res); // final response carries both maps
		showToast(__("{0} saved", [activeLabel.value]));
	} catch (err) {
		showToast(err.message || __("Failed to save"), "error");
	} finally {
		saving.value = false;
	}
}

const activeLabel = computed(
	() => workspaces.value.find((w) => w.slug === activeSlug.value)?.label || __("Workspace"),
);

const breadcrumbs = [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: __("Settings"), to: "/settings" },
	{ label: __("Workspace Setting") },
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
		:title="__('Workspace Setting')"
		:subtitle="__('Report-style shortcut tiles shown in each workspace')"
		:breadcrumbs="breadcrumbs"
	>
		<DeskForm>
			<template #action-bar>
				<DeskActionBar
					:save-label="saving ? __('Saving…') : __('Save {0}', [activeLabel])"
					:saving="saving"
					@save="save"
					@cancel="load"
				/>
			</template>

			<div v-if="loading" class="py-12 text-center text-sm text-ink-500">{{ __("Loading…") }}</div>

			<template v-else>
				<!-- Workspace tabs -->
				<div class="flex items-center gap-1 border-b border-ink-200 mb-4 overflow-x-auto">
					<button
						v-for="w in workspaces"
						:key="w.slug"
						class="px-3 py-2 text-sm whitespace-nowrap border-b-2 -mb-px transition-colors"
						:class="
							activeSlug === w.slug
								? 'border-brand-600 text-brand-700 font-medium'
								: 'border-transparent text-ink-500 hover:text-ink-800'
						"
						@click="activeSlug = w.slug"
					>
						{{ w.label }}
						<span v-if="byWorkspace[w.slug]?.length" class="text-[10px] text-ink-400"
							>· {{ byWorkspace[w.slug].length }}</span
						>
					</button>
				</div>

				<DeskSection :title="__('{0} reports', [activeLabel])" :cols="1">
					<p class="text-sm text-ink-500 -mt-1">
						Tiles render in the {{ activeLabel }} workspace in the order below. Set a
						<strong>Report</strong> (its Desk route is used) <em>or</em> a
						<strong>Route</strong> (an in-app path like
						<code>/subcontractor-work-orders</code>, or a Desk URL like
						<code>/app/query-report/Stock Balance</code>). Route overrides Report.
					</p>
					<div class="overflow-x-auto">
						<table class="w-full text-sm">
							<thead>
								<tr class="text-left text-ink-500 border-b border-ink-100">
									<th class="py-1.5 pr-2 font-medium w-8">#</th>
									<th class="py-1.5 pr-2 font-medium w-44">{{ __("Label") }}</th>
									<th class="py-1.5 pr-2 font-medium w-52">{{ __("Report") }}</th>
									<th class="py-1.5 pr-2 font-medium w-52">{{ __("Route") }}</th>
									<th class="py-1.5 pr-2 font-medium w-28">{{ __("Icon") }}</th>
									<th class="py-1.5 pr-2 font-medium">{{ __("Description") }}</th>
									<th class="w-20"></th>
								</tr>
							</thead>
							<tbody>
								<tr
									v-for="(r, i) in rows"
									:key="i"
									class="border-b border-ink-50 align-top"
								>
									<td class="py-1 pr-2 text-ink-400 tabular-nums pt-2.5">
										{{ i + 1 }}
									</td>
									<td class="py-1 pr-2">
										<DeskInput v-model="r.label" :placeholder="__('Tile title')" />
									</td>
									<td class="py-1 pr-2">
										<DeskLinkPicker
											v-model="r.report"
											doctype="Report"
											:placeholder="__('Select report')"
											label-field="report_name"
											value-field="name"
											:search-fields="['report_name', 'name']"
											:page-length="20"
										/>
									</td>
									<td class="py-1 pr-2">
										<DeskInput
											v-model="r.route"
											:placeholder="__('/path or /app/…')"
										/>
									</td>
									<td class="py-1 pr-2">
										<DeskInput v-model="r.icon" placeholder="file-text" />
									</td>
									<td class="py-1 pr-2">
										<DeskInput
											v-model="r.description"
											:placeholder="__('Short description')"
										/>
									</td>
									<td class="py-1 text-center whitespace-nowrap pt-2">
										<button
											class="text-ink-400 hover:text-ink-700 px-1 disabled:opacity-30"
											:disabled="i === 0"
											:title="__('Move up')"
											@click="move(rows, i, -1)"
										>
											↑
										</button>
										<button
											class="text-ink-400 hover:text-ink-700 px-1 disabled:opacity-30"
											:disabled="i === rows.length - 1"
											:title="__('Move down')"
											@click="move(rows, i, 1)"
										>
											↓
										</button>
										<button
											class="text-ink-400 hover:text-danger-600 px-1"
											:title="__('Remove')"
											@click="removeReport(i)"
										>
											×
										</button>
									</td>
								</tr>
								<tr v-if="!rows.length">
									<td colspan="7" class="py-3 text-center text-ink-400">
										{{ __("No reports configured for {0} yet.", [activeLabel]) }}
									</td>
								</tr>
							</tbody>
						</table>
					</div>
					<button class="mt-2 text-sm text-brand-600 hover:underline" @click="addReport">
						{{ __("+ Add report") }}
					</button>
				</DeskSection>

				<DeskSection :title="__('{0} records', [activeLabel])" :cols="1">
					<p class="text-sm text-ink-500 -mt-1">
						DocType tiles render in the {{ activeLabel }} workspace's
						<strong>Records</strong> group. Each opens the generic list + add/edit form
						for that DocType (columns and filters come from the DocType's own fields).
					</p>
					<div class="overflow-x-auto">
						<table class="w-full text-sm">
							<thead>
								<tr class="text-left text-ink-500 border-b border-ink-100">
									<th class="py-1.5 pr-2 font-medium w-8">#</th>
									<th class="py-1.5 pr-2 font-medium w-44">{{ __("Label") }}</th>
									<th class="py-1.5 pr-2 font-medium w-52">{{ __("DocType") }}</th>
									<th class="py-1.5 pr-2 font-medium w-28">{{ __("Icon") }}</th>
									<th class="py-1.5 pr-2 font-medium">{{ __("Description") }}</th>
									<th class="w-20"></th>
								</tr>
							</thead>
							<tbody>
								<tr
									v-for="(r, i) in docRows"
									:key="i"
									class="border-b border-ink-50 align-top"
								>
									<td class="py-1 pr-2 text-ink-400 tabular-nums pt-2.5">
										{{ i + 1 }}
									</td>
									<td class="py-1 pr-2">
										<DeskInput
											v-model="r.label"
											:placeholder="__('Tile title (defaults to DocType)')"
										/>
									</td>
									<td class="py-1 pr-2">
										<DeskLinkPicker
											v-model="r.doctype"
											doctype="DocType"
											:placeholder="__('Select DocType')"
											value-field="name"
											:search-fields="['name']"
											:page-length="20"
										/>
									</td>
									<td class="py-1 pr-2">
										<DeskInput v-model="r.icon" placeholder="file-text" />
									</td>
									<td class="py-1 pr-2">
										<DeskInput
											v-model="r.description"
											:placeholder="__('Short description')"
										/>
									</td>
									<td class="py-1 text-center whitespace-nowrap pt-2">
										<button
											class="text-ink-400 hover:text-ink-700 px-1 disabled:opacity-30"
											:disabled="i === 0"
											:title="__('Move up')"
											@click="move(docRows, i, -1)"
										>
											↑
										</button>
										<button
											class="text-ink-400 hover:text-ink-700 px-1 disabled:opacity-30"
											:disabled="i === docRows.length - 1"
											:title="__('Move down')"
											@click="move(docRows, i, 1)"
										>
											↓
										</button>
										<button
											class="text-ink-400 hover:text-danger-600 px-1"
											:title="__('Remove')"
											@click="removeRecord(i)"
										>
											×
										</button>
									</td>
								</tr>
								<tr v-if="!docRows.length">
									<td colspan="6" class="py-3 text-center text-ink-400">
										{{ __("No records configured for {0} yet.", [activeLabel]) }}
									</td>
								</tr>
							</tbody>
						</table>
					</div>
					<button class="mt-2 text-sm text-brand-600 hover:underline" @click="addRecord">
						{{ __("+ Add record") }}
					</button>
				</DeskSection>
			</template>
		</DeskForm>
	</DeskPage>
</template>
