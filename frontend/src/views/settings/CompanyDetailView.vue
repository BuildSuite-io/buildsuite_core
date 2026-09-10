<script setup>
// Company detail / edit — Settings sub-page. Admin-only mutations (Edit / Save
// / Delete buttons hidden for non-admin). ID is locked after create (stripped
// from any patch in store.updateCompany, per Frappe Naming Series convention).
// Delete is reference-guarded — store.deleteCompany returns {ok:false} with the
// list of linked projects when blocked.

import { ref, computed, watch } from "vue";
import { useRouter, RouterLink } from "vue-router";
import { useDataStore } from "@/stores";
import { useConfirm } from "@/composables/useConfirm";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskTextarea from "@/components/desk/DeskTextarea.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import {
	getCompanyBranding,
	updateCompanyBranding,
	uploadCompanyLogo,
	getCompanyProjects,
} from "@/data/companyApi";
import { showToast } from "@/utils/appToast";

const props = defineProps({ id: String });
const router = useRouter();
const store = useDataStore();
const confirmDialog = useConfirm();

const COLOR_OPTIONS = [
	{ value: "bg-brand-600", label: "Green" },
	{ value: "bg-blue-600", label: "Blue" },
	{ value: "bg-violet-600", label: "Violet" },
	{ value: "bg-amber-600", label: "Amber" },
	{ value: "bg-emerald-600", label: "Emerald" },
	{ value: "bg-rose-600", label: "Rose" },
	{ value: "bg-cyan-600", label: "Cyan" },
	{ value: "bg-ink-600", label: "Slate" },
];

const company = computed(() => store.companyById(props.id));
// Real projects that belong to this company (backend, permission-respecting) — not the
// prototype's local projects slice.
const linkedProjects = ref([]); // a capped sample of the company's projects
const linkedProjectsTotal = ref(0); // the real total (a company can own thousands)
async function loadLinkedProjects() {
	try {
		const r = (await getCompanyProjects(props.id)) || {};
		linkedProjects.value = r.rows || [];
		linkedProjectsTotal.value = r.total || 0;
	} catch {
		linkedProjects.value = [];
		linkedProjectsTotal.value = 0;
	}
}
const editing = ref(false);
const form = ref({});

watch(
	company,
	(c) => {
		if (c) form.value = JSON.parse(JSON.stringify(c));
	},
	{ immediate: true }
);

function startEdit() {
	if (!store.isAdmin) return;
	form.value = JSON.parse(JSON.stringify(company.value));
	editing.value = true;
}
function cancelEdit() {
	form.value = JSON.parse(JSON.stringify(company.value));
	editing.value = false;
}
async function saveEdit() {
	if (!store.isAdmin) return;
	// Name (company_name) and Short name (abbr) are the real editable identity fields;
	// colour is derived and description isn't a Company field, so neither persists.
	try {
		await store.updateCompany(props.id, {
			name: form.value.name,
			shortName: form.value.shortName,
		});
		editing.value = false;
	} catch (err) {
		showToast(err.message || "Could not save the company.", "error");
	}
}
function onPrimary() {
	editing.value ? saveEdit() : startEdit();
}

async function deleteCompany() {
	if (!store.isAdmin) return;
	// The backend is the authority on whether the company is still referenced (Frappe
	// LinkExistsError across every doctype) — don't pre-judge from the local projects slice,
	// which can't see every real link and would give a false "safe to delete".
	if (
		!(await confirmDialog({
			title: "Delete company",
			message: `Delete company "${company.value.name}"?\n\nThis is permanent and only succeeds if no record still references this company.`,
			confirmLabel: "Delete",
			destructive: true,
		}))
	)
		return;
	const result = await store.deleteCompany(props.id);
	if (result.ok) {
		router.push("/settings/companies");
	} else {
		showToast(
			`Can't delete "${company.value.name}" — records still reference it. Reassign or remove them first.`,
			"error"
		);
	}
}

const breadcrumbs = computed(() => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Settings", to: "/settings" },
	{ label: "Companies", to: "/settings/companies" },
]);

const titleStatus = computed(() => {
	const out = [];
	if (company.value && company.value.id === store.activeCompany) out.push("Active");
	return out;
});

// --- Branding & Letter Head -------------------------------------------------
// The brand (logo + subtext) is a REAL ERPNext Company field, materialised into the
// shared letter head server-side (Company.on_update → rebuild_letter_head), so saving
// re-brands every print format. Single-company seam: only the default company drives the
// (single) letter head today, so the section shows on the active company; per-company
// branding falls out when multi-company support lands (the backend is already keyed by
// company). Wired to the real backend independent of the prototype's mock company store.
const isActiveCompany = computed(
	() => company.value && company.value.id === store.activeCompany
);
const brandFileInput = ref(null);
const brand = ref({ loading: false, saving: false, uploading: false });
const brandCompanyName = ref("");
const letterHeadName = ref("");
const brandLoaded = ref({ logo: "", subtext: "" });
const brandForm = ref({ logo: "", subtext: "" });
const brandDirty = computed(
	() =>
		brandForm.value.logo !== brandLoaded.value.logo ||
		brandForm.value.subtext !== brandLoaded.value.subtext
);

// Initials for the no-logo placeholder — mirrors the backend letter head (legal suffixes dropped).
const monogram = computed(() => {
	const words = String(brandCompanyName.value || company.value?.name || "")
		.split(/\s+/)
		.filter((w) => w && !/^(pvt|private|ltd|limited|llp|inc|co|and|&)$/i.test(w))
		.map((w) => w.replace(/[^A-Za-z0-9]/g, ""))
		.filter(Boolean);
	return (
		words
			.slice(0, 2)
			.map((w) => w[0].toUpperCase())
			.join("") || "BS"
	);
});

async function loadBrand() {
	brand.value.loading = true;
	try {
		const b = await getCompanyBranding(props.id);
		brandCompanyName.value = b.company_name || b.company || "";
		letterHeadName.value = b.letter_head || "";
		brandLoaded.value = { logo: b.logo || "", subtext: b.letter_head_subtext || "" };
		brandForm.value = { ...brandLoaded.value };
	} catch (err) {
		showToast(err.message || "Failed to load branding", "error");
	} finally {
		brand.value.loading = false;
	}
}
function pickLogo() {
	if (store.isAdmin) brandFileInput.value?.click();
}
async function onLogoSelected(e) {
	const file = e.target.files?.[0];
	e.target.value = ""; // allow re-selecting the same file
	if (!file) return;
	if (!file.type.startsWith("image/")) {
		showToast("Please choose an image file.", "error");
		return;
	}
	brand.value.uploading = true;
	try {
		const url = await uploadCompanyLogo(file);
		if (!url) throw new Error("Upload returned no file URL.");
		brandForm.value.logo = url;
		showToast("Logo uploaded — Save branding to apply.", "success");
	} catch (err) {
		showToast(err.message || "Upload failed", "error");
	} finally {
		brand.value.uploading = false;
	}
}
function removeLogo() {
	brandForm.value.logo = "";
}
async function saveBrand() {
	if (!store.isAdmin || !brandDirty.value) return;
	brand.value.saving = true;
	try {
		const b = await updateCompanyBranding({
			company: props.id,
			logo: brandForm.value.logo,
			letter_head_subtext: brandForm.value.subtext,
		});
		brandLoaded.value = { logo: b.logo || "", subtext: b.letter_head_subtext || "" };
		brandForm.value = { ...brandLoaded.value };
		showToast("Branding saved — this company's letter head updated.", "success");
	} catch (err) {
		showToast(err.message || "Save failed", "error");
	} finally {
		brand.value.saving = false;
	}
}

// Branding + linked projects are per-company — (re)load for whichever company is being viewed.
watch(
	() => props.id,
	(id) => {
		if (!id) return;
		loadBrand();
		loadLinkedProjects();
	},
	{ immediate: true }
);
</script>

<template>
	<DeskPage
		v-if="company"
		:title="company.name"
		:subtitle="company.id"
		:breadcrumbs="breadcrumbs"
		:status="titleStatus"
	>
		<DeskForm>
			<template #action-bar>
				<DeskActionBar
					v-if="store.isAdmin"
					:save-label="editing ? 'Save' : 'Edit'"
					:show-cancel="editing"
					cancel-label="Cancel"
					@save="onPrimary"
					@cancel="cancelEdit"
				>
					<template #left>
						<span v-if="linkedProjectsTotal" class="text-[11px] text-ink-500">
							{{ linkedProjectsTotal }} project{{
								linkedProjectsTotal === 1 ? "" : "s"
							}}
							reference this company
						</span>
						<span v-else class="text-[11px] text-ink-400"
							>No projects reference this company · safe to delete</span
						>
					</template>
					<template #menu>
						<button
							type="button"
							class="text-xs px-2 py-1 border border-ink-200 bg-white hover:bg-ink-50"
							style="border-radius: 2px; color: #b91c1c"
							@click="deleteCompany"
						>
							Delete
						</button>
					</template>
				</DeskActionBar>
				<!-- Non-admin: no action bar; show a read-only marker instead. -->
				<div
					v-else
					class="px-3 py-2 bg-warning-50 border-b border-warning-100 text-xs text-warning-700"
				>
					Read-only view. Editing requires the System Manager role.
				</div>
			</template>

			<div class="max-w-3xl mx-auto">
				<!-- Identity -->
				<DeskSection title="Identity" v-if="!editing">
					<DeskField label="Name">
						<div class="text-sm text-ink-900 py-1">{{ company.name }}</div>
					</DeskField>
					<DeskField label="Short name" hint="Topbar pill text.">
						<div class="text-sm text-ink-900 py-1">{{ company.shortName }}</div>
					</DeskField>
					<DeskField label="ID" hint="Stable identifier — locked after create.">
						<div class="text-sm text-ink-500 py-1 font-mono">{{ company.id }}</div>
					</DeskField>
					<DeskField label="Description">
						<div class="text-sm text-ink-700 py-1">
							{{ company.description || "—" }}
						</div>
					</DeskField>
				</DeskSection>
				<DeskSection title="Identity" v-else>
					<DeskField label="Name" required>
						<DeskInput v-model="form.name" />
					</DeskField>
					<DeskField label="Short name" required hint="Topbar pill text.">
						<DeskInput v-model="form.shortName" />
					</DeskField>
					<DeskField
						label="ID"
						hint="Locked after create per Frappe Naming Series convention."
					>
						<DeskInput :model-value="company.id" disabled class="font-mono" />
					</DeskField>
				</DeskSection>

				<!-- Brand colour -->
				<DeskSection title="Brand colour" v-if="!editing" :cols="2">
					<DeskField label="Pill colour">
						<div class="flex items-center gap-2 py-1">
							<span
								:class="company.color"
								class="w-4 h-4"
								style="border-radius: 2px"
							></span>
							<span class="text-sm text-ink-700">{{ company.color }}</span>
						</div>
					</DeskField>
				</DeskSection>
				<!-- Branding & Letter Head — real Company fields; drives print letter heads -->
				<DeskSection title="Branding & Letter Head">
					<div class="md:col-span-2 space-y-4">
						<p class="text-[11px] text-ink-500">
							Logo and subtext for
							<b>{{ brandCompanyName || company.name }}</b>, materialised into the
							<span class="font-mono">{{ letterHeadName || "letter head" }}</span>
							that fronts every print of this company's documents (Work Order, Purchase
							Order, Invoice…). No logo? The letter head shows the company's initials.
						</p>

						<!-- Logo -->
						<div class="flex items-center gap-4">
							<div
								class="w-24 h-24 border border-ink-200 rounded flex items-center justify-center bg-ink-50 overflow-hidden flex-shrink-0"
							>
								<img
									v-if="brandForm.logo"
									:src="brandForm.logo"
									alt="Company logo"
									class="max-w-full max-h-full object-contain"
								/>
								<span v-else class="text-[10px] text-ink-400">No logo</span>
							</div>
							<div v-if="store.isAdmin" class="flex flex-col gap-2">
								<button
									type="button"
									class="text-xs px-3 py-1.5 rounded bg-ink-900 text-white hover:bg-ink-800 disabled:opacity-50"
									:disabled="brand.uploading"
									@click="pickLogo"
								>
									{{
										brand.uploading
											? "Uploading…"
											: brandForm.logo
												? "Replace logo"
												: "Upload logo"
									}}
								</button>
								<button
									v-if="brandForm.logo"
									type="button"
									class="text-xs px-3 py-1.5 rounded border border-ink-200 hover:bg-ink-50"
									@click="removeLogo"
								>
									Remove
								</button>
								<input
									ref="brandFileInput"
									type="file"
									accept="image/*"
									class="hidden"
									@change="onLogoSelected"
								/>
							</div>
						</div>

						<!-- Subtext -->
						<div>
							<div class="text-[10px] uppercase tracking-wider text-ink-500 mb-1">
								Letter head subtext
							</div>
							<DeskTextarea
								v-model="brandForm.subtext"
								:rows="3"
								:disabled="!store.isAdmin"
								placeholder="Registered address · GSTIN · phone / email"
							/>
							<p class="text-[11px] text-ink-500 mt-1">
								Shown under the company name in the letter head; line breaks preserved.
							</p>
						</div>

						<!-- Live preview -->
						<div>
							<div class="text-[10px] uppercase tracking-wider text-ink-500 mb-1">
								Preview
							</div>
							<div class="border border-ink-200 rounded p-4 bg-white">
								<div class="flex items-center gap-3">
									<img
										v-if="brandForm.logo"
										:src="brandForm.logo"
										alt=""
										style="height: 44px; width: auto; object-fit: contain"
									/>
									<div
										v-else
										class="rounded-lg bg-brand-600 text-white flex items-center justify-center font-semibold flex-shrink-0"
										style="height: 44px; width: 44px; font-size: 18px"
									>
										{{ monogram }}
									</div>
									<div>
										<div class="text-base font-semibold text-ink-900">
											{{ brandCompanyName || company.name }}
										</div>
										<div
											v-if="brandForm.subtext"
											class="text-[11px] text-ink-500 mt-0.5 whitespace-pre-line"
										>
											{{ brandForm.subtext }}
										</div>
									</div>
								</div>
							</div>
						</div>

						<!-- Save (independent of the identity Edit/Save above) -->
						<div v-if="store.isAdmin" class="flex items-center gap-3">
							<button
								type="button"
								class="text-xs px-3 py-1.5 rounded bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-50"
								:disabled="!brandDirty || brand.saving"
								@click="saveBrand"
							>
								{{ brand.saving ? "Saving…" : "Save branding" }}
							</button>
							<span v-if="brandDirty" class="text-[11px] text-warning-700"
								>Unsaved branding changes</span
							>
						</div>
					</div>
				</DeskSection>

				<!-- Linked projects (always visible — informs delete safety) -->
				<DeskSection title="Linked projects">
					<div class="md:col-span-2">
						<div
							v-if="linkedProjects.length"
							class="border border-ink-200"
							style="border-radius: 2px"
						>
							<div
								class="grid bg-ink-50 border-b border-ink-200 text-[10px] uppercase tracking-wider text-ink-500 font-medium"
								style="grid-template-columns: 140px 1fr 100px"
							>
								<div class="px-3 py-1.5">Code</div>
								<div class="px-3 py-1.5">Project</div>
								<div class="px-3 py-1.5">Status</div>
							</div>
							<div
								v-for="p in linkedProjects"
								:key="p.id"
								class="grid desk-row-stripe hover:bg-brand-50 border-b border-ink-100 last:border-b-0 items-center text-sm"
								style="grid-template-columns: 140px 1fr 100px"
							>
								<div class="px-3 py-1.5 font-mono text-xs text-ink-600">
									{{ p.code }}
								</div>
								<div class="px-3 py-1.5">
									<DeskLink :to="`/projects/${p.id}`">{{ p.name }}</DeskLink>
								</div>
								<div class="px-3 py-1.5 text-xs text-ink-500">{{ p.status }}</div>
							</div>
							<div
								v-if="linkedProjectsTotal > linkedProjects.length"
								class="px-3 py-1.5 text-[11px] text-ink-500 bg-ink-50 border-t border-ink-200"
							>
								Showing {{ linkedProjects.length }} of {{ linkedProjectsTotal }} — open the
								Projects list to see them all.
							</div>
						</div>
						<div v-else class="text-xs text-ink-400 italic">
							No projects reference this company. Safe to delete.
						</div>
						<div class="text-[11px] text-ink-500 mt-2">
							Delete is refused while any project links to this company
							(Frappe-standard LinkExistsError pattern).
						</div>
					</div>
				</DeskSection>
			</div>
		</DeskForm>
	</DeskPage>

	<div v-else class="px-6 py-20 text-center text-sm text-ink-400">
		Company not found ·
		<RouterLink to="/settings/companies" class="desk-link">Back to list →</RouterLink>
	</div>
</template>
