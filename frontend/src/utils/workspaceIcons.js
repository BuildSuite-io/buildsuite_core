// Workspace icon utilities
//
// Centralized mapping so all workspace-facing surfaces (shell, home, shortcut
// cards, placeholder headers) render the same outline icon language.
//
// `resolveWorkspaceIconSlug` accepts either a known slug (`site-execution`) or
// legacy emoji (`🏗️`) and normalizes to a single icon key.
// `getWorkspaceIconPath` returns SVG path markup for inline v-html rendering.

const EMOJI_TO_SLUG = {
	"🏗️": "site-execution",
	"📐": "estimation",
	"🛒": "procurement",
	"🤝": "subcontract",
	"👷": "workforce",
	"💵": "project-finance",
	"📊": "accounting",
	"📥": "buying",
	"📦": "stock",
	"🏭": "assets",
	"👤": "hr",
	"⚙": "settings",
	"⚙️": "settings",
	"📋": "clipboard-list",
	"✅": "check-circle",
	"📝": "file-text",
	"📅": "calendar",
	"📈": "chart-line",
	"🔁": "refresh-ccw",
	"💸": "wallet",
	"🏦": "landmark",
	"📄": "file",
};

const PATHS = {
	home: '<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
	settings:
		'<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/>',

	"site-execution":
		'<path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z"/><path d="M6 12h12"/><path d="M6 7h12"/><path d="M6 17h12"/>',
	estimation:
		'<rect width="16" height="20" x="4" y="2" rx="2"/><line x1="8" x2="16" y1="6" y2="6"/><path d="M16 10h.01"/><path d="M12 10h.01"/><path d="M8 10h.01"/><path d="M16 14h.01"/><path d="M12 14h.01"/><path d="M8 14h.01"/>',
	procurement:
		'<circle cx="8" cy="21" r="1"/><circle cx="19" cy="21" r="1"/><path d="M2.05 2.05h2l2.66 12.42a2 2 0 0 0 2 1.58h9.78a2 2 0 0 0 1.95-1.57l1.65-7.43H5.12"/>',
	subcontract:
		'<rect width="20" height="14" x="2" y="7" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>',
	workforce:
		'<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
	"project-finance":
		'<path d="M21 12V7H5a2 2 0 0 1 0-4h14v4"/><path d="M3 5v14a2 2 0 0 0 2 2h16v-5"/><path d="M18 12a2 2 0 0 0 0 4h4v-4Z"/>',
	accounting:
		'<path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/><path d="M8 7h6"/><path d="M8 11h8"/>',
	buying: '<path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" x2="21" y1="6" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/>',
	stock: '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" x2="12" y1="22.08" y2="12"/>',
	assets: '<path d="M2 20a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8l-7 5V8l-7 5V4a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z"/><path d="M17 18h1"/><path d="M12 18h1"/><path d="M7 18h1"/>',
	hr: '<circle cx="12" cy="8" r="5"/><path d="M20 21a8 8 0 0 0-16 0"/>',

	"clipboard-list":
		'<rect x="8" y="2" width="8" height="4" rx="1" ry="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="M12 11h4"/><path d="M12 16h4"/><path d="M8 11h.01"/><path d="M8 16h.01"/>',
	"check-circle":
		'<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
	"file-text":
		'<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" x2="8" y1="13" y2="13"/><line x1="16" x2="8" y1="17" y2="17"/><line x1="10" x2="8" y1="9" y2="9"/>',
	calendar:
		'<rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/>',
	"chart-line": '<path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/>',
	"chart-bar":
		'<line x1="12" x2="12" y1="20" y2="10"/><line x1="18" x2="18" y1="20" y2="4"/><line x1="6" x2="6" y1="20" y2="16"/><line x1="3" x2="21" y1="20" y2="20"/>',
	"hard-hat":
		'<path d="M2 18a1 1 0 0 0 1 1h18a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1H3a1 1 0 0 0-1 1z"/><path d="M10 10V5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v5"/><path d="M4 15v-3a6 6 0 0 1 6-6"/><path d="M14 6a6 6 0 0 1 6 6v3"/>',
	"users-2":
		'<path d="M14 19a6 6 0 0 0-12 0"/><circle cx="8" cy="9" r="4"/><path d="M22 19a6 6 0 0 0-6-6 4 4 0 1 0 0-8"/>',
	"refresh-ccw":
		'<path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 16h5v5"/>',
	wallet: '<path d="M21 12V7H5a2 2 0 0 1 0-4h14v4"/><path d="M3 5v14a2 2 0 0 0 2 2h16v-5"/><path d="M18 12a2 2 0 0 0 0 4h4v-4Z"/>',
	landmark:
		'<line x1="3" x2="21" y1="22" y2="22"/><line x1="6" x2="6" y1="18" y2="11"/><line x1="10" x2="10" y1="18" y2="11"/><line x1="14" x2="14" y1="18" y2="11"/><line x1="18" x2="18" y1="18" y2="11"/><polygon points="12 2 20 7 4 7"/>',
	file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>',
	"building-2":
		'<path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18"/><path d="M4 22h16"/><path d="M10 6h4"/><path d="M10 10h4"/><path d="M10 14h4"/>',
	users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
	shield: '<path d="M20 13c0 5-3.5 7.5-8 9-4.5-1.5-8-4-8-9V5l8-3 8 3z"/>',
	tag: '<path d="M20.59 13.41 11 23l-9-9V3h11z"/><line x1="7" x2="7.01" y1="8" y2="8"/>',
	puzzle: '<path d="M14.5 4a2.5 2.5 0 1 0-5 0V6H8a2 2 0 0 0-2 2v1.5H4a2.5 2.5 0 1 0 0 5H6V16a2 2 0 0 0 2 2h1.5V20a2.5 2.5 0 1 0 5 0V18H16a2 2 0 0 0 2-2v-1.5h2a2.5 2.5 0 1 0 0-5H18V8a2 2 0 0 0-2-2h-1.5z"/>',
	"layout-grid":
		'<rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/><rect width="7" height="7" x="14" y="14" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/>',
	mail: '<rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-10 6L2 7"/>',
	wrench: '<path d="M14.7 6.3a4 4 0 0 0-5.6 5.6L3 18v3h3l6.1-6.1a4 4 0 0 0 5.6-5.6l-2.2 2.2-2.8-2.8z"/>',
	plug: '<path d="M12 22v-5"/><path d="M9 8V2"/><path d="M15 8V2"/><path d="M6 8h12v2a6 6 0 0 1-6 6h0a6 6 0 0 1-6-6z"/>',
	database:
		'<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.66 4.03 3 9 3s9-1.34 9-3V5"/><path d="M3 12c0 1.66 4.03 3 9 3s9-1.34 9-3"/>',
	image: '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="1.5"/><path d="m21 15-3.5-3.5a1.5 1.5 0 0 0-2.1 0L8 19"/>',
	archive:
		'<rect width="20" height="5" x="2" y="3" rx="1"/><path d="M4 8h16v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z"/><path d="M10 12h4"/>',
	"message-circle":
		'<path d="M21 11.5a8.5 8.5 0 1 1-4.7-7.6A8.5 8.5 0 0 1 21 11.5z"/><path d="m8 19-1.5 3 3.8-1"/>',
	paperclip:
		'<path d="M21.44 11.05 12 20.5a5 5 0 0 1-7.07-7.07l9.2-9.19a3.5 3.5 0 0 1 4.95 4.95l-9.19 9.2a2 2 0 1 1-2.83-2.83l8.48-8.49"/>',
	camera: '<path d="M14.5 4h-5L7.5 6H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-2.5z"/><circle cx="12" cy="12" r="3"/>',
	flag: '<path d="M4 22V4"/><path d="m4 4 6-2 4 2 6-2v12l-6 2-4-2-6 2"/>',
	pencil: '<path d="M12 20h9"/><path d="m16.5 3.5 4 4L7 21l-4 1 1-4Z"/>',
	trash: '<path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M10 11v6"/><path d="M14 11v6"/>',
	x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',

	app: '<rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/><rect width="7" height="7" x="14" y="14" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/>',
};

/**
 * Normalize a workspace icon reference to a slug.
 * Accepts legacy emoji and direct slugs.
 */
export function resolveWorkspaceIconSlug(input) {
	if (!input) return "app";
	if (EMOJI_TO_SLUG[input]) return EMOJI_TO_SLUG[input];
	if (PATHS[input]) return input;
	return "app";
}

/**
 * Return inline SVG path markup for a workspace icon slug.
 */
export function getWorkspaceIconPath(slug) {
	return PATHS[resolveWorkspaceIconSlug(slug)] || PATHS.app;
}
