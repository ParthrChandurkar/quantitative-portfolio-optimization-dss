import { useQuery } from '@tanstack/react-query'
import { Activity, ArrowDownRight, Gauge, TrendingUp } from 'lucide-react'
import { useParams } from 'react-router-dom'
import { EmptyState, PageError, PageLoading } from '../components/PageState'
import { Metric } from '../components/Metric'
import { useApi } from '../lib/api/context'
import { money, number, percent } from '../lib/format'
import { loadSelection } from '../lib/selection'

function PerformanceChart({ values }: { values: Array<{ portfolio_value: number }> }) {
  if (values.length < 2) return null
  const sampled = values.filter((_, index) => index % Math.max(1, Math.floor(values.length / 40)) === 0 || index === values.length - 1)
  const min = Math.min(...sampled.map(point => point.portfolio_value))
  const max = Math.max(...sampled.map(point => point.portfolio_value))
  const points = sampled.map((point, index) => `${10 + index * 740 / (sampled.length - 1)},${240 - (point.portfolio_value - min) * 220 / Math.max(max - min, 1)}`).join(' ')
  return <svg className="live-chart" viewBox="0 0 760 260" aria-label="Out-of-sample historical backtest"><polyline points={points} fill="none" stroke="#39e6a1" strokeWidth="3"/></svg>
}

export function AnalyticsPage() {
  const api = useApi(), params = useParams(), saved = loadSelection()
  const portfolioId = params.portfolioId ?? saved?.portfolioId
  const snapshotId = params.snapshotId ?? saved?.snapshotId
  const query = useQuery({ queryKey: ['analytics', portfolioId, snapshotId], queryFn: () => api.analytics(portfolioId!, snapshotId!), enabled: Boolean(portfolioId && snapshotId) })
  if (!portfolioId || !snapshotId) return <EmptyState>Optimize a portfolio before viewing analytics.</EmptyState>
  if (query.isLoading) return <PageLoading label="Computing out-of-sample backtest and efficient frontier…"/>
  if (query.error) return <PageError error={query.error} retry={() => query.refetch()}/>
  const data = query.data!, risk = data.risk_metrics, audit = data.methodology
  return <>
    <section className="page-intro"><div><p className="eyebrow">REAL PHASE 7 ANALYTICS</p><h2>Portfolio diagnostics</h2><p>Backtest, realized risk, model risk, and frontier values are computed from PostgreSQL prices.</p></div></section>
    <section className="methodology-banner" aria-label="Backtest methodology"><strong>{audit.label}</strong><span>Fit μ/Σ: {audit.estimation_start_date} to {audit.estimation_last_date} ({audit.estimation_observations} observations)</span><span>Evaluation: {audit.evaluation_start_date} to {audit.evaluation_end_date} ({audit.evaluation_observations} observations)</span><b>{audit.windows_overlap ? 'INVALID: windows overlap' : 'Verified: zero overlapping dates'}</b></section>
    <section className="metric-grid"><Metric label="OOS REALIZED RETURN" value={percent(risk.realized_annualized_return)} detail={`Fit estimate ${percent(data.risk_return.expected_return)}`} icon={TrendingUp}/><Metric label="OOS REALIZED VOLATILITY" value={percent(risk.realized_annualized_volatility)} detail={`Fit model ${percent(risk.model_annualized_volatility)}`} icon={Activity}/><Metric label="OOS MAX DRAWDOWN" value={percent(risk.max_drawdown)} detail="Evaluation window only" icon={ArrowDownRight}/><Metric label="OOS REALIZED SHARPE" value={number(risk.realized_sharpe_ratio)} detail={`Historical VaR ${money(risk.historical_var_95)}`} icon={Gauge}/></section>
    <section className="main-grid"><div className="card performance"><div className="card-head"><div><span>OUT-OF-SAMPLE BACKTEST</span><h3>Periodic rebalance portfolio value</h3></div></div><PerformanceChart values={data.performance.periodic_rebalance.points}/><div className="legend"><span>Start <b>{money(data.performance.periodic_rebalance.points[0]?.portfolio_value ?? 0)}</b></span><span>Final <b>{money(data.performance.periodic_rebalance.points.at(-1)?.portfolio_value ?? 0)}</b></span></div></div><div className="card allocation"><div className="card-head"><div><span>FIT-PERIOD ALLOCATION</span><h3>Sector allocation versus cap</h3></div></div><div className="sector-bars">{data.sector_distribution.map(row => <div key={row.sector}><span>{row.sector}{row.is_binding ? ' · binding' : ''}</span><div><i style={{ width: `${Math.min(100, row.allocation / row.cap * 100)}%` }}/></div><b>{percent(row.allocation)}</b></div>)}</div></div></section>
    <section className="card shock-table"><div className="card-head"><div><span>FIT-PERIOD EFFICIENT FRONTIER</span><h3>{data.efficient_frontier.length} feasible risk-return points</h3></div></div><div className="table-head"><span>POINT</span><span>EXPECTED RETURN</span><span>VOLATILITY</span><span></span><span></span></div>{data.efficient_frontier.map((point, index) => <div className="shock-row" key={index}><span>#{index + 1}</span><span>{percent(point.expected_return)}</span><span>{percent(point.volatility)}</span><span></span><span></span></div>)}</section>
  </>
}
