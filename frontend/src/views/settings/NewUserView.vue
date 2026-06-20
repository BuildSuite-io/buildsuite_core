<script setup>
// New User — create a real Frappe User with a BuildSuite persona. The persona
// drives the BuildSuite role via the server-side sync hook. Optional welcome /
// password-reset emails use Frappe's native flows.

import { ref, reactive, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import {
	createBuildsuiteUser,
	sendUserPasswordReset,
	outgoingEmailConfigured,
} from "@/data/usersApi";
import { useDoctypeMeta } from "@/composables/useDoctypeMeta";
import { showToast } from "@/utils/appToast";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";

const router = useRouter();
const store = useDataStore();

const form = reactive({
	fullName: "",
	email: "",
	persona: "",
	enabled: true,
	sendWelcome: true,
	sendReset: false,
});
const errors = ref({});
const formError = ref("");
const saving = ref(false);
const mailConfigured = ref(null);

onMounted(() => {
	outgoingEmailConfigured()
		.then((ok) => {
			mailConfigured.value = !!ok;
		})
		.catch(() => {
			mailConfigured.value = null;
		});
});

const { selectOptions } = useDoctypeMeta("User");
const personaOptions = computed(() => selectOptions("persona"));

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Settings", to: "/settings" },
	{ label: "Users", to: "/settings/users" },
	{ label: "New User" },
];

function validate() {
	const e = {};
	if (!form.fullName.trim()) e.fullName = "Full name is required.";
	if (!form.email.trim()) e.email = "Email is required.";
	else if (!EMAIL_RE.test(form.email.trim())) e.email = "Enter a valid email address.";
	if (!form.persona) e.persona = "Pick a persona.";
	errors.value = e;
	return Object.keys(e).length === 0;
}

async function save() {
	if (!validate()) return;
	formError.value = "";
	saving.value = true;
	try {
		const user = await createBuildsuiteUser({
			full_name: form.fullName.trim(),
			email: form.email.trim().toLowerCase(),
			persona: form.persona,
			enabled: form.enabled ? 1 : 0,
			send_welcome: form.sendWelcome ? 1 : 0,
		});
		// Optional separate password-reset link (welcome was handled on create).
		if (form.sendReset) {
			try {
				await sendUserPasswordReset(user.name);
			} catch {
				/* email queue handles it */
			}
		}
		showToast(`User ${user.full_name} created`);
		router.push({ path: "/settings/users", query: { created: user.name } });
	} catch (err) {
		formError.value = err.message || "Could not create the user.";
		saving.value = false;
	}
}
</script>

<template>
	<DeskPage title="New User" :breadcrumbs="breadcrumbs">
		<div
			v-if="!store.isAdmin"
			class="mb-3 px-3 py-2 bg-warning-50 border border-warning-100 text-xs text-warning-700 dark:bg-ink-800 dark:border-ink-700"
			style="border-radius: 6px"
		>
			Creating users is restricted to administrators.
		</div>

		<DeskForm v-else>
			<template #action-bar>
				<DeskActionBar
					:saving="saving"
					save-label="Create user"
					saving-label="Creating…"
					@save="save"
					@cancel="router.push('/settings/users')"
				/>
			</template>

			<div class="max-w-3xl mx-auto">
				<div
					v-if="formError"
					class="mb-4 px-3 py-2 bg-danger-50 border border-danger-100 text-xs text-danger-700 dark:bg-ink-800 dark:border-ink-700"
					style="border-radius: 6px"
				>
					{{ formError }}
				</div>
				<DeskSection title="Account">
					<DeskField label="Full name" required :error="errors.fullName">
						<DeskInput
							v-model="form.fullName"
							placeholder="e.g. Asha Menon"
							@input="
								errors.fullName = '';
								formError = '';
							"
						/>
					</DeskField>
					<DeskField
						label="Email"
						required
						:error="errors.email"
						hint="Used as the login id + destination for the welcome and password-reset emails."
					>
						<DeskInput
							v-model="form.email"
							type="email"
							placeholder="name@company.com"
							@input="
								errors.email = '';
								formError = '';
							"
						/>
					</DeskField>
					<DeskField
						label="Account status"
						hint="Disabled users keep their record but cannot log in."
					>
						<label
							class="inline-flex items-center gap-2 cursor-pointer select-none text-sm text-ink-700 dark:text-ink-200"
						>
							<input
								v-model="form.enabled"
								type="checkbox"
								class="accent-brand-600"
							/>
							Enabled — user can log in immediately
						</label>
					</DeskField>
				</DeskSection>

				<DeskSection title="Persona">
					<DeskField
						label="Persona"
						required
						:error="errors.persona"
						hint="Frappe Roles are auto-assigned from the persona on the production side. Pick the one that matches the user's day-to-day work."
					>
						<DeskSelect
							v-model="form.persona"
							@change="
								errors.persona = '';
								formError = '';
							"
						>
							<option value="">— Select persona —</option>
							<option v-for="opt in personaOptions" :key="opt" :value="opt">
								{{ opt }}
							</option>
						</DeskSelect>
					</DeskField>
				</DeskSection>

				<DeskSection title="Onboarding">
					<DeskField label="Emails">
						<div
							v-if="mailConfigured === false"
							class="mb-2 px-3 py-2 bg-warning-50 border border-warning-100 text-[11px] text-warning-700 dark:bg-ink-800 dark:border-ink-700"
							style="border-radius: 6px"
						>
							Outgoing email isn't configured — these emails won't be sent until an
							outgoing Email Account is set up.
						</div>
						<label class="flex items-start gap-2 cursor-pointer select-none">
							<input
								v-model="form.sendWelcome"
								type="checkbox"
								class="accent-brand-600 mt-0.5"
							/>
							<div>
								<div class="text-sm text-ink-900 dark:text-[#F5F5F5]">
									Send welcome email
								</div>
								<div class="text-[11px] text-ink-500">
									Brief intro to BuildSuite Core, link to set up their profile.
								</div>
							</div>
						</label>
						<label class="flex items-start gap-2 cursor-pointer select-none mt-3">
							<input
								v-model="form.sendReset"
								type="checkbox"
								class="accent-brand-600 mt-0.5"
							/>
							<div>
								<div class="text-sm text-ink-900 dark:text-[#F5F5F5]">
									Send password reset link
								</div>
								<div class="text-[11px] text-ink-500">
									Lets the user set their own password instead of you assigning
									one.
								</div>
							</div>
						</label>
					</DeskField>
				</DeskSection>
			</div>
		</DeskForm>
	</DeskPage>
</template>
