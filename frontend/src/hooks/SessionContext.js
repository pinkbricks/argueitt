import { createContext } from 'react'

// Kept apart from the provider component so fast refresh doesn't choke on a
// module that exports both a component and a value.
export const SessionContext = createContext({
  user: null,
  status: 'loading',
  signIn: () => {},
  signOut: () => {},
})
