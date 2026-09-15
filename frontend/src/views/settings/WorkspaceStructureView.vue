<script setup>
// Workspace Structure — BSA/Admin editor for the per-workspace quick-nav shortcut tiles.
// Backed by the BuildSuite Workspace Shortcut registry (get/set via api.workspace_setting),
// so edits are real, server-side, and role-filtered — the Site Execution landing (and any
// other workspace) renders its shortcut grid from the same source. Each shortcut can be
// restricted to a subset of the workspace's roles; no restriction = every role that can see
// the workspace sees the shortcut.

import { ref, computed, onMounted } from "vue";
import { RouterLink } from "vue-router";
import { useDataStore } from "@/stores";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import { getWorkspaceShortcutsConfig, setWorkspaceShortcuts } from "@/data/workspaceSettingApi";
import { showToast } from "@/utils/appToast";

const store = useDataStore();

// [{ slug, label, available_roles:[roleName], shortcuts:[{label,icon,route,sort_order,enabled,roles:[roleName]}] }]
const config = ref([]);
const editing = ref(false);
const saving = ref(false);
const loading = ref(true);

async function load() {
	loading.value = true;
	try {
		config.value = await getWorkspaceShortcutsConfig();
	} catch (e) {
		config.value = [];
		showToast(e.message || "Could not load workspace shortcuts.", "error");
	} finally {
		loading.value = false;
	}
}
onMounted(load);

const canEdit = computed(() => store.isBSA || store.isAdmin);
const totalShortcuts = computed(() =>
	config.value.reduce((sum, w) => sum + (w.shortcuts?.length || 0), 0)
);

function startEdit() {
	editing.value = true;
}
async function cancelEdit() {
	editing.value = false;
	await load(); // discard local edits
}
async function save() {
	if (!canEdit.value) return;
	saving.value = true;
	try {
		for (const ws of config.value) {
			const rows = (ws.shortcuts || []).filter((s) => s.label?.trim() && s.route?.trim());
			await setWorkspaceShortcuts(ws.slug, rows);
		}
		showToast("Workspace shortcuts saved.");
		editing.value = false;
		await load();
	} catch (e) {
		showToast(e.message || "Could not save.", "error");
	} finally {
		saving.value = false;
	}
}
function onPrimary() {
	editing.value ? save() : startEdit();
}

// --- shortcut row ops (local until Save) ---
function addShortcut(ws) {
	const nextOrder = (ws.shortcuts || []).reduce((m, s) => Math.max(m, s.sort_order || 0), 0) + 1;
	ws.shortcuts.push({ label: "", icon: "🔗", route: "/", sort_order: nextOrder, enabled: true, roles: [] });
}
function removeShortcut(ws, i) {
	ws.shortcuts.splice(i, 1);
}
function moveShortcut(ws, i, dir) {
	const t = i + dir;
	if (t < 0 || t >= ws.shortcuts.length) return;
	const rows = ws.shortcuts;
	[rows[i], rows[t]] = [rows[t], rows[i]];
	rows.forEach((s, idx) => (s.sort_order = idx + 1));
}
function toggleRole(sc, role) {
	const i = sc.roles.indexOf(role);
	if (i >= 0) sc.roles.splice(i, 1);
	else sc.roles.push(role);
}
// "BuildSuite Foreman" -> "Foreman"; "System Manager" stays.
const roleLabel = (r) => r.replace(/^BuildSuite /, "");
const scVisibility = (sc) => (sc.roles?.length ? sc.roles.map(roleLabel).join(", ") : "Everyone");

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Settings", to: "/settings" },
	{ label: "Workspace Structure" },
];
</script>

<template>
	<DeskPage
		title="Workspace Structure"
		subtitle="Configure the quick-nav shortcut tiles shown on each workspace"
		:breadcrumbs="breadcrumbs"
	>
		<DeskForm>
			<template #action-bar>
				<DeskActionBar
					v-if="canEdit"
					:save-label="editing ? (saving ? 'Saving…' : 'Save') : 'Edit'"
					:show-cancel="editing"
					:saving="saving"
					cancel-label="Cancel"
					@save="onPrimary"
					@cancel="cancelEdit"
				>
					<template #left>
						<span class="text-[11px] text-ink-500">
							{{ config.length }} workspace{{ config.length === 1 ? "" : "s" }} ·
							{{ totalShortcuts }} shortcuts
						</span>
					</template>
				</DeskActionBar>
				<div
					v-else
					class="px-3 py-2 bg-warning-50 border-b border-warning-100 text-xs text-warning-700"
				>
					Read-only. Editing requires the BuildSuite Administrator role.
				</div>
			</template>

			<div class="max-w-4xl mx-auto">
				<div v-if="loading" class="px-4 py-6 text-sm text-ink-500">Loading…</div>

				<DeskSection v-for="ws in config" :key="ws.slug" :title="ws.label">
					<div class="md:col-span-2">
						<div
							v-if="(ws.shortcuts || []).length"
							class="border border-ink-200"
							style="border-radius: 2px"
						>
							<div
								v-for="(sc, scIdx) in ws.shortcuts"
								:key="scIdx"
								class="flex items-start gap-2 border-b border-ink-100 last:border-b-0 px-2 py-2 text-sm"
							>
								<!-- Reorder (edit only) -->
								<div v-if="editing" class="flex flex-col items-center gap-0.5 pt-1">
									<button
										type="button"
										class="text-[9px] px-1 border border-ink-200 bg-white hover:bg-ink-50"
										style="border-radius: 2px"
										:disabled="scIdx === 0"
										:class="scIdx === 0 ? 'opacity-30 cursor-not-allowed' : ''"
										@click="moveShortcut(ws, scIdx, -1)"
									>
										▲
									</button>
									<button
										type="button"
										class="text-[9px] px-1 border border-ink-200 bg-white hover:bg-ink-50"
										style="border-radius: 2px"
										:disabled="scIdx === ws.shortcuts.length - 1"
										:class="scIdx === ws.shortcuts.length - 1 ? 'opacity-30 cursor-not-allowed' : ''"
										@click="moveShortcut(ws, scIdx, +1)"
									>
										▼
									</button>
								</div>

								<div class="flex-1 min-w-0">
									<!-- Icon / Label / Route -->
									<div class="flex items-center gap-2">
										<template v-if="editing">
											<DeskInput v-model="sc.icon" class="!text-base !w-10 !text-center" />
											<DeskInput v-model="sc.label" placeholder="Label" class="!text-xs !flex-1" />
											<DeskInput v-model="sc.route" placeholder="/route" class="!text-xs !flex-1 !font-mono" />
											<label class="flex items-center gap-1 text-[11px] text-ink-600">
												<input type="checkbox" v-model="sc.enabled" class="accent-brand-600" />
												On
											</label>
										</template>
										<template v-else>
											<span class="text-base">{{ sc.icon }}</span>
											<span class="text-ink-900 font-medium">{{ sc.label }}</span>
											<span class="text-xs font-mono text-ink-500">{{ sc.route }}</span>
											<span v-if="!sc.enabled" class="text-[10px] text-ink-400 italic">(off)</span>
										</template>
									</div>

									<!-- Visible-to roles -->
									<div class="mt-1.5 text-[11px]">
										<template v-if="editing">
											<span class="text-ink-500 mr-1">Visible to:</span>
											<label
												v-for="role in ws.available_roles"
												:key="role"
												class="inline-flex items-center gap-1 mr-2 text-ink-700"
											>
												<input
													type="checkbox"
													:checked="sc.roles.includes(role)"
													class="accent-brand-600"
													@change="toggleRole(sc, role)"
												/>
												{{ roleLabel(role) }}
											</label>
											<span v-if="!sc.roles.length" class="text-ink-400 italic ml-1">
												(none checked = everyone who can see this workspace)
											</span>
										</template>
										<template v-else>
											<span class="text-ink-500">Visible to:</span>
											<span class="text-ink-700 ml-1">{{ scVisibility(sc) }}</span>
										</template>
									</div>
								</div>

								<button
									v-if="editing"
									type="button"
									class="text-[11px] text-danger-600 hover:text-danger-800 px-1 pt-1"
									@click="removeShortcut(ws, scIdx)"
								>
									Remove
								</button>
							</div>
						</div>
						<div v-else class="text-xs text-ink-400 italic px-1 py-2">No shortcuts.</div>

						<button
							v-if="editing"
							type="button"
							class="mt-2 text-[11px] text-brand-700 hover:underline"
							@click="addShortcut(ws)"
						>
							+ Add shortcut
						</button>
					</div>
				</DeskSection>

				<div v-if="!loading && !config.length" class="px-4 py-6 text-sm text-ink-500">
					No workspaces configured.
					<RouterLink to="/settings" class="text-brand-700 hover:underline">Back to Settings</RouterLink>
				</div>
			</div>
		</DeskForm>
	</DeskPage>
</template>
