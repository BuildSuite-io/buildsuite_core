<script setup>
// A self-service diagnostic for "the BuildSuite app icon isn't showing". Reads the server-side
// state of every surface the icon lives on (the /apps launcher hook + logo, the 16.5x Dock /
// Sidebar fixtures, the legacy Workspace) so an admin can copy it back without SSH / Desk access.
// Admin only.
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { frappeRequest } from "frappe-ui-frappe-request";
import { useDataStore } from "@/stores";
import { showToast } from "@/utils/appToast";
import { parseFrappeError } from "@/utils/frappeError";
import { __ } from "@/utils/translate";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSection from "@/components/desk/DeskSection.vue";

const router = useRouter();
const store = useDataStore();

const loading = ref(true);
const error = ref("");
const report = ref(null);
const json = ref("");

async function run() {
	loading.value = true;
	error.value = "";
	try {
		const res = await frappeRequest({
			url: "buildsuite_core.api.diagnostics.app_icon_diagnostics",
		});
		report.value = res;
		json.value = JSON.stringify(res, null, 2);
	} catch (err) {
		error.value = parseFrappeError(err).summary || __("Failed to run diagnostics");
	} finally {
		loading.value = false;
	}
}

async function copy() {
	try {
		await navigator.clipboard.writeText(json.value);
		showToast(__("Report copied to clipboard."));
	} catch {
		showToast(__("Couldn't copy — select the text and copy manually."), "error");
	}
}

const breadcrumbs = [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: __("Settings"), to: "/settings" },
	{ label: __("App icon diagnostics") },
];

onMounted(() => {
	if (!store.isAdmin && !store.isBSA) {
		router.replace("/settings");
		return;
	}
	run();
});
</script>

<template>
	<DeskPage
		:title="__('App icon diagnostics')"
		:subtitle="
			__('Why the BuildSuite app icon may not be showing — copy this back for support')
		"
		:breadcrumbs="breadcrumbs"
	>
		<div class="max-w-3xl mx-auto">
			<div class="flex items-center gap-2 mb-4">
				<button
					type="button"
					class="desk-save-btn"
					:disabled="loading || !json"
					@click="copy"
				>
					{{ __("Copy report") }}
				</button>
				<button
					type="button"
					class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
					style="border-radius: 6px"
					:disabled="loading"
					@click="run"
				>
					{{ loading ? __("Running…") : __("Re-run") }}
				</button>
			</div>

			<div v-if="loading" class="py-12 text-center text-sm text-ink-500">
				{{ __("Running diagnostics…") }}
			</div>

			<div
				v-else-if="error"
				class="px-3 py-2 bg-danger-50 border border-danger-200 text-sm text-danger-700"
				style="border-radius: 6px"
			>
				{{ error }}
			</div>

			<template v-else-if="report">
				<!-- Plain-language read, surfaced first. -->
				<DeskSection :title="__('Likely cause')">
					<ul class="list-disc pl-5 space-y-1.5 text-sm text-ink-800">
						<li v-for="(h, i) in report.hints || []" :key="i">{{ h }}</li>
					</ul>
				</DeskSection>

				<DeskSection :title="__('Full report')">
					<p class="text-[11px] text-ink-500 mb-2">
						{{ __("Copy everything below and paste it back.") }}
					</p>
					<pre
						class="text-[11px] leading-relaxed bg-ink-50 border border-ink-200 p-3 overflow-x-auto whitespace-pre-wrap break-words"
						style="border-radius: 6px; max-height: 60vh"
						>{{ json }}</pre
					>
				</DeskSection>
			</template>
		</div>
	</DeskPage>
</template>
