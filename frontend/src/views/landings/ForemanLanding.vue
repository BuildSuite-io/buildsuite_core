<script setup>
import { computed } from "vue";
import { ROLES } from "@/data/roles";
import { useDataStore } from "@/stores";
import LandingShell from "@/layouts/LandingShell.vue";

const ROLE_ID = "foreman";
const role = ROLES.find((r) => r.id === ROLE_ID);
const store = useDataStore();
const workspaceCount = computed(() => store.visibleWorkspaces.length);
</script>

<template>
	<LandingShell>
		<div class="max-w-4xl mx-auto px-6 py-12">
			<div class="flex items-center gap-4 mb-5">
				<span :class="role.color" class="w-12 h-12 rounded-xl flex-shrink-0"></span>
				<div>
					<p class="text-xs text-ink-500 uppercase tracking-wider mb-0.5">
						Logged in as
					</p>
					<h1 class="text-3xl font-semibold text-ink-900 tracking-tight">
						{{ role.name }}
					</h1>
				</div>
			</div>

			<p class="text-base text-ink-600 leading-relaxed max-w-2xl">{{ role.description }}</p>

			<div class="mt-8 grid grid-cols-2 sm:grid-cols-3 gap-3 max-w-xl">
				<div class="bg-white border border-ink-200 rounded-xl p-4">
					<div class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">
						Workspaces
					</div>
					<div class="text-2xl font-semibold text-ink-900 mt-1">
						{{ workspaceCount }}
					</div>
				</div>
			</div>

			<div
				class="mt-10 px-5 py-4 bg-brand-50 border border-brand-200 rounded-lg text-sm text-brand-800 max-w-2xl"
			>
				<strong>Detailed landing page coming in Phase 2.x.</strong>
				This is a stub. The next set of prompts will populate role-specific shortcuts,
				KPIs, and recent activity tuned to a {{ role.shortName }}'s day.
			</div>
		</div>
	</LandingShell>
</template>
