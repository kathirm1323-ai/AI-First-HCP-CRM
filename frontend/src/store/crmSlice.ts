import { createAsyncThunk, createSlice, type PayloadAction } from '@reduxjs/toolkit'
import { createInteraction, fetchHcps, fetchInteractions } from '../services/api'
import type { Draft, Interaction, Message, Mode } from '../types'

const emptyDraft = (): Draft => ({ hcp_name: '', occurred_at: '', interaction_type: 'visit', products: [], notes: '', samples_distributed: '', sentiment: '', follow_up_action: '', follow_up_due_at: '' })
export const loadDashboard = createAsyncThunk('crm/load', async () => ({ interactions: await fetchInteractions(), hcps: await fetchHcps() }))
export const saveDraft = createAsyncThunk('crm/save', createInteraction)
type State = { mode: Mode; draft: Draft; messages: Message[]; interactions: Interaction[]; hcps: { id:number; name:string }[]; busy: boolean; error?: string }
const initialState: State = { mode: 'form', draft: emptyDraft(), messages: [{ id:'welcome', role:'assistant', content:'Tell me about an HCP interaction in your own words. I’ll turn it into a reviewable record before anything is saved.' }], interactions: [], hcps: [], busy: false }
const slice = createSlice({ name: 'crm', initialState, reducers: {
  setMode: (s, a: PayloadAction<Mode>) => { s.mode = a.payload },
  patchDraft: (s, a: PayloadAction<Partial<Draft>>) => { s.draft = { ...s.draft, ...a.payload } },
  resetDraft: s => { s.draft = emptyDraft() },
  addMessage: (s, a: PayloadAction<Message>) => { s.messages.push(a.payload) },
  clearConfirmations: s => {
    s.messages.forEach(message => {
      message.requiresConfirmation = false
    })
  },
}, extraReducers: builder => builder
  .addCase(loadDashboard.fulfilled, (s,a) => { s.interactions=a.payload.interactions; s.hcps=a.payload.hcps })
  .addCase(saveDraft.pending, s => { s.busy=true; s.error=undefined })
  .addCase(saveDraft.fulfilled, (s,a) => { s.busy=false; s.interactions.unshift(a.payload); s.draft=emptyDraft() })
  .addCase(saveDraft.rejected, (s,a) => { s.busy=false; s.error=a.error.message ?? 'Could not save interaction' }) })
export const { setMode, patchDraft, resetDraft, addMessage, clearConfirmations } = slice.actions
export default slice.reducer
