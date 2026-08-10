<script setup>
// New Subcontractor form. A subcontractor is a native ERPNext Supplier tagged
// supplier_type="Subcontractor" — so accounting (PI/payment) is native. Contact
// details live on the Supplier's native Contact (managed in Desk).

import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { showToast } from "@/utils/appToast";
import { useFormErrors } from "@/composables/useFormErrors";
import { createSubcontractor } from "@/data/subcontractApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import TradePicker from "@/components/TradePicker.vue";

const router = useRouter();

const form = reactive({
	subcontractor_name: "",
	trade: "",
	status: "Active",
	tax_id: "",
	contact_person: "",
	phone: "",
	email: "",
});
const { errors, applyServerErrors, setErrors } = useFormErrors({
	supplier_name: "subcontractor_name",
	custom_trade: "trade",
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
		const res = await createSubcontractor({
			subcontractor_name: form.subcontractor_name.trim(),
			trade: form.trade,
			tax_id: form.tax_id,
			status: form.status,
			contact_person: form.contact_person,
			phone: form.phone,
			email: form.email,
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

			<DeskSection title="Details" :cols="3">
				<DeskField label="Name" required :error="errors.subcontractor_name">
					<DeskInput v-model="form.subcontractor_name" />
				</DeskField>
				<DeskField label="Trade" required :error="errors.trade">
					<TradePicker v-model="form.trade" :error="errors.trade" />
				</DeskField>
				<DeskField label="Status">
					<DeskSelect v-model="form.status">
						<option>Active</option>
						<option>Inactive</option>
					</DeskSelect>
				</DeskField>
				<DeskField label="Tax ID" hint="e.g. GSTIN (India), VAT No, TIN"
					><DeskInput v-model="form.tax_id"
				/></DeskField>
			</DeskSection>

			<DeskSection title="Contact" :cols="3">
				<DeskField label="Contact person">
					<DeskInput v-model="form.contact_person" />
				</DeskField>
				<DeskField label="Phone number">
					<DeskInput v-model="form.phone" />
				</DeskField>
				<DeskField label="Email id">
					<DeskInput v-model="form.email" type="email" />
				</DeskField>
			</DeskSection>
		</DeskForm>
	</DeskPage>
</template>
