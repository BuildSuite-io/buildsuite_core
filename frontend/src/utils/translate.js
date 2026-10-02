// i18n for the SPA — a thin, Frappe-compatible translation layer.
//
// It reuses Frappe's translation system wholesale: the boot payload (www/core.py get_boot →
// get_messages_for_boot) already ships `window.translated_messages` — the merged message map for
// the user's language, across Frappe core + every installed app (incl. this one's
// buildsuite_core/translations/<lang>.csv). This mirrors Desk's `frappe._` / `window.__` exactly:
//   - the key is the English source string, or `source:context` when a context is given;
//   - `{0}`/`{1}` (array) and `{name}` (object) placeholders are substituted;
//   - an untranslated string falls back to the source, so wrapping a string is always safe even
//     before a translation exists.
//
// So a string whose source Frappe already translates (e.g. "Save", "Customer", "Status") is
// translated for free; a BuildSuite-specific string just needs a row in the app's CSV.

function messages() {
	return (typeof window !== "undefined" && window.translated_messages) || {};
}

// Frappe's $.format equivalent: {0}/{1} for array args, {name} for object args.
function format(text, replace) {
	if (!replace || typeof replace !== "object") return text;
	return text.replace(/\{([\w]+)\}/g, (match, key) =>
		Object.prototype.hasOwnProperty.call(replace, key) ? String(replace[key]) : match
	);
}

/**
 * Translate `text` into the current language.
 * @param {string} text     the English source string
 * @param {object|array} [replace]  placeholder values ({0:…} / [a,b] / {name:…})
 * @param {string} [context]  disambiguation context (maps to the `source:context` key)
 */
export function __(text, replace = null, context = null) {
	if (!text || typeof text !== "string") return text;
	const map = messages();
	let translated = "";
	if (context) translated = map[`${text}:${context}`];
	if (!translated) translated = map[text] || text;
	return format(translated, replace);
}

/** The active language code (from boot), e.g. "en", "fr", "ar". */
export function currentLang() {
	return (typeof window !== "undefined" && window.lang) || "en";
}

/** Whether the active language renders right-to-left (from boot). */
export function isRTL() {
	return (typeof window !== "undefined" && window.text_direction === "rtl") || false;
}

// Expose a Frappe-compatible global so frappe-ui components (and any Desk-style code) translate
// through the same map. Safe to call repeatedly.
export function installGlobalTranslate() {
	if (typeof window === "undefined") return;
	window.__ = __;
}
