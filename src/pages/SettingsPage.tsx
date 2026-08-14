import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Save } from 'lucide-react'
import type { FormEvent } from 'react'
import { PageError, PageLoading } from '../components/PageState'
import { useApi } from '../lib/api/context'

export function SettingsPage() {
  const api = useApi()
  const cache = useQueryClient()
  const profile = useQuery({ queryKey: ['me'], queryFn: () => api.me() })
  const save = useMutation({
    mutationFn: (values: { full_name: string; risk_profile_default: string | null }) => api.updateMe(values),
    onSuccess: data => cache.setQueryData(['me'], data),
  })
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    save.mutate({
      full_name: String(form.get('full_name')),
      risk_profile_default: String(form.get('risk_profile_default')) || null,
    })
  }
  if (profile.isLoading) return <PageLoading label="Loading your live profile…"/>
  if (profile.error) return <PageError error={profile.error} retry={() => profile.refetch()}/>
  return <>
    <section className="page-intro"><div><p className="eyebrow">AUTHENTICATED PROFILE</p><h2>{profile.data!.full_name}</h2><p>Settings and risk defaults are saved to your PostgreSQL user record.</p></div></section>
    {save.error && <PageError error={save.error}/>}<form className="card settings-form" onSubmit={submit}>
      <label>Email<input value={profile.data!.email} disabled readOnly/></label>
      <label>Full name<input name="full_name" aria-label="Full name" defaultValue={profile.data!.full_name} required/></label>
      <label>Default risk profile<select name="risk_profile_default" aria-label="Default risk profile" defaultValue={profile.data!.risk_profile_default ?? ''}><option value="">Not set</option><option value="conservative">Conservative</option><option value="balanced">Balanced</option><option value="aggressive">Aggressive</option></select></label>
      <button className="primary" disabled={save.isPending}><Save/>{save.isPending ? 'Saving…' : 'Save profile'}</button>
      {save.isSuccess && <p className="success-message">Profile saved successfully.</p>}
    </form>
  </>
}
