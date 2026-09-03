<script setup>
// New Company — Settings sub-page. Admin-only (route is allowlisted at the
// Settings hub tile level; non-admins who hit the URL still see the form but
// the save action checks isAdmin and refuses).
//
// Creates a REAL ERPNext Company. ERPNext requires `company_name` + `abbr`
// (the docname is derived from company_name) and a `default_currency`; we also
// pass `country`. The docname is stable after create — there is no separate id
// field. shortName / colour are derived in the store, not collected here.

import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import { showToast } from "@/utils/appToast";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";

const router = useRouter();
const store = useDataStore();

const form = reactive({
	name: "",
	abbr: "",
	currency: "INR",
	country: "India",
});
const errors = ref({});
const saving = ref(false);

function validate() {
	const e = {};
	if (!form.name.trim()) e.name = "Company name is required";
	if (!form.abbr.trim()) e.abbr = "Abbreviation is required (ERPNext prefixes accounts with it)";
	errors.value = e;
	return Object.keys(e).length === 0;
}

async function save() {
	if (!store.isAdmin) {
		alert("Only the System Manager role can create companies.");
		return;
	}
	if (!validate()) return;
	saving.value = true;
	try {
		const created = await store.addCompany({
			name: form.name.trim(),
			abbr: form.abbr.trim(),
			currency: form.currency.trim() || "INR",
			country: form.country.trim() || "India",
		});
		router.push(`/settings/companies/${created.id}`);
	} catch (err) {
		showToast(err.message || "Failed to create company", "error");
	} finally {
		saving.value = false;
	}
}
function cancel() {
	router.back();
}

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Settings", to: "/settings" },
	{ label: "Companies", to: "/settings/companies" },
	{ label: "New" },
];
</script>

<template>
	<DeskPage
		title="New Company"
		subtitle="Legal entity for project / accounting segregation (§14)"
		:breadcrumbs="breadcrumbs"
	>
		<DeskForm>
			<template #action-bar>
				<DeskActionBar
					:save-label="saving ? 'Creating…' : 'Create company'"
					:saving="saving"
					@save="save"
					@cancel="cancel"
				/>
			</template>

			<div class="max-w-3xl mx-auto">
				<!-- Non-admin guard. -->
				<div
					v-if="!store.isAdmin"
					class="mb-3 px-3 py-2 bg-warning-50 border border-warning-100 text-xs text-warning-700"
					style="border-radius: 2px"
				>
					You're viewing this form as
					<span class="font-medium">{{ store.currentRole?.name }}</span
					>. Saving requires the System Manager role.
				</div>

				<DeskSection title="Identity">
					<DeskField
						label="Company Name"
						required
						:error="errors.name"
						hint="Legal entity name. Becomes the company's name and appears on invoices / contracts."
					>
						<DeskInput v-model="form.name" placeholder="e.g. Acme Realty Pvt Ltd" />
					</DeskField>
					<DeskField
						label="Abbreviation"
						required
						:error="errors.abbr"
						hint="Short code ERPNext prefixes onto the company's accounts (e.g. ARP)."
					>
						<DeskInput v-model="form.abbr" placeholder="e.g. ARP" class="font-mono" />
					</DeskField>
				</DeskSection>

				<DeskSection title="Accounting" :cols="2">
					<DeskField label="Default currency" hint="ISO code. Defaults to INR.">
						<DeskInput v-model="form.currency" placeholder="INR" class="font-mono" />
					</DeskField>
					<DeskField label="Country" hint="Defaults to India.">
						<DeskInput v-model="form.country" placeholder="India" />
					</DeskField>
				</DeskSection>
			</div>
		</DeskForm>
	</DeskPage>
</template>
