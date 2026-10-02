// Formatting helpers used across views.
import { ref } from 'vue'

// Site currency + decimals from the boot payload (set in www/core.py) — the pre-boot fallback.
function defs() {
  return (typeof window !== 'undefined' && window.sysdefaults) || {}
}

// The currency the SPA renders amounts in: the active (or default) company's default_currency. The
// store sets it (setDisplayCurrency) once companies load and again whenever the company switches.
// It's a ref so every fmtCurrency()/currencySymbol() call made during a component's render re-runs
// when it changes — switching company reformats every amount on screen without touching a single
// call site. Starts from the boot default so the first paint isn't wrong before the store narrows it.
const displayCurrency = ref(defs().currency || 'INR')

export function setDisplayCurrency(code) {
  if (code) displayCurrency.value = code
}
export function getDisplayCurrency() {
  return displayCurrency.value
}

// INR groups in lakh/crore (en-IN); everything else uses en-US grouping. `narrowSymbol` forces the
// symbol (₹, ₦, $, €) over the ISO code some locale/currency pairs would otherwise render.
function localeFor(currency) {
  return currency === 'INR' ? 'en-IN' : 'en-US'
}

// fmtCurrency(150000) -> the active company's currency, e.g. ₦150,000.00 ; fmtCurrency(150000, 'USD') -> $150,000.00
export function fmtCurrency(value, currency = displayCurrency.value, precision) {
  if (value == null || value === '') value = 0
  if (precision == null || precision === '') {
    const p = Number(defs().currency_precision)
    precision = p > 0 ? p : 2
  }
  return new Intl.NumberFormat(localeFor(currency), {
    style: 'currency',
    currency,
    currencyDisplay: 'narrowSymbol',
    minimumFractionDigits: precision,
    maximumFractionDigits: precision,
  }).format(Number(value) || 0)
}

// Compact: ₹1.5Cr / $1.5M etc.
export function fmtCompactCurrency(value, currency = displayCurrency.value) {
  if (value == null || value === '') value = 0
  return new Intl.NumberFormat(localeFor(currency), {
    style: 'currency',
    currency,
    currencyDisplay: 'narrowSymbol',
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(Number(value) || 0)
}

// Just the currency symbol (₹, ₦, $, €…) for the active company — for field labels and input
// adornments that can't route a number through fmtCurrency. Reactive via the same ref, so a label
// using it re-renders when the company switches.
export function currencySymbol(currency = displayCurrency.value) {
  try {
    const parts = new Intl.NumberFormat(localeFor(currency), {
      style: 'currency',
      currency,
      currencyDisplay: 'narrowSymbol',
      maximumFractionDigits: 0,
    }).formatToParts(0)
    const sym = parts.find((p) => p.type === 'currency')
    return sym ? sym.value : currency
  } catch {
    return currency
  }
}

// Legacy aliases — now follow the active company currency, not hardcoded ₹.
export const fmtINR = fmtCurrency
export const fmtCompactINR = fmtCompactCurrency

export function fmtDate(d) {
	if (!d) return "—";
	try {
		return new Date(d).toLocaleDateString("en-IN", {
			day: "2-digit",
			month: "short",
			year: "numeric",
		});
	} catch (e) {
		return d;
	}
}

export function daysBetween(a, b) {
	if (!a || !b) return 0;
	const d1 = new Date(a);
	const d2 = new Date(b);
	return Math.round((d2 - d1) / 86400000);
}
