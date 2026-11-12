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

import { getCurrentInstance, provide, reactive } from "vue";
import { FORM_KEY } from "@/sdk/anchors";
import { docFields, runDocHook } from "@/sdk/registry";

export function useExtensionFields(doctype, form = {}) {
	const custom = reactive({});
	const state = reactive({ doc: null });
	const context = reactive({ doctype, form, custom, doc: null });
	// Every DeskSection below this form (with an `id`) now offers before/after anchors for it.
	if (getCurrentInstance()) provide(FORM_KEY, { doctype, context });

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
		beforeSave: (payload, f) => runDocHook(doctype, "beforeSave", payload, f ?? form),
		afterSave: (doc, info) => runDocHook(doctype, "afterSave", doc, info),
	};
}
