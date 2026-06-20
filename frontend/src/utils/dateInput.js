/**
 * Convert arbitrary date-like input into a native date-input value
 * (YYYY-MM-DD). Returns an empty string for null/invalid inputs.
 */
export function toDateInputValue(value) {
	if (!value) return "";

	if (typeof value === "string") {
		return value.slice(0, 10);
	}

	const date = new Date(value);
	if (Number.isNaN(date.getTime())) return "";
	return date.toISOString().slice(0, 10);
}
