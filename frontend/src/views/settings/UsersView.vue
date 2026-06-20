<script setup>
// Users — Settings sub-page. Admin-only management of real Frappe Users.
// Lists users carrying a BuildSuite persona; create / edit persona / enable-
// disable / resend welcome / send password-reset. Persona drives the BuildSuite
// role server-side (sync_persona_roles hook).

import { computed, ref, reactive, onMounted } from "vue";
import { useRouter, useRoute, RouterLink } from "vue-router";
import { useDataStore } from "@/stores";
import {
	listBuildsuiteUsers,
	updateBuildsuiteUser,
	sendUserWelcome,
	sendUserPasswordReset,
	deleteBuildsuiteUser,
	outgoingEmailConfigured,
} from "@/data/usersApi";
import { useDoctypeMeta } from "@/composables/useDoctypeMeta";
import { useConfirm } from "@/composables/useConfirm";
import { showToast } from "@/utils/appToast";
import StatusBadge from "@/components/StatusBadge.vue";
import FrappeUserBadge from "@/components/FrappeUserBadge.vue";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskList from "@/components/desk/DeskList.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";

const store = useDataStore();
const router = useRouter();
const route = useRoute();
const confirmDialog = useConfirm();

const PERSONA_PILL = "bg-ink-100 text-ink-700";

const users = ref([]);
const loading = ref(true);
const loadError = ref("");
const search = ref("");

async function loadUsers() {
	loading.value = true;
	loadError.value = "";
	try {
		users.value = await listBuildsuiteUsers();
	} catch (err) {
		loadError.value = err.message || "Could not load users.";
	} finally {
		loading.value = false;
	}
}
onMounted(loadUsers);

const createdBanner = ref(route.query.created || "");
onMounted(() => {
	if (route.query.created) {
		const q = { ...route.query };
		delete q.created;
		router.replace({ query: q });
	}
});

const items = computed(() => {
	const term = search.value.trim().toLowerCase();
	if (!term) return users.value;
	return users.value.filter((u) =>
		`${u.full_name} ${u.email} ${u.persona}`.toLowerCase().includes(term)
	);
});

const columns = [
	{ key: "avatar", label: "" },
	{ key: "full_name", label: "Name" },
	{ key: "persona", label: "Persona" },
	{ key: "email", label: "Email" },
	{ key: "enabled", label: "Status" },
];

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Settings", to: "/settings" },
	{ label: "Users" },
];

// ---- Edit modal ----
const editOpen = ref(false);
const editForm = reactive({ email: "", fullName: "", persona: "", enabled: true });
const editErrors = ref({});
const editError = ref("");
const editSaving = ref(false);
const emailActing = ref(""); // '' | 'welcome' | 'reset'
const mailConfigured = ref(null);

const { selectOptions } = useDoctypeMeta("User");
const personaOptions = computed(() => selectOptions("persona"));

function openEdit(row) {
	editForm.email = row.email || row.name;
	editForm.fullName = row.full_name || "";
	editForm.persona = row.persona || "";
	editForm.enabled = !!row.enabled;
	editErrors.value = {};
	editError.value = "";
	editOpen.value = true;
	outgoingEmailConfigured()
		.then((ok) => {
			mailConfigured.value = !!ok;
		})
		.catch(() => {
			mailConfigured.value = null;
		});
}

async function saveEdit() {
	const e = {};
	if (!editForm.fullName.trim()) e.fullName = "Full name is required.";
	if (!editForm.persona) e.persona = "Pick a persona.";
	editErrors.value = e;
	if (Object.keys(e).length) return;
	editError.value = "";
	editSaving.value = true;
	try {
		await updateBuildsuiteUser({
			email: editForm.email,
			full_name: editForm.fullName.trim(),
			persona: editForm.persona,
			enabled: editForm.enabled ? 1 : 0,
		});
		showToast("User updated");
		editOpen.value = false;
		await loadUsers();
	} catch (err) {
		editError.value = err.message || "Could not save.";
	} finally {
		editSaving.value = false;
	}
}

async function resendWelcome() {
	emailActing.value = "welcome";
	try {
		await sendUserWelcome(editForm.email);
		showToast("Welcome email queued");
	} catch (err) {
		showToast(err.message || "Could not send welcome email", "error");
	} finally {
		emailActing.value = "";
	}
}
async function sendReset() {
	emailActing.value = "reset";
	try {
		await sendUserPasswordReset(editForm.email);
		showToast("Password-reset link queued");
	} catch (err) {
		showToast(err.message || "Could not send reset link", "error");
	} finally {
		emailActing.value = "";
	}
}

async function deleteUser() {
	const ok = await confirmDialog({
		title: "Delete user",
		message: `Delete ${
			editForm.fullName || editForm.email
		}? They can no longer log in or be assigned new work.`,
		confirmLabel: "Delete user",
		destructive: true,
	});
	if (!ok) return;
	editError.value = "";
	editSaving.value = true;
	try {
		await deleteBuildsuiteUser(editForm.email);
		showToast("User deleted");
		editOpen.value = false;
		await loadUsers();
	} catch (err) {
		editError.value = err.message || "Could not delete user.";
	} finally {
		editSaving.value = false;
	}
}
</script>

<template>
	<DeskPage title="Users" :breadcrumbs="breadcrumbs">
		<template #actions>
			<RouterLink v-if="store.isAdmin" to="/settings/users/new" class="desk-save-btn"
				>+ New User</RouterLink
			>
		</template>

		<div
			v-if="!store.isAdmin"
			class="mb-3 px-3 py-2 bg-warning-50 border border-warning-100 text-xs text-warning-700 dark:bg-ink-800 dark:border-ink-700"
			style="border-radius: 6px"
		>
			Users management is restricted to administrators.
		</div>

		<div
			v-if="createdBanner"
			class="mb-3 px-3 py-2 bg-success-50 border border-success-100 text-xs text-success-700 dark:bg-ink-800 dark:border-ink-700"
			style="border-radius: 6px"
		>
			User <span class="font-medium">{{ createdBanner }}</span> created.
		</div>

		<div
			v-if="loadError"
			class="mb-3 px-3 py-2 bg-danger-50 border border-danger-100 text-xs text-danger-700 dark:bg-ink-800 dark:border-ink-700"
			style="border-radius: 6px"
		>
			{{ loadError }}
		</div>

		<DeskList
			v-model="search"
			:rows="items"
			:columns="columns"
			row-key="name"
			search-placeholder="Search by name, email, persona…"
			@row-click="openEdit"
		>
			<template #cell-avatar="{ row }">
				<FrappeUserBadge :user-id="row.name" :show-name="false" size="sm" />
			</template>
			<template #cell-full_name="{ row }">
				<span class="text-sm font-medium text-ink-900 dark:text-[#F5F5F5]">{{
					row.full_name || row.name
				}}</span>
			</template>
			<template #cell-email="{ row }">
				<span class="text-xs text-ink-500">{{ row.email || row.name }}</span>
			</template>
			<template #cell-persona="{ row }">
				<span
					v-if="row.persona"
					class="text-[10px] px-2 py-0.5 rounded-full font-medium"
					:class="PERSONA_PILL"
					>{{ row.persona }}</span
				>
				<span v-else class="text-[10px] text-ink-400">—</span>
			</template>
			<template #cell-enabled="{ row }">
				<StatusBadge :status="row.enabled ? 'Active' : 'Disabled'" size="xs" />
			</template>

			<template #empty>
				<div class="text-sm text-ink-500">
					{{ loading ? "Loading users…" : "No users match this search." }}
				</div>
			</template>
		</DeskList>

		<!-- Edit modal -->
		<Teleport to="body">
			<div
				v-if="editOpen"
				class="fixed inset-0 bg-ink-900/40 z-[60] flex items-center justify-center p-6"
				@click.self="editOpen = false"
			>
				<div
					class="bg-white border border-ink-200 w-full max-w-2xl shadow-fp-lg flex flex-col dark:bg-[#242424] dark:border-ink-700"
					style="border-radius: 12px; max-height: calc(100vh - 3rem)"
					@click.stop
				>
					<header
						class="px-5 py-3 border-b border-ink-200 flex items-center justify-between flex-shrink-0 bg-white dark:bg-[#242424] dark:border-ink-700"
						style="border-radius: 12px 12px 0 0"
					>
						<div class="flex items-center gap-3 min-w-0 flex-1">
							<FrappeUserBadge
								:user-id="editForm.email"
								:show-name="false"
								size="sm"
							/>
							<div class="min-w-0">
								<h2
									class="text-sm font-semibold text-ink-900 truncate dark:text-[#F5F5F5]"
								>
									{{ editForm.fullName || editForm.email }}
								</h2>
								<p class="text-[11px] text-ink-500 mt-0.5 truncate">
									{{ editForm.email }}
								</p>
							</div>
						</div>
						<button
							type="button"
							class="text-ink-500 hover:text-ink-900 text-lg leading-none flex-shrink-0 ml-3 dark:text-ink-400 dark:hover:text-ink-200"
							aria-label="Close"
							@click="editOpen = false"
						>
							×
						</button>
					</header>

					<div class="p-5 overflow-y-auto flex-1">
						<div
							v-if="editError"
							class="mb-4 px-3 py-2 bg-danger-50 border border-danger-100 text-xs text-danger-700 dark:bg-ink-800 dark:border-ink-700"
							style="border-radius: 6px"
						>
							{{ editError }}
						</div>
						<DeskSection title="Account">
							<DeskField label="Full name" required :error="editErrors.fullName">
								<DeskInput
									v-model="editForm.fullName"
									@input="
										editErrors.fullName = '';
										editError = '';
									"
								/>
							</DeskField>
							<DeskField
								label="Email"
								hint="Login id — cannot be changed after the user is created."
							>
								<DeskInput :model-value="editForm.email" disabled />
							</DeskField>
							<DeskField
								label="Account status"
								hint="Disabled users keep their record but cannot log in."
							>
								<label
									class="inline-flex items-center gap-2 cursor-pointer select-none text-sm text-ink-700 dark:text-ink-200"
								>
									<input
										v-model="editForm.enabled"
										type="checkbox"
										class="accent-brand-600"
									/>
									Enabled
								</label>
							</DeskField>
						</DeskSection>

						<DeskSection title="Persona">
							<DeskField
								label="Persona"
								required
								:error="editErrors.persona"
								hint="Frappe Roles are auto-assigned from the persona on the production side."
							>
								<DeskSelect
									v-model="editForm.persona"
									@change="
										editErrors.persona = '';
										editError = '';
									"
								>
									<option value="">— Select persona —</option>
									<option v-for="opt in personaOptions" :key="opt" :value="opt">
										{{ opt }}
									</option>
								</DeskSelect>
							</DeskField>
						</DeskSection>

						<DeskSection title="Email actions">
							<div class="md:col-span-2 space-y-2">
								<div
									v-if="mailConfigured === false"
									class="px-3 py-2 bg-warning-50 border border-warning-100 text-[11px] text-warning-700 dark:bg-ink-800 dark:border-ink-700"
									style="border-radius: 6px"
								>
									Outgoing email isn't configured — these emails won't be sent
									until an outgoing Email Account is set up.
								</div>
								<div
									class="flex items-center justify-between gap-3 px-3 py-2 border border-ink-100 bg-ink-50 dark:bg-ink-800 dark:border-ink-700"
									style="border-radius: 6px"
								>
									<div class="text-sm text-ink-900 dark:text-[#F5F5F5]">
										Welcome email
									</div>
									<button
										type="button"
										class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 flex-shrink-0 dark:bg-ink-800 dark:border-ink-700 dark:text-ink-100 dark:hover:bg-ink-700"
										style="border-radius: 6px"
										:disabled="!!emailActing"
										@click="resendWelcome"
									>
										{{
											emailActing === "welcome" ? "Sending…" : "Send welcome"
										}}
									</button>
								</div>
								<div
									class="flex items-center justify-between gap-3 px-3 py-2 border border-ink-100 bg-ink-50 dark:bg-ink-800 dark:border-ink-700"
									style="border-radius: 6px"
								>
									<div class="text-sm text-ink-900 dark:text-[#F5F5F5]">
										Password reset link
									</div>
									<button
										type="button"
										class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 flex-shrink-0 dark:bg-ink-800 dark:border-ink-700 dark:text-ink-100 dark:hover:bg-ink-700"
										style="border-radius: 6px"
										:disabled="!!emailActing"
										@click="sendReset"
									>
										{{
											emailActing === "reset"
												? "Sending…"
												: "Send reset link"
										}}
									</button>
								</div>
							</div>
						</DeskSection>
					</div>

					<footer
						class="px-5 py-3 border-t border-ink-200 flex items-center justify-between gap-2 flex-shrink-0 bg-white dark:bg-[#242424] dark:border-ink-700"
						style="border-radius: 0 0 12px 12px"
					>
						<button
							type="button"
							class="text-xs px-3 py-1.5 border border-danger-200 bg-white hover:bg-danger-50 text-danger-700 dark:bg-ink-800 dark:border-ink-700 dark:hover:bg-ink-700"
							style="border-radius: 6px"
							:disabled="editSaving"
							@click="deleteUser"
						>
							Delete user
						</button>
						<div class="flex items-center gap-2">
							<button
								type="button"
								class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 dark:bg-ink-800 dark:border-ink-700 dark:text-ink-100 dark:hover:bg-ink-700"
								style="border-radius: 6px"
								:disabled="editSaving"
								@click="editOpen = false"
							>
								Cancel
							</button>
							<button
								type="button"
								class="desk-save-btn"
								:disabled="editSaving"
								@click="saveEdit"
							>
								{{ editSaving ? "Saving…" : "Save" }}
							</button>
						</div>
					</footer>
				</div>
			</div>
		</Teleport>
	</DeskPage>
</template>
