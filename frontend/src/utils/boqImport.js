/**
 * S430 — BOQ import from a spreadsheet.
 *
 * Reads .xlsx (and .csv, or rows pasted from Excel) with NO library: an .xlsx
 * file is a zip of XML, and the browser's DecompressionStream inflates zip
 * entries. That keeps the app dependency-free here.
 * Old binary .xls files are not readable this way; the screen says to save as
 * .xlsx or .csv.
 *
 * Everything here is pure (no store, no DOM), so it can run under node:
 *   readSpreadsheet  file bytes -> { sheets: [{ name, rows }] }
 *   detectColumns    rows -> { headerRow, mapping }
 *   planImport       rows + mapping + what the BOQ already has -> a plan that
 *                    says what each row becomes and what needs the user's OK
 *   buildPayload     plan + the user's decisions -> what the backend imports
 *
 * The caller passes the units the app knows (ERPNext UOM master names) via
 * ctx.units — the parser never imports a store.
 */

// ---------------------------------------------------------------- reading

async function inflateRaw(bytes) {
	const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("deflate-raw"));
	return new Uint8Array(await new Response(stream).arrayBuffer());
}

/** The entries of a zip archive, read through its central directory. */
async function unzip(buffer) {
	const u8 = buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer);
	const dv = new DataView(u8.buffer, u8.byteOffset, u8.byteLength);
	let eocd = -1;
	for (let i = u8.length - 22; i >= Math.max(0, u8.length - 65557); i--) {
		if (dv.getUint32(i, true) === 0x06054b50) {
			eocd = i;
			break;
		}
	}
	if (eocd < 0) throw new Error("This file is not a spreadsheet Excel can save (.xlsx).");
	const count = dv.getUint16(eocd + 10, true);
	let p = dv.getUint32(eocd + 16, true);
	const td = new TextDecoder();
	const files = {};
	for (let n = 0; n < count; n++) {
		if (dv.getUint32(p, true) !== 0x02014b50) break;
		const method = dv.getUint16(p + 10, true);
		const size = dv.getUint32(p + 20, true);
		const nameLen = dv.getUint16(p + 28, true);
		const extraLen = dv.getUint16(p + 30, true);
		const commentLen = dv.getUint16(p + 32, true);
		const local = dv.getUint32(p + 42, true);
		files[td.decode(u8.subarray(p + 46, p + 46 + nameLen))] = { method, size, local };
		p += 46 + nameLen + extraLen + commentLen;
	}
	return {
		has: (name) => !!files[name],
		async text(name) {
			const f = files[name];
			if (!f) return null;
			const start =
				f.local + 30 + dv.getUint16(f.local + 26, true) + dv.getUint16(f.local + 28, true);
			const data = u8.subarray(start, start + f.size);
			if (f.method === 0) return td.decode(data);
			if (f.method === 8) return td.decode(await inflateRaw(data));
			throw new Error(
				"This spreadsheet uses a compression this screen cannot read. Save it again as .xlsx or .csv."
			);
		},
	};
}

const ENTITIES = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'" };
function decodeXml(s) {
	return String(s).replace(/&(#x[0-9a-f]+|#\d+|amp|lt|gt|quot|apos);/gi, (m, e) => {
		if (e[0] === "#")
			return String.fromCodePoint(
				e[1] === "x" || e[1] === "X" ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10)
			);
		return ENTITIES[e.toLowerCase()] ?? m;
	});
}
function attrs(tag) {
	const out = {};
	for (const m of tag.matchAll(/([\w:]+)="([^"]*)"/g)) out[m[1]] = decodeXml(m[2]);
	return out;
}
/** All the text in a run of rich text, without phonetic hints. */
function textOf(xml) {
	return decodeXml(
		xml
			.replace(/<rPh\b[\s\S]*?<\/rPh>/g, "")
			.match(/<t\b[^>]*>[\s\S]*?<\/t>/g)
			?.map((t) => t.replace(/<t\b[^>]*>|<\/t>/g, ""))
			.join("") ?? ""
	);
}
function colIndex(ref) {
	const letters = (ref.match(/^[A-Z]+/i) || [""])[0].toUpperCase();
	let n = 0;
	for (const ch of letters) n = n * 26 + (ch.charCodeAt(0) - 64);
	return n - 1;
}
export function colLetter(i) {
	let s = "";
	for (let n = i + 1; n > 0; n = Math.floor((n - 1) / 26))
		s = String.fromCharCode(65 + ((n - 1) % 26)) + s;
	return s;
}

function sheetRows(xml, shared) {
	const rows = [];
	let nextRow = 0;
	for (const rm of xml.matchAll(/<row\b([^>]*?)(?:\/>|>([\s\S]*?)<\/row>)/g)) {
		const ra = attrs(rm[1]);
		const r = ra.r ? parseInt(ra.r, 10) - 1 : nextRow;
		nextRow = r + 1;
		const cells = [];
		let nextCol = 0;
		for (const cm of (rm[2] || "").matchAll(/<c\b([^>]*?)(?:\/>|>([\s\S]*?)<\/c>)/g)) {
			const ca = attrs(cm[1]);
			const c = ca.r ? colIndex(ca.r) : nextCol;
			nextCol = c + 1;
			const body = cm[2] || "";
			const v = (body.match(/<v>([\s\S]*?)<\/v>/) || [])[1];
			let val = "";
			if (ca.t === "s") val = shared[parseInt(v, 10)] ?? "";
			else if (ca.t === "inlineStr") val = textOf(body);
			else if (ca.t === "str" || ca.t === "e") val = v != null ? decodeXml(v) : "";
			else if (ca.t === "b") val = v === "1" ? "TRUE" : "FALSE";
			else if (v != null && v !== "") {
				const num = Number(v);
				val = Number.isFinite(num) ? num : decodeXml(v);
			}
			cells[c] = val;
		}
		for (let i = 0; i < cells.length; i++) if (cells[i] === undefined) cells[i] = "";
		rows[r] = cells;
	}
	for (let i = 0; i < rows.length; i++) if (!rows[i]) rows[i] = [];
	while (rows.length && rows[rows.length - 1].every((v) => v === "" || v == null)) rows.pop();
	return rows;
}

export async function readXlsx(buffer) {
	const zip = await unzip(buffer);
	const ssXml = await zip.text("xl/sharedStrings.xml");
	const shared = ssXml
		? [...ssXml.matchAll(/<si\b[^>]*>([\s\S]*?)<\/si>|<si\b[^>]*\/>/g)].map((m) =>
				textOf(m[1] || "")
		  )
		: [];
	const wb = await zip.text("xl/workbook.xml");
	const rels = (await zip.text("xl/_rels/workbook.xml.rels")) || "";
	const relTarget = {};
	for (const m of rels.matchAll(/<Relationship\b[^>]*>/g)) {
		const a = attrs(m[0]);
		relTarget[a.Id] = a.Target;
	}
	const sheets = [];
	for (const m of (wb || "").matchAll(/<sheet\b[^>]*>/g)) {
		const a = attrs(m[0]);
		let target = relTarget[a["r:id"]] || "";
		target = target.startsWith("/") ? target.slice(1) : "xl/" + target.replace(/^\.\//, "");
		const xml = await zip.text(target);
		if (xml != null) sheets.push({ name: a.name || "Sheet", rows: sheetRows(xml, shared) });
	}
	if (!sheets.length) throw new Error("No worksheets were found in this file.");
	return { sheets };
}

/** CSV, or rows pasted from Excel (tab-separated). Picks the delimiter from the first line. */
export function parseDelimited(text) {
	text = String(text).replace(/^\uFEFF/, ""); // strip a leading UTF-8 BOM
	const first = text.split(/\r?\n/, 1)[0] || "";
	const counts = {
		"\t": first.split("\t").length,
		",": first.split(",").length,
		";": first.split(";").length,
	};
	const delim = Object.keys(counts).sort((a, b) => counts[b] - counts[a])[0];
	const rows = [];
	let row = [],
		cell = "",
		quoted = false;
	for (let i = 0; i < text.length; i++) {
		const ch = text[i];
		if (quoted) {
			if (ch === '"' && text[i + 1] === '"') {
				cell += '"';
				i++;
			} else if (ch === '"') quoted = false;
			else cell += ch;
		} else if (ch === '"' && cell === "") quoted = true;
		else if (ch === delim) {
			row.push(cell);
			cell = "";
		} else if (ch === "\n" || ch === "\r") {
			if (ch === "\r" && text[i + 1] === "\n") i++;
			row.push(cell);
			rows.push(row);
			row = [];
			cell = "";
		} else cell += ch;
	}
	if (cell !== "" || row.length) {
		row.push(cell);
		rows.push(row);
	}
	while (rows.length && rows[rows.length - 1].every((v) => v.trim() === "")) rows.pop();
	return rows;
}

/** Any supported file, by its name. */
export async function readSpreadsheet(buffer, fileName = "") {
	const name = fileName.toLowerCase();
	if (name.endsWith(".xls"))
		throw new Error(
			"Old .xls files cannot be read here. Open it in Excel and save it as .xlsx or .csv."
		);
	if (name.endsWith(".xlsx") || name.endsWith(".xlsm")) return readXlsx(buffer);
	const text = new TextDecoder().decode(
		buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer)
	);
	return { sheets: [{ name: fileName || "Rows", rows: parseDelimited(text) }] };
}

// ---------------------------------------------------------------- columns

export const FIELDS = [
	{
		key: "group",
		label: "Group",
		words: [
			"group",
			"section",
			"trade",
			"work head",
			"head",
			"category",
			"chapter",
			"group name",
		],
	},
	{
		key: "code",
		label: "Code",
		words: [
			"code",
			"item code",
			"item no",
			"sl no",
			"s no",
			"sr no",
			"no",
			"ref",
			"ref no",
			"boq ref",
		],
	},
	{
		key: "description",
		label: "Description",
		words: [
			"description",
			"item description",
			"description of work",
			"particulars",
			"specification",
			"item",
			"details",
			"work",
		],
	},
	{
		key: "unit",
		label: "Unit",
		words: ["unit", "units", "uom", "unit of measure", "unit of measurement"],
	},
	{
		key: "qty",
		label: "Quantity",
		words: ["qty", "quantity", "qnty", "planned qty", "quantities"],
	},
	{
		key: "rate",
		label: "Rate",
		words: ["rate", "unit rate", "unit price", "price", "rate per unit"],
	},
	{
		key: "amount",
		label: "Amount",
		words: ["amount", "total", "value", "total amount", "cost"],
	},
	{ key: "costHead", label: "Cost head", words: ["cost head", "cost type", "type"] },
];

const normHeader = (s) =>
	String(s ?? "")
		.toLowerCase()
		.replace(/\((rs|inr|₹|rs\.)\)|in (rs|inr)|₹|rs\./g, " ")
		.replace(/[^a-z0-9]+/g, " ")
		.trim();

/** Find the header row (within the first 15 rows) and which column holds what. */
export function detectColumns(rows) {
	let best = { headerRow: -1, mapping: {}, score: 0 };
	const limit = Math.min(rows.length, 15);
	for (let r = 0; r < limit; r++) {
		const cells = rows[r] || [];
		const scored = [];
		cells.forEach((cell, c) => {
			const h = normHeader(cell);
			if (!h) return;
			for (const f of FIELDS) {
				const words = f.words.map(normHeader);
				let s = 0;
				if (words.includes(h)) s = 3;
				else if (
					words.some(
						(w) => w.length > 2 && (h.startsWith(w + " ") || h.endsWith(" " + w))
					)
				)
					s = 2;
				if (s) scored.push({ c, key: f.key, s });
			}
		});
		scored.sort((a, b) => b.s - a.s);
		const mapping = {};
		const usedCols = new Set();
		let score = 0;
		for (const x of scored) {
			if (mapping[x.key] != null || usedCols.has(x.c)) continue;
			mapping[x.key] = x.c;
			usedCols.add(x.c);
			score += x.s;
		}
		if (mapping.description != null && Object.keys(mapping).length >= 2 && score > best.score)
			best = { headerRow: r, mapping, score };
	}
	return { headerRow: best.headerRow, mapping: best.mapping };
}

// ---------------------------------------------------------------- units

const unitKey = (s) =>
	String(s ?? "")
		.toLowerCase()
		.replace(/²/g, "2")
		.replace(/³/g, "3")
		.replace(/[\s.]/g, "");

// Spellings common in Excel BOQs, mapped to an ERPNext UOM master name that the
// live app ships. A match here is only a SUGGESTION: "MT" can mean metric tonne
// or metre, so the screen asks before using it. Clearly-feet units (sq.ft, cu.ft,
// running foot) and lump-sum have no live UOM, so their aliases are dropped —
// matchUnit then falls through to "unknown" and the user creates/maps/skips them.
const UNIT_ALIASES = {
	sqm: "Square Meter",
	sqmt: "Square Meter",
	sqmtr: "Square Meter",
	m2: "Square Meter",
	squaremetre: "Square Meter",
	squaremeter: "Square Meter",
	squaremetres: "Square Meter",
	cum: "Cubic Meter",
	cumt: "Cubic Meter",
	m3: "Cubic Meter",
	cubicmetre: "Cubic Meter",
	cubicmeter: "Cubic Meter",
	cubicmetres: "Cubic Meter",
	rmt: "Meter",
	rm: "Meter",
	runningmetre: "Meter",
	runningmeter: "Meter",
	no: "Nos",
	number: "Nos",
	numbers: "Nos",
	each: "Nos",
	ea: "Nos",
	nr: "Nos",
	pcs: "Nos",
	pc: "Nos",
	pieces: "Nos",
	kgs: "Kg",
	kilogram: "Kg",
	kilograms: "Kg",
	mt: "Tonne",
	tonne: "Tonne",
	tonnes: "Tonne",
	tons: "Tonne",
	t: "Tonne",
	ltr: "Litre",
	ltrs: "Litre",
	litre: "Litre",
	liter: "Litre",
	litres: "Litre",
	l: "Litre",
	sets: "Set",
	pairs: "Pair",
	days: "Day",
	hr: "Hour",
	hrs: "Hour",
	hours: "Hour",
	bag: "Bag",
	bags: "Bag",
};

/**
 * What a unit in the file is, against the units the app knows.
 *   exact   — the same unit (case and dots ignored); used as is
 *   alias   — a common spelling of a known unit; used only once the user agrees
 *   unknown — not known; the user creates it, maps it, or skips those rows
 *   missing — the cell is empty
 */
export function matchUnit(raw, known) {
	const text = String(raw ?? "").trim();
	if (!text) return { status: "missing", raw: "" };
	const k = unitKey(text);
	const exact =
		known.find((u) => u.toLowerCase() === text.toLowerCase()) ||
		known.find((u) => unitKey(u) === k);
	if (exact) return { status: "exact", raw: text, value: exact };
	const alias = UNIT_ALIASES[k];
	if (alias && known.includes(alias)) return { status: "alias", raw: text, suggestion: alias };
	return { status: "unknown", raw: text };
}

// ---------------------------------------------------------------- planning

export const COST_HEADS = [
	"Material",
	"Labour",
	"Equipment",
	"Subcontract",
	"Preliminaries",
	"Other",
];
const TOTAL_ROW =
	/^(sub[\s-]?total|grand\s+total|total|carried\s+(over|forward)|brought\s+forward)\b/i;

const str = (v) => (v == null ? "" : String(v).trim());
/** A number from a cell: Excel number, or text like "1,25,000.50" or "₹ 450". null = empty, NaN = not a number. */
export function toNumber(v) {
	if (typeof v === "number") return Number.isFinite(v) ? v : NaN;
	const s = str(v)
		.replace(/₹|rs\.?|inr/gi, "")
		.replace(/[,\s]/g, "");
	if (!s || s === "-") return null;
	const n = Number(s);
	return Number.isFinite(n) ? n : NaN;
}

/**
 * What each row becomes. Groups come from a Group column when the file has
 * one; otherwise a row with a description and nothing else (no unit,
 * quantity, rate or amount) is a group heading and the rows under it belong
 * to it. Total rows are skipped. Nothing is changed here.
 *
 * ctx: { units: [known unit values], groups: [{ id, code, name }] of the BOQ,
 *        codes: [item codes already in the BOQ], defaultGroup: 'General' }
 */
export function planImport(rows, { headerRow = -1, mapping = {} } = {}, ctx = {}) {
	const has = (k) => mapping[k] !== undefined && mapping[k] !== null && mapping[k] !== "";
	const cell = (r, k) => (has(k) ? r[mapping[k]] : "");
	const known = ctx.units || [];
	const existing = ctx.groups || [];
	const takenCodes = new Set((ctx.codes || []).map((c) => String(c).toLowerCase()));
	const seenCodes = new Set();

	const groups = [];
	const items = [];
	const skipped = [];
	let current = null;

	const groupFor = (name, code) => {
		const nm = name || ctx.defaultGroup || "General";
		// By NAME only. Codes are local to a file: its "A" is rarely the BOQ's
		// "A", and merging on a code clash would pour lines into an unrelated
		// group. A new group whose code is taken is given the next free one.
		const ex = existing.find((g) => (g.name || "").trim().toLowerCase() === nm.toLowerCase());
		const key = ex ? "existing:" + ex.id : "new:" + nm.toLowerCase();
		let g = groups.find((x) => x.key === key);
		if (!g) {
			g = {
				key,
				name: ex ? ex.name : nm,
				code: ex ? ex.code : code || "",
				existingId: ex?.id || null,
				rowNo: null,
			};
			groups.push(g);
		}
		return g;
	};

	for (let i = headerRow + 1; i < rows.length; i++) {
		const r = rows[i] || [];
		const rowNo = i + 1;
		const description = str(cell(r, "description"));
		const code = str(cell(r, "code"));
		const unitRaw = str(cell(r, "unit"));
		const groupCell = str(cell(r, "group"));
		const qty = toNumber(cell(r, "qty"));
		const rate = toNumber(cell(r, "rate"));
		const amount = toNumber(cell(r, "amount"));
		const empty = (n) => n === null;
		if (
			!description &&
			!code &&
			!unitRaw &&
			!groupCell &&
			empty(qty) &&
			empty(rate) &&
			empty(amount)
		)
			continue;

		if (TOTAL_ROW.test(description) && empty(qty) && empty(rate)) {
			skipped.push({ rowNo, reason: "A total row, not a line of work" });
			continue;
		}

		if (has("group")) {
			if (groupCell) current = groupFor(groupCell, "");
		} else if (description && !unitRaw && empty(qty) && empty(rate) && empty(amount)) {
			current = groupFor(description, code);
			if (current.rowNo == null) current.rowNo = rowNo;
			continue;
		}
		if (!description) {
			skipped.push({ rowNo, reason: "No description" });
			continue;
		}
		if (!current) current = groupFor("", "");

		const notes = [];
		let q = qty,
			rt = rate;
		const amountOnly = empty(qty) && empty(rate) && !empty(amount) && !Number.isNaN(amount);
		if (amountOnly) {
			q = 1;
			rt = amount;
			notes.push("Amount only: imported as 1 × the amount");
		}
		if (Number.isNaN(q)) {
			notes.push(`Quantity "${str(cell(r, "qty"))}" is not a number: imported as 0`);
			q = 0;
		}
		if (Number.isNaN(rt)) {
			notes.push(`Rate "${str(cell(r, "rate"))}" is not a number: imported as 0`);
			rt = 0;
		}
		if (q === null) {
			notes.push("No quantity: imported as 0");
			q = 0;
		}
		if (rt === null) {
			notes.push("No rate: imported as 0");
			rt = 0;
		}
		if (
			!amountOnly &&
			!empty(amount) &&
			!Number.isNaN(amount) &&
			q &&
			rt &&
			Math.abs(q * rt - amount) > Math.max(1, Math.abs(amount) * 0.005)
		) {
			notes.push("The amount in the file is not quantity × rate; quantity × rate is used");
		}

		let itemCode = code;
		if (
			itemCode &&
			(takenCodes.has(itemCode.toLowerCase()) || seenCodes.has(itemCode.toLowerCase()))
		) {
			notes.push(`Code ${itemCode} is already used: a new one is given`);
			itemCode = "";
		}
		if (itemCode) seenCodes.add(itemCode.toLowerCase());

		let costHead = "";
		const ch = str(cell(r, "costHead"));
		if (ch) {
			costHead = COST_HEADS.find((h) => h.toLowerCase() === ch.toLowerCase()) || "";
			if (!costHead)
				notes.push(`Cost head "${ch}" is not one of ${COST_HEADS.join(", ")}: left blank`);
		}

		items.push({
			rowNo,
			groupKey: current.key,
			code: itemCode,
			description,
			unit: matchUnit(unitRaw || (amountOnly ? "LS" : ""), known),
			qty: q,
			rate: rt,
			amount: Math.round(q * rt * 100) / 100,
			costHead,
			notes,
		});
	}

	// Units that need the user: one entry per distinct spelling.
	const unitMap = new Map();
	let missingUnit = 0;
	for (const it of items) {
		if (it.unit.status === "missing") missingUnit++;
		if (it.unit.status !== "alias" && it.unit.status !== "unknown") continue;
		const k = it.unit.raw.toLowerCase();
		const e = unitMap.get(k) || {
			raw: it.unit.raw,
			status: it.unit.status,
			suggestion: it.unit.suggestion || null,
			count: 0,
		};
		e.count++;
		unitMap.set(k, e);
	}
	const counts = {};
	for (const it of items) counts[it.groupKey] = (counts[it.groupKey] || 0) + 1;
	return {
		items,
		skipped,
		groups: groups.filter((g) => counts[g.key]).map((g) => ({ ...g, count: counts[g.key] })),
		units: [...unitMap.values()],
		missingUnit,
	};
}

/** The default answer for each question the plan raises. The screen shows these so the user can change them. */
export function defaultDecisions(plan) {
	const units = {};
	for (const u of plan.units) {
		units[u.raw.toLowerCase()] = u.suggestion
			? { action: "map", value: u.suggestion }
			: { action: "create", value: u.raw };
	}
	return { units, missingUnit: { action: "set", value: "nos" } };
}

/**
 * The plan, with the user's decisions applied: the units to create, the
 * groups and the lines the backend imports. Rows the user chose to skip are
 * dropped, and a group left with no lines is not created.
 */
export function buildPayload(plan, decisions) {
	const newUnits = new Map();
	const out = [];
	let skipped = 0;
	for (const it of plan.items) {
		let unit = null;
		if (it.unit.status === "exact") unit = it.unit.value;
		else if (it.unit.status === "missing")
			unit = decisions.missingUnit?.action === "set" ? decisions.missingUnit.value : null;
		else {
			const d = decisions.units?.[it.unit.raw.toLowerCase()];
			if (d?.action === "create") {
				unit = it.unit.raw;
				newUnits.set(unit.toLowerCase(), unit);
			} else if (d?.action === "map") unit = d.value || null;
		}
		if (!unit) {
			skipped++;
			continue;
		}
		out.push({
			groupKey: it.groupKey,
			code: it.code,
			description: it.description,
			unit,
			plannedQty: it.qty,
			rate: it.rate,
			costHead: it.costHead,
		});
	}
	const used = new Set(out.map((x) => x.groupKey));
	return {
		units: [...newUnits.values()],
		groups: plan.groups
			.filter((g) => used.has(g.key))
			.map((g) => ({ key: g.key, existingId: g.existingId, code: g.code, name: g.name })),
		items: out,
		skippedByChoice: skipped,
	};
}

/** A starter file: Excel opens CSV, and the header names are ones detectColumns knows. */
export function templateCsv() {
	return (
		[
			"Group,Code,Description,Unit,Quantity,Rate,Cost head",
			"Civil works,,PCC 1:4:8 below footings,m³,12.5,5200,Material",
			"Civil works,,RCC M25 in footings and columns,m³,40,7800,Material",
			"Masonry,,230 mm brick masonry in CM 1:6,m³,65,6400,Material",
			"Finishes,,Vitrified tile flooring 600 x 600,m²,850,1250,Material",
			"Finishes,,Internal plaster 12 mm,m²,1900,380,Labour",
		].join("\r\n") + "\r\n"
	);
}
