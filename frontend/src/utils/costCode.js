// Maps a CostCodePicker value ({ type, group_code, item_code, label } | null) to the four
// stored cost_code_* fields on a document, and back.

export function costCodeToFields(cc) {
	if (cc && typeof cc === "object") {
		return {
			cost_code_type: cc.type === "item" ? "Item" : "Group",
			cost_code_group: cc.group_code || "",
			cost_code_item: cc.item_code || "",
			cost_code_label: cc.label || "",
		};
	}
	return { cost_code_type: "", cost_code_group: "", cost_code_item: "", cost_code_label: "" };
}

export function costCodeFromDoc(d) {
	if (!d || !(d.cost_code_group || d.cost_code_item)) return null;
	return {
		type: (d.cost_code_type || "").toLowerCase(),
		group_code: d.cost_code_group || "",
		item_code: d.cost_code_item || null,
		label: d.cost_code_label || "",
	};
}
