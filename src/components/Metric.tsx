import type { LucideIcon } from 'lucide-react'

export function Metric({ label, value, detail, icon: Icon }: { label: string; value: string; detail: string; icon: LucideIcon }) {
  return <div className="metric card"><div className="metric-top"><span>{label}</span><Icon size={17}/></div><strong>{value}</strong><small className="good">{detail}</small></div>
}
