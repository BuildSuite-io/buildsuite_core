<script setup>
// New Machinery form — mirrors the demo. Asset shows only for Owned plant.

import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import { showToast } from "@/utils/appToast";
import { useFormErrors } from "@/composables/useFormErrors";
import { usePermissions } from "@/composables/usePermissions";
import { createDataAdapter } from "@/data/adapters";
import { getActiveCompany } from "@/data/companyApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";

const router = useRouter();
const adapter = createDataAdapter(useDataStore());
const { canCreate } = usePermissions();

const form = reactive({
	machinery_name: "",
	machinery_type: "",
	ownership: "Owned",
	rate: 0,
	rate_unit: "Day",
	owner_vendor: "",
	asset: "",
	status: "Active",
	company: "",
});
const { errors, applyServerErrors, setErrors } = useFormErrors({
	machinery_name: "machinery_name",
	machinery_type: "machinery_type",
	company: "company",
});
const saving = ref(false);

// Prefill the user's default company (editable).
getActiveCompany()
	.then((c) => {
		if (c && !form.company) form.company = c;
	})
	.catch(() => {});

function validate() {
	const e = {};
	if (!form.machinery_name.trim()) e.machinery_name = "Name is required.";
	if (!form.machinery_type) e.machinery_type = "Type is required.";
	if (!form.company) e.company = "Company is required.";
	setErrors(e);
	return Object.keys(e).length === 0;
}

function onCancel() {
	router.back();
}

async function onSave() {
	if (!validate()) return;
	saving.value = true;
	try {
		const res = await adapter.create("Machinery", {
			machinery_name: form.machinery_name.trim(),
			machinery_type: form.machinery_type,
			ownership: form.ownership,
			rate: form.rate,
			rate_unit: form.rate_unit,
			owner_vendor: form.owner_vendor,
			asset: form.ownership === "Owned" ? form.asset : "",
			status: form.status,
			company: form.company,
		});
		router.push(`/machinery/${res.name}`);
	} catch (err) {
		showToast(applyServerErrors(err) ?? "Failed to create machinery", "error");
	} finally {
		saving.value = false;
	}
}

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Equipment", to: "/equipment" },
	{ label: "Machinery", to: "/machinery" },
	{ label: "New" },
];
</script>

<template>
	<DeskPage title="New Machinery" :breadcrumbs="breadcrumbs">
		<div
			v-if="!canCreate('machinery')"
			class="px-3 py-2 bg-warning-50 border border-warning-100 text-xs text-warning-700 dark:bg-ink-800 dark:border-ink-700"
			style="border-radius: 6px"
		>
			You don't have permission to create machinery.
		</div>
		<DeskForm v-else>
			<template #action-bar>
				<DeskActionBar
					:save-label="saving ? 'Creating…' : 'Create machinery'"
					:saving="saving"
					@save="onSave"
					@cancel="onCancel"
				/>
			</template>

			<DeskSection title="Machinery" :cols="3">
				<DeskField label="Name" required :error="errors.machinery_name">
					<DeskInput v-model="form.machinery_name" />
				</DeskField>
				<DeskField label="Type" required :error="errors.machinery_type">
					<DeskLinkPicker
						v-model="form.machinery_type"
						doctype="Machinery Type"
						label-field="name"
						value-field="name"
						placeholder="Pick a type…"
					/>
				</DeskField>
				<DeskField label="Ownership">
					<DeskSelect v-model="form.ownership">
						<option>Owned</option>
						<option>Hired</option>
					</DeskSelect>
				</DeskField>

				<DeskField label="Rate (₹)">
					<DeskInput v-model.number="form.rate" type="number" min="0" />
				</DeskField>
				<DeskField label="Rate unit">
					<DeskSelect v-model="form.rate_unit">
						<option>Hour</option>
						<option>Day</option>
						<option>Month</option>
					</DeskSelect>
				</DeskField>
				<DeskField label="Status">
					<DeskSelect v-model="form.status">
						<option>Active</option>
						<option>Inactive</option>
					</DeskSelect>
				</DeskField>

				<DeskField label="Owner / Vendor">
					<DeskInput v-model="form.owner_vendor" />
				</DeskField>
				<DeskField
					v-if="form.ownership === 'Owned'"
					label="Linked asset (ERPNext)"
					hint="Optional — the owned fixed asset in ERPNext Assets. Leave blank for hired plant."
				>
					<DeskLinkPicker
						v-model="form.asset"
						doctype="Asset"
						label-field="asset_name"
						value-field="name"
						placeholder="— No linked asset —"
					/>
				</DeskField>
				<DeskField label="Company" required :error="errors.company">
					<DeskLinkPicker
						v-model="form.company"
						doctype="Company"
						label-field="name"
						value-field="name"
						placeholder="Company…"
					/>
				</DeskField>
			</DeskSection>
		</DeskForm>
	</DeskPage>
</template>
