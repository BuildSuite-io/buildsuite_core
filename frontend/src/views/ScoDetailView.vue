<script setup>
// Scope Change Order detail + approval flow (M7). Pending Approval → Approved /
// Rejected, with Revise to re-open. Workflow transitions go through scoApi; the
// doc itself is read/edited/deleted via the standard data adapter.

import { computed, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import { useConfirm } from "@/composables/useConfirm";
import { useFormErrors } from "@/composables/useFormErrors";
import { useDoctypeMeta } from "@/composables/useDoctypeMeta";
import { showToast } from "@/utils/appToast";
import { createDataAdapter } from "@/data/adapters";
import { fmtINR, fmtDate, impactClass, impactSign } from "@/utils/format";
import * as scoApi from "@/data/scoApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskTextarea from "@/components/desk/DeskTextarea.vue";
import StatusBadge from "@/components/StatusBadge.vue";

const props = defineProps({ id: String });
const router = useRouter();
const confirmDialog = useConfirm();
const { applyServerErrors } = useFormErrors({});
const adapter = createDataAdapter(useDataStore());

// Select options come from the DocType meta (single source of truth) — no
// hardcoded duplicate of the sco_type / cost_recovery field definitions.
const { selectOptions } = useDoctypeMeta("Scope Change Order");
const typeOptions = computed(() => selectOptions("sco_type"));
const recoveryOptions = computed(() => selectOptions("cost_recovery"));

const ACTION_LABEL = {
	raised: "Raised",
	submitted: "Submitted",
	approved: "Approved",
	rejected: "Rejected",
	revised: "Revised",
};

const resource = adapter.read("Scope Change Order", props.id, { fields: ["*"] });
const doc = computed(() => resource?.doc || null);

const isPending = computed(() => doc.value?.status === "Pending Approval");
const isApproved = computed(() => doc.value?.status === "Approved");
const isRejected = computed(() => doc.value?.status === "Rejected");
const canEdit = computed(() => isPending.value || isRejected.value);

const busy = ref(false);

const breadcrumbs = computed(() => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Scope Change", to: "/sco" },
	{ label: doc.value?.name || props.id },
]);

// Newest action first (most recent on top).
const activity = computed(() =>
	[...(doc.value?.scope_change_order_activity || [])].sort((a, b) =>
		(b.activity_on || "").localeCompare(a.activity_on || "")
	)
);

async function reload() {
	await resource?.reload?.();
}

// --- workflow actions -----------------------------------------------------
async function onApprove() {
	const ok = await confirmDialog({
		title: `Approve ${doc.value.name}?`,
		message: "This marks the scope change order as approved.",
		confirmLabel: "Approve",
	});
	if (!ok) return;
	busy.value = true;
	try {
		await scoApi.approveSco(props.id);
		await reload();
	} catch (err) {
		showToast(err.message || "Failed to approve", "error");
	} finally {
		busy.value = false;
	}
}

async function onRevise() {
	busy.value = true;
	try {
		await scoApi.reviseSco(props.id);
		await reload();
	} catch (err) {
		showToast(err.message || "Failed to re-open", "error");
	} finally {
		busy.value = false;
	}
}

async function onDelete() {
	const ok = await confirmDialog({
		title: `Delete ${doc.value.name}?`,
		message: "The scope change order will be permanently removed.",
		confirmLabel: "Delete",
		destructive: true,
	});
	if (!ok) return;
	try {
		await adapter.remove("Scope Change Order", props.id);
		router.push("/sco");
	} catch (err) {
		showToast(applyServerErrors(err) ?? "Failed to delete", "error");
	}
}

// --- edit modal -----------------------------------------------------------
const editing = ref(false);
const editForm = reactive({
	title: "",
	sco_type: "Design Change",
	cost_impact: 0,
	cost_recovery: "Internal",
	reason__justification: "",
});
function startEdit() {
	const d = doc.value;
	editForm.title = d.title || "";
	editForm.sco_type = d.sco_type || "Design Change";
	editForm.cost_impact = d.cost_impact || 0;
	editForm.cost_recovery = d.cost_recovery || "Internal";
	editForm.reason__justification = d.reason__justification || "";
	editing.value = true;
}
async function saveEdit() {
	busy.value = true;
	try {
		await adapter.update("Scope Change Order", props.id, {
			title: editForm.title.trim(),
			sco_type: editForm.sco_type,
			cost_impact: Number(editForm.cost_impact) || 0,
			cost_recovery: editForm.cost_recovery,
			reason__justification: editForm.reason__justification,
		});
		await reload();
		editing.value = false;
	} catch (err) {
		showToast(applyServerErrors(err) ?? "Failed to update", "error");
	} finally {
		busy.value = false;
	}
}

// --- reject modal ---------------------------------------------------------
const rejectOpen = ref(false);
const rejectComment = ref("");
const rejectError = ref("");
function openReject() {
	rejectComment.value = "";
	rejectError.value = "";
	rejectOpen.value = true;
}
async function confirmReject() {
	if (!rejectComment.value.trim()) {
		rejectError.value = "A reason is required to reject.";
		return;
	}
	busy.value = true;
	try {
		await scoApi.rejectSco(props.id, rejectComment.value.trim());
		rejectOpen.value = false;
		await reload();
	} catch (err) {
		showToast(err.message || "Failed to reject", "error");
	} finally {
		busy.value = false;
	}
}
</script>

<template>
	<DeskPage
		v-if="doc"
		:title="doc.title"
		:subtitle="`${doc.name} · ${doc.project}`"
		:breadcrumbs="breadcrumbs"
		:status="[doc.status, doc.sco_type]"
	>
		<template #actions>
			<button
				v-if="canEdit"
				type="button"
				class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
				style="border-radius: 6px"
				@click="startEdit"
			>
				Edit
			</button>
			<template v-if="isPending">
				<button
					type="button"
					class="text-xs px-2.5 py-1 border border-success-300 bg-success-50 hover:bg-success-100 text-success-700 font-medium"
					style="border-radius: 6px"
					:disabled="busy"
					@click="onApprove"
				>
					Approve
				</button>
				<button
					type="button"
					class="text-xs px-2.5 py-1 border border-danger-200 bg-white hover:bg-danger-50 text-danger-700"
					style="border-radius: 6px"
					:disabled="busy"
					@click="openReject"
				>
					Reject
				</button>
			</template>
			<template v-else-if="isApproved">
				<button
					type="button"
					class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
					style="border-radius: 6px"
					:disabled="busy"
					@click="onRevise"
				>
					Revise
				</button>
			</template>
			<template v-else-if="isRejected">
				<button
					type="button"
					class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
					style="border-radius: 6px"
					:disabled="busy"
					@click="onRevise"
				>
					Re-open
				</button>
			</template>
			<button
				type="button"
				class="text-xs px-2.5 py-1 border border-danger-200 bg-white hover:bg-danger-50 text-danger-700"
				style="border-radius: 6px"
				@click="onDelete"
			>
				Delete
			</button>
		</template>

		<!-- Rejected banner -->
		<div
			v-if="isRejected && doc.rejection_comment"
			class="mb-4 px-4 py-2.5 bg-danger-50 border border-danger-200 text-xs text-danger-700"
			style="border-radius: 6px"
		>
			<span class="font-semibold">Rejected:</span> {{ doc.rejection_comment }}
		</div>

		<!-- Summary strip -->
		<div class="grid grid-cols-2 md:grid-cols-5 gap-2 mb-4">
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Project</div>
				<div class="text-sm text-ink-900 mt-0.5 truncate">{{ doc.project }}</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Type</div>
				<div class="text-sm text-ink-900 mt-0.5">{{ doc.sco_type }}</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Cost impact</div>
				<div
					class="text-base font-semibold tabular-nums mt-0.5"
					:class="impactClass(doc.cost_impact)"
				>
					{{ impactSign(doc.cost_impact) }}{{ fmtINR(Math.abs(doc.cost_impact || 0)) }}
				</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Cost recovery</div>
				<div class="text-sm mt-0.5">
					{{ doc.cost_recovery === "Recoverable from Client" ? "Recoverable · client" : "Internal" }}
				</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Raised by</div>
				<div class="text-sm text-ink-900 mt-0.5 truncate">{{ doc.raised_by || "—" }}</div>
				<div class="text-[10px] text-ink-500">{{ doc.raised_date ? fmtDate(doc.raised_date) : "" }}</div>
			</div>
		</div>

		<!-- Reason -->
		<section
			v-if="doc.reason__justification"
			class="mb-4 px-4 py-3 bg-ink-50 border border-ink-200"
			style="border-radius: 6px"
		>
			<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-1">
				Reason / justification
			</div>
			<div class="text-sm text-ink-800 whitespace-pre-line">{{ doc.reason__justification }}</div>
		</section>


		<!-- Activity -->
		<section>
			<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700 mb-2">Activity</h3>
			<ul class="space-y-1.5">
				<li v-for="(a, i) in activity" :key="i" class="flex items-start gap-2 text-xs">
					<span class="text-ink-900 font-medium">{{ ACTION_LABEL[a.action] || a.action }}</span>
					<div class="text-ink-500">
						<span>by {{ a.user }}</span>
						<span class="text-ink-400"> · {{ a.activity_on ? fmtDate(a.activity_on.slice(0, 10)) : "" }}</span>
						<div v-if="a.comment" class="text-ink-600 mt-0.5">{{ a.comment }}</div>
					</div>
				</li>
			</ul>
		</section>

		<!-- Edit modal (Pending / Rejected only) -->
		<Teleport to="body">
			<div
				v-if="editing"
				class="fixed inset-0 bg-ink-900/40 z-[60] flex items-center justify-center p-6"
				@click.self="editing = false"
			>
				<div
					class="bg-white border border-ink-200 w-full max-w-2xl shadow-fp-lg flex flex-col"
					style="border-radius: 12px; max-height: calc(100vh - 3rem)"
					@click.stop
				>
					<header
						class="px-5 py-3 border-b border-ink-200 flex items-center justify-between"
						style="border-radius: 12px 12px 0 0"
					>
						<h2 class="text-sm font-semibold text-ink-900">Edit {{ doc.name }}</h2>
						<button
							type="button"
							class="text-ink-500 hover:text-ink-900 text-lg leading-none"
							@click="editing = false"
						>
							×
						</button>
					</header>
					<div class="p-5 overflow-y-auto flex-1">
						<DeskSection title="Scope change" :cols="2">
							<div class="md:col-span-2">
								<DeskField label="Title" required>
									<DeskInput v-model="editForm.title" />
								</DeskField>
							</div>
							<DeskField label="Type">
								<DeskSelect v-model="editForm.sco_type">
									<option v-for="t in typeOptions" :key="t">{{ t }}</option>
								</DeskSelect>
							</DeskField>
							<DeskField label="Cost impact (₹)" hint="Positive = added cost; negative = saving.">
								<DeskInput v-model.number="editForm.cost_impact" type="number" />
							</DeskField>
							<DeskField label="Cost recovery">
								<DeskSelect v-model="editForm.cost_recovery">
									<option v-for="r in recoveryOptions" :key="r">{{ r }}</option>
								</DeskSelect>
							</DeskField>
							<div class="md:col-span-2">
								<DeskField label="Reason / justification">
									<DeskTextarea v-model="editForm.reason__justification" :rows="4" />
								</DeskField>
							</div>
						</DeskSection>
						<p class="text-[11px] text-ink-400 italic mt-1">
							Project can't be changed after raising.
						</p>
					</div>
					<footer
						class="px-5 py-3 border-t border-ink-200 flex items-center justify-end gap-2"
						style="border-radius: 0 0 12px 12px"
					>
						<button
							type="button"
							class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
							style="border-radius: 6px"
							:disabled="busy"
							@click="editing = false"
						>
							Cancel
						</button>
						<button type="button" class="desk-save-btn" :disabled="busy" @click="saveEdit">
							{{ busy ? "Saving…" : "Save" }}
						</button>
					</footer>
				</div>
			</div>
		</Teleport>

		<!-- Reject modal -->
		<Teleport to="body">
			<div
				v-if="rejectOpen"
				class="fixed inset-0 bg-ink-900/40 z-[60] flex items-center justify-center p-6"
				@click.self="rejectOpen = false"
			>
				<div
					class="bg-white border border-ink-200 w-full max-w-md shadow-fp-lg flex flex-col"
					style="border-radius: 12px"
					@click.stop
				>
					<header class="px-5 py-3 border-b border-ink-200 flex items-center justify-between">
						<h2 class="text-sm font-semibold text-ink-900">Reject {{ doc.name }}</h2>
						<button
							type="button"
							class="text-ink-500 hover:text-ink-900 text-lg leading-none"
							@click="rejectOpen = false"
						>
							×
						</button>
					</header>
					<div class="p-5">
						<label class="block text-[11px] uppercase tracking-wider text-ink-500 font-medium mb-1">
							Reason for rejection<span class="text-danger-600 ml-0.5">*</span>
						</label>
						<DeskTextarea v-model="rejectComment" :rows="3" placeholder="Why is this scope change being rejected?" />
						<p v-if="rejectError" class="text-[11px] text-danger-700 mt-1">{{ rejectError }}</p>
					</div>
					<footer class="px-5 py-3 border-t border-ink-200 flex items-center justify-end gap-2">
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
							class="text-xs px-3 py-1.5 bg-danger-600 text-white hover:bg-danger-700 font-medium"
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

	<div v-else class="px-6 py-16 text-center">
		<div class="text-sm text-ink-700 mb-2">
			No scope change order <span class="font-mono">{{ props.id }}</span>.
		</div>
		<DeskLink to="/sco">← Back to Scope Change</DeskLink>
	</div>
</template>
