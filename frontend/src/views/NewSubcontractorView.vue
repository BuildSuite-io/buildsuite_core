<script setup>
// New Subcontractor form. A subcontractor is a native ERPNext Supplier tagged
// supplier_type="Subcontractor" — so accounting (PI/payment) is native. Contact
// details live on the Supplier's native Contact (managed in Desk).

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
	tax_id: "",
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
		const res = await adapter.create("Supplier", {
			supplier_name: form.subcontractor_name.trim(),
			supplier_type: "Subcontractor",
			supplier_group: "Subcontractor",
			custom_trade: form.trade,
			tax_id: form.tax_id,
			disabled: form.status === "Inactive" ? 1 : 0,
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
				<DeskField label="Tax ID" hint="e.g. GSTIN (India), VAT No, TIN"
					><DeskInput v-model="form.tax_id"
				/></DeskField>
			</DeskSection>
			<p class="text-xs text-ink-400 mt-3">
				Contact person, phone and email are managed on the subcontractor's Supplier record in the
				accounting desk.
			</p>
		</DeskForm>
	</DeskPage>
</template>
