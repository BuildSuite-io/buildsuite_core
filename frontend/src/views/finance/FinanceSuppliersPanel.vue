<script setup>
import { computed, reactive, ref } from "vue";
import { useFinanceMock } from "@/data/financeMock";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskList from "@/components/desk/DeskList.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";

const fin = useFinanceMock();
const search = ref("");
const rows = computed(() => {
	const q = search.value.trim().toLowerCase();
	return fin.suppliers.filter((c) => !q || c.name.toLowerCase().includes(q) || (c.gstin || "").toLowerCase().includes(q));
});
const columns = [
	{ key: "name", label: "Name" },
	{ key: "type", label: "Type" },
	{ key: "contactPerson", label: "Contact" },
	{ key: "phone", label: "Phone" },
	{ key: "gstin", label: "GST no." },
];
const breadcrumbs = [{ label: "Project Finance", to: "/project-finance" }, { label: "Suppliers" }];

const form = reactive({ open: false, name: "", type: "Material", contactPerson: "", phone: "", email: "", gstin: "" });
function save() {
	if (!form.name.trim()) return;
	fin.addSupplier({ name: form.name.trim(), type: form.type, contactPerson: form.contactPerson, phone: form.phone, email: form.email, gstin: form.gstin });
	form.open = false;
	Object.assign(form, { name: "", contactPerson: "", phone: "", email: "", gstin: "" });
}
</script>

<template>
	<DeskPage title="Suppliers" :breadcrumbs="breadcrumbs">
		<template #actions><button class="desk-save-btn" @click="form.open = true">+ New</button></template>
		<DeskList v-model="search" :rows="rows" :columns="columns" row-key="id" search-placeholder="Search suppliers…">
			<template #cell-type="{ row }"><span class="text-[11px] px-1.5 py-0.5 bg-ink-100 text-ink-700 rounded">{{ row.type }}</span></template>
			<template #cell-gstin="{ row }"><span class="font-mono text-xs text-ink-500">{{ row.gstin || "—" }}</span></template>
		</DeskList>
		<div v-if="form.open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" @click.self="form.open = false">
			<div class="bg-white rounded-lg shadow-xl w-full max-w-md p-5">
				<h3 class="text-sm font-semibold text-ink-900 mb-4">New supplier</h3>
				<div class="space-y-3">
					<DeskField label="Name" required><DeskInput v-model="form.name" /></DeskField>
					<DeskField label="Type"><DeskSelect v-model="form.type"><option>Material</option><option>Service</option><option>Both</option></DeskSelect></DeskField>
					<DeskField label="Contact person"><DeskInput v-model="form.contactPerson" /></DeskField>
					<DeskField label="Phone"><DeskInput v-model="form.phone" /></DeskField>
					<DeskField label="Email"><DeskInput v-model="form.email" /></DeskField>
					<DeskField label="GST no."><DeskInput v-model="form.gstin" /></DeskField>
				</div>
				<div class="flex justify-end gap-2 mt-5"><button class="desk-btn" @click="form.open = false">Cancel</button><button class="desk-save-btn" @click="save">Save</button></div>
			</div>
		</div>
	</DeskPage>
</template>
