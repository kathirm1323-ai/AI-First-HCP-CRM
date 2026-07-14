import axios from 'axios'
import type { Draft, Interaction } from '../types'
const api = axios.create({ baseURL: import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8002' })
export const fetchInteractions = async (q?: string) => (await api.get<Interaction[]>('/interactions', { params: q ? { q } : {} })).data
export const fetchHcps = async () => (await api.get('/hcps')).data
export const createInteraction = async (draft: Draft) => (await api.post<Interaction>('/interactions', { ...draft, occurred_at: new Date(draft.occurred_at).toISOString(), products: draft.products, sentiment: draft.sentiment || null, samples_distributed: draft.samples_distributed || null, follow_up_action: draft.follow_up_action || null, follow_up_due_at: draft.follow_up_due_at ? new Date(draft.follow_up_due_at).toISOString() : null })).data
export const sendChat = async (session_id: string, message: string, draft_context?: Draft) => (await api.post('/chat', { session_id, message, draft_context })).data

export const summarizeVoiceNote = async (transcript: string) => (await api.post<{ summary: string }>('/voice/summarize', { transcript })).data
