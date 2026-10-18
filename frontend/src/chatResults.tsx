import { createContext, useContext, useState, type ReactNode } from 'react'
import type { ChatProductCard, Theme } from './types'

/**
 * Shared store for the products the chat agent found (Problem 7).
 *
 * The chat widget calls show() with the `products` and `search_id` from POST /api/chat.
 * The Home and Products pages read `results` and render those matches as product cards
 * on the main page, not just inside the chat window.
 */
export type ChatResults = {
  question: string
  products: ChatProductCard[]
  searchId: string | null // id of this search in backend/logs/search_path.jsonl
  id: number // changes on every new search so pages can scroll to the new results
}

export type PathEvent = 'shown_on_page' | 'card_opened' | 'added_to_cart' | 'go_to_checkout' | 'full_page_opened'

type PathDetail = { page?: string; product_id?: string; size?: string; quantity?: number }

type ChatResultsState = {
  results: ChatResults | null
  show: (question: string, products: ChatProductCard[], searchId: string | null) => void
  clear: () => void
  /** Add a step to this search's path log (POST /api/search-path/{search_id}/events). */
  logStep: (event: PathEvent, detail?: PathDetail) => void
  /** Problem 10: sport or field-of-study theme of the latest search (banner + chat persona). */
  theme: Theme | null
  setTheme: (theme: Theme | null) => void
}

const ChatResultsContext = createContext<ChatResultsState | null>(null)

export function ChatResultsProvider({ children }: { children: ReactNode }) {
  const [results, setResults] = useState<ChatResults | null>(null)
  const [theme, setTheme] = useState<Theme | null>(null)

  function show(question: string, products: ChatProductCard[], searchId: string | null) {
    setResults({ question, products, searchId, id: Date.now() })
  }

  function logStep(event: PathEvent, detail: PathDetail = {}) {
    if (!results?.searchId) return
    const body = { event, page: window.location.pathname, ...detail }
    // Logging must never get in the shopper's way, so failures are ignored.
    fetch(`/api/search-path/${results.searchId}/events`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      keepalive: true,
    }).catch(() => {})
  }

  return (
    <ChatResultsContext.Provider value={{ results, show, clear: () => setResults(null), logStep, theme, setTheme }}>
      {children}
    </ChatResultsContext.Provider>
  )
}

export function useChatResults(): ChatResultsState {
  const ctx = useContext(ChatResultsContext)
  if (!ctx) throw new Error('useChatResults must be used inside <ChatResultsProvider>')
  return ctx
}
