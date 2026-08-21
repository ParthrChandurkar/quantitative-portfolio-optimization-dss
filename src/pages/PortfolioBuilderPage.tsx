import { Check, RefreshCw, Settings2, Sparkles } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { PageError, PageLoading } from '../components/PageState'
import { useApi } from '../lib/api/context'
import { money, percent } from '../lib/format'
import { loadPersonalizedDefaults } from '../lib/personalization'
import { saveSelection } from '../lib/selection'

export function PortfolioBuilderPage(){
  const api=useApi(),navigate=useNavigate(),cache=useQueryClient(),personalized=loadPersonalizedDefaults()
  const[params]=useSearchParams()
  const[budget,setBudget]=useState(1_000_000),[name,setName]=useState('My Nifty-50 Portfolio'),[selected,setSelected]=useState(params.get('portfolio')??'')
  const[riskTolerance,setRiskTolerance]=useState(personalized?.risk_tolerance??1)
  const[maxSingleWeight,setMaxSingleWeight]=useState(personalized?.max_single_weight??.2)
  const[defaultSectorCap,setDefaultSectorCap]=useState(personalized?.default_sector_cap??.35)
  const portfolios=useQuery({queryKey:['portfolios'],queryFn:()=>api.portfolios()})
  const mutation=useMutation({mutationFn:async()=>{
    const portfolioId=selected||(await api.createPortfolio(name)).id
    const result=await api.optimize(portfolioId,{budget,risk_tolerance:riskTolerance,max_single_weight:maxSingleWeight,default_sector_cap:defaultSectorCap,solver:'SciPy',lookback_days:252,label:'Live optimized snapshot'})
    if(result.run.status==='pending'){let polled=await api.optimizationRun(result.run.id);while(polled.status==='pending'){await new Promise(resolve=>setTimeout(resolve,500));polled=await api.optimizationRun(result.run.id)}}
    if(result.run.status!=='solved'||!result.snapshot)throw new Error(result.run.message??`Optimization ${result.run.status}`)
    saveSelection({portfolioId,snapshotId:result.snapshot.id});await cache.invalidateQueries();return{portfolioId,result}
  },onSuccess:({portfolioId,result})=>navigate(`/portfolio/${portfolioId}/${result.snapshot!.id}`,{state:{optimization:result}})})
  const submit=(event:FormEvent)=>{event.preventDefault();mutation.mutate()}
  if(portfolios.isLoading)return <PageLoading/>
  if(portfolios.error)return <PageError error={portfolios.error} retry={()=>portfolios.refetch()}/>
  return <><section className="page-intro"><div><p className="eyebrow">REAL 49-STOCK UNIVERSE</p><h2>Build an optimal portfolio</h2><p>The request uses 252 loaded market observations and persists the full decision trail.</p></div><div className="model-badge"><span className="pulse"/>SciPy mean–variance</div></section>
    {personalized&&<div className="methodology-banner"><strong>PERSONALIZED DEFAULTS</strong><span>Based on your questionnaire: {personalized.category} ({(personalized.confidence*100).toFixed(1)}% confidence)</span><b>Every value remains editable</b></div>}
    {mutation.error&&<PageError error={mutation.error} retry={()=>mutation.mutate()}/>}<section className="optimizer-grid"><form className="card controls" onSubmit={submit}><div className="card-head"><div><span>MODEL INPUTS</span><h3>Investment constraints</h3></div><Settings2/></div><label>Portfolio<select aria-label="Portfolio" value={selected} onChange={e=>setSelected(e.target.value)}><option value="">Create a new portfolio</option>{portfolios.data?.filter(p=>p.is_active).map(p=><option value={p.id} key={p.id}>{p.name}</option>)}</select></label>{!selected&&<label>Portfolio name<input value={name} onChange={e=>setName(e.target.value)} required/></label>}<label>Investment capital (INR)<div className="input-prefix"><span>₹</span><input aria-label="Investment capital" value={budget} type="number" min="1000" onChange={e=>setBudget(Number(e.target.value))}/></div></label><div className="two-fields"><label>Risk tolerance<input aria-label="Risk tolerance" type="number" min="0.01" max="1" step="0.01" value={riskTolerance} onChange={e=>setRiskTolerance(Number(e.target.value))}/></label><label>Maximum stock weight<input aria-label="Maximum stock weight" type="number" min="0.01" max="1" step="0.01" value={maxSingleWeight} onChange={e=>setMaxSingleWeight(Number(e.target.value))}/></label></div><label>Default sector cap<input aria-label="Default sector cap" type="number" min="0.01" max="1" step="0.01" value={defaultSectorCap} onChange={e=>setDefaultSectorCap(Number(e.target.value))}/></label><div className="constraint-list"><div><Check/>Long-only positions</div><div><Check/>Maximum stock weight {percent(maxSingleWeight)}</div><div><Check/>Default sector cap {percent(defaultSectorCap)}</div><div><Check/>Real covariance lookback 252</div></div><button className="primary solve" disabled={mutation.isPending}>{mutation.isPending?<><RefreshCw className="spin"/>Solving live universe…</>:<><Sparkles/>Optimize {money(budget)}</>}</button></form><div className="card result"><div className="card-head"><div><span>SOLVER OUTPUT</span><h3>Real result appears here</h3></div></div>{mutation.isPending?<PageLoading label="Building μ and Σ, solving constraints, and generating explanations…"/>:<div className="result-placeholder"><Sparkles/><h3>Ready to optimize</h3><p>The solved snapshot will contain holdings, expected return, volatility, Sharpe ratio, diversification score, and narrative explanations.</p><small>Risk ceiling: {percent(riskTolerance)}</small></div>}</div></section></>
}
