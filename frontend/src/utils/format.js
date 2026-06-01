// Formatting helpers used across views.

export function fmt(n) {
  if (n == null || n === '') return ''
  return Number(n).toLocaleString('en-IN')
}

export function fmtINR(n) {
  if (n == null) return '₹0'
  return '₹' + fmt(n)
}

export function fmtCompactINR(n) {
  if (n == null) return '₹0'
  if (n >= 10000000) return `₹${(n / 10000000).toFixed(2)} Cr`
  if (n >= 100000)   return `₹${(n / 100000).toFixed(2)} L`
  if (n >= 1000)     return `₹${(n / 1000).toFixed(1)} k`
  return `₹${n}`
}

export function fmtDate(d) {
  if (!d) return '—'
  try {
    return new Date(d).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
  } catch (e) {
    return d
  }
}

export function daysBetween(a, b) {
  if (!a || !b) return 0
  const d1 = new Date(a)
  const d2 = new Date(b)
  return Math.round((d2 - d1) / 86400000)
}
