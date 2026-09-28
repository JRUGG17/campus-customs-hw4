import { createContext, useContext, useState, type ReactNode } from 'react'

/** Lets any part of the site (search bar, empty filter results) hand a question to the chat. */
interface ChatControl {
  request: { text: string; id: number } | null
  askAssistant: (text: string) => void
}

const ChatControlContext = createContext<ChatControl | null>(null)

export function ChatControlProvider({ children }: { children: ReactNode }) {
  const [request, setRequest] = useState<ChatControl['request']>(null)
  const askAssistant = (text: string) => setRequest({ text, id: Date.now() })
  return (
    <ChatControlContext.Provider value={{ request, askAssistant }}>{children}</ChatControlContext.Provider>
  )
}

export function useChatControl(): ChatControl {
  const ctx = useContext(ChatControlContext)
  if (!ctx) throw new Error('useChatControl must be used inside <ChatControlProvider>')
  return ctx
}
