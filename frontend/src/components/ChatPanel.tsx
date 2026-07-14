import { FormEvent, useState } from 'react'
import { sendChat } from '../services/api'
import { useAppDispatch, useAppSelector } from '../hooks'
import { addMessage, clearConfirmations, patchDraft } from '../store/crmSlice'
import type { Draft } from '../types'

const sessionId = crypto.randomUUID()
const localDateTime = (value: unknown) => typeof value === 'string' && value ? new Date(value).toISOString().slice(0, 16) : undefined

export function ChatPanel() {
  const dispatch = useAppDispatch()
  const { messages, draft } = useAppSelector(s => s.crm)
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)

  const applyExtraction = (data?: Record<string, unknown>) => {
    if (!data) return
    const update: Partial<Draft> = {}
    if (typeof data.hcp_name === 'string') update.hcp_name = data.hcp_name
    if (typeof data.notes === 'string') update.notes = data.notes
    if (Array.isArray(data.products)) update.products = data.products.filter((value): value is string => typeof value === 'string')
    if (typeof data.samples_distributed === 'string' || typeof data.samples_distributed === 'number') update.samples_distributed = String(data.samples_distributed)
    if (data.sentiment === 'positive' || data.sentiment === 'neutral' || data.sentiment === 'negative') update.sentiment = data.sentiment
    if (data.interaction_type === 'visit' || data.interaction_type === 'call' || data.interaction_type === 'email') update.interaction_type = data.interaction_type
    if (typeof data.follow_up_action === 'string') update.follow_up_action = data.follow_up_action
    const occurredAt = localDateTime(data.occurred_at)
    const followUpAt = localDateTime(data.follow_up_due_at)
    if (occurredAt) update.occurred_at = occurredAt
    if (followUpAt) update.follow_up_due_at = followUpAt
    dispatch(patchDraft(update))
  }

  const submit = async (e?: FormEvent) => {
    e?.preventDefault()
    const text = input.trim()
    if (!text || sending) return
    dispatch(clearConfirmations())
    dispatch(addMessage({ id: crypto.randomUUID(), role: 'user', content: text }))
    setInput('')
    setSending(true)
    try {
      const response = await sendChat(sessionId, text, draft)
      applyExtraction(response.extracted_data)
      const applied = (response.action === 'log_interaction' || response.action === 'edit_draft') && response.extracted_data && !response.extracted_data.missing_fields?.length
      dispatch(addMessage({ id: crypto.randomUUID(), role: 'assistant', content: applied ? (response.action === 'edit_draft' ? response.reply : 'Interaction draft applied to the form. Review the fields on the left, then select Log interaction.') : response.reply, tone: applied ? 'success' : undefined, extractedData: response.extracted_data, records: response.records }))
    } catch {
      dispatch(addMessage({ id: crypto.randomUUID(), role: 'assistant', content: 'I could not reach the CRM service. Please try again.' }))
    } finally { setSending(false) }
  }

  return <aside className="chat-panel">
    <header className="assistant-header"><div className="assistant-mark">AI</div><div><h2>AI Assistant</h2><p>Log interaction details here via chat</p></div></header>
    <div className="chat-intro">Log interaction details here (for example: “Met Dr. Smith, discussed CardioX efficacy, positive sentiment, shared brochure”) or ask for help.</div>
    <div className="messages" aria-live="polite">{messages.map(message => <div className={`message ${message.role} ${message.tone ?? ''}`} key={message.id}><div className="bubble">{message.content}</div>{message.records?.map(record => <div className="history-result" key={record.id}><strong>{record.hcp_name ?? record.hcp?.name ?? 'Unknown HCP'}</strong><br />{record.notes || 'No notes recorded.'}<details className="history-details"><summary>View full details</summary><dl><div><dt>Date</dt><dd>{record.occurred_at ? new Date(record.occurred_at).toLocaleString() : 'Not recorded'}</dd></div><div><dt>Interaction type</dt><dd>{record.interaction_type ?? 'Not recorded'}</dd></div><div><dt>Materials</dt><dd>{record.products?.length ? record.products.join(', ') : 'None'}</dd></div><div><dt>Samples</dt><dd>{record.samples_distributed ?? 'None'}</dd></div><div><dt>Sentiment</dt><dd>{record.sentiment ?? 'Not recorded'}</dd></div><div><dt>Follow-up</dt><dd>{record.follow_up_action ?? 'None'}</dd></div></dl></details></div>)}</div>)}</div>
    <form className="chat-input" onSubmit={submit}><textarea rows={2} value={input} onChange={e => setInput(e.target.value)} placeholder="Describe interaction..." /><button className="ai-log-button" disabled={sending}>{sending ? '...' : 'AI Log'}</button></form>
  </aside>
}