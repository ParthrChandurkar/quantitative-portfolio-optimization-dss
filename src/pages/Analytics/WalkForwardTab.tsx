import { useEffect, useMemo, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { LoaderCircle, Play } from 'lucide-react'
import { PageError } from '../../components/PageState'
import { useApi } from '../../lib/api/context'
import type { WalkForwardRun } from '../../lib/api/client'
import { money, number, percent } from '../../lib/format'

const colours = ['#39e6a1', '#60a5fa', '#fbbf24', '#f472b6', '#a78bfa', '#fb7185', '#2dd4bf', '#94a3b8']

function linePoints(points: Array<{ portfolio_value: number }>, min: number, max: number) {
  if (points.length < 2) return ''
  return points.map((point, index) => `${20 + index * 720 / (points.length - 1)},${230 - (point.portfolio_value - min) * 200 / Math.max(max - min, 1)}`).join(' ')
}

function ValueComparison({ run }: { run: WalkForwardRun }) {
  const walk = run.result.walk_forward.points, fixed = run.result.static_comparison.points
  const values = [...walk, ...fixed].map(point => point.portfolio_value)
  const min = Math.min(...values), max = Math.max(...values)
  return <div className="card walk-chart"><div className="card-head"><div><span>CUMULATIVE VALUE · SAME PERIOD</span><h3>Walk-forward versus static Phase 9C allocation</h3></div></div><svg viewBox="0 0 760 250" role="img" aria-label="Cumulative portfolio value comparison"><polyline points={linePoints(fixed, min, max)} fill="none" stroke="#64748b" strokeWidth="2"/><polyline points={linePoints(walk, min, max)} fill="none" stroke="#39e6a1" strokeWidth="3"/></svg><div className="legend"><span><i className="portfolio-dot"/>Walk-forward <b>{money(walk.at(-1)?.portfolio_value ?? 0)}</b></span><span><i/>Static <b>{money(fixed.at(-1)?.portfolio_value ?? 0)}</b></span></div></div>
}

function CompositionChart({ run }: { run: WalkForwardRun }) {
  const periods = run.result.walk_forward.periods
  const symbols = useMemo(() => Object.keys(periods.reduce<Record<string, number>>((acc, period) => { Object.entries(period.weights).forEach(([symbol, weight]) => { acc[symbol] = Math.max(acc[symbol] ?? 0, weight) }); return acc }, {})).sort((a, b) => Math.max(...periods.map(p => p.weights[b] ?? 0)) - Math.max(...periods.map(p => p.weights[a] ?? 0))).slice(0, 8), [periods])
  const bands = symbols.map((symbol, symbolIndex) => {
    const lower = periods.map(period => symbols.slice(0, symbolIndex).reduce((total, prior) => total + (period.weights[prior] ?? 0), 0))
    const upper = periods.map((period, index) => lower[index] + (period.weights[symbol] ?? 0))
    const top = upper.map((value, index) => `${20 + index * 720 / Math.max(periods.length - 1, 1)},${230 - value * 200}`)
    const bottom = lower.map((value, index) => `${20 + index * 720 / Math.max(periods.length - 1, 1)},${230 - value * 200}`).reverse()
    return <polygon key={symbol} points={[...top, ...bottom].join(' ')} fill={colours[symbolIndex]} opacity=".82"><title>{symbol}</title></polygon>
  })
  return <div className="card walk-chart"><div className="card-head"><div><span>COMPOSITION OVER TIME</span><h3>Target weights at each rebalance</h3></div></div><svg viewBox="0 0 760 250" role="img" aria-label="Walk-forward composition stacked area chart">{bands}</svg><div className="walk-legend">{symbols.map((symbol, index) => <span key={symbol}><i style={{background: colours[index]}}/>{symbol}</span>)}</div></div>
}

function MetricsComparison({ run }: { run: WalkForwardRun }) {
  const walk = run.result.walk_forward.metrics, fixed = run.result.static_comparison.metrics
  const rows = [['Annualized return', percent(walk.annualized_return), percent(fixed.annualized_return)], ['Realized Sharpe', number(walk.sharpe_ratio), number(fixed.sharpe_ratio)], ['Max drawdown', percent(walk.max_drawdown), percent(fixed.max_drawdown)], ['Final value', money(walk.final_value_inr), money(fixed.final_value_inr)]]
  return <section className="card walk-metrics"><div className="card-head"><div><span>DIRECT COMPARISON</span><h3>Same dates, different estimation policy</h3></div></div><div className="table-head"><span>METRIC</span><span>WALK-FORWARD</span><span>STATIC 9C</span></div>{rows.map(row => <div className="walk-metric-row" key={row[0]}><span>{row[0]}</span><b>{row[1]}</b><b>{row[2]}</b></div>)}<p>Transaction costs are not modeled. Total reported turnover: <b>{number(run.result.walk_forward.total_turnover)}</b>.</p></section>
}

export function WalkForwardTab({ portfolioId }: { portfolioId: string }) {
  const api = useApi()
  const [frequency, setFrequency] = useState('monthly'), [lookback, setLookback] = useState(252)
  const [progress, setProgress] = useState(1)
  const mutation = useMutation({ mutationFn: () => api.runWalkForward(portfolioId, { rebalance_frequency: frequency, lookback_days: lookback }) })
  useEffect(() => {
    if (!mutation.isPending) return
    const timer = window.setInterval(() => setProgress(value => Math.min(12, value + 1)), 1400)
    return () => window.clearInterval(timer)
  }, [mutation.isPending])
  return <section className="walk-forward-tab"><div className="card walk-controls"><div><span>STRICT CHRONOLOGICAL VALIDATION</span><h3>Walk-forward re-estimation</h3><p>At every rebalance, OptiVest fits μ/Σ only on observations strictly before that date.</p></div><label>Frequency<select value={frequency} onChange={event => setFrequency(event.target.value)}><option value="monthly">Monthly</option><option value="quarterly">Quarterly</option><option value="annually">Annually</option><option value="weekly">Weekly</option></select></label><label>Lookback days<input type="number" min="2" max="2520" value={lookback} onChange={event => setLookback(Number(event.target.value))}/></label><button className="primary" disabled={mutation.isPending} onClick={() => { setProgress(1); mutation.mutate() }}>{mutation.isPending ? <LoaderCircle className="spin"/> : <Play/>}{mutation.isPending ? 'Re-optimizing…' : 'Run walk-forward'}</button></div>{mutation.isPending && <div className="walk-progress" role="status"><LoaderCircle className="spin"/><span>Re-optimizing period {progress} of approximately 12</span><i><b style={{width: `${progress / 12 * 100}%`}}/></i></div>}{mutation.error && <PageError error={mutation.error} retry={() => mutation.mutate()}/>} {mutation.data && <><div className="methodology-banner"><strong>{mutation.data.result.methodology.label}</strong><span>{mutation.data.result.walk_forward.periods.length} independently fitted periods</span><b>Verified: every fit date precedes its rebalance</b></div><div className="walk-grid"><CompositionChart run={mutation.data}/><ValueComparison run={mutation.data}/></div><MetricsComparison run={mutation.data}/></>}</section>
}
