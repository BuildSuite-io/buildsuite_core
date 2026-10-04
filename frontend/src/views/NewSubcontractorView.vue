<script setup>
// New Subcontractor form. A subcontractor is a native ERPNext Supplier tagged
// supplier_type="Subcontractor" — so accounting (PI/payment) is native. Contact
// details live on the Supplier's native Contact (managed in Desk).

import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { showToast } from "@/utils/appToast";
import { useFormErrors } from "@/composables/useFormErrors";
import { usePermissions } from "@/composables/usePermissions";
import { createSubcontractor } from "@/data/subcontractApi";
import { __ } from "@/utils/translate";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import TradePicker from "@/components/TradePicker.vue";

const router = useRouter();
const { canCreate } = usePermissions();

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
	if (!form.subcontractor_name.trim()) e.subcontractor_name = __("Name is required.");
	if (!form.trade) e.trade = __("Trade is required.");
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
		showToast(applyServerErrors(err) ?? __("Failed to create subcontractor"), "error");
	} finally {
		saving.value = false;
	}
}

const breadcrumbs = [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: __("Subcontract"), to: "/subcontract" },
	{ label: __("Subcontractors"), to: "/subcontractors" },
	{ label: __("New") },
];
</script>

<template>
	<DeskPage :title="__('New Subcontractor')" :breadcrumbs="breadcrumbs">
		<div
			v-if="!canCreate('subcontractor')"
			class="px-3 py-2 bg-warning-50 border border-warning-100 text-xs text-warning-700 dark:bg-ink-800 dark:border-ink-700"
			style="border-radius: 6px"
		>
			{{ __("You don't have permission to create a subcontractor.") }}
		</div>
		<DeskForm v-else>
			<template #action-bar>
				<DeskActionBar
					:save-label="saving ? __('Creating…') : __('Create subcontractor')"
					:saving="saving"
					@save="onSave"
					@cancel="onCancel"
				/>
			</template>

			<DeskSection :title="__('Details')" :cols="3">
				<DeskField :label="__('Name')" required :error="errors.subcontractor_name">
					<DeskInput v-model="form.subcontractor_name" />
				</DeskField>
				<DeskField :label="__('Trade')" required :error="errors.trade">
					<TradePicker v-model="form.trade" :error="errors.trade" />
				</DeskField>
				<DeskField :label="__('Status')">
					<DeskSelect v-model="form.status">
						<option value="Active">{{ __("Active") }}</option>
						<option value="Inactive">{{ __("Inactive") }}</option>
					</DeskSelect>
				</DeskField>
				<DeskField :label="__('Tax ID')" :hint="__('e.g. GSTIN (India), VAT No, TIN')"
					><DeskInput v-model="form.tax_id"
				/></DeskField>
			</DeskSection>

			<DeskSection :title="__('Contact')" :cols="3">
				<DeskField :label="__('Contact person')">
					<DeskInput v-model="form.contact_person" />
				</DeskField>
				<DeskField :label="__('Phone number')">
					<DeskInput v-model="form.phone" />
				</DeskField>
				<DeskField :label="__('Email id')">
					<DeskInput v-model="form.email" type="email" />
				</DeskField>
			</DeskSection>
		</DeskForm>
	</DeskPage>
</template>
