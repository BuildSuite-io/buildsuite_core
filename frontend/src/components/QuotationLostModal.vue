<script setup>
// "Why was it lost?" — ERPNext's Set as Lost for a quotation. At least one reason (or a few words
// of explanation) is needed; reasons and competitors are ERPNext masters, added in place the way a
// Link field's "Create new" would.
import { computed, ref, watch } from "vue";
import { useDataStore } from "@/stores";
import { createDataAdapter } from "@/data/adapters";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskTextarea from "@/components/desk/DeskTextarea.vue";
import { __ } from "@/utils/translate";

const props = defineProps({
	open: { type: Boolean, default: false },
	title: { type: String, default: "" },
	saving: { type: Boolean, default: false },
});
const emit = defineEmits(["close", "confirm"]);

const adapter = createDataAdapter(useDataStore());
const rowsOf = (r) => {
	const raw = r?.data;
	return Array.isArray(raw) ? raw : Array.isArray(raw?.value) ? raw.value : [];
};
const reasonsResource = adapter.list("Quotation Lost Reason", {
	fields: ["name", "order_lost_reason"],
	orderBy: "order_lost_reason asc",
	pageLength: 0,
});
const competitorsResource = adapter.list("Competitor", {
	fields: ["name", "competitor_name"],
	orderBy: "competitor_name asc",
	pageLength: 0,
});
const reasons = computed(() => rowsOf(reasonsResource));
const competitors = computed(() => rowsOf(competitorsResource));

const chosenReasons = ref([]);
const chosenCompetitors = ref([]);
const detail = ref("");
const newReason = ref("");
const newCompetitor = ref("");
const error = ref("");

watch(
	() => props.open,
	(o) => {
		if (!o) return;
		chosenReasons.value = [];
		chosenCompetitors.value = [];
		detail.value = "";
		newReason.value = "";
		newCompetitor.value = "";
		error.value = "";
	}
);

function toggle(list, name) {
	const i = list.value.indexOf(name);
	if (i >= 0) list.value.splice(i, 1);
	else list.value.push(name);
}

async function addReason() {
	const n = newReason.value.trim();
	if (!n) return;
	try {
		const doc = await adapter.create("Quotation Lost Reason", { order_lost_reason: n });
		await reasonsResource.reload?.();
		chosenReasons.value.push(doc.name || n);
		newReason.value = "";
	} catch (e) {
		error.value = e?.message || __("Could not add the reason.");
	}
}
async function addCompetitor() {
	const n = newCompetitor.value.trim();
	if (!n) return;
	try {
		const doc = await adapter.create("Competitor", { competitor_name: n });
		await competitorsResource.reload?.();
		chosenCompetitors.value.push(doc.name || n);
		newCompetitor.value = "";
	} catch (e) {
		error.value = e?.message || __("Could not add the competitor.");
	}
}

function confirm() {
	if (!chosenReasons.value.length && !detail.value.trim()) {
		error.value = __("Pick a reason, or say in a few words why it was lost.");
		return;
	}
	emit("confirm", {
		lostReasons: [...chosenReasons.value],
		competitors: [...chosenCompetitors.value],
		detailedReason: detail.value.trim(),
	});
}
</script>

<template>
	<Teleport to="body">
		<div
			v-if="open"
			class="fixed inset-0 bg-ink-900/40 z-[60] flex items-end sm:items-center justify-center sm:p-4"
			@click="emit('close')"
		>
			<div
				class="bg-white w-full sm:max-w-lg max-h-[92vh] flex flex-col rounded-t-2xl sm:rounded-xl border border-ink-200 shadow-fp-lg"
				role="dialog"
				@click.stop
			>
				<header class="px-4 sm:px-5 py-3 border-b border-ink-200 shrink-0">
					<h2 class="text-sm font-semibold text-ink-900">
						{{ __("Why was it lost?") }}
					</h2>
					<p v-if="title" class="text-xs text-ink-500 mt-0.5">{{ title }}</p>
				</header>
				<div class="px-4 sm:px-5 py-4 overflow-y-auto flex-1 space-y-4">
					<DeskField :label="__('Reasons')">
						<div class="flex flex-wrap gap-1.5">
							<button
								v-for="r in reasons"
								:key="r.name"
								type="button"
								class="text-xs px-2.5 py-1 border"
								style="border-radius: 9999px"
								:class="
									chosenReasons.includes(r.name)
										? 'bg-danger-50 border-danger-300 text-danger-700'
										: 'bg-white border-ink-200 text-ink-700 hover:bg-ink-50'
								"
								@click="toggle(chosenReasons, r.name)"
							>
								{{ r.order_lost_reason || r.name }}
							</button>
							<span v-if="!reasons.length" class="text-xs text-ink-500">{{
								__("None yet. Add one below.")
							}}</span>
						</div>
						<div class="flex gap-2 mt-2">
							<DeskInput
								v-model="newReason"
								:placeholder="__('Add a reason…')"
								@keyup.enter="addReason"
							/>
							<button
								type="button"
								class="text-xs px-3 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 shrink-0"
								style="border-radius: 6px"
								@click="addReason"
							>
								{{ __("Add") }}
							</button>
						</div>
					</DeskField>

					<DeskField :label="__('Lost to')">
						<div class="flex flex-wrap gap-1.5">
							<button
								v-for="c in competitors"
								:key="c.name"
								type="button"
								class="text-xs px-2.5 py-1 border"
								style="border-radius: 9999px"
								:class="
									chosenCompetitors.includes(c.name)
										? 'bg-ink-900 border-ink-900 text-white'
										: 'bg-white border-ink-200 text-ink-700 hover:bg-ink-50'
								"
								@click="toggle(chosenCompetitors, c.name)"
							>
								{{ c.competitor_name || c.name }}
							</button>
						</div>
						<div class="flex gap-2 mt-2">
							<DeskInput
								v-model="newCompetitor"
								:placeholder="__('Add a competitor…')"
								@keyup.enter="addCompetitor"
							/>
							<button
								type="button"
								class="text-xs px-3 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 shrink-0"
								style="border-radius: 6px"
								@click="addCompetitor"
							>
								{{ __("Add") }}
							</button>
						</div>
					</DeskField>

					<DeskField :label="__('In a few words')">
						<DeskTextarea
							v-model="detail"
							:rows="3"
							:placeholder="__('What the client said')"
						/>
					</DeskField>
					<p v-if="error" class="text-xs text-danger-700">{{ error }}</p>
				</div>
				<footer
					class="px-4 sm:px-5 py-3 border-t border-ink-200 flex justify-end gap-2 shrink-0"
				>
					<button
						type="button"
						class="text-xs px-3 h-9 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 rounded-md"
						@click="emit('close')"
					>
						{{ __("Cancel") }}
					</button>
					<button
						type="button"
						class="desk-save-btn !h-9"
						:disabled="saving"
						@click="confirm"
					>
						{{ saving ? __("Saving…") : __("Mark as rejected") }}
					</button>
				</footer>
			</div>
		</div>
	</Teleport>
</template>
