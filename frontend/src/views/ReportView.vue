<script setup>
// Routed page for any Frappe/ERPNext report, rendered in-app via <FrappeReport>.
// Reached from a workspace's report tiles (route /reports/view/:report). The report
// name is the route param.
import { computed } from "vue";
import { useRoute } from "vue-router";
import DeskPage from "@/components/desk/DeskPage.vue";
import FrappeReport from "@/components/FrappeReport.vue";

const route = useRoute();
const report = computed(() => route.params.report || "");
// The report's description (from its workspace tile), shown as the page subtitle. Falls back to
// a generic label when the report was opened without one (e.g. a direct URL).
const subtitle = computed(() => route.query.desc || "Report");
// Where this report belongs, so the breadcrumb points back (defaults to Reports).
const backTo = computed(() => route.query.from || "");
const backLabel = computed(() => route.query.fromLabel || "Reports");

const breadcrumbs = computed(() => {
	const crumbs = [{ label: "BuildSuite Core", to: "/" }];
	if (backTo.value) crumbs.push({ label: backLabel.value, to: backTo.value });
	crumbs.push({ label: report.value });
	return crumbs;
});
</script>

<template>
	<DeskPage :title="report" :subtitle="subtitle" :breadcrumbs="breadcrumbs" printable>
		<FrappeReport :report="report" />
	</DeskPage>
</template>
