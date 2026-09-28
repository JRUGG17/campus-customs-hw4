import { createContext, useContext, useState, type ReactNode } from 'react'

/** Lets any part of the site open the chat, or hand it a question (search bar, empty results). */
interface ChatControl {
  request: { text: string; id: number } | null // text '' = just open the chat
  askAssistant: (text: string) => void
  openAssistant: () => void
}

const ChatControlContext = createContext<ChatControl | null>(null)

export function ChatControlProvider({ children }: { children: ReactNode }) {
  const [request, setRequest] = useState<ChatControl['request']>(null)
  const askAssistant = (text: string) => setRequest({ text, id: Date.now() })
  const openAssistant = () => setRequest({ text: '', id: Date.now() })
  return (
    <ChatControlContext.Provider value={{ request, askAssistant, openAssistant }}>
      {children}
    </ChatControlContext.Provider>
  )
}

export function useChatControl(): ChatControl {
  const ctx = useContext(ChatControlContext)
  if (!ctx) throw new Error('useChatControl must be used inside <ChatControlProvider>')
  return ctx
}
