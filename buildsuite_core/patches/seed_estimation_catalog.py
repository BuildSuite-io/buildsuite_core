# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Seed the estimation catalog masters (hardcoded).

Scope: UOMs, Rate Master Category, Construction Rate Master, Assembly Category,
Assembly, and Estimate Templates. Idempotent (skips anything already present),
safe to re-run. Runs post_model_sync, after Project Category is seeded.
"""

import frappe

# Only UOMs not already in ERPNext. Cubic Meter / Square Meter / Litre / Tonne /
# Kg / Nos / Day / Hour already exist as standard UOMs and are used as-is.
UOMS = ["Bag", "KL", "Lump-sum"]

# (category, resource_type) for the Rate Master Category master.
RATE_MASTER_CATEGORIES = [
	("Cement", "Material"),
	("Aggregate", "Material"),
	("Steel", "Material"),
	("Masonry", "Material"),
	("Consumable", "Material"),
	("Formwork", "Material"),
	("Finishes", "Material"),
	("Plant", "Equipment"),
	("Skilled Labour", "Labour"),
	("Semi-skilled Labour", "Labour"),
	("Unskilled Labour", "Labour"),
]

RATE_MASTERS = [
	{
		"code": "MAT-CEM-OPC43",
		"description": "OPC 43 Grade Cement",
		"category": "Cement",
		"resource_type": "Material",
		"uom": "Bag",
		"current_rate": 400,
	},
	{
		"code": "MAT-SAND-RIV",
		"description": "River Sand (fine aggregate)",
		"category": "Aggregate",
		"resource_type": "Material",
		"uom": "Cubic Meter",
		"current_rate": 2200,
	},
	{
		"code": "MAT-AGG-20",
		"description": "Coarse Aggregate 20mm",
		"category": "Aggregate",
		"resource_type": "Material",
		"uom": "Cubic Meter",
		"current_rate": 1600,
	},
	{
		"code": "MAT-AGG-12",
		"description": "Coarse Aggregate 12mm",
		"category": "Aggregate",
		"resource_type": "Material",
		"uom": "Cubic Meter",
		"current_rate": 1700,
	},
	{
		"code": "MAT-BRICK",
		"description": "Burnt Clay Brick (modular)",
		"category": "Masonry",
		"resource_type": "Material",
		"uom": "Nos",
		"current_rate": 8,
	},
	{
		"code": "MAT-AAC-BLK",
		"description": "AAC Block 600x200x200",
		"category": "Masonry",
		"resource_type": "Material",
		"uom": "Cubic Meter",
		"current_rate": 3800,
	},
	{
		"code": "MAT-STEEL-TMT",
		"description": "TMT Reinforcement Steel Fe500",
		"category": "Steel",
		"resource_type": "Material",
		"uom": "Tonne",
		"current_rate": 68000,
	},
	{
		"code": "MAT-BINDWIRE",
		"description": "Binding Wire 18 SWG",
		"category": "Steel",
		"resource_type": "Material",
		"uom": "Kg",
		"current_rate": 85,
	},
	{
		"code": "MAT-WATER",
		"description": "Water",
		"category": "Consumable",
		"resource_type": "Material",
		"uom": "KL",
		"current_rate": 30,
	},
	{
		"code": "MAT-SHUTMAT",
		"description": "Formwork Material - ply & props (amortised/use)",
		"category": "Formwork",
		"resource_type": "Material",
		"uom": "Square Meter",
		"current_rate": 90,
	},
	{
		"code": "MAT-TILE-VIT",
		"description": "Vitrified Tile 600x600",
		"category": "Finishes",
		"resource_type": "Material",
		"uom": "Square Meter",
		"current_rate": 700,
	},
	{
		"code": "MAT-TILE-CER",
		"description": "Ceramic Floor Tile",
		"category": "Finishes",
		"resource_type": "Material",
		"uom": "Square Meter",
		"current_rate": 550,
	},
	{
		"code": "MAT-PUTTY",
		"description": "Wall Putty (white cement based)",
		"category": "Finishes",
		"resource_type": "Material",
		"uom": "Kg",
		"current_rate": 35,
	},
	{
		"code": "MAT-PRIMER",
		"description": "Wall Primer",
		"category": "Finishes",
		"resource_type": "Material",
		"uom": "Litre",
		"current_rate": 150,
	},
	{
		"code": "MAT-EMULSION",
		"description": "Acrylic Emulsion Paint",
		"category": "Finishes",
		"resource_type": "Material",
		"uom": "Litre",
		"current_rate": 260,
	},
	{
		"code": "LAB-MASON1",
		"description": "Mason - 1st class",
		"category": "Skilled Labour",
		"resource_type": "Labour",
		"uom": "Day",
		"current_rate": 900,
	},
	{
		"code": "LAB-MASON2",
		"description": "Mason - 2nd class",
		"category": "Skilled Labour",
		"resource_type": "Labour",
		"uom": "Day",
		"current_rate": 750,
	},
	{
		"code": "LAB-BARBEND",
		"description": "Bar Bender / Steel Fixer",
		"category": "Skilled Labour",
		"resource_type": "Labour",
		"uom": "Day",
		"current_rate": 850,
	},
	{
		"code": "LAB-CARP",
		"description": "Carpenter (Shuttering)",
		"category": "Skilled Labour",
		"resource_type": "Labour",
		"uom": "Day",
		"current_rate": 900,
	},
	{
		"code": "LAB-PAINT",
		"description": "Painter",
		"category": "Skilled Labour",
		"resource_type": "Labour",
		"uom": "Day",
		"current_rate": 800,
	},
	{
		"code": "LAB-TILEMASON",
		"description": "Tile Mason",
		"category": "Skilled Labour",
		"resource_type": "Labour",
		"uom": "Day",
		"current_rate": 950,
	},
	{
		"code": "LAB-UNSKILLED",
		"description": "Unskilled Labour (Mazdoor)",
		"category": "Unskilled Labour",
		"resource_type": "Labour",
		"uom": "Day",
		"current_rate": 600,
	},
	{
		"code": "LAB-MATE",
		"description": "Mate / Beldar",
		"category": "Semi-skilled Labour",
		"resource_type": "Labour",
		"uom": "Day",
		"current_rate": 650,
	},
	{
		"code": "LAB-BHISTI",
		"description": "Bhisti (water carrier)",
		"category": "Unskilled Labour",
		"resource_type": "Labour",
		"uom": "Day",
		"current_rate": 600,
	},
	{
		"code": "PLT-MIXER",
		"description": "Concrete Mixer (1 bag)",
		"category": "Plant",
		"resource_type": "Equipment",
		"uom": "Day",
		"current_rate": 1000,
	},
	{
		"code": "PLT-VIBRATOR",
		"description": "Needle Vibrator",
		"category": "Plant",
		"resource_type": "Equipment",
		"uom": "Day",
		"current_rate": 500,
	},
	{
		"code": "PLT-COMPACTOR",
		"description": "Plate Compactor",
		"category": "Plant",
		"resource_type": "Equipment",
		"uom": "Day",
		"current_rate": 1200,
	},
	{
		"code": "PLT-EXCAV",
		"description": "Excavator (JCB 3DX)",
		"category": "Plant",
		"resource_type": "Equipment",
		"uom": "Hour",
		"current_rate": 1200,
	},
]


ASSEMBLY_CATEGORIES = [
	"Concrete",
	"Earthwork",
	"Finishing",
	"Formwork",
	"Masonry",
	"Plaster",
	"Reinforcement",
	"General",
]

# category "Finishes" from the seed is stored as "Finishing" (current spelling).
# Components carry only resource + coefficient; uom/rate/amount are fetched/computed by the Assembly controller.
ASSEMBLIES = [
	{
		"code": "ASM-PCC-148",
		"name": "PCC 1:4:8 - leveling course",
		"category": "Concrete",
		"uom": "Cubic Meter",
		"components": [
			{"resource": "MAT-CEM-OPC43", "coefficient": 3.4},
			{"resource": "MAT-SAND-RIV", "coefficient": 0.47},
			{"resource": "MAT-AGG-20", "coefficient": 0.9},
			{"resource": "MAT-WATER", "coefficient": 0.18},
			{"resource": "LAB-MASON2", "coefficient": 0.1},
			{"resource": "LAB-UNSKILLED", "coefficient": 1.5},
			{"resource": "PLT-MIXER", "coefficient": 0.15},
		],
	},
	{
		"code": "ASM-RCC-M20",
		"name": "RCC M20 - concrete only (excl. steel & formwork)",
		"category": "Concrete",
		"uom": "Cubic Meter",
		"components": [
			{"resource": "MAT-CEM-OPC43", "coefficient": 8.0},
			{"resource": "MAT-SAND-RIV", "coefficient": 0.42},
			{"resource": "MAT-AGG-20", "coefficient": 0.84},
			{"resource": "MAT-WATER", "coefficient": 0.19},
			{"resource": "LAB-MASON1", "coefficient": 0.2},
			{"resource": "LAB-UNSKILLED", "coefficient": 2.5},
			{"resource": "PLT-MIXER", "coefficient": 0.2},
			{"resource": "PLT-VIBRATOR", "coefficient": 0.2},
		],
	},
	{
		"code": "ASM-RCC-M25",
		"name": "RCC M25 - concrete only (excl. steel & formwork)",
		"category": "Concrete",
		"uom": "Cubic Meter",
		"components": [
			{"resource": "MAT-CEM-OPC43", "coefficient": 8.6},
			{"resource": "MAT-SAND-RIV", "coefficient": 0.4},
			{"resource": "MAT-AGG-20", "coefficient": 0.8},
			{"resource": "MAT-WATER", "coefficient": 0.19},
			{"resource": "LAB-MASON1", "coefficient": 0.2},
			{"resource": "LAB-UNSKILLED", "coefficient": 2.5},
			{"resource": "PLT-MIXER", "coefficient": 0.2},
			{"resource": "PLT-VIBRATOR", "coefficient": 0.2},
		],
	},
	{
		"code": "ASM-STEEL-RCC",
		"name": "Reinforcement steel - cut, bend & place",
		"category": "Reinforcement",
		"uom": "Tonne",
		"components": [
			{"resource": "MAT-STEEL-TMT", "coefficient": 1.03},
			{"resource": "MAT-BINDWIRE", "coefficient": 9.0},
			{"resource": "LAB-BARBEND", "coefficient": 6.0},
			{"resource": "LAB-UNSKILLED", "coefficient": 6.0},
		],
	},
	{
		"code": "ASM-FORM-RCC",
		"name": "Formwork / shuttering to RCC (per contact area)",
		"category": "Formwork",
		"uom": "Square Meter",
		"components": [
			{"resource": "MAT-SHUTMAT", "coefficient": 1.1},
			{"resource": "LAB-CARP", "coefficient": 0.12},
			{"resource": "LAB-UNSKILLED", "coefficient": 0.1},
		],
	},
	{
		"code": "ASM-BW-CM16",
		"name": "Brickwork in CM 1:6 - burnt clay brick",
		"category": "Masonry",
		"uom": "Cubic Meter",
		"components": [
			{"resource": "MAT-BRICK", "coefficient": 500},
			{"resource": "MAT-CEM-OPC43", "coefficient": 1.1},
			{"resource": "MAT-SAND-RIV", "coefficient": 0.25},
			{"resource": "LAB-MASON1", "coefficient": 0.75},
			{"resource": "LAB-UNSKILLED", "coefficient": 1.0},
			{"resource": "MAT-WATER", "coefficient": 0.1},
		],
	},
	{
		"code": "ASM-AAC-BW",
		"name": "AAC block masonry in CM 1:6",
		"category": "Masonry",
		"uom": "Cubic Meter",
		"components": [
			{"resource": "MAT-AAC-BLK", "coefficient": 0.98},
			{"resource": "MAT-CEM-OPC43", "coefficient": 0.5},
			{"resource": "MAT-SAND-RIV", "coefficient": 0.1},
			{"resource": "LAB-MASON1", "coefficient": 0.55},
			{"resource": "LAB-UNSKILLED", "coefficient": 0.7},
		],
	},
	{
		"code": "ASM-PLAST-12",
		"name": "Cement plaster 12mm CM 1:4 - internal",
		"category": "Plaster",
		"uom": "Square Meter",
		"components": [
			{"resource": "MAT-CEM-OPC43", "coefficient": 0.1},
			{"resource": "MAT-SAND-RIV", "coefficient": 0.013},
			{"resource": "LAB-MASON1", "coefficient": 0.1},
			{"resource": "LAB-UNSKILLED", "coefficient": 0.1},
		],
	},
	{
		"code": "ASM-PLAST-20",
		"name": "Cement plaster 20mm CM 1:6 - external",
		"category": "Plaster",
		"uom": "Square Meter",
		"components": [
			{"resource": "MAT-CEM-OPC43", "coefficient": 0.12},
			{"resource": "MAT-SAND-RIV", "coefficient": 0.022},
			{"resource": "LAB-MASON1", "coefficient": 0.12},
			{"resource": "LAB-UNSKILLED", "coefficient": 0.12},
		],
	},
	{
		"code": "ASM-TILE-VIT",
		"name": "Vitrified tile flooring 600x600 laid on CM bed",
		"category": "Finishing",
		"uom": "Square Meter",
		"components": [
			{"resource": "MAT-TILE-VIT", "coefficient": 1.05},
			{"resource": "MAT-CEM-OPC43", "coefficient": 0.2},
			{"resource": "MAT-SAND-RIV", "coefficient": 0.025},
			{"resource": "LAB-TILEMASON", "coefficient": 0.15},
			{"resource": "LAB-UNSKILLED", "coefficient": 0.12},
		],
	},
	{
		"code": "ASM-PAINT-EMUL",
		"name": "Emulsion paint - putty + primer + 2 coats",
		"category": "Finishing",
		"uom": "Square Meter",
		"components": [
			{"resource": "MAT-PUTTY", "coefficient": 0.5},
			{"resource": "MAT-PRIMER", "coefficient": 0.1},
			{"resource": "MAT-EMULSION", "coefficient": 0.2},
			{"resource": "LAB-PAINT", "coefficient": 0.1},
			{"resource": "LAB-UNSKILLED", "coefficient": 0.05},
		],
	},
	{
		"code": "ASM-EXCAV-MECH",
		"name": "Earthwork excavation in ordinary soil - mechanical",
		"category": "Earthwork",
		"uom": "Cubic Meter",
		"components": [
			{"resource": "PLT-EXCAV", "coefficient": 0.05},
			{"resource": "LAB-UNSKILLED", "coefficient": 0.05},
		],
	},
]


# Each row is (group_name, assembly_code, placeholder_qty, description). The
# controller derives uom/rate/amount from the linked Assembly and rolls up
# estimated_total; the groups child table is derived from the distinct row groups.
ESTIMATE_TEMPLATES = [
	{
		"code": "EST-TPL-RES",
		"name": "Residential - RCC framed (G+1)",
		"project_category": "Residential",
		"rows": [
			("Earthwork", "ASM-EXCAV-MECH", 120, "Excavation for foundation"),
			("Substructure", "ASM-PCC-148", 15, "PCC 1:4:8 leveling course"),
			("Substructure", "ASM-RCC-M20", 25, "RCC M20 in footings & plinth beams"),
			("Reinforcement", "ASM-STEEL-RCC", 2.2, "TMT reinforcement - substructure"),
			("Superstructure", "ASM-RCC-M20", 45, "RCC M20 in columns, beams, slab"),
			("Reinforcement", "ASM-STEEL-RCC", 4.5, "TMT reinforcement - superstructure"),
			("Formwork", "ASM-FORM-RCC", 380, "Formwork to RCC members"),
			("Masonry", "ASM-BW-CM16", 60, "Brickwork in CM 1:6 - external walls"),
			("Masonry", "ASM-AAC-BW", 35, "AAC block masonry - internal walls"),
			("Plaster", "ASM-PLAST-12", 650, "Internal cement plaster 12mm"),
			("Plaster", "ASM-PLAST-20", 420, "External cement plaster 20mm"),
			("Flooring", "ASM-TILE-VIT", 220, "Vitrified tile flooring"),
			("Painting", "ASM-PAINT-EMUL", 650, "Internal emulsion paint"),
		],
	},
	{
		"code": "EST-TPL-COM",
		"name": "Commercial - RCC framed structure",
		"project_category": "Commercial",
		"rows": [
			("Earthwork", "ASM-EXCAV-MECH", 600, "Excavation for raft/footings"),
			("Substructure", "ASM-PCC-148", 60, "PCC 1:4:8 below raft"),
			("Substructure", "ASM-RCC-M25", 180, "RCC M25 in raft & footings"),
			("Reinforcement", "ASM-STEEL-RCC", 18, "TMT reinforcement - substructure"),
			("Superstructure", "ASM-RCC-M25", 320, "RCC M25 in columns, beams, slabs"),
			("Reinforcement", "ASM-STEEL-RCC", 32, "TMT reinforcement - superstructure"),
			("Formwork", "ASM-FORM-RCC", 2800, "Formwork to RCC members"),
			("Masonry", "ASM-AAC-BW", 240, "AAC block masonry"),
			("Plaster", "ASM-PLAST-12", 3200, "Internal cement plaster 12mm"),
			("Plaster", "ASM-PLAST-20", 1800, "External cement plaster 20mm"),
			("Flooring", "ASM-TILE-VIT", 1500, "Vitrified tile flooring"),
			("Painting", "ASM-PAINT-EMUL", 4000, "Internal emulsion paint"),
		],
	},
	{
		"code": "EST-TPL-CW",
		"name": "Boundary / Compound Wall",
		"project_category": "Infrastructure",
		"rows": [
			("Earthwork", "ASM-EXCAV-MECH", 45, "Excavation for wall foundation"),
			("Substructure", "ASM-PCC-148", 8, "PCC 1:4:8 below footing"),
			("Substructure", "ASM-RCC-M20", 12, "RCC M20 in footing & coping"),
			("Reinforcement", "ASM-STEEL-RCC", 0.9, "TMT reinforcement"),
			("Masonry", "ASM-BW-CM16", 60, "Brickwork in CM 1:6"),
			("Plaster", "ASM-PLAST-20", 300, "Cement plaster 20mm - both faces"),
			("Painting", "ASM-PAINT-EMUL", 300, "Exterior emulsion paint"),
		],
	},
]


def execute():
	_seed_uoms()
	_seed_rate_master_categories()
	_seed_rate_masters()
	_seed_assembly_categories()
	_seed_assemblies()
	_seed_estimate_templates()


def _seed_uoms():
	for uom in UOMS:
		if not frappe.db.exists("UOM", uom):
			frappe.get_doc({"doctype": "UOM", "uom_name": uom}).insert()


def _seed_rate_master_categories():
	for category, resource_type in RATE_MASTER_CATEGORIES:
		if not frappe.db.exists("Rate Master Category", category):
			frappe.get_doc(
				{"doctype": "Rate Master Category", "category": category, "resource_type": resource_type}
			).insert()


def _seed_rate_masters():
	for r in RATE_MASTERS:
		if frappe.db.exists("Construction Rate Master", r["code"]):
			continue
		frappe.get_doc(
			{
				"doctype": "Construction Rate Master",
				"rate_code": r["code"],
				"rate_name": r["description"],
				"category": r["resource_type"],
				"rate_master_category": r["category"],
				"uom": r["uom"],
				"current_rate": r["current_rate"],
			}
		).insert()


def _seed_assembly_categories():
	for category in ASSEMBLY_CATEGORIES:
		if not frappe.db.exists("Assembly Category", category):
			frappe.get_doc({"doctype": "Assembly Category", "category": category}).insert()


def _seed_assemblies():
	for a in ASSEMBLIES:
		if frappe.db.exists("Assembly", a["code"]):
			continue
		frappe.get_doc(
			{
				"doctype": "Assembly",
				"assembly_code": a["code"],
				"assembly_name": a["name"],
				"category": a["category"],
				"uom": a["uom"],
				"components": [
					{"resource": c["resource"], "coefficient": c["coefficient"]} for c in a["components"]
				],
			}
		).insert()


def _seed_estimate_templates():
	for t in ESTIMATE_TEMPLATES:
		if frappe.db.exists("Estimate Template", t["code"]):
			continue
		groups = list(dict.fromkeys(group for group, _assembly, _qty, _desc in t["rows"]))
		frappe.get_doc(
			{
				"doctype": "Estimate Template",
				"template_code": t["code"],
				"template_name": t["name"],
				"project_category": t["project_category"],
				"enabled": 1,
				"groups": [{"group_name": g} for g in groups],
				"rows": [
					{
						"group_name": group,
						"line_type": "Assembly",
						"assembly": assembly,
						"placeholder_qty": qty,
						"description": description,
					}
					for group, assembly, qty, description in t["rows"]
				],
			}
		).insert()
