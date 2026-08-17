<script setup>
// Routed page for any Frappe/ERPNext report, rendered in-app via <FrappeReport>.
// Reached from a workspace's report tiles (route /reports/view/:report). The report
// name is the route param.
import { computed } from "vue";
import { useRoute } from "vue-router";
import DeskPage from "@/components/desk/DeskPage.vue";
import FrappeReport from "@/components/FrappeReport.vue";
import DelayAnalysisReportView from "@/views/DelayAnalysisReportView.vue";

const route = useRoute();
const report = computed(() => route.params.report || "");
// Reports with a bespoke view (richer than a flat Query Report table) render their own
// component; everything else falls through to the generic FrappeReport renderer.
const CUSTOM_VIEWS = { "Delay Analysis": DelayAnalysisReportView };
const customView = computed(() => CUSTOM_VIEWS[report.value] || null);
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
	<!-- Bespoke report views render their own page chrome. -->
	<component :is="customView" v-if="customView" />
	<DeskPage v-else :title="report" subtitle="Report" :breadcrumbs="breadcrumbs">
		<FrappeReport :report="report" />
	</DeskPage>
</template>
