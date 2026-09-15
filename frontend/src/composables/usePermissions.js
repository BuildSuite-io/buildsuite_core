// UI permission helper. Decides which create/edit/delete affordances to show for
// the logged-in user. The caps are DERIVED FROM THE BACKEND (frappe.has_permission,
// via api.permission.get_resource_permissions → session store), so this mirrors the
// authoritative DocPerm matrix exactly instead of a hand-maintained client copy.
// The backend (permissions/*.py) remains the real gate; this only hides buttons that
// would fail.
//
//   const { canCreate, canEdit, canDelete, canRead } = usePermissions()
//   v-if="canCreate('task')"   v-if="canEdit('stagePlanning')"
//
// Resource keys are the camelCase keys of permissions/resource_map.py RESOURCE_DOCTYPES
// ('project' | 'task' | 'rateMaster' | 'supplierBill' | …). A key with no backend perms
// (or before the session boots) resolves to no access.
//
// Note: because caps now reflect the ACTUAL logged-in user, the dev RoleSwitcher no longer
// previews CRUD gates (it still drives workspace visibility). To preview a persona's gates,
// log in as that persona's user.

import { computed } from "vue";
import { useSessionStore } from "@/stores/session";
import { getSessionUser } from "@/utils/session";

// An 'own'-scope persona (Site Engineer / Foreman) may only edit or delete the
// records it created. We resolve the creator from the record's Frappe `owner`
// (kept on the detail read transforms). This mirrors the backend own-record
// gate, so the button only shows when the save/delete would actually succeed —
// fixes the "error after edit + save" UX for tasks a user didn't create.
function ownsRecord(record) {
	if (!record) return false;
	const uid = getSessionUser();
	return record.owner === uid || record.createdBy === uid;
}

// The backend payload gives booleans + a scope ("all" | "own" | "none") for write/delete.
// Collapse each resource back to the tri-state the gates below expect: `true` (unrestricted),
// `'own'` (only your own records), or `false` (none). Read/create/submit stay boolean.
function scopeToCap(scope) {
	if (scope === "all") return true;
	if (scope === "own") return "own";
	return false;
}

export function usePermissions() {
	const session = useSessionStore();
	const caps = computed(() => {
		const rp = session.access?.resourcePermissions || {};
		const out = {};
		for (const [key, p] of Object.entries(rp)) {
			out[key] = {
				c: p.c === true,
				r: p.r === true,
				e: scopeToCap(p.writeScope),
				d: scopeToCap(p.deleteScope),
				x: p.x === true,
			};
		}
		return out;
	});

	function cap(resource, action) {
		return caps.value?.[resource]?.[action] ?? false;
	}

	// Record-aware gates: `true` cap → always; `false` → never; `'own'` → only when
	// the current user created the record. Prefer these on detail-page buttons.
	function canEditRecord(resource, record) {
		const c = cap(resource, "e");
		if (c === true) return true;
		if (c === "own") return ownsRecord(record);
		return false;
	}
	function canDeleteRecord(resource, record) {
		const c = cap(resource, "d");
		if (c === true) return true;
		if (c === "own") return ownsRecord(record);
		return false;
	}

	return {
		// Create is an unconditional capability (no record context).
		canCreate: (resource) => cap(resource, "c") === true,
		canRead: (resource) => cap(resource, "r") !== false,
		// Coarse (no record) — true for full + own-scope personas. Use for
		// list-level affordances; prefer the record-aware variants on detail pages.
		canEdit: (resource) => cap(resource, "e") !== false,
		canDelete: (resource) => cap(resource, "d") !== false,
		// Submit/cancel a submittable doctype (backend S/X). Distinct from create: a role may
		// raise a draft but not submit it. Unconditional capability, like create.
		canSubmit: (resource) => cap(resource, "x") === true,
		// Precise (record in hand) — own-scope resolves against the creator.
		canEditRecord,
		canDeleteRecord,
	};
}
