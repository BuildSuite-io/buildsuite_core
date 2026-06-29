// Formatting helpers used across views.

// Site currency + decimals from the boot payload (set in www/core.py).
function defs() {
  return (typeof window !== 'undefined' && window.sysdefaults) || {}
}

// fmtCurrency(150000) -> ₹1,50,000.00 ; fmtCurrency(150000, 'USD') -> $150,000.00
export function fmtCurrency(value, currency = defs().currency || 'INR', precision) {
  if (value == null || value === '') value = 0
  if (precision == null || precision === '') {
    const p = Number(defs().currency_precision)
    precision = p > 0 ? p : 2
  }
  const locale = currency === 'INR' ? 'en-IN' : 'en-US'
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: precision,
    maximumFractionDigits: precision,
  }).format(Number(value) || 0)
}

// Compact: ₹1.5Cr / $1.5M etc.
export function fmtCompactCurrency(value, currency = defs().currency || 'INR') {
  if (value == null || value === '') value = 0
  const locale = currency === 'INR' ? 'en-IN' : 'en-US'
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(Number(value) || 0)
}

// Legacy aliases — now follow the site currency, not hardcoded ₹.
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
