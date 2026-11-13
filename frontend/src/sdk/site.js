// Site-level customisations: the records of "BuildSuite Customisation", validated on the server and
// delivered in boot (`buildsuite_customisations`), turned here into the same registry entries an
// installed app adds. They are registered last, so for anything where order matters the site wins
// over apps, and apps over Core.
//
// Data only: a list column, a form field, a workspace tile, a notice. A notice's message is drawn as
// text (never as HTML) and every link is an in-app path the server already checked.

import { defineComponent, h } from "vue";
import DeskField from "@/components/desk/DeskField.vue";
import DocTypeFieldControl from "@/components/doctype/DocTypeFieldControl.vue";
import { addDocHooks, addSlot, addWorkspaceTile } from "@/sdk/registry";

const SITE = "site";

const TONES = {
	info: "bg-ink-50 border-ink-200 text-ink-700",
	success: "bg-success-50 border-success-100 text-success-700",
	warning: "bg-warning-50 border-warning-100 text-warning-700",
};

function noticeComponent(config) {
	return defineComponent({
		name: "SiteNotice",
		setup: () => () =>
			h(
				"div",
				{
					class: `mb-3 px-3 py-2 text-xs border ${TONES[config.tone] || TONES.info}`,
					style: "border-radius: 6px",
					"data-test": "site-notice",
				},
				config.message
			),
	});
}

// A control for a Custom Field, drawn from its meta. It only shows on a form that hands it `custom`
// (the bespoke forms that adopted useExtensionFields); the generic DocType form already draws every
// Custom Field itself.
function fieldComponent(config) {
	const field = config.field;
	return defineComponent({
		name: "SiteFieldControl",
		props: {
			custom: { type: Object, default: null },
			form: { type: Object, default: () => ({}) },
		},
		setup(props) {
			return () =>
				props.custom
					? h(
							"div",
							{
								class: "mb-3 max-w-xs",
								"data-test": `site-field-${field.fieldname}`,
							},
							h(
								DeskField,
								{
									label: field.label,
									required: !!field.reqd,
									hint: field.description || "",
								},
								{
									default: () =>
										h(DocTypeFieldControl, {
											field,
											modelValue: props.custom[field.fieldname] ?? "",
											context: props.custom,
											"onUpdate:modelValue": (v) =>
												(props.custom[field.fieldname] = v),
										}),
								}
							)
					  )
					: null;
		},
	});
}

const APPLY = {
	"List Column"(c) {
		addDocHooks(SITE, c.doctype, {
			listColumns: [{ field: c.field, label: c.label, align: c.align }],
		});
	},
	"Form Field"(c) {
		addDocHooks(SITE, c.doctype, { fields: [c.fieldname] });
		addSlot(SITE, `form.${c.doctype}.${c.position}`, fieldComponent(c));
	},
	"Workspace Tile"(c) {
		addWorkspaceTile(SITE, c.workspace, {
			label: c.label,
			to: c.to,
			description: c.description || "",
		});
	},
	Notice(c) {
		addSlot(SITE, c.slot, noticeComponent(c));
	},
};

/** Register every customisation; one that fails is logged and skipped, never fatal. */
export function applySiteCustomisations(list = window.buildsuite_customisations) {
	let applied = 0;
	for (const item of list || []) {
		try {
			const apply = APPLY[item.kind];
			if (!apply) throw new Error(`unknown kind ${item.kind}`);
			apply(item.config);
			applied++;
		} catch (error) {
			console.warn(`[buildsuite] site customisation "${item?.name}" skipped`, error);
		}
	}
	return applied;
}
