import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ApiProvider } from '../../../lib/api/context'
import type { OptiVestApi, WalkForwardRun } from '../../../lib/api/client'
import { WalkForwardTab } from '../WalkForwardTab'

const result: WalkForwardRun = {
  id: 'walk-1', portfolio_id: 'portfolio-1', rebalance_frequency: 'monthly', lookback_days: 252,
  start_date: '2025-01-30', end_date: '2026-01-30', constraints_snapshot: {}, created_at: '2026-08-15T00:00:00Z',
  result: {
    methodology: { label: 'WALK-FORWARD OUT-OF-SAMPLE BACKTEST', strict_pre_rebalance_estimation: true, transaction_costs_included: false, start_date: '2025-01-30', end_date: '2026-01-30' },
    walk_forward: {
      frequency: 'monthly', lookback_days: 252, symbols: ['A', 'B'], total_turnover: 0.4, warnings: [],
      points: [{ trade_date: '2025-01-30', portfolio_value: 1_000_000, portfolio_return: 0 }, { trade_date: '2026-01-30', portfolio_value: 1_120_000, portfolio_return: 0.01 }],
      periods: [{ period_number: 1, rebalance_date: '2025-01-30', holding_end_date: '2025-02-28', estimation_start_date: '2024-01-01', estimation_end_date: '2025-01-29', estimation_observations: 252, weights: { A: 0.6, B: 0.4 }, turnover: 0, expected_return: 0.12, expected_volatility: 0.2 }],
      metrics: { annualized_return: 0.12, annualized_volatility: 0.18, sharpe_ratio: 0.67, max_drawdown: -0.1, historical_var_95_inr: 15_000, final_value_inr: 1_120_000 },
    },
    static_comparison: {
      label: 'STATIC SINGLE-SPLIT OUT-OF-SAMPLE',
      points: [{ trade_date: '2025-01-30', portfolio_value: 1_000_000, portfolio_return: 0 }, { trade_date: '2026-01-30', portfolio_value: 1_101_424, portfolio_return: 0.008 }],
      metrics: { annualized_return: 0.1031, annualized_volatility: 0.152, sharpe_ratio: 0.68, max_drawdown: -0.1326, historical_var_95_inr: 15_800, final_value_inr: 1_101_424 },
    },
  },
}

function show(runWalkForward: ReturnType<typeof vi.fn>) {
  const query = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  const client = { runWalkForward } as unknown as OptiVestApi
  return render(<QueryClientProvider client={query}><ApiProvider client={client}><WalkForwardTab portfolioId="portfolio-1"/></ApiProvider></QueryClientProvider>)
}

describe('WalkForwardTab', () => {
  it('shows period progress while the real request is pending', async () => {
    show(vi.fn(() => new Promise(() => undefined)))
    await userEvent.click(screen.getByRole('button', { name: 'Run walk-forward' }))
    expect(screen.getByRole('status')).toHaveTextContent('Re-optimizing period 1')
  })

  it('renders composition, value overlay, and side-by-side metrics', async () => {
    const runWalkForward = vi.fn().mockResolvedValue(result)
    show(runWalkForward)
    await userEvent.click(screen.getByRole('button', { name: 'Run walk-forward' }))
    expect(await screen.findByText('WALK-FORWARD OUT-OF-SAMPLE BACKTEST')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Walk-forward composition stacked area chart' })).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Cumulative portfolio value comparison' })).toBeInTheDocument()
    expect(screen.getByText('Verified: every fit date precedes its rebalance')).toBeInTheDocument()
    expect(runWalkForward).toHaveBeenCalledWith('portfolio-1', { rebalance_frequency: 'monthly', lookback_days: 252 })
  })

  it('uses the shared API error state', async () => {
    show(vi.fn().mockRejectedValue(new Error('walk-forward failed')))
    await userEvent.click(screen.getByRole('button', { name: 'Run walk-forward' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('walk-forward failed')
  })
})
