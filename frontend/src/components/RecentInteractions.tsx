import { useAppSelector } from '../hooks'

export function RecentInteractions() {
  const rows = useAppSelector(s => s.crm.interactions)
  return <aside className="recent"><div className="recent-head"><div><span className="eyebrow">HISTORY</span><h2>Recent interactions</h2></div><span>{rows.length}</span></div>{rows.length ? rows.slice(0, 6).map(row => {
    const name = row.hcp?.name ?? row.hcp_name ?? 'Unknown HCP'
    return <article key={row.id}><div className="avatar">{name.slice(0, 1)}</div><div><strong>{name}</strong><p>{row.interaction_type} · {new Date(row.occurred_at).toLocaleDateString()}</p><small>{row.notes}</small></div><i className={'sentiment ' + (row.sentiment ?? 'neutral')}></i></article>
  }) : <p className="empty">Your logged interactions will appear here.</p>}</aside>
}