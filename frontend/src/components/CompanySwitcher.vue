<script setup>
// Topbar Company switcher. CLAUDE.md §14.6.
//
// Visible only when more than one company exists in the seed (via store.isMultiCompany).
// Same UX shape as RoleSwitcher — pill trigger + dropdown panel + "Prototype affordance"
// caption so reviewers don't mistake this for a real authorization mechanism.
//
// Picking a company calls store.setActiveCompany which writes to its own
// localStorage key (buildsuite:company) and persists across reloads.

import { ref, computed } from "vue";
import { useDataStore } from "@/stores";

const store = useDataStore();
const open = ref(false);
const currentCompany = computed(() => store.currentCompany);

function pickCompany(id) {
	store.setActiveCompany(id);
	open.value = false;
}
</script>

<template>
	<div v-if="store.isMultiCompany && currentCompany" class="relative">
		<!-- Trigger -->
		<button
			@click="open = !open"
			class="h-7 pl-1 pr-2 rounded-md hover:bg-ink-50 flex items-center gap-2 border border-ink-200"
			:title="`Switch company · current: ${currentCompany.name}`"
		>
			<span :class="currentCompany.color" class="w-5 h-5 rounded flex-shrink-0"></span>
			<span class="text-xs font-medium text-ink-700 whitespace-nowrap">{{
				currentCompany.shortName
			}}</span>
			<svg
				class="w-3 h-3 text-ink-400"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M19 9l-7 7-7-7"
				/>
			</svg>
		</button>

		<!-- Backdrop + panel -->
		<template v-if="open">
			<div class="fixed inset-0 z-30" @click="open = false"></div>
			<div
				class="absolute right-0 top-full mt-1 w-80 bg-white border border-ink-200 rounded-lg shadow-fp-lg z-40 overflow-hidden"
				@click.stop
			>
				<div
					class="px-3 py-2 text-[11px] font-semibold text-ink-500 uppercase tracking-wider border-b border-ink-200 bg-ink-50"
				>
					Switch company
				</div>
				<div class="max-h-[65vh] overflow-y-auto scrollbar-thin">
					<button
						v-for="c in store.companies"
						:key="c.id"
						@click="pickCompany(c.id)"
						class="w-full flex items-start gap-2.5 px-3 py-2.5 text-left hover:bg-ink-50 border-b border-ink-100 last:border-b-0"
						:class="c.id === currentCompany.id ? 'bg-brand-50' : ''"
					>
						<span
							:class="c.color"
							class="w-2.5 h-2.5 rounded-full mt-1.5 flex-shrink-0"
						></span>
						<div class="flex-1 min-w-0">
							<div class="text-sm font-medium text-ink-900 leading-tight">
								{{ c.name }}
							</div>
							<div class="text-[11px] text-ink-500 mt-0.5 leading-snug">
								{{ c.description }}
							</div>
						</div>
						<span
							v-if="c.id === currentCompany.id"
							class="text-brand-600 text-sm mt-0.5 flex-shrink-0"
							aria-label="current company"
							>✓</span
						>
					</button>
				</div>
			</div>
		</template>
	</div>
</template>
