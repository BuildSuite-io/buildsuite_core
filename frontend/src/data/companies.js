// Companies — CLAUDE.md §14 (locked Company segregation decision).
//
// Static fixture. Pattern intentionally mirrors src/data/roles.js — each company
// has id / name / shortName / description / color (Tailwind badge class for the
// switcher pill and any future per-company indicators). To add a company, edit
// this file. There is NO admin UI for company management in the prototype, and
// per §14.6 the only multi-company affordance is the topbar switcher.
//
// Production note: in Frappe these would be Company DocType records. The id
// shape here ('ACME-COM' / 'ACME-INF' / 'ACME-RES') is short for the prototype;
// production company IDs are typically the company name itself per Frappe's
// naming convention (e.g., "Acme Commercial Pvt Ltd").

export const COMPANIES = [
  {
    id: 'ACME-COM',
    name: 'Acme Commercial Pvt Ltd',
    shortName: 'Acme Commercial',
    description: 'Commercial buildings · offices · IT parks · retail',
    color: 'bg-violet-600',
  },
  {
    id: 'ACME-RES',
    name: 'Acme Builders Pvt Ltd',
    shortName: 'Acme Builders',
    description: 'Residential towers · apartments · gated communities',
    color: 'bg-blue-600',
  },
  {
    id: 'ACME-INF',
    name: 'Acme Infrastructure Pvt Ltd',
    shortName: 'Acme Infra',
    description: 'Metro stations · roads · bridges · public infrastructure',
    color: 'bg-amber-600',
  },
]

// The company id that auto-fills when only one company exists in seed AND nothing
// is persisted yet. Falls back to the first entry — change the seed to flip the
// default if needed.
export const DEFAULT_COMPANY_ID = COMPANIES[0].id

export function companyById(id) {
  return COMPANIES.find(c => c.id === id) || null
}
