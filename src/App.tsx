import { Navigate, Route, Routes } from 'react-router-dom'
import { Shell } from './components/Shell'
import { useApi } from './lib/api/context'
import { AnalyticsPage } from './pages/AnalyticsPage'
import { AuthPage } from './pages/AuthPage'
import { DashboardPage } from './pages/DashboardPage'
import { PortfolioBuilderPage } from './pages/PortfolioBuilderPage'
import { PortfolioDetailsPage } from './pages/PortfolioDetailsPage'
import { ReportsPage } from './pages/ReportsPage'
import { ScenarioSimulatorPage } from './pages/ScenarioSimulatorPage'
import { SettingsPage } from './pages/SettingsPage'

function ProtectedLayout(){const api=useApi();return api.isAuthenticated()?<Shell/>:<Navigate to="/auth" replace/>}

export default function App(){return <Routes><Route path="/auth" element={<AuthPage/>}/><Route element={<ProtectedLayout/>}><Route index element={<DashboardPage/>}/><Route path="builder" element={<PortfolioBuilderPage/>}/><Route path="portfolio" element={<PortfolioDetailsPage/>}/><Route path="portfolio/:portfolioId/:snapshotId" element={<PortfolioDetailsPage/>}/><Route path="scenarios" element={<ScenarioSimulatorPage/>}/><Route path="analytics" element={<AnalyticsPage/>}/><Route path="analytics/:portfolioId/:snapshotId" element={<AnalyticsPage/>}/><Route path="reports" element={<ReportsPage/>}/><Route path="settings" element={<SettingsPage/>}/></Route><Route path="*" element={<Navigate to="/" replace/>}/></Routes>}
