import { useAppDispatch, useAppSelector } from '../hooks'
import { setMode } from '../store/crmSlice'
export function ModeToggle() { const mode=useAppSelector(s=>s.crm.mode), dispatch=useAppDispatch(); return <div className="mode-toggle" role="tablist"><button className={mode==='form'?'active':''} onClick={()=>dispatch(setMode('form'))}>Structured form</button><button className={mode==='chat'?'active':''} onClick={()=>dispatch(setMode('chat'))}>AI conversation</button></div> }
