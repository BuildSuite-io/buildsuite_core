<script setup>
import { computed } from "vue";
import WorkspaceShortcut from "@/components/WorkspaceShortcut.vue";
import WorkspaceReportsSection from "@/components/workspaces/WorkspaceReportsSection.vue";
import { __, currentLang } from "@/utils/translate";

const today = computed(() =>
	new Date().toLocaleDateString(currentLang(), {
		weekday: "long",
		month: "short",
		day: "numeric",
	})
);

const SHORTCUTS = [
	{ to: "/customers", icon: "users-round", label: "Customers", cap: "customer" },
	{ to: "/quotations", icon: "file-text", label: "Quotations" },
	{ to: "/tenders", icon: "clipboard-list", label: "Tenders" },
];
const SETUP = [
	{
		to: "/payment-terms",
		icon: "calendar",
		label: "Payment terms templates",
		description: "Reusable payment schedules for quotations and tenders.",
	},
];
</script>

<template>
	<div class="bg-white min-h-full">
		<div class="max-w-6xl mx-auto px-6 py-8">
			<div class="mb-6">
				<div class="text-xs text-ink-500 mb-1">{{ today }}</div>
				<h1 class="text-2xl font-semibold text-ink-900">{{ __("Sales") }}</h1>
			</div>

			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-8">
				<WorkspaceShortcut
					v-for="shortcut in SHORTCUTS"
					:key="shortcut.to"
					:to="shortcut.to"
					:icon="shortcut.icon"
					:label="__(shortcut.label)"
					:cap="shortcut.cap"
				/>
			</div>

			<h2 class="text-[11px] font-semibold uppercase tracking-wider text-ink-700 mb-2">
				{{ __("Setup") }}
			</h2>
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
				<WorkspaceShortcut
					v-for="shortcut in SETUP"
					:key="shortcut.to"
					:to="shortcut.to"
					:icon="shortcut.icon"
					:label="__(shortcut.label)"
					:description="__(shortcut.description)"
				/>
			</div>

			<WorkspaceReportsSection workspace="sales" />
		</div>
	</div>
</template>
