import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, matchPath, useLocation, useNavigate } from 'react-router-dom'
import { errorMessage, useAuth } from '../auth'
import { useChatResults } from '../chatResults'
import type { ChatMemory, ChatProductCard, ChatReply } from '../types'

type ChatMessage = {
  role: 'user' | 'assistant'
  content: string
  followUp?: string
  products?: ChatProductCard[]
  suggestions?: string[] // Problem 8: quick-reply buttons
  isError?: boolean
  isNotice?: boolean // greetings and dividers: shown, but not sent to the agent
}

const HISTORY_LIMIT = 10

const WELCOME: ChatMessage = {
  role: 'assistant',
  content: 'Hi! I’m the Campus Customs assistant. Ask me about our merch, prices or sizes.',
  isNotice: true,
}

/** The page the shopper is on, sent with every chat message (Problem 8). */
function pageContext(pathname: string) {
  const match = matchPath('/products/:productId', pathname)
  return { path: pathname, product_id: match?.params.productId ?? null }
}

export default function ChatWidget() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const listRef = useRef<HTMLDivElement>(null)
  const chatResults = useChatResults()
  const theme = chatResults.theme
  const { user, token, loginCount } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()

  // Keep the newest message in view.
  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight })
  }, [messages, open])

  // Problem 8: when a shopper is logged in, reload their saved chat from the database and
  // add a "welcome back" message. When they log out, start a fresh guest chat.
  useEffect(() => {
    if (!user || !token) {
      setMessages([WELCOME])
      return
    }
    let cancelled = false
    fetch('/api/chat/history', { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => (res.ok ? res.json() : Promise.reject()))
      .then((memory: ChatMemory) => {
        if (cancelled) return
        const saved: ChatMessage[] = memory.messages.map((m) => ({
          role: m.role,
          content: m.content,
          products: m.products,
        }))
        setMessages([
          ...(saved.length > 0
            ? [{ role: 'assistant' as const, content: 'Your saved chat', isNotice: true }, ...saved]
            : []),
          {
            role: 'assistant',
            content: memory.welcome_back,
            products: memory.recalled_product ? [memory.recalled_product] : [],
            suggestions: memory.suggestions,
            isNotice: true,
          },
        ])
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [user?.id, token]) // eslint-disable-line react-hooks/exhaustive-deps

  // Open the chat right after logging in, so the shopper sees where they left off.
  useEffect(() => {
    if (loginCount > 0) setOpen(true)
  }, [loginCount])

  async function sendText(text: string) {
    if (!text || sending) return

    // Guests: earlier turns from this tab give the agent context. Logged-in shoppers:
    // the backend loads their saved history from the database instead.
    const history = messages
      .filter((m) => !m.isNotice && !m.isError)
      .slice(-HISTORY_LIMIT)
      .map(({ role, content, followUp }) => ({
        role,
        content: followUp ? `${content}\n\n${followUp}` : content,
      }))

    setMessages((m) => [
      ...m.map((x) => ({ ...x, suggestions: undefined })), // answered: hide old buttons
      { role: 'user', content: text },
    ])
    setInput('')
    setSending(true)
    try {
      const page = pageContext(location.pathname)
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        // Problem 10: the theme on screen keeps the chat persona for follow-up questions.
        body: JSON.stringify({ message: text, history, page, theme_key: theme?.key ?? null }),
      })
      if (!res.ok) throw new Error(await errorMessage(res))
      const data: ChatReply = await res.json()

      // Problem 10: a sport or field-of-study search switches the page theme and chat persona;
      // a new general search (several unthemed results) goes back to the classic look.
      if (data.theme) chatResults.setTheme(data.theme)
      else if (data.products.length > 1) chatResults.setTheme(null)

      // Problem 7: put the agent's product matches on the main page, not just in the chat.
      // The Home and Products pages show them; from any other page, go to Home to see them.
      // Problem 8: a question about the product page they are on ("this in pink?") that only
      // brings back that same product keeps them on the page.
      const onlyThisProduct =
        page.product_id !== null && data.products.every((p) => p.product_id === page.product_id)
      if (data.products.length > 0 && !onlyThisProduct) {
        chatResults.show(text, data.products, data.search_id ?? null)
        if (location.pathname !== '/' && location.pathname !== '/products') navigate('/')
      }
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          content: data.reply,
          followUp: data.follow_up_question ?? undefined,
          products: data.products,
        },
      ])
    } catch (err) {
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          content: err instanceof Error ? err.message : 'Sorry, I couldn’t reach the server. Please try again.',
          isError: true,
        },
      ])
    } finally {
      setSending(false)
    }
  }

  function send(e: FormEvent) {
    e.preventDefault()
    sendText(input.trim())
  }

  if (!open) {
    return (
      <button className="chat-launcher" onClick={() => setOpen(true)} aria-label="Open chat">
        <span className="launcher-dot" aria-hidden="true" />
        {theme ? `Chat with ${theme.persona}` : 'Ask a Bulldog'}
      </button>
    )
  }

  return (
    <section className={theme ? `chat-panel themed theme-${theme.kind}` : 'chat-panel'} aria-label="Campus Customs chat">
      <header className="chat-header">
        <span className="chat-avatar" aria-hidden="true">
          {theme ? theme.persona.replace(/^(Coach|Dr\.|Maestro|Reverend) /, '').slice(0, 1) : 'CC'}
        </span>
        <span className="chat-who">
          <span className="chat-name">{theme ? theme.persona : 'Campus Customs'}</span>
          <span className="chat-role">
            {theme
              ? `${theme.persona_role[0].toUpperCase()}${theme.persona_role.slice(1)}, ${theme.label}`
              : user
                ? `Your campus shop assistant for ${user.first_name}`
                : 'Your campus shop assistant'}
          </span>
        </span>
        <button onClick={() => setOpen(false)} aria-label="Close chat">
          ×
        </button>
      </header>

      <div className="chat-messages" ref={listRef}>
        {messages.map((m, i) =>
          m.isNotice && m.content === 'Your saved chat' ? (
            <p key={i} className="chat-divider">
              Your saved chat
            </p>
          ) : (
            <div key={i} className={`chat-bubble ${m.role}`}>
              <p>
                {/* Problem 10: with a theme on screen, the greeting comes from the persona. */}
                {m === WELCOME && theme
                  ? `Hi! I'm ${theme.persona}, ${theme.persona_role}. Ask me anything about ${theme.label} gear: prices, sizes or what's in stock.`
                  : m.content}
              </p>
              {m.products && m.products.length > 0 && (
                <div className="chat-products">
                  {m.products.map((p) => (
                    <Link key={p.product_id} to={`/products/${p.product_id}`} className="chat-product">
                      <img src={p.image_url} alt={p.name} />
                      <span className="chat-product-text">
                        <span>{p.name}</span>
                        <span className={p.in_stock ? 'chat-product-stock' : 'chat-product-stock sold-out'}>
                          {p.in_stock ? `In stock: ${p.sizes_in_stock.join(', ')}` : 'Sold out'}
                        </span>
                      </span>
                      <strong>${p.price.toFixed(2)}</strong>
                    </Link>
                  ))}
                </div>
              )}
              {m.followUp && <p className="chat-follow-up">{m.followUp}</p>}
              {m.suggestions && m.suggestions.length > 0 && (
                <div className="chat-suggestions">
                  {m.suggestions.map((s) => (
                    <button key={s} type="button" disabled={sending} onClick={() => sendText(s)}>
                      {s}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ),
        )}
        {sending && <div className="chat-bubble assistant typing">{theme ? `${theme.persona} is typing…` : 'Typing…'}</div>}
        {!user && (
          <p className="chat-guest-note">
            Chatting as a guest. <Link to="/login">Log in</Link> to save your chat.
          </p>
        )}
      </div>

      <form className="chat-input" onSubmit={send}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about merch…"
          aria-label="Chat message"
        />
        <button type="submit" disabled={sending || !input.trim()}>
          Send
        </button>
      </form>
    </section>
  )
}
