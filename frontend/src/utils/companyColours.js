// A company's pill colour in the top bar and on lists. The Company doctype stores the NAME
// (custom_brand_colour: Green, Blue…); this maps it to the Tailwind class the pill uses. A company
// with no saved colour gets one derived from its ID (see the store), so the pill is never blank.
// The class names are written out in full so Tailwind keeps them.
export const COMPANY_COLOUR_OPTIONS = [
	{ value: "Green", cls: "bg-brand-600" },
	{ value: "Blue", cls: "bg-blue-600" },
	{ value: "Violet", cls: "bg-violet-600" },
	{ value: "Amber", cls: "bg-amber-600" },
	{ value: "Emerald", cls: "bg-emerald-600" },
	{ value: "Rose", cls: "bg-rose-600" },
	{ value: "Cyan", cls: "bg-cyan-600" },
	{ value: "Slate", cls: "bg-ink-600" },
];

// The pill class for a saved colour name ("" when none / unknown).
export const colourClass = (name) =>
	COMPANY_COLOUR_OPTIONS.find((o) => o.value === name)?.cls || "";

// The colour name behind a pill class — used to show a derived (unsaved) colour in the selector.
export const colourNameForClass = (cls) =>
	COMPANY_COLOUR_OPTIONS.find((o) => o.cls === cls)?.value || "";
