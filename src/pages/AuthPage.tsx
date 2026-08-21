import { TrendingUp } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { PageError } from '../components/PageState'
import { useApi } from '../lib/api/context'

export function AuthPage() {
  const api = useApi()
  const navigate = useNavigate()
  const [mode, setMode] = useState<'signup' | 'login'>('signup')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<unknown>()
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setPending(true)
    setError(undefined)
    const form = new FormData(event.currentTarget)
    try {
      if (mode === 'signup') {
        await api.signup(String(form.get('email')), String(form.get('password')), String(form.get('full_name')))
        navigate('/onboarding/risk-profile')
      } else {
        await api.login(String(form.get('email')), String(form.get('password')))
        navigate('/')
      }
    } catch (value) { setError(value) } finally { setPending(false) }
  }
  return <main className="auth-page"><section className="card auth-card">
    <div className="brand"><div className="brand-mark"><TrendingUp/></div><span>OptiVest</span></div>
    <p className="eyebrow">AI-DRIVEN PERSONALIZED INVESTMENT PLANNING</p><h2>{mode === 'signup' ? 'Create your workspace' : 'Welcome back'}</h2><p>Use the live Nifty-50 optimization foundation while the AI personalization layer is developed.</p>
    {error != null ? <PageError error={error}/> : null}<form onSubmit={submit}>
      {mode === 'signup' && <label>Full name<input name="full_name" required defaultValue="OptiVest Investor"/></label>}
      <label>Email<input name="email" type="email" required defaultValue="investor@example.com"/></label>
      <label>Password<input name="password" type="password" minLength={8} required defaultValue="optivest-demo-password"/></label>
      <button className="primary" disabled={pending}>{pending ? 'Connecting…' : mode === 'signup' ? 'Sign up' : 'Sign in'}</button>
    </form><button className="text-btn auth-switch" onClick={() => setMode(mode === 'signup' ? 'login' : 'signup')}>{mode === 'signup' ? 'Already registered? Sign in' : 'Need an account? Sign up'}</button>
  </section></main>
}
