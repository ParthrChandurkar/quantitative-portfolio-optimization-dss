import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { ApiProvider } from '../../lib/api/context'
import type { AnalyticsBundle, OptiVestApi, Portfolio, ScenarioResponse, UserProfile } from '../../lib/api/client'
import { saveSelection } from '../../lib/selection'
import { AnalyticsPage } from '../AnalyticsPage'
import { AuthPage } from '../AuthPage'
import { DashboardPage } from '../DashboardPage'
import { PortfolioBuilderPage } from '../PortfolioBuilderPage'
import { PortfolioDetailsPage } from '../PortfolioDetailsPage'
import { ReportsPage } from '../ReportsPage'
import { ScenarioSimulatorPage } from '../ScenarioSimulatorPage'
import { SettingsPage } from '../SettingsPage'

const snapshot={id:'snapshot-1',label:'Live snapshot',expected_return:.16,expected_volatility:.2,sharpe_ratio:.8,diversification_score:82,is_baseline:true,created_at:'2026-08-14T10:00:00Z',budget_inr:1_000_000,holding_count:1,holdings:[{symbol:'RELIANCE',company_name:'Reliance Industries',sector:'Energy',weight:1,allocated_amount_inr:1_000_000,shares:700}],explanations:{included:[{symbol:'RELIANCE',decision:'included',primary_reason:'return contribution',binding_constraint:null,narrative_text:'Real persisted narrative.'}],notable_exclusions:[]}}
const portfolio:Portfolio={id:'portfolio-1',name:'Live Portfolio',is_active:true,created_at:'2026-08-14T09:00:00Z',latest_snapshot:snapshot}
const profile:UserProfile={id:'user-1',email:'user@example.com',full_name:'Live User',risk_profile_default:'balanced',created_at:'2026-08-14T08:00:00Z'}
const analytics:AnalyticsBundle={allocation:[{symbol:'RELIANCE',sector:'Energy',weight:1,allocated_amount_inr:1_000_000}],risk_return:{expected_return:.16,volatility:.2},growth_projection:[],performance:{buy_and_hold:{points:[{trade_date:'2025-01-01',portfolio_value:1_000_000,portfolio_return:0},{trade_date:'2025-12-31',portfolio_value:1_120_000,portfolio_return:.12}],warnings:[]},periodic_rebalance:{points:[{trade_date:'2025-01-01',portfolio_value:1_000_000,portfolio_return:0},{trade_date:'2025-12-31',portfolio_value:1_100_000,portfolio_return:.1}],warnings:[]}},risk_metrics:{sharpe_ratio:.8,model_annualized_volatility:.2,realized_annualized_volatility:.18,max_drawdown:-.08,parametric_var_95:169000,historical_var_95:43000},efficient_frontier:[{expected_return:.12,volatility:.15}],sector_distribution:[{sector:'Energy',allocation:1,cap:1,remaining_capacity:0,is_binding:true,exceeds_cap:false}]}
const scenario:ScenarioResponse={scenario_run_id:'scenario-1',scenario_type:'MARKET_CRASH',status:'optimal',comparison:{holdings:[{symbol:'RELIANCE',base_weight:1,simulated_weight:1,delta_w:0,direction:'unchanged'}],base_metrics:{expected_return:.16,volatility:.2,sharpe_ratio:.8,diversification_score:82},simulated_metrics:{expected_return:-.04,volatility:.22,sharpe_ratio:-.18,diversification_score:82},expected_return_delta:-.2,volatility_delta:.02,sharpe_ratio_delta:-.98,diversification_score_delta:0},explanations:null,weights_unchanged:true,scale_change_explanation:null}

const rejected=()=>Promise.reject(new Error('network failure'))
const pending=<T,>()=>new Promise<T>(()=>undefined)
function api(overrides:Partial<OptiVestApi>={}):OptiVestApi{return {isAuthenticated:()=>true,signup:vi.fn(),login:vi.fn(),logout:vi.fn(),me:vi.fn().mockResolvedValue(profile),updateMe:vi.fn().mockResolvedValue(profile),stocks:vi.fn().mockResolvedValue([]),sectors:vi.fn().mockResolvedValue([]),portfolios:vi.fn().mockResolvedValue([portfolio]),createPortfolio:vi.fn().mockResolvedValue(portfolio),portfolio:vi.fn().mockResolvedValue(portfolio),updatePortfolio:vi.fn().mockResolvedValue(portfolio),snapshots:vi.fn().mockResolvedValue([snapshot]),optimize:vi.fn(),optimizationRun:vi.fn(),scenario:vi.fn().mockResolvedValue(scenario),analytics:vi.fn().mockResolvedValue(analytics),generateReport:vi.fn(),reports:vi.fn().mockResolvedValue([]),downloadReport:vi.fn(),...overrides} as OptiVestApi}
function show(element:React.ReactNode,client:OptiVestApi){const query=new QueryClient({defaultOptions:{queries:{retry:false},mutations:{retry:false}}});return render(<MemoryRouter><QueryClientProvider client={query}><ApiProvider client={client}><Routes><Route path="*" element={element}/></Routes></ApiProvider></QueryClientProvider></MemoryRouter>)}

const pages=[
  {name:'Dashboard',element:<DashboardPage/>,method:'portfolios',success:'Live Portfolio'},
  {name:'Portfolio Builder',element:<PortfolioBuilderPage/>,method:'portfolios',success:'Build an optimal portfolio'},
  {name:'Portfolio Details',element:<PortfolioDetailsPage/>,method:'portfolio',success:'Real persisted narrative.'},
  {name:'Scenario Simulator',element:<ScenarioSimulatorPage/>,method:'portfolios',success:'Stress-test Live Portfolio'},
  {name:'Analytics',element:<AnalyticsPage/>,method:'analytics',success:'Portfolio diagnostics'},
  {name:'Reports',element:<ReportsPage/>,method:'reports',success:'Reporting centre'},
  {name:'Settings/Profile',element:<SettingsPage/>,method:'me',success:'Live User'},
] as const

describe.each(pages)('$name page',({element,method,success})=>{
  it('renders a loading state',()=>{saveSelection({portfolioId:'portfolio-1',snapshotId:'snapshot-1'});show(element,api({[method]:vi.fn(()=>pending())}));expect(screen.getByRole('status')).toBeInTheDocument()})
  it('renders real-client success data',async()=>{saveSelection({portfolioId:'portfolio-1',snapshotId:'snapshot-1'});show(element,api());expect(await screen.findByText(success)).toBeInTheDocument()})
  it('renders a consistent error state',async()=>{saveSelection({portfolioId:'portfolio-1',snapshotId:'snapshot-1'});show(element,api({[method]:vi.fn(rejected)}));expect(await screen.findByRole('alert')).toHaveTextContent('network failure')})
})

describe('real-client mutation flows',()=>{
  it('signs up through the auth page',async()=>{const signup=vi.fn().mockResolvedValue({...profile,access_token:'a',refresh_token:'r',token_type:'bearer',access_expires_at:'now',refresh_expires_at:'later'});show(<AuthPage/>,api({signup}));await userEvent.click(screen.getByRole('button',{name:'Sign up'}));expect(signup).toHaveBeenCalledWith('investor@example.com','optivest-demo-password','OptiVest Investor')})
  it('creates and optimizes a portfolio, then stores the real snapshot selection',async()=>{const optimize=vi.fn().mockResolvedValue({run:{id:'run-1',portfolio_id:portfolio.id,status:'solved',solver_used:'SciPy',solve_time_ms:120,message:null},snapshot,explanations:snapshot.explanations});show(<PortfolioBuilderPage/>,api({portfolios:vi.fn().mockResolvedValue([]),createPortfolio:vi.fn().mockResolvedValue(portfolio),optimize}));await screen.findByText('Build an optimal portfolio');await userEvent.click(screen.getByRole('button',{name:/Optimize/}));expect(await screen.findByText('Build an optimal portfolio')).toBeInTheDocument();expect(optimize).toHaveBeenCalled();expect(JSON.parse(localStorage.getItem('optivest.selection')!)).toEqual({portfolioId:'portfolio-1',snapshotId:'snapshot-1'})})
  it('runs and renders a real scenario comparison',async()=>{saveSelection({portfolioId:'portfolio-1',snapshotId:'snapshot-1'});const run=vi.fn().mockResolvedValue(scenario);show(<ScenarioSimulatorPage/>,api({scenario:run}));await screen.findByText('Stress-test Live Portfolio');await userEvent.click(screen.getByRole('button',{name:'Run live scenario'}));expect(await screen.findByText('MARKET_CRASH · optimal')).toBeInTheDocument();expect(run).toHaveBeenCalled()})
  it('generates a persisted report and refreshes history',async()=>{saveSelection({portfolioId:'portfolio-1',snapshotId:'snapshot-1'});const generate=vi.fn().mockResolvedValue({id:'report-1',snapshot_id:'snapshot-1',report_type:'portfolio_summary',file_path:'report.pdf',download_url:'/reports/report-1/download'});show(<ReportsPage/>,api({generateReport:generate}));await screen.findByText('Reporting centre');await userEvent.click(screen.getAllByRole('button',{name:'Generate real PDF'})[0]);expect(generate).toHaveBeenCalledWith('portfolio-1','snapshot-1','portfolio_summary')})
  it('opens a downloaded PDF from the authenticated report endpoint',async()=>{const download=vi.fn().mockResolvedValue(new Blob(['%PDF-test'],{type:'application/pdf'}));const createUrl=vi.fn().mockReturnValue('blob:report');const open=vi.spyOn(window,'open').mockImplementation(()=>null);vi.stubGlobal('URL',{...URL,createObjectURL:createUrl,revokeObjectURL:vi.fn()});show(<ReportsPage/>,api({reports:vi.fn().mockResolvedValue([{id:'report-1',snapshot_id:'snapshot-1',report_type:'portfolio_summary',file_path:'report.pdf',generated_at:'2026-08-14T12:00:00Z',download_url:'/reports/report-1/download'}]),downloadReport:download}));await screen.findByText('portfolio summary');await userEvent.click(screen.getByRole('button',{name:'Open'}));expect(download).toHaveBeenCalledWith('report-1');expect(open).toHaveBeenCalledWith('blob:report','_blank','noopener,noreferrer');vi.unstubAllGlobals()})
  it('patches the authenticated profile',async()=>{const update=vi.fn().mockResolvedValue({...profile,full_name:'Updated User'});show(<SettingsPage/>,api({updateMe:update}));const input=await screen.findByLabelText('Full name');await userEvent.clear(input);await userEvent.type(input,'Updated User');await userEvent.click(screen.getByRole('button',{name:'Save profile'}));expect(update).toHaveBeenCalledWith({full_name:'Updated User',risk_profile_default:'balanced'});expect(await screen.findByText('Profile saved successfully.')).toBeInTheDocument()})
})
