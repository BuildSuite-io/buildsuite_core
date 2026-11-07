<script setup>
// Workforce landing — greeting, a DocType shortcuts grid, and a Reports group.

import { computed } from "vue";
import { RouterLink } from "vue-router";
import { usePermissions } from "@/composables/usePermissions";
import WorkspaceIcon from "@/components/WorkspaceIcon.vue";
import WorkspaceShortcut from "@/components/WorkspaceShortcut.vue";
import WorkspaceReportsSection from "@/components/workspaces/WorkspaceReportsSection.vue";
import { __, currentLang } from "@/utils/translate";

const { canRead } = usePermissions();

const today = computed(() => {
	const d = new Date();
	return d.toLocaleDateString(currentLang(), {
		weekday: "long",
		month: "short",
		day: "numeric",
	});
});

const shortcuts = [
	{ label: "Field Employees", icon: "hard-hat", to: "/field-employees", cap: "fieldEmployee" },
	{ label: "Crews", icon: "users-2", to: "/crews", cap: "crew" },
	{
		label: "Field Attendance",
		icon: "clipboard-list",
		to: "/field-attendance",
		cap: "fieldAttendance",
	},
];
</script>

<template>
	<div class="bg-white min-h-full">
		<div class="max-w-6xl mx-auto px-6 py-8">
			<div class="mb-6">
				<div class="text-xs text-ink-500 mb-1">{{ today }}</div>
				<h1 class="text-2xl font-semibold text-ink-900">{{ __("Workforce") }}</h1>
			</div>

			<!-- Dashboard CTA tile -->
			<RouterLink
				v-if="canRead('fieldAttendance')"
				to="/workforce-dashboard"
				class="mb-5 block bg-brand-50 border border-brand-200 hover:border-brand-400 hover:shadow-sm p-4 rounded-lg group transition-all"
			>
				<div class="flex items-start gap-4">
					<div
						class="w-11 h-11 rounded-lg bg-brand-100 text-brand-700 flex items-center justify-center flex-shrink-0"
					>
						<WorkspaceIcon slug="chart-bar" :size="22" :stroke-width="1.75" />
					</div>
					<div class="flex-1 min-w-0">
						<div class="flex items-center gap-2">
							<div
								class="text-base font-semibold text-ink-900 group-hover:text-brand-700 transition-colors"
							>
								{{ __("Workforce Dashboard") }}
							</div>
							<span
								class="text-[9px] px-1.5 py-0.5 bg-brand-100 text-brand-700 font-medium uppercase tracking-wider"
								style="border-radius: 2px"
								>{{ __("Live") }}</span
							>
						</div>
						<div class="text-xs text-brand-700 mt-1 leading-snug">
							{{ __("Workers, crews, man-days and labour cost at a glance.") }}
						</div>
					</div>
					<div
						class="text-brand-400 group-hover:text-brand-600 transition-colors text-xl"
					>
						→
					</div>
				</div>
			</RouterLink>

			<!-- Shortcuts grid -->
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
				<WorkspaceShortcut
					v-for="sc in shortcuts"
					:key="sc.label"
					:icon="sc.icon"
					:label="__(sc.label)"
					:to="sc.to"
					:cap="sc.cap"
				/>
			</div>

			<WorkspaceReportsSection workspace="workforce" />
		</div>
	</div>
</template>
