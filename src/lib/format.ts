export const money = (value: number) => new Intl.NumberFormat('en-IN', {
  style: 'currency', currency: 'INR', maximumFractionDigits: 0,
}).format(value)

export const percent = (value: number | null | undefined, digits = 2) =>
  value == null ? '—' : `${(value * 100).toFixed(digits)}%`

export const number = (value: number | null | undefined, digits = 2) =>
  value == null ? '—' : value.toFixed(digits)
