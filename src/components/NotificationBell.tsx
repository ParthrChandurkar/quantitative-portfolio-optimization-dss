import { AlertTriangle, Bell, Check, LoaderCircle } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useApi } from '../lib/api/context'

export function NotificationBell() {
  const api = useApi()
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const alerts = useQuery({ queryKey: ['alerts'], queryFn: () => api.alerts(), refetchInterval: 30_000 })
  const acknowledge = useMutation({
    mutationFn: (id: string) => api.acknowledgeAlert(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['alerts'] }),
  })
  const unread = alerts.data?.filter(alert => !alert.acknowledged).length ?? 0

  return <div className="notification-wrap">
    <button className="notification" aria-label={`Notifications${unread ? ` (${unread} unread)` : ''}`} aria-expanded={open} onClick={() => setOpen(value => !value)}>
      <Bell/>{unread > 0 && <b className="notification-count">{unread}</b>}
    </button>
    {open && <div className="notification-panel" role="dialog" aria-label="Personalized alerts">
      <div className="notification-head"><div><span>PERSONALIZED ALERTS</span><strong>{unread} unacknowledged</strong></div></div>
      {alerts.isLoading && <div className="notification-state" role="status"><LoaderCircle className="spin"/>Loading alerts…</div>}
      {alerts.error && <div className="notification-state notification-failed" role="alert"><AlertTriangle/>{alerts.error instanceof Error ? alerts.error.message : 'Unable to load alerts.'}</div>}
      {alerts.data?.length === 0 && <div className="notification-state">No risk drift or stock anomalies detected.</div>}
      <div className="notification-list">{alerts.data?.map(alert => <button
        type="button"
        className={`notification-item ${alert.severity} ${alert.acknowledged ? 'acknowledged' : ''}`}
        key={alert.id}
        disabled={alert.acknowledged || acknowledge.isPending}
        onClick={() => acknowledge.mutate(alert.id)}
      >
        <i/><span><b>{alert.alert_type.replaceAll('_', ' ')}</b><p>{alert.message}</p><small>{new Date(alert.created_at).toLocaleString('en-IN')} · grounded in {Object.keys(alert.grounding).join(', ')}</small></span>{alert.acknowledged && <Check/>}
      </button>)}</div>
    </div>}
  </div>
}
