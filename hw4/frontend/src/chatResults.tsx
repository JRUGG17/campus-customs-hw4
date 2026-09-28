import { createContext, useContext, useState, type ReactNode } from 'react'
import type { ProductSummary } from './api'

/** Products the chat agent found for a search, shown as cards on the Products page. */
export interface ChatResults {
  heading: string
  query: string // the shopper message that produced these results
  products: ProductSummary[]
}

interface ChatResultsState {
  results: ChatResults | null
  showResults: (results: ChatResults) => void
  clearResults: () => void
}

const STORAGE_KEY = 'cc_chat_results'
const ChatResultsContext = createContext<ChatResultsState | null>(null)

function loadSaved(): ChatResults | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as ChatResults) : null
  } catch {
    return null
  }
}

export function ChatResultsProvider({ children }: { children: ReactNode }) {
  // Kept in sessionStorage so results survive opening a product and coming back, or a refresh.
  const [results, setResults] = useState<ChatResults | null>(loadSaved)

  const value: ChatResultsState = {
    results,
    showResults: (r) => {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(r))
      setResults(r)
    },
    clearResults: () => {
      sessionStorage.removeItem(STORAGE_KEY)
      setResults(null)
    },
  }

  return <ChatResultsContext.Provider value={value}>{children}</ChatResultsContext.Provider>
}

export function useChatResults(): ChatResultsState {
  const ctx = useContext(ChatResultsContext)
  if (!ctx) throw new Error('useChatResults must be used inside <ChatResultsProvider>')
  return ctx
}
