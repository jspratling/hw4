import { Link } from 'react-router-dom'
import type { Product } from '../types'

/** Problem 10: a slow-moving ticker of new and in-season arrivals under the hero. */
export default function ArrivalsTicker({ products }: { products: Product[] }) {
  if (products.length === 0) return null
  const items = products.map((p) => (
    <Link key={p.product_id} to={`/products/${p.product_id}`} className="ticker-item">
      <span className="ticker-name">{p.name}</span>
      <span className="ticker-price">${p.price.toFixed(0)}</span>
    </Link>
  ))
  return (
    <section className="ticker" aria-label="New arrivals">
      <p className="ticker-label">New arrivals</p>
      <div className="ticker-window">
        {/* The list is repeated so the loop is seamless; the copy is hidden from screen readers. */}
        <div className="ticker-track">
          <div className="ticker-group">{items}</div>
          <div className="ticker-group" aria-hidden="true">{items}</div>
        </div>
      </div>
    </section>
  )
}
