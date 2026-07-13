<script setup>
// New Subcontractor master form — Desk-styled, mirrors the prototype.
// Trade is a Link to Construction Trade (seeded master), picked with
// DeskLinkPicker. The optional Supplier link is the one addition over
// the prototype (for future accounting integration).

import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import { showToast } from "@/utils/appToast";
import { useFormErrors } from "@/composables/useFormErrors";
import { createDataAdapter } from "@/data/adapters";
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

const form = reactive({
	subcontractor_name: "",
	trade: "",
	status: "Active",
	supplier: "",
	contact_person: "",
	phone: "",
	email: "",
	gstin: "",
	pan: "",
});
const { errors, applyServerErrors, setErrors } = useFormErrors({
	subcontractor_name: "subcontractor_name",
	trade: "trade",
});
const saving = ref(false);

function validate() {
	const e = {};
	if (!form.subcontractor_name.trim()) e.subcontractor_name = "Name is required.";
	if (!form.trade) e.trade = "Trade is required.";
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
		const res = await adapter.create("Subcontractor", {
			subcontractor_name: form.subcontractor_name.trim(),
			trade: form.trade,
			status: form.status,
			supplier: form.supplier || null,
			contact_person: form.contact_person,
			phone: form.phone,
			email: form.email,
			gstin: form.gstin,
			pan: form.pan,
		});
		router.push(`/subcontractors/${res.name}`);
	} catch (err) {
		showToast(applyServerErrors(err) ?? "Failed to create subcontractor", "error");
	} finally {
		saving.value = false;
	}
}

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Subcontract", to: "/subcontract" },
	{ label: "Subcontractors", to: "/subcontractors" },
	{ label: "New" },
];
</script>

<template>
	<DeskPage title="New Subcontractor" :breadcrumbs="breadcrumbs">
		<DeskForm>
			<template #action-bar>
				<DeskActionBar
					:save-label="saving ? 'Creating…' : 'Create subcontractor'"
					:saving="saving"
					@save="onSave"
					@cancel="onCancel"
				/>
			</template>

			<DeskSection title="Contact" :cols="3">
				<DeskField label="Name" required :error="errors.subcontractor_name">
					<DeskInput v-model="form.subcontractor_name" />
				</DeskField>
				<DeskField label="Trade" required :error="errors.trade">
					<DeskLinkPicker
						v-model="form.trade"
						doctype="Construction Trade"
						label-field="name"
						value-field="name"
						placeholder="Pick a trade…"
					/>
				</DeskField>
				<DeskField label="Status">
					<DeskSelect v-model="form.status">
						<option>Active</option>
						<option>Inactive</option>
					</DeskSelect>
				</DeskField>
				<DeskField label="Contact person"
					><DeskInput v-model="form.contact_person"
				/></DeskField>
				<DeskField label="Phone"><DeskInput v-model="form.phone" /></DeskField>
				<DeskField label="Email"
					><DeskInput v-model="form.email" type="email"
				/></DeskField>
			</DeskSection>

			<DeskSection title="Statutory & accounting" :cols="3">
				<DeskField label="GSTIN"><DeskInput v-model="form.gstin" /></DeskField>
				<DeskField label="PAN"><DeskInput v-model="form.pan" /></DeskField>
				<DeskField
					label="Supplier"
					hint="Optional — link to an ERPNext Supplier for accounting."
				>
					<DeskLinkPicker
						v-model="form.supplier"
						doctype="Supplier"
						label-field="supplier_name"
						value-field="name"
						placeholder="— Optional —"
					/>
				</DeskField>
			</DeskSection>
		</DeskForm>
	</DeskPage>
</template>
