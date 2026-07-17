<script setup>
// Workspace Setting — the report-style shortcut tiles shown in each live BuildSuite
// workspace. One tab per workspace; each row is a tile (label + destination + icon +
// description), row order = display order. Destination is a linked Frappe Report OR an
// explicit route (in-app path or Desk URL). Admin / BSA only.

import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import { showToast } from "@/utils/appToast";
import { getWorkspaceSettings, setWorkspaceReports } from "@/data/workspaceSettingApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";

const store = useDataStore();
const router = useRouter();

const workspaces = ref([]); // [{ slug, label }]
const byWorkspace = ref({}); // { slug: [row, …] }
const activeSlug = ref("");
const saving = ref(false);
const loading = ref(true);

const rows = computed(() => byWorkspace.value[activeSlug.value] || []);

async function load() {
	loading.value = true;
	try {
		const res = await getWorkspaceSettings();
		workspaces.value = res?.workspaces || [];
		const map = {};
		for (const w of workspaces.value) {
			map[w.slug] = (res?.reports?.[w.slug] || []).map((r) => ({ ...r }));
		}
		byWorkspace.value = map;
		if (!activeSlug.value && workspaces.value.length)
			activeSlug.value = workspaces.value[0].slug;
	} catch (err) {
		showToast(err.message || "Failed to load settings", "error");
	} finally {
		loading.value = false;
	}
}

function addReport() {
	rows.value.push({ label: "", report: "", route: "", icon: "file-text", description: "" });
}
function removeReport(i) {
	rows.value.splice(i, 1);
}
function move(i, delta) {
	const j = i + delta;
	if (j < 0 || j >= rows.value.length) return;
	const [row] = rows.value.splice(i, 1);
	rows.value.splice(j, 0, row);
}

async function save() {
	if (saving.value) return;
	const bad = rows.value.find((r) => !r.report && !(r.route || "").trim());
	if (bad) {
		showToast("Every row needs a report or a route.", "error");
		return;
	}
	saving.value = true;
	try {
		const res = await setWorkspaceReports(activeSlug.value, rows.value);
		// re-hydrate all workspaces from the authoritative response
		const map = {};
		for (const w of workspaces.value) {
			map[w.slug] = (res?.reports?.[w.slug] || []).map((r) => ({ ...r }));
		}
		byWorkspace.value = map;
		showToast(`${activeLabel.value} reports saved`);
	} catch (err) {
		showToast(err.message || "Failed to save", "error");
	} finally {
		saving.value = false;
	}
}

const activeLabel = computed(
	() => workspaces.value.find((w) => w.slug === activeSlug.value)?.label || "Workspace",
);

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Settings", to: "/settings" },
	{ label: "Workspace Setting" },
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
		title="Workspace Setting"
		subtitle="Report-style shortcut tiles shown in each workspace"
		:breadcrumbs="breadcrumbs"
	>
		<DeskForm>
			<template #action-bar>
				<DeskActionBar
					:save-label="saving ? 'Saving…' : `Save ${activeLabel} reports`"
					:saving="saving"
					@save="save"
					@cancel="load"
				/>
			</template>

			<div v-if="loading" class="py-12 text-center text-sm text-ink-500">Loading…</div>

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

				<DeskSection :title="`${activeLabel} reports`" :cols="1">
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
									<th class="py-1.5 pr-2 font-medium w-44">Label</th>
									<th class="py-1.5 pr-2 font-medium w-52">Report</th>
									<th class="py-1.5 pr-2 font-medium w-52">Route</th>
									<th class="py-1.5 pr-2 font-medium w-28">Icon</th>
									<th class="py-1.5 pr-2 font-medium">Description</th>
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
										<DeskInput v-model="r.label" placeholder="Tile title" />
									</td>
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
										<DeskInput
											v-model="r.route"
											placeholder="/path or /app/…"
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
									<td class="py-1 text-center whitespace-nowrap pt-2">
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
											:disabled="i === rows.length - 1"
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
								<tr v-if="!rows.length">
									<td colspan="7" class="py-3 text-center text-ink-400">
										No reports configured for {{ activeLabel }} yet.
									</td>
								</tr>
							</tbody>
						</table>
					</div>
					<button class="mt-2 text-sm text-brand-600 hover:underline" @click="addReport">
						+ Add report
					</button>
				</DeskSection>
			</template>
		</DeskForm>
	</DeskPage>
</template>
