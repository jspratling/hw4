import { useEffect, useRef, useState } from 'react'
import { useChatResults } from '../chatResults'
import ProductCard from './ProductCard'
import ProductQuickView from './ProductQuickView'
import ThemeBanner from './ThemeBanner'
import { useReveal } from '../reveal'

/**
 * Shows the chat agent's product matches on the main page (Problem 7).
 * Clicking a card opens a popup with the price, description and available sizes,
 * where the shopper can add to cart or go to checkout. The popup links to the full
 * single-item page from Problem 3.
 */
export default function ChatResultsPanel() {
  const { results, clear, logStep, theme, setTheme } = useChatResults()
  const gridRef = useReveal<HTMLDivElement>([results?.id])
  const [openId, setOpenId] = useState<string | null>(null)
  const ref = useRef<HTMLElement>(null)

  // Each new set of matches: scroll it into view and log that it reached the page.
  useEffect(() => {
    if (!results) return
    setOpenId(null)
    ref.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    logStep('shown_on_page')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [results?.id])

  if (!results) return null

  return (
    <section className="chat-results" ref={ref} aria-live="polite" aria-label="Matches from our chat">
      {theme && <ThemeBanner theme={theme} onClear={() => setTheme(null)} />}
      <div className="chat-results-header">
        <div>
          <p className="chat-results-label">Matches from our chat</p>
          <h2>“{results.question}”</h2>
          <p className="chat-results-count">
            {results.products.length} {results.products.length === 1 ? 'item' : 'items'} found · click
            any item to see sizes and add it to your cart
          </p>
        </div>
        <button type="button" className="chat-results-clear" onClick={clear}>
          Clear matches
        </button>
      </div>
      <div className="product-grid" ref={gridRef}>
        {results.products.map((p) => (
          <ProductCard
            key={p.product_id}
            product={p}
            short
            onOpen={() => {
              setOpenId(p.product_id)
              logStep('card_opened', { product_id: p.product_id })
            }}
          />
        ))}
      </div>
      {openId && <ProductQuickView productId={openId} onClose={() => setOpenId(null)} />}
    </section>
  )
}
