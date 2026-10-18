import { useEffect, useState } from 'react'
import type { LiveStock, ProductDetail } from './types'

const REFRESH_MS = 30_000

/**
 * Problem 9: keep a product's price and stock up to the minute.
 * Re-checks GET /api/products/{id}/stock every 30 seconds and whenever the shopper comes
 * back to the tab, and merges the fresh numbers into the product shown on screen.
 */
export function useLiveStock(
  product: ProductDetail | null,
  setProduct: (update: (p: ProductDetail | null) => ProductDetail | null) => void,
): Date | null {
  const [checkedAt, setCheckedAt] = useState<Date | null>(null)
  const productId = product?.product_id

  useEffect(() => {
    if (!productId) return
    let cancelled = false
    setCheckedAt(new Date())

    async function refresh() {
      try {
        const res = await fetch(`/api/products/${encodeURIComponent(productId!)}/stock`, { cache: 'no-store' })
        if (!res.ok || cancelled) return
        const live: LiveStock = await res.json()
        setProduct((p) =>
          p && p.product_id === live.product_id
            ? { ...p, price: live.price, inventory: live.inventory, total_stock: live.total_stock }
            : p,
        )
        setCheckedAt(new Date(live.checked_at))
      } catch {
        // Keep showing the last numbers; the next refresh will try again.
      }
    }

    const timer = window.setInterval(refresh, REFRESH_MS)
    const onVisible = () => document.visibilityState === 'visible' && refresh()
    document.addEventListener('visibilitychange', onVisible)
    window.addEventListener('focus', refresh)
    return () => {
      cancelled = true
      window.clearInterval(timer)
      document.removeEventListener('visibilitychange', onVisible)
      window.removeEventListener('focus', refresh)
    }
  }, [productId]) // eslint-disable-line react-hooks/exhaustive-deps

  return checkedAt
}

/** "Stock checked just now" / "Stock checked 20 seconds ago", kept up to date. */
export function StockFreshness({ checkedAt }: { checkedAt: Date | null }) {
  const [, tick] = useState(0)
  useEffect(() => {
    const t = window.setInterval(() => tick((n) => n + 1), 5000)
    return () => window.clearInterval(t)
  }, [])
  if (!checkedAt) return null
  const seconds = Math.max(0, Math.round((Date.now() - checkedAt.getTime()) / 1000))
  const ago = seconds < 10 ? 'just now' : seconds < 60 ? `${seconds} seconds ago` : `${Math.round(seconds / 60)} min ago`
  return (
    <p className="stock-freshness" aria-live="polite">
      <span className="live-dot" aria-hidden="true" /> Live stock and price · checked {ago}
    </p>
  )
}
