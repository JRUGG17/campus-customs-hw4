import { useEffect, useRef, useState, type SubmitEvent } from 'react'
import { Link, matchPath, useLocation, useNavigate } from 'react-router-dom'
import {
  fetchChatHistory,
  formatPrice,
  sendChatMessage,
  type ChatMessage,
  type HistoryMessage,
  type PageContext,
} from '../api'
import { useAuth } from '../auth'
import { useChatControl } from '../chatControl'
import { useChatResults } from '../chatResults'
import HandsomeDan from './HandsomeDan'

// `local` messages are widget notices, not real agent turns, so they're never sent as history.
const GREETING: ChatMessage = {
  role: 'assistant',
  content: "Woof! I'm Handsome Dan, the Campus Customs assistant. Ask me about styles, sizes, stock, or prices.",
  local: true,
}

const clock = (d: Date) => d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
const now = () => clock(new Date())

const fromHistory = (m: HistoryMessage): ChatMessage => ({
  role: m.role,
  content: m.content,
  products: m.products,
  productsOnPage: m.results_heading !== null && m.products.length > 0,
  // SQLite stores UTC as "YYYY-MM-DD HH:MM:SS"; show it in the shopper's local time.
  time: clock(new Date(m.created_at.replace(' ', 'T') + 'Z')),
})

export default function ChatWidget() {
  const [open, setOpen] = useState(false)
  // The launcher shows in full for a few seconds on a shopper's first page of the visit, then
  // tucks into a small Dan face at the screen edge so it doesn't cover the page.
  const [intro, setIntro] = useState(() => !sessionStorage.getItem('cc_dan_intro_seen'))
  useEffect(() => {
    if (!intro) return
    sessionStorage.setItem('cc_dan_intro_seen', '1')
    const timer = setTimeout(() => setIntro(false), 4000)
    return () => clearTimeout(timer)
  }, [intro])
  const [messages, setMessages] = useState<ChatMessage[]>([GREETING])
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)
  const { results, showResults } = useChatResults()
  const { user, loading } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  // Logged in: reload the saved chat from the database. Logged out / guest: start fresh.
  useEffect(() => {
    if (loading) return
    if (!user) {
      setMessages([GREETING])
      return
    }
    let cancelled = false
    fetchChatHistory()
      .then((saved) => {
        if (cancelled) return
        const welcome: ChatMessage = {
          role: 'assistant',
          local: true,
          content: saved.length
            ? `Welcome back, ${user.first_name}! Here's where we left off.`
            : `Hi ${user.first_name}! I'm Handsome Dan, the Campus Customs assistant. Our chats are saved to your account.`,
        }
        setMessages([...saved.map(fromHistory), welcome])
      })
      .catch(() => !cancelled && setMessages([GREETING]))
    return () => {
      cancelled = true
    }
  }, [user, loading])

  function pageContext(): PageContext {
    const product = matchPath('/products/:productId', location.pathname)
    const onProducts = location.pathname === '/products'
    return {
      path: location.pathname,
      product_id: product?.params.productId ?? null,
      visible_product_ids: onProducts && results ? results.products.map((p) => p.product_id) : [],
    }
  }

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, open])

  // Questions handed over from elsewhere on the site (search bar, empty filter results).
  const { request } = useChatControl()
  useEffect(() => {
    if (!request) return
    setOpen(true)
    void send(request.text)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [request])

  function handleSubmit(e: SubmitEvent<HTMLFormElement>) {
    e.preventDefault()
    void send(draft)
  }

  async function send(raw: string) {
    const text = raw.trim()
    if (!text || sending) return
    const history = messages.filter((m) => !m.local && !m.error)
    setMessages([...messages, { role: 'user', content: text, time: now() }])
    setDraft('')
    setSending(true)
    try {
      const { reply, results_heading, products } = await sendChatMessage(
        history,
        text,
        pageContext(),
      )
      const isSearch = results_heading !== null && products.length > 0
      if (isSearch) {
        // Search results go on the page; the chat bubble just carries the agent's summary.
        showResults({ heading: results_heading, query: text, products })
        if (location.pathname !== '/products') navigate('/products')
        window.scrollTo({ top: 0, behavior: 'smooth' })
      }
      setMessages((m) => [
        ...m,
        { role: 'assistant', content: reply, products, productsOnPage: isSearch, time: now() },
      ])
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: 'assistant', content: (err as Error).message, error: true, time: now() },
      ])
    } finally {
      setSending(false)
    }
  }

  if (!open) {
    return (
      <button
        className={`chat-launcher${intro ? ' intro' : ''}`}
        onClick={() => setOpen(true)}
        aria-label="Open chat with Handsome Dan"
      >
        <span className="chat-launcher-dan" aria-hidden="true">
          <HandsomeDan size={46} />
        </span>
        <span className="chat-launcher-text">
          Ask Dan
          <small>Sizes, stock &amp; prices</small>
        </span>
      </button>
    )
  }

  return (
    <section className="chat-panel" aria-label="Chat with Handsome Dan, the shop assistant">
      <header className="chat-header">
        <HandsomeDan size={40} className="chat-header-dan" />
        <span className="chat-header-text">
          Handsome Dan
          <small>
            <span className="online-dot" aria-hidden="true" /> Campus Customs assistant
          </small>
        </span>
        <button onClick={() => setOpen(false)} aria-label="Close chat">
          ×
        </button>
      </header>
      <div className="chat-messages">
        {messages.map((m, i) => (
          <div key={i} className={`chat-row ${m.role}`}>
            {m.role === 'assistant' && <HandsomeDan size={28} className="chat-avatar" />}
            <div className="chat-stack">
              <div className={`chat-bubble ${m.role}${m.error ? ' error' : ''}`}>
                {m.content}
                {m.products && m.products.length > 0 && !m.productsOnPage && (
                  <div className="chat-cards">
                    {m.products.map((p) => (
                      <Link key={p.product_id} to={`/products/${p.product_id}`} className="chat-card">
                        <img src={p.image_url} alt="" />
                        <span className="chat-card-text">
                          <strong>{p.name}</strong>
                          <span>{formatPrice(p.price)}</span>
                        </span>
                      </Link>
                    ))}
                  </div>
                )}
                {m.productsOnPage && m.products && (
                  <span className="chat-onpage-note">↖ {m.products.length} shown on the page</span>
                )}
              </div>
              {m.time && <span className="chat-time">{m.time}</span>}
            </div>
          </div>
        ))}
        {sending && (
          <div className="chat-row assistant">
            <HandsomeDan size={28} className="chat-avatar" />
            <div className="chat-bubble assistant typing" role="status">
              <span className="paws" aria-hidden="true">
                <span>🐾</span>
                <span>🐾</span>
                <span>🐾</span>
              </span>
              Dan is checking the stockroom…
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>
      <form className="chat-input" onSubmit={handleSubmit}>
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Ask Dan about merch…"
          aria-label="Chat message"
        />
        <button type="submit" disabled={!draft.trim() || sending}>
          Send
        </button>
      </form>
    </section>
  )
}
