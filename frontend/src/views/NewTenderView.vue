<script setup>
// New tender — page shell. The fields and save land next.

import { useRouter } from "vue-router";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";

const router = useRouter();

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Estimation", to: "/estimation" },
	{ label: "Tenders", to: "/tenders" },
	{ label: "New" },
];
</script>

<template>
	<DeskPage title="New Tender"
		subtitle="Type the items straight in, or pull them from an assembly or an estimate."
		:breadcrumbs="breadcrumbs">
		<DeskForm>
			<template #action-bar>
				<DeskActionBar save-label="Create tender" :show-save="false"
					@cancel="router.back()" />
			</template>

			<div class="text-sm text-ink-500">Nothing here yet.</div>
		</DeskForm>
	</DeskPage>
</template>
