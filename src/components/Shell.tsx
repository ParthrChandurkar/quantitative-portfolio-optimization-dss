import { BarChart3, BookOpen, BriefcaseBusiness, LayoutDashboard, LogOut, Menu, Settings2, SlidersHorizontal, TrendingUp, X, Zap } from 'lucide-react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useApi } from '../lib/api/context'
import { NotificationBell } from './NotificationBell'

const links = [
  ['Dashboard', '/', LayoutDashboard],
  ['Portfolio Builder', '/builder', SlidersHorizontal],
  ['Portfolio Details', '/portfolio', BriefcaseBusiness],
  ['Scenario Simulator', '/scenarios', Zap],
  ['Analytics', '/analytics', BarChart3],
  ['Reports', '/reports', BookOpen],
  ['Settings', '/settings', Settings2],
] as const

export function Shell() {
  const [open, setOpen] = useState(false)
  const api = useApi()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const location = useLocation()
  const current = links.find(([, path]) => path === '/' ? location.pathname === '/' : location.pathname.startsWith(path))?.[0] ?? 'OptiVest'
  const logout = async () => { await api.logout(); queryClient.clear(); navigate('/auth') }
  return <div className="app"><aside className={open?'sidebar open':'sidebar'}>
    <div className="brand"><div className="brand-mark"><TrendingUp size={19}/></div><span>OptiVest</span><button aria-label="Close menu" className="mobile-close" onClick={()=>setOpen(false)}><X/></button></div>
    <p className="side-label">WORKSPACE</p><nav>{links.map(([label,path,Icon])=><NavLink key={label} end={path==='/' } to={path} className={({isActive})=>isActive?'nav-link active':'nav-link'} onClick={()=>setOpen(false)}><Icon size={18}/><span>{label}</span></NavLink>)}</nav>
    <div className="sidebar-bottom"><div className="system-card"><div><span className="pulse"/>LIVE DATA</div><strong>Nifty-50 PostgreSQL</strong><small>49-stock universe</small></div><button className="nav-link" onClick={logout}><LogOut size={18}/>Sign out</button></div>
  </aside>{open&&<div className="backdrop" onClick={()=>setOpen(false)}/>}<main><header><button aria-label="Open menu" className="menu" onClick={()=>setOpen(true)}><Menu/></button><div><span className="crumb">AI-DRIVEN INVESTMENT PLANNING</span><h1>{current}</h1></div><div className="top-actions"><div className="market"><span className="pulse"/>LIVE BACKEND <b>NIFTY 50</b></div><NotificationBell/></div></header><div className="content"><Outlet/></div></main></div>
}
