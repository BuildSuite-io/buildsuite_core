// Debounced, quiet auto-save for draft forms.
//
// Mirrors the StagePlanningDetailView inline-edit pattern: while a draft exists, field changes are
// saved in the background — no spinner, no navigation, no reload — so the focused input is never
// disrupted mid-keystroke. Saves are coalesced (never overlap; the latest wins), and errors are
// swallowed on purpose: the explicit Save button stays the single place validation and save errors
// surface (per product decision — auto-save skips silently when the form isn't saveable).
//
// The caller owns the gate via `canAutosave`, which MUST include the same access-control the Save
// button uses (e.g. canEdit("salesInvoice")) plus "draft exists", "form valid", and a load-ready
// flag — auto-save must never write where the button itself would be denied.
//
//   const { status } = useAutosave(form, quietSave, {
//     canAutosave: () => ready.value && isEdit.value && canManage.value && isSaveable(),
//   });
//
// `status` is "idle" | "saving" | "saved" for an optional subtle indicator.
import { ref, watch, onScopeDispose } from "vue";

export function useAutosave(source, saveFn, options = {}) {
	const { canAutosave, delay = 1000 } = options;
	const status = ref("idle");
	let timer = null;
	let inFlight = false;
	let queued = false;
	let savedResetTimer = null;

	function allowed() {
		return !canAutosave || canAutosave();
	}

	async function flush() {
		if (!allowed()) return;
		if (inFlight) {
			// A change arrived while a save was in flight — run once more when it settles.
			queued = true;
			return;
		}
		inFlight = true;
		status.value = "saving";
		try {
			await saveFn();
			status.value = "saved";
			clearTimeout(savedResetTimer);
			savedResetTimer = setTimeout(() => {
				if (status.value === "saved") status.value = "idle";
			}, 2000);
		} catch {
			// Quiet: the manual Save button surfaces validation / save errors.
			status.value = "idle";
		} finally {
			inFlight = false;
			if (queued) {
				queued = false;
				flush();
			}
		}
	}

	const stop = watch(
		source,
		() => {
			if (!allowed()) return;
			clearTimeout(timer);
			timer = setTimeout(flush, delay);
		},
		{ deep: true }
	);

	onScopeDispose(() => {
		clearTimeout(timer);
		clearTimeout(savedResetTimer);
		stop();
	});

	return { status, flush };
}
