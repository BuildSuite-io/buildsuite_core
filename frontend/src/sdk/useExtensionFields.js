// The contract that lets a bespoke form carry an extension's Custom Fields.
//
// The fields themselves are native Frappe: the extension app ships Custom Field fixtures for the
// doctype. This composable is the binding. A form calls it once:
//
//   const ext = useExtensionFields("Quotation");
//   ...read the saved document:    ext.load(doc)            // fills ext.custom from the document
//   ...before saving:              Object.assign(payload, ext.payload())
//   ...around the save:            await ext.beforeSave(payload, form); ...; await ext.afterSave(doc, { isNew })
//   ...in the template:            <ExtensionSlot :name="ext.slot('top')" :context="ext.context" />
//   ...sections: a <DeskSection id="items"> below this form also offers the slots
//   form.<DocType>.before.items and form.<DocType>.after.items, with no markup in the view.
//
// An extension registers one control for the slot "form.<DocType>.<position>" and it works on every
// form that adopts this. The control receives `form` (the whole form), `custom` (reactive: its
// fields, read and write) and `doc` (the saved document, or null on a new one).
//
// Fields an extension owns are declared with sdk.doctype(name).on({ fields: ["custom_region"] }), the
// same call that registers its hooks. Defaults run when the form is new (hook `defaults`).

import { getCurrentInstance, nextTick, provide, reactive } from "vue";
import { FORM_KEY } from "@/sdk/anchors";
import { __ } from "@/utils/translate";
import {
	FieldErrors,
	docFields,
	fieldRule,
	fieldRuleNames,
	fieldValue,
	runDocHook,
} from "@/sdk/registry";

const isEmpty = (v) =>
	v == null || (typeof v === "string" && !v.trim()) || (Array.isArray(v) && !v.length);

export function useExtensionFields(doctype, form = {}) {
	const custom = reactive({});
	const state = reactive({ doc: null });
	// fieldErrors: a message per field name, shown under that field (DeskField `name`).
	const fieldErrors = reactive({});
	const context = reactive({ doctype, form, custom, doc: null, fieldErrors });
	// The fields on screen (DeskField with a `name` registers itself), so a rule for a field this form
	// does not show can never block a save with an error nobody can see.
	const mounted = new Map(); // name -> { label: ComputedRef, hidden: ComputedRef }
	// Every DeskSection and every named DeskField below this form offers anchors and rules for it.
	if (getCurrentInstance()) provide(FORM_KEY, { doctype, context, mounted });

	function setErrors(errors) {
		for (const key of Object.keys(fieldErrors)) delete fieldErrors[key];
		Object.assign(fieldErrors, errors);
		// bring the first message into view
		if (typeof document === "undefined") return;
		nextTick(() =>
			document.querySelector("[data-field-error]")?.scrollIntoView?.({ block: "center" })
		);
	}

	const warnedUnreadable = new Set();

	/** Fields an extension made required (fieldRules.required) that are on screen and empty. A field
	 *  whose value is not on the form's own model (a file picker, a value shown but not edited) cannot
	 *  be checked, so it is skipped with one warning rather than refused for ever. */
	function missingRequired() {
		const missing = {};
		for (const name of fieldRuleNames(doctype)) {
			const field = mounted.get(name);
			if (!field || field.hidden.value) continue;
			const rule = fieldRule(doctype, name, context);
			if (!rule.required) continue;
			const value = fieldValue(context, name);
			if (value === undefined) {
				if (!warnedUnreadable.has(name)) {
					warnedUnreadable.add(name);
					console.warn(
						`[buildsuite] ${doctype}.${name} is not on the form's model, so "required" cannot be enforced on it`
					);
				}
				continue;
			}
			if (isEmpty(value)) {
				missing[name] = __("{0} is required", [field.label.value || name]);
			}
		}
		return missing;
	}

	return {
		custom,
		context,
		/** The slot name for a position on this form, e.g. slot("top"). */
		slot: (position) => `form.${doctype}.${position}`,
		/** The extension-owned field names for this doctype. */
		fields: () => docFields(doctype),
		/** Read the saved document into `custom`. Call after the form has loaded it. */
		async load(doc) {
			state.doc = doc || null;
			context.doc = state.doc;
			for (const field of docFields(doctype)) custom[field] = doc?.[field] ?? null;
			await runDocHook(doctype, "onLoad", form, doc, context);
		},
		/** A new document starts the way extensions say. */
		async defaults() {
			await runDocHook(doctype, "defaults", form, context);
		},
		/** The extension fields to merge into what is saved: Object.assign(payload, ext.payload()). */
		payload() {
			return Object.fromEntries(docFields(doctype).map((f) => [f, custom[f] ?? null]));
		},
		/** Required-by-extension fields first, then every extension's beforeSave. A FieldErrors thrown
		 *  by either puts its messages under the fields and stops the save. */
		async beforeSave(payload, f) {
			setErrors({});
			const missing = missingRequired();
			if (Object.keys(missing).length) {
				setErrors(missing);
				throw new FieldErrors(missing);
			}
			try {
				await runDocHook(doctype, "beforeSave", payload, f ?? form);
			} catch (error) {
				if (error instanceof FieldErrors) setErrors(error.errors);
				throw error;
			}
		},
		/** Messages currently shown under fields (also on `context.fieldErrors`). */
		fieldErrors,
		afterSave: (doc, info) => runDocHook(doctype, "afterSave", doc, info),
	};
}
