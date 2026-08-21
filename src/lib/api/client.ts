export type ApiErrorBody = { code: string; message: string }
export type ApiEnvelope<T> = { data: T | null; error: ApiErrorBody | null }

export type UserProfile = {
  id: string
  email: string
  full_name: string
  risk_profile_default: string | null
  created_at: string
}

export type TokenSet = {
  access_token: string
  refresh_token: string
  token_type: 'bearer'
  access_expires_at: string
  refresh_expires_at: string
}

export type Portfolio = {
  id: string
  name: string
  is_active: boolean
  created_at: string
  latest_snapshot: Snapshot | null
}

export type Snapshot = {
  id: string
  label: string
  expected_return: number | null
  expected_volatility: number | null
  sharpe_ratio: number | null
  diversification_score: number | null
  is_baseline: boolean
  created_at: string
  budget_inr?: number | null
  holding_count?: number
  holdings?: Holding[]
  explanations?: ExplanationBundle
}

export type Holding = {
  symbol: string
  company_name: string
  sector: string
  weight: number
  allocated_amount_inr: number
  shares: number
}

export type Explanation = {
  symbol: string | null
  decision: string
  primary_reason: string
  marginal_return_contribution?: number | null
  marginal_risk_contribution?: number | null
  binding_constraint: string | null
  narrative_text: string
}

export type ExplanationBundle = {
  summary?: string
  included: Explanation[]
  notable_exclusions: Explanation[]
  constraint_insights?: Array<Record<string, unknown>>
  diversification?: { overall_score: number }
}

export type OptimizationResponse = {
  run: { id: string; portfolio_id: string; status: 'pending' | 'solved' | 'infeasible' | 'failed'; solver_used: string; solve_time_ms: number | null; message: string | null }
  snapshot: Snapshot | null
  explanations: ExplanationBundle | null
}

export type ScenarioResponse = {
  scenario_run_id: string
  scenario_type: string
  status: string
  comparison: {
    holdings: Array<{ symbol: string; base_weight: number; simulated_weight: number; delta_w: number; direction: string }>
    base_metrics: PortfolioMetrics
    simulated_metrics: PortfolioMetrics
    expected_return_delta: number
    volatility_delta: number
    sharpe_ratio_delta: number
    diversification_score_delta: number
  } | null
  explanations: ExplanationBundle | null
  weights_unchanged: boolean
  scale_change_explanation: string | null
}

export type PortfolioMetrics = { expected_return: number; volatility: number; sharpe_ratio: number; diversification_score: number }
export type AnalyticsBundle = {
  methodology: {
    label: 'OUT-OF-SAMPLE BACKTEST' | 'IN-SAMPLE REPLAY'
    estimation_start_date: string | null
    estimation_last_date: string | null
    split_date: string | null
    evaluation_start_date: string
    evaluation_end_date: string
    estimation_observations: number
    evaluation_observations: number
    windows_overlap: boolean
  }
  allocation: Array<{ symbol: string; sector: string; weight: number; allocated_amount_inr: number }>
  risk_return: { expected_return: number; volatility: number }
  growth_projection: Array<{ year: number; projected_value: number; lower_1sigma: number; upper_1sigma: number; lower_2sigma: number; upper_2sigma: number }>
  performance: { buy_and_hold: BacktestResult; periodic_rebalance: BacktestResult }
  risk_metrics: Record<string, number>
  efficient_frontier: Array<{ expected_return: number; volatility: number }>
  sector_distribution: Array<{ sector: string; allocation: number; cap: number; remaining_capacity: number; is_binding: boolean; exceeds_cap: boolean }>
}
export type BacktestResult = { points: Array<{ trade_date: string; portfolio_value: number; portfolio_return: number }>; warnings: string[]; validation_mode: string; estimation_end_date: string | null }
export type WalkForwardMetrics = { annualized_return: number; annualized_volatility: number; sharpe_ratio: number; max_drawdown: number; historical_var_95_inr: number; final_value_inr: number }
export type WalkForwardRun = {
  id: string
  portfolio_id: string
  rebalance_frequency: string
  lookback_days: number
  start_date: string
  end_date: string
  constraints_snapshot: Record<string, unknown>
  created_at: string
  result: {
    methodology: { label: string; strict_pre_rebalance_estimation: boolean; transaction_costs_included: boolean; start_date: string; end_date: string }
    walk_forward: {
      frequency: string
      lookback_days: number
      symbols: string[]
      points: Array<{ trade_date: string; portfolio_value: number; portfolio_return: number }>
      periods: Array<{ period_number: number; rebalance_date: string; holding_end_date: string; estimation_start_date: string; estimation_end_date: string; estimation_observations: number; weights: Record<string, number>; turnover: number; expected_return: number; expected_volatility: number }>
      total_turnover: number
      warnings: string[]
      metrics: WalkForwardMetrics
    }
    static_comparison: { label: string; points: Array<{ trade_date: string; portfolio_value: number; portfolio_return: number }>; metrics: WalkForwardMetrics }
  }
}
export type ReportRecord = { id: string; snapshot_id: string; report_type: string; file_path: string; generated_at?: string; download_url: string; size_bytes?: number }

export type Stock = {
  id: string
  symbol: string
  company_name: string
  sector: string
  industry: string | null
  listed_since: string | null
}

export type OptimizeRequest = {
  budget: number
  target_return?: number | null
  risk_tolerance?: number | null
  max_single_weight?: number
  min_holdings?: number | null
  max_holdings?: number | null
  min_lot_weight?: number
  sector_caps?: Record<string, number>
  default_sector_cap?: number
  solver?: 'Auto' | 'SciPy' | 'PuLP' | 'OR-Tools'
  risk_free_rate?: number
  lookback_days?: number
  label?: string
}

export type RiskQuestionnaireAnswers = {
  age_bracket: 'under_30' | '30_44' | '45_59' | '60_plus'
  investment_horizon: 'under_3_years' | '3_5_years' | '6_10_years' | 'over_10_years'
  income_stability: 'unstable' | 'variable' | 'stable' | 'highly_stable'
  loss_reaction: 'sell_all' | 'sell_some' | 'hold' | 'buy_more'
  experience_level: 'none' | 'beginner' | 'intermediate' | 'advanced'
  financial_dependents: 'three_or_more' | 'one_or_two' | 'none'
}

export type PersonalizedConstraints = { risk_tolerance: number; max_single_weight: number; default_sector_cap: number }
export type RiskProfile = { id: string; predicted_category: 'conservative' | 'moderate' | 'aggressive'; category_confidence: number; probabilities: Record<string, number>; recommended_constraints: PersonalizedConstraints; questionnaire_answers: RiskQuestionnaireAnswers; model_name: string; created_at: string }

export class OptiVestApiError extends Error {
  constructor(public readonly status: number, public readonly code: string, message: string) {
    super(message)
  }
}

export interface TokenStore {
  get(): TokenSet | null
  set(tokens: TokenSet): void
  clear(): void
}

class BrowserTokenStore implements TokenStore {
  private readonly key = 'optivest.tokens'

  get(): TokenSet | null {
    const value = globalThis.localStorage?.getItem(this.key)
    return value ? JSON.parse(value) as TokenSet : null
  }

  set(tokens: TokenSet): void {
    globalThis.localStorage?.setItem(this.key, JSON.stringify(tokens))
  }

  clear(): void {
    globalThis.localStorage?.removeItem(this.key)
  }
}

export interface OptiVestApi {
  isAuthenticated(): boolean
  signup(email: string, password: string, fullName: string): Promise<UserProfile & TokenSet>
  login(email: string, password: string): Promise<UserProfile & TokenSet>
  logout(): Promise<void>
  me(): Promise<UserProfile>
  updateMe(values: Partial<Pick<UserProfile, 'full_name' | 'risk_profile_default'>>): Promise<UserProfile>
  submitRiskProfile(answers: RiskQuestionnaireAnswers): Promise<RiskProfile>
  riskProfile(): Promise<RiskProfile>
  stocks(sector?: string): Promise<Stock[]>
  sectors(): Promise<Array<{ id: string; name: string }>>
  portfolios(): Promise<Portfolio[]>
  createPortfolio(name: string): Promise<Portfolio>
  portfolio(id: string): Promise<Portfolio>
  updatePortfolio(id: string, values: { name?: string; is_active?: boolean }): Promise<Portfolio>
  snapshots(portfolioId: string): Promise<Snapshot[]>
  optimize(portfolioId: string, values: OptimizeRequest): Promise<OptimizationResponse>
  optimizationRun(id: string): Promise<Record<string, unknown>>
  scenario(portfolioId: string, values: Record<string, unknown>): Promise<ScenarioResponse>
  analytics(portfolioId: string, snapshotId: string, query?: URLSearchParams): Promise<AnalyticsBundle>
  runWalkForward(portfolioId: string, values?: { start_date?: string; end_date?: string; rebalance_frequency?: string; lookback_days?: number }): Promise<WalkForwardRun>
  walkForwardRun(portfolioId: string, runId: string): Promise<WalkForwardRun>
  generateReport(portfolioId: string, snapshotId: string, reportType: string): Promise<ReportRecord>
  reports(): Promise<ReportRecord[]>
  downloadReport(id: string): Promise<Blob>
}

export class ApiClient implements OptiVestApi {
  private refreshPromise: Promise<TokenSet> | null = null

  constructor(
    private readonly baseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1',
    private readonly tokenStore: TokenStore = new BrowserTokenStore(),
    private readonly fetcher: typeof fetch = globalThis.fetch.bind(globalThis),
  ) {}

  isAuthenticated = () => this.tokenStore.get() !== null

  private async parse<T>(response: Response): Promise<T> {
    const envelope = await response.json() as ApiEnvelope<T>
    if (!response.ok || envelope.error || envelope.data === null) {
      const error = envelope.error ?? { code: 'INVALID_RESPONSE', message: 'The server returned an invalid response.' }
      throw new OptiVestApiError(response.status, error.code, error.message)
    }
    return envelope.data
  }

  private async rotate(): Promise<TokenSet> {
    if (this.refreshPromise) return this.refreshPromise
    const current = this.tokenStore.get()
    if (!current) throw new OptiVestApiError(401, 'AUTH_REQUIRED', 'Sign in is required.')
    this.refreshPromise = this.fetcher(`${this.baseUrl}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: current.refresh_token }),
    }).then(response => this.parse<TokenSet>(response)).then(tokens => {
      this.tokenStore.set(tokens)
      return tokens
    }).catch(error => {
      this.tokenStore.clear()
      throw error
    }).finally(() => { this.refreshPromise = null })
    return this.refreshPromise
  }

  private async request<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
    const tokens = this.tokenStore.get()
    const headers = new Headers(init.headers)
    if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
    if (tokens) headers.set('Authorization', `Bearer ${tokens.access_token}`)
    const response = await this.fetcher(`${this.baseUrl}${path}`, { ...init, headers })
    if (response.status === 401 && retry && tokens) {
      await this.rotate()
      return this.request<T>(path, init, false)
    }
    return this.parse<T>(response)
  }

  async signup(email: string, password: string, fullName: string): Promise<UserProfile & TokenSet> {
    const data = await this.request<{ user: UserProfile } & TokenSet>('/auth/signup', {
      method: 'POST', body: JSON.stringify({ email, password, full_name: fullName }),
    }, false)
    this.tokenStore.set(data)
    return { ...data.user, ...data }
  }

  async login(email: string, password: string): Promise<UserProfile & TokenSet> {
    const data = await this.request<{ user: UserProfile } & TokenSet>('/auth/login', {
      method: 'POST', body: JSON.stringify({ email, password }),
    }, false)
    this.tokenStore.set(data)
    return { ...data.user, ...data }
  }

  async logout(): Promise<void> {
    const tokens = this.tokenStore.get()
    if (tokens) await this.request('/auth/logout', {
      method: 'POST', body: JSON.stringify({ refresh_token: tokens.refresh_token }),
    }, false)
    this.tokenStore.clear()
  }

  me = () => this.request<UserProfile>('/me')
  updateMe = (values: Partial<Pick<UserProfile, 'full_name' | 'risk_profile_default'>>) =>
    this.request<UserProfile>('/me', { method: 'PATCH', body: JSON.stringify(values) })
  submitRiskProfile = (answers: RiskQuestionnaireAnswers) =>
    this.request<RiskProfile>('/me/risk-profile', { method: 'POST', body: JSON.stringify({ answers }) })
  riskProfile = () => this.request<RiskProfile>('/me/risk-profile')
  stocks = (sector?: string) => this.request<Stock[]>(`/stocks${sector ? `?sector=${encodeURIComponent(sector)}` : ''}`)
  sectors = () => this.request<Array<{ id: string; name: string }>>('/sectors')
  portfolios = () => this.request<Portfolio[]>('/portfolios')
  createPortfolio = (name: string) => this.request<Portfolio>('/portfolios', { method: 'POST', body: JSON.stringify({ name }) })
  portfolio = (id: string) => this.request<Portfolio>(`/portfolios/${id}`)
  updatePortfolio = (id: string, values: { name?: string; is_active?: boolean }) =>
    this.request<Portfolio>(`/portfolios/${id}`, { method: 'PATCH', body: JSON.stringify(values) })
  snapshots = (portfolioId: string) => this.request<Snapshot[]>(`/portfolios/${portfolioId}/snapshots`)
  optimize = (portfolioId: string, values: OptimizeRequest) =>
    this.request<OptimizationResponse>(`/portfolios/${portfolioId}/optimize`, { method: 'POST', body: JSON.stringify(values) })
  optimizationRun = (id: string) => this.request<Record<string, unknown>>(`/optimization-runs/${id}`)
  scenario = (portfolioId: string, values: Record<string, unknown>) =>
    this.request<ScenarioResponse>(`/portfolios/${portfolioId}/scenarios`, { method: 'POST', body: JSON.stringify(values) })
  analytics = (portfolioId: string, snapshotId: string, query = new URLSearchParams()) =>
    this.request<AnalyticsBundle>(`/portfolios/${portfolioId}/snapshots/${snapshotId}/analytics${query.size ? `?${query}` : ''}`)
  runWalkForward = (portfolioId: string, values: { start_date?: string; end_date?: string; rebalance_frequency?: string; lookback_days?: number } = {}) =>
    this.request<WalkForwardRun>(`/portfolios/${portfolioId}/walk-forward`, { method: 'POST', body: JSON.stringify(values) })
  walkForwardRun = (portfolioId: string, runId: string) =>
    this.request<WalkForwardRun>(`/portfolios/${portfolioId}/walk-forward/${runId}`)
  generateReport = (portfolioId: string, snapshotId: string, reportType: string) =>
    this.request<ReportRecord>(`/portfolios/${portfolioId}/snapshots/${snapshotId}/reports`, { method: 'POST', body: JSON.stringify({ report_type: reportType }) })
  reports = () => this.request<ReportRecord[]>('/reports')

  async downloadReport(id: string): Promise<Blob> {
    const tokens = this.tokenStore.get()
    const response = await this.fetcher(`${this.baseUrl}/reports/${id}/download`, {
      headers: tokens ? { Authorization: `Bearer ${tokens.access_token}` } : {},
    })
    if (!response.ok) await this.parse(response)
    return response.blob()
  }
}

export const apiClient = new ApiClient()
