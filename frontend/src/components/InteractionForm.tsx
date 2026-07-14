import { FormEvent, useMemo, useRef, useState } from 'react'
import { useAppDispatch, useAppSelector } from '../hooks'
import { summarizeVoiceNote } from '../services/api'
import { patchDraft, saveDraft } from '../store/crmSlice'

type SpeechRecognitionLike = {
  continuous: boolean
  interimResults: boolean
  lang: string
  start: () => void
  stop: () => void
  onresult: ((event: any) => void) | null
  onerror: ((event: any) => void) | null
  onend: (() => void) | null
}

export function InteractionForm() {
  const dispatch = useAppDispatch()
  const { draft, busy, error, hcps } = useAppSelector(s => s.crm)
  const [material, setMaterial] = useState('')
  const [attendees, setAttendees] = useState('')
  const [outcomes, setOutcomes] = useState('')
  const [voiceDialogOpen, setVoiceDialogOpen] = useState(false)
  const [voiceConsent, setVoiceConsent] = useState(false)
  const [listening, setListening] = useState(false)
  const [voiceStatus, setVoiceStatus] = useState('')
  const [voiceComplete, setVoiceComplete] = useState(false)
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null)
  const date = useMemo(() => draft.occurred_at.slice(0, 10), [draft.occurred_at])
  const time = useMemo(() => draft.occurred_at.slice(11, 16), [draft.occurred_at])

  const patchOccurredAt = (nextDate = date, nextTime = time) => dispatch(patchDraft({ occurred_at: `${nextDate}T${nextTime}` }))
  const submit = (e: FormEvent) => {
    e.preventDefault()
    const notes = [draft.notes, outcomes && `Outcome: ${outcomes}`].filter(Boolean).join('\n\n')
    dispatch(saveDraft({ ...draft, notes }))
  }
  const addMaterial = () => {
    const value = material.trim()
    if (value && !draft.products.includes(value)) dispatch(patchDraft({ products: [...draft.products, value] }))
    setMaterial('')
  }
  const closeVoiceDialog = () => {
    recognitionRef.current?.stop()
    recognitionRef.current = null
    setListening(false)
    setVoiceDialogOpen(false)
    setVoiceComplete(false)
  }
  const startVoiceNote = () => {
    if (!voiceConsent) return
    const Recognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!Recognition) {
      setVoiceStatus('Voice capture is not supported in this browser. Use Chrome or enter the notes manually.')
      return
    }
    const recognition: SpeechRecognitionLike = new Recognition()
    recognition.lang = 'en-US'
    recognition.continuous = false
    recognition.interimResults = false
    recognition.onresult = async (event: any) => {
      const transcript = Array.from(event.results as any[]).map((result: any) => result[0]?.transcript ?? '').join(' ').trim()
      if (!transcript) {
        setVoiceStatus('No speech was captured. Please try again.')
        return
      }
      setListening(false)
      setVoiceStatus('Summarizing your voice note...')
      try {
        const response = await summarizeVoiceNote(transcript)
        dispatch(patchDraft({ notes: [draft.notes, response.summary].filter(Boolean).join(draft.notes ? '\n\n' : '') }))
        setVoiceStatus('Summary added to Topics Discussed. Review it before logging.')
        setVoiceComplete(true)
      } catch {
        dispatch(patchDraft({ notes: [draft.notes, transcript].filter(Boolean).join(draft.notes ? '\n\n' : '') }))
        setVoiceStatus('The AI summary was unavailable, so the transcript was added to Topics Discussed.')
        setVoiceComplete(true)
      }
    }
    recognition.onerror = () => {
      setListening(false)
      setVoiceStatus('Microphone access was not available. Allow microphone permission and try again.')
    }
    recognition.onend = () => setListening(false)
    recognitionRef.current = recognition
    setVoiceStatus('Listening... speak your interaction notes, then pause.')
    setListening(true)
    recognition.start()
  }

  return <form className="interaction-form" onSubmit={submit}>
    <div className="form-title-row">
      <div><span className="section-kicker">FIELD ENGAGEMENT</span><h1>Log HCP Interaction</h1></div>
      <button className="log-button" type="submit" disabled={busy}>{busy ? 'Logging...' : 'Log interaction'}</button>
    </div>

    <h2 className="section-heading">Interaction Details</h2>
    <div className="two-column-grid">
      <label>HCP Name<input required list="hcp-options" placeholder="Search or select HCP..." value={draft.hcp_name} onChange={e => dispatch(patchDraft({ hcp_name: e.target.value }))} /><datalist id="hcp-options">{hcps.map(hcp => <option key={hcp.id} value={hcp.name} />)}</datalist></label>
      <label>Interaction Type<select value={draft.interaction_type} onChange={e => dispatch(patchDraft({ interaction_type: e.target.value as typeof draft.interaction_type }))}><option value="visit">Meeting</option><option value="call">Phone call</option><option value="email">Email</option></select></label>
      <label>Date<input required type="date" value={date} onChange={e => patchOccurredAt(e.target.value, time)} /></label>
      <label>Time<input required type="time" value={time} onChange={e => patchOccurredAt(date, e.target.value)} /></label>
    </div>

    <label>Attendees<input placeholder="Enter names or search..." value={attendees} onChange={e => setAttendees(e.target.value)} /></label>
    <label>Topics Discussed<textarea required rows={4} placeholder="Enter key discussion points..." value={draft.notes} onChange={e => dispatch(patchDraft({ notes: e.target.value }))} /></label>
    <button className="voice-note" type="button" onClick={() => { setVoiceDialogOpen(true); setVoiceStatus(''); setVoiceComplete(false) }}>Summarize from Voice Note</button>

    <section className="form-section">
      <h2 className="section-heading">Materials Shared / Samples Distributed</h2>
      <label>Materials Shared<div className="material-entry"><input placeholder="Brochures, study summary, leave-behind..." value={material} onChange={e => setMaterial(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addMaterial() } }} /><button type="button" onClick={addMaterial}>Search/Add</button></div><div className="material-list">{draft.products.length ? draft.products.map(item => <button type="button" className="material-chip" key={item} onClick={() => dispatch(patchDraft({ products: draft.products.filter(product => product !== item) }))}>{item} x</button>) : <span>No materials added.</span>}</div></label>
      <label>Samples Distributed<input placeholder="No samples added" value={draft.samples_distributed} onChange={e => dispatch(patchDraft({ samples_distributed: e.target.value }))} /></label>
    </section>

    <section className="form-section"><h2 className="section-heading">Observed/Inferred HCP Sentiment</h2><div className="sentiment-options">{(['positive', 'neutral', 'negative'] as const).map(value => <label key={value} className="sentiment-choice"><input type="radio" name="sentiment" value={value} checked={draft.sentiment === value} onChange={() => dispatch(patchDraft({ sentiment: value }))} /><span className={`sentiment-dot ${value}`} />{value[0].toUpperCase() + value.slice(1)}</label>)}</div></section>
    <label>Outcomes<textarea rows={3} placeholder="Key outcomes or agreements..." value={outcomes} onChange={e => setOutcomes(e.target.value)} /></label>
    <section className="form-section follow-up-grid"><h2 className="section-heading">Follow-up Actions</h2><label>Action<input placeholder="Schedule meeting, share study summary..." value={draft.follow_up_action} onChange={e => dispatch(patchDraft({ follow_up_action: e.target.value }))} /></label><label>Due date<input type="datetime-local" value={draft.follow_up_due_at} onChange={e => dispatch(patchDraft({ follow_up_due_at: e.target.value }))} /></label></section>
    {error && <p className="error">{error}</p>}
    <div className="form-footer"><span>Review the extracted details before logging the interaction.</span><button className="log-button" type="submit" disabled={busy}>{busy ? 'Logging...' : 'Log interaction'}</button></div>

    {voiceDialogOpen && <div className="voice-overlay" role="dialog" aria-modal="true" aria-labelledby="voice-title"><section className="voice-dialog"><h2 id="voice-title">Summarize a Voice Note</h2><p>After you confirm consent, your browser will transcribe your speech and send the transcript to the AI service for a CRM summary. Do not record patient-identifiable or sensitive information without permission.</p><label className="consent-check"><input type="checkbox" checked={voiceConsent} onChange={e => setVoiceConsent(e.target.checked)} />I confirm I have consent to record and summarize this note.</label>{voiceStatus && <p className="voice-status">{voiceStatus}</p>}<div className="voice-actions"><button type="button" className="secondary" onClick={closeVoiceDialog}>{voiceComplete ? 'Close' : 'Cancel'}</button>{voiceComplete ? <button type="button" className="log-button" onClick={closeVoiceDialog}>OK</button> : <button type="button" className="log-button" disabled={!voiceConsent || listening} onClick={startVoiceNote}>{listening ? 'Listening...' : 'Start recording'}</button>}</div></section></div>}
  </form>
}