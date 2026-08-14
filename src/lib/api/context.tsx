import { createContext, useContext, type PropsWithChildren } from 'react'
import { apiClient, type OptiVestApi } from './client'

const ApiContext = createContext<OptiVestApi>(apiClient)

export function ApiProvider({ client = apiClient, children }: PropsWithChildren<{ client?: OptiVestApi }>) {
  return <ApiContext.Provider value={client}>{children}</ApiContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export const useApi = () => useContext(ApiContext)
