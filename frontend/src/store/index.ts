import { configureStore } from '@reduxjs/toolkit'
import crm from './crmSlice'
export const store = configureStore({ reducer: { crm } })
export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
