import { useContext } from 'react'
import { SessionContext } from './SessionContext'

export function useSession() {
  return useContext(SessionContext)
}
