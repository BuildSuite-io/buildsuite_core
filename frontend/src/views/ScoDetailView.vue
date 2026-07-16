<script setup>
// Scope Change Order detail — view / edit (Pending or Rejected) + the approval
// flow (Approve / Reject / Revise) and the BOQ-revision tie-in raised from an
// approved change order. Impact colouring: positive = cost = red, negative = saving.

import { computed, ref, watch } from "vue";
import { useRouter, RouterLink } from "vue-router";
import { useDataStore } from "@/stores";
import { useSessionStore } from "@/stores/session";
import { useConfirm } from "@/composables/useConfirm";
import { useFormErrors } from "@/composables/useFormErrors";
import { showToast } from "@/utils/appToast";
import { createDataAdapter } from "@/data/adapters";
import { approveSco, rejectSco, reviseSco, createBoqRevision } from "@/data/scoApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskTextarea from "@/components/desk/DeskTextarea.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import { fmtINR, fmtDate } from "@/utils/format";

const props = defineProps({ id: String });
const router = useRouter();
const session = useSessionStore();
const confirmDialog = useConfirm();
const adapter = createDataAdapter(useDataStore());
const { errors, applyServerErrors, setErrors } = useFormErrors({ title: "title" });

const TYPES = [
	"Design Change",
	"Client Request",
	"Statutory",
	"Site Condition",
	"Rework",
	"Other",
];
const APPROVER_ROLES = [
	"BuildSuite PM",
	"BuildSuite Director",
	"BuildSuite Administrator",
	"System Manager",
];

const resource = adapter.read("Scope Change Order", props.id, { fields: ["*"] });
const sco = computed(() => resource?.doc || null);

const isPending = computed(() => sco.value?.status === "Pending Approval");
const isApproved = computed(() => sco.value?.status === "Approved");
const isRejected = computed(() => sco.value?.status === "Rejected");
// Audit trail of workflow actions (approve / reject / revise), newest first.
const activity = computed(() =>
	[...(sco.value?.scope_change_order_activity || [])].sort((a, b) =>
		(b.activity_on || "").localeCompare(a.activity_on || ""),
	),
);
const canApprove = computed(() =>
	(session.access?.roles || []).some((r) => APPROVER_ROLES.includes(r)),
);

const editing = ref(false);
const saving = ref(false);
const busy = ref(false);
const form = ref({});

function snapshot() {
	const d = sco.value;
	if (!d) return {};
	return {
		title: d.title || "",
		type: d.type || "Design Change",
		impact: d.impact || 0,
		recoverable: d.recoverable ? "1" : "0",
		reason: d.reason || "",
	};
}
watch(
	sco,
	(v) => {
		if (v && !editing.value) form.value = snapshot();
	},
	{ immediate: true },
);

function startEdit() {
	form.value = snapshot();
	setErrors({});
	editing.value = true;
}
function cancelEdit() {
	editing.value = false;
}
async function saveEdit() {
	if (!form.value.title?.trim()) {
		setErrors({ title: "Title is required." });
		return;
	}
	saving.value = true;
	try {
		await adapter.update("Scope Change Order", props.id, {
			title: form.value.title.trim(),
			type: form.value.type,
			impact: Number(form.value.impact) || 0,
			recoverable: form.value.recoverable === "1" ? 1 : 0,
			reason: form.value.reason,
		});
		await resource?.reload?.();
		editing.value = false;
	} catch (err) {
		showToast(applyServerErrors(err) ?? "Failed to update change order", "error");
	} finally {
		saving.value = false;
	}
}

async function onApprove() {
	const ok = await confirmDialog({
		title: `Approve ${sco.value.name}?`,
		message: "Approving lets a BOQ revision be raised from this change order.",
		confirmLabel: "Approve",
	});
	if (!ok) return;
	busy.value = true;
	try {
		await approveSco(sco.value.name);
		await resource?.reload?.();
		showToast("Scope change order approved.");
	} catch (err) {
		showToast(err.message || "Approve failed", "error");
	} finally {
		busy.value = false;
	}
}

const rejectOpen = ref(false);
const rejectReason = ref("");
function openReject() {
	rejectReason.value = "";
	rejectOpen.value = true;
}
async function confirmReject() {
	busy.value = true;
	try {
		await rejectSco(sco.value.name, rejectReason.value);
		await resource?.reload?.();
		rejectOpen.value = false;
		showToast("Scope change order rejected.");
	} catch (err) {
		showToast(err.message || "Reject failed", "error");
	} finally {
		busy.value = false;
	}
}

async function onRevise() {
	busy.value = true;
	try {
		await reviseSco(sco.value.name);
		await resource?.reload?.();
		showToast("Reopened for revision.");
	} catch (err) {
		showToast(err.message || "Revise failed", "error");
	} finally {
		busy.value = false;
	}
}

async function onCreateBoqRevision() {
	const ok = await confirmDialog({
		title: "Raise BOQ revision?",
		message:
			"This clones the project's current BOQ into a new Draft revision linked to this change order.",
		confirmLabel: "Raise revision",
	});
	if (!ok) return;
	busy.value = true;
	try {
		const res = await createBoqRevision(sco.value.name);
		router.push(`/boq/${res.boq}`);
	} catch (err) {
		showToast(err.message || "Failed to raise BOQ revision", "error");
	} finally {
		busy.value = false;
	}
}

async function onDelete() {
	const ok = await confirmDialog({
		title: `Delete ${sco.value.name}?`,
		message: "This scope change order will be removed permanently.",
		confirmLabel: "Delete",
		destructive: true,
	});
	if (!ok) return;
	try {
		await adapter.remove("Scope Change Order", props.id);
		router.push("/sco");
	} catch (err) {
		showToast(err.message || "Failed to delete change order", "error");
	}
}

const breadcrumbs = computed(() => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Scope Change Orders", to: "/sco" },
	{ label: sco.value?.name || props.id },
]);
</script>

<template>
	<DeskPage
		v-if="sco"
		:title="sco.title"
		:subtitle="`${sco.name} · ${sco.project_name || sco.project}`"
		:breadcrumbs="breadcrumbs"
		:status="sco.status"
	>
		<template #actions>
			<template v-if="!editing">
				<button
					v-if="isPending || isRejected"
					type="button"
					class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
					style="border-radius: 6px"
					@click="startEdit"
				>
					Edit
				</button>
				<button
					v-if="isPending && canApprove"
					type="button"
					class="text-xs px-2.5 py-1 border border-success-300 bg-success-50 hover:bg-success-100 text-success-700 font-medium"
					style="border-radius: 6px"
					:disabled="busy"
					@click="onApprove"
				>
					Approve
				</button>
				<button
					v-if="isPending && canApprove"
					type="button"
					class="text-xs px-2.5 py-1 border border-danger-200 bg-white hover:bg-danger-50 text-danger-700"
					style="border-radius: 6px"
					:disabled="busy"
					@click="openReject"
				>
					Reject
				</button>
				<button
					v-if="isApproved && !sco.boq_revision"
					type="button"
					class="text-xs px-2.5 py-1 border border-brand-300 bg-brand-50 hover:bg-brand-100 text-brand-700 font-medium"
					style="border-radius: 6px"
					:disabled="busy"
					@click="onCreateBoqRevision"
				>
					+ Raise BOQ revision
				</button>
				<button
					v-if="isApproved || isRejected"
					type="button"
					class="text-xs px-2.5 py-1 border border-warning-200 bg-warning-50 hover:bg-warning-100 text-warning-700 font-medium"
					style="border-radius: 6px"
					:disabled="busy"
					@click="onRevise"
				>
					Revise
				</button>
				<button
					type="button"
					class="text-xs px-2.5 py-1 border border-danger-200 bg-white hover:bg-danger-50 text-danger-700"
					style="border-radius: 6px"
					@click="onDelete"
				>
					Delete
				</button>
			</template>
			<template v-else>
				<button
					type="button"
					class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
					style="border-radius: 6px"
					@click="cancelEdit"
				>
					Cancel
				</button>
				<button type="button" class="desk-save-btn" :disabled="saving" @click="saveEdit">
					{{ saving ? "Saving…" : "Save" }}
				</button>
			</template>
		</template>

		<!-- Pending, not an approver: hint -->
		<div
			v-if="isPending && !canApprove && !editing"
			class="mb-4 px-3 py-2 text-xs text-ink-600 bg-warning-50 border border-warning-200 rounded"
		>
			Awaiting PM / Director approval.
		</div>

		<!-- View mode -->
		<div v-if="!editing">
			<div class="grid grid-cols-2 md:grid-cols-5 gap-2 mb-4">
				<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
						Project
					</div>
					<div class="text-sm text-ink-900 mt-0.5 truncate">
						{{ sco.project_name || sco.project }}
					</div>
				</div>
				<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
						Type
					</div>
					<div class="text-sm text-ink-900 mt-0.5">{{ sco.type }}</div>
				</div>
				<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
						Cost impact
					</div>
					<div
						class="text-base font-semibold tabular-nums mt-0.5"
						:class="Number(sco.impact) >= 0 ? 'text-danger-700' : 'text-success-700'"
					>
						{{ Number(sco.impact) >= 0 ? "+" : "-"
						}}{{ fmtINR(Math.abs(Number(sco.impact) || 0)) }}
					</div>
				</div>
				<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
						Recoverable
					</div>
					<div class="text-sm text-ink-900 mt-0.5">
						{{ sco.recoverable ? "Yes · from client" : "Internal" }}
					</div>
				</div>
				<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
						Raised
					</div>
					<div class="text-sm text-ink-900 mt-0.5 truncate">
						{{ sco.raised_by || "—" }}
					</div>
					<div class="text-[10px] text-ink-500">{{ fmtDate(sco.raised_date) }}</div>
				</div>
			</div>

			<DeskSection title="Justification" :cols="1">
				<DeskField label="Reason"
					><div class="text-sm text-ink-800 whitespace-pre-line">
						{{ sco.reason || "—" }}
					</div></DeskField
				>
			</DeskSection>

			<DeskSection v-if="isRejected && sco.rejection_reason" title="Rejection" :cols="1">
				<DeskField label="Reason"
					><div class="text-sm text-danger-700 whitespace-pre-line">
						{{ sco.rejection_reason }}
					</div></DeskField
				>
			</DeskSection>

			<!-- BOQ Impact -->
			<section class="mt-6">
				<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700 mb-2">
					BOQ impact
				</h3>
				<div v-if="sco.boq_revision" class="text-sm text-ink-700">
					BOQ revision raised:
					<DeskLink :to="`/boq/${sco.boq_revision}`">{{ sco.boq_revision }}</DeskLink>
				</div>
				<div v-else-if="isApproved" class="text-xs text-ink-500 italic">
					No BOQ revision yet — use “+ Raise BOQ revision” above to branch the project's
					BOQ.
				</div>
				<div v-else class="text-xs text-ink-400 italic">
					A BOQ revision can be raised once this change order is approved.
				</div>
			</section>

			<!-- Activity -->
			<section v-if="activity.length" class="mt-6">
				<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700 mb-2">
					Activity
				</h3>
				<ul class="space-y-1.5">
					<li
						v-for="(a, i) in activity"
						:key="i"
						class="flex items-start gap-1.5 text-xs flex-wrap"
					>
						<span class="font-medium text-ink-800">{{ a.action }}</span>
						<span class="text-ink-500">by {{ a.user }}</span>
						<span class="text-ink-400">
							· {{ a.activity_on ? fmtDate(a.activity_on.slice(0, 10)) : "" }}</span
						>
						<span v-if="a.comment" class="text-ink-600 italic">— {{ a.comment }}</span>
					</li>
				</ul>
			</section>
		</div>

		<!-- Edit mode -->
		<div v-else>
			<DeskSection title="Change order" :cols="2">
				<DeskField label="Project"
					><div class="text-sm text-ink-700">
						{{ sco.project_name || sco.project }}
					</div></DeskField
				>
				<DeskField label="Type">
					<DeskSelect v-model="form.type"
						><option v-for="t in TYPES" :key="t">{{ t }}</option></DeskSelect
					>
				</DeskField>
				<DeskField label="Title" required :error="errors.title" class="md:col-span-2"
					><DeskInput v-model="form.title"
				/></DeskField>
				<DeskField
					label="Cost impact (₹)"
					hint="Positive = added cost; negative = a saving."
					><DeskInput v-model.number="form.impact" type="number" step="1000"
				/></DeskField>
				<DeskField label="Cost recovery">
					<DeskSelect v-model="form.recoverable">
						<option value="1">Recoverable from client</option>
						<option value="0">Internal — absorbed by us</option>
					</DeskSelect>
				</DeskField>
				<DeskField label="Reason / justification" class="md:col-span-2"
					><DeskTextarea v-model="form.reason" :rows="4"
				/></DeskField>
			</DeskSection>
		</div>

		<!-- Reject modal -->
		<Teleport to="body">
			<div
				v-if="rejectOpen"
				class="fixed inset-0 bg-ink-900/40 z-[60] flex items-center justify-center p-6"
				@click.self="rejectOpen = false"
			>
				<div
					class="bg-white border border-ink-200 w-full max-w-md shadow-lg"
					style="border-radius: 12px"
					@click.stop
				>
					<header class="px-5 py-3 border-b border-ink-200">
						<h2 class="text-sm font-semibold text-ink-900">Reject {{ sco.name }}</h2>
					</header>
					<div class="p-5">
						<DeskField label="Rejection reason"
							><DeskTextarea
								v-model="rejectReason"
								:rows="4"
								placeholder="Why is this change order rejected?"
						/></DeskField>
					</div>
					<footer
						class="px-5 py-3 border-t border-ink-200 flex items-center justify-end gap-2"
					>
						<button
							type="button"
							class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
							style="border-radius: 6px"
							@click="rejectOpen = false"
						>
							Cancel
						</button>
						<button
							type="button"
							class="text-xs px-3 py-1.5 border border-danger-300 bg-danger-50 hover:bg-danger-100 text-danger-700 font-medium"
							style="border-radius: 6px"
							:disabled="busy"
							@click="confirmReject"
						>
							Reject
						</button>
					</footer>
				</div>
			</div>
		</Teleport>
	</DeskPage>

	<div v-else class="px-3 py-2 text-sm text-ink-500">Loading scope change order…</div>
</template>
