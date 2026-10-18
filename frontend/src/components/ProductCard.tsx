import type { MouseEvent } from 'react'
import { Link } from 'react-router-dom'
import type { Product } from '../types'

const SHORT_DESCRIPTION_LENGTH = 100

/** First sentence of the description, cut to about 100 characters (Problem 7). */
export function shortDescription(text: string): string {
  const firstSentence = text.split(/(?<=[.!?])\s/)[0].trim()
  if (firstSentence.length <= SHORT_DESCRIPTION_LENGTH) return firstSentence
  return firstSentence.slice(0, SHORT_DESCRIPTION_LENGTH).replace(/\s+\S*$/, '') + '…'
}

type Props = {
  product: Product
  /** Cards the chat put on the page show a short description (Problem 7). */
  short?: boolean
  /** If given, a plain click opens a popup instead of the single-item page (Problem 7).
   *  Ctrl/Cmd-click or middle-click still opens the single-item page. */
  onOpen?: () => void
  /** Extra line under the price, e.g. why it was recommended (Problem 9). */
  note?: string
}

export default function ProductCard({ product, short, onOpen, note }: Props) {
  function handleClick(e: MouseEvent<HTMLAnchorElement>) {
    if (!onOpen || e.ctrlKey || e.metaKey || e.shiftKey || e.button !== 0) return
    e.preventDefault()
    onOpen()
  }

  // Problem 9: labels from the backend's metadata tags.
  const soldOut = product.total_stock === 0
  const badges = [
    soldOut ? { text: 'Sold out', kind: 'sold-out' } : null,
    // Most fall items are in season in autumn, so only game-day picks get a label.
    product.in_season && !soldOut && product.seasons?.includes('Game day') ? { text: 'Game day', kind: 'season' } : null,
    product.style === 'Formal' ? { text: 'Formal', kind: 'style' } : null,
    product.brand && product.brand !== 'Campus Customs' ? { text: product.brand, kind: 'brand' } : null,
  ].filter((b): b is { text: string; kind: string } => b !== null)

  return (
    <Link to={`/products/${product.product_id}`} className="product-card" onClick={handleClick}>
      <div className="card-image">
        <img src={product.image_url} alt={product.name} loading="lazy" />
        {badges.length > 0 && (
          <div className="card-badges">
            {badges.map((b) => (
              <span key={b.text} className={`card-badge ${b.kind}`}>
                {b.text}
              </span>
            ))}
          </div>
        )}
      </div>
      <div className="product-info">
        <h2>{product.name}</h2>
        <p className="price">${product.price.toFixed(2)}</p>
        {note && <p className="card-note">{note}</p>}
        <p className="description">
          {short ? shortDescription(product.description) : product.description}
        </p>
      </div>
    </Link>
  )
}
