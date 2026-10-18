import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { recordView, useAuth } from '../auth'
import { useCart } from '../cart'
import { useChatResults } from '../chatResults'
import type { ProductDetail } from '../types'
import PurchasePanel from './PurchasePanel'
import ZoomImage from './ZoomImage'
import { StockFreshness, useLiveStock } from '../liveStock'

/**
 * Popup for a product card the chat put on the page (Problem 7, Panel B).
 * Shows the large image, price, full description and the sizes available, with
 * Add to cart and Go to checkout. Data comes from GET /api/products/{product_id},
 * the same route the single-item page uses, so stock is always current.
 */
export default function ProductQuickView({ productId, onClose }: { productId: string; onClose: () => void }) {
  const [product, setProduct] = useState<ProductDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const { count } = useCart()
  const { logStep } = useChatResults()
  const navigate = useNavigate()
  const { token } = useAuth()
  // Problem 9: price and stock re-checked every 30 seconds.
  const checkedAt = useLiveStock(product, setProduct)

  // Problem 8: opening the popup counts as looking at the product.
  useEffect(() => {
    if (product) recordView(token, product.product_id)
  }, [product?.product_id, token]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    setProduct(null)
    setError(null)
    fetch(`/api/products/${encodeURIComponent(productId)}`)
      .then((res) => {
        if (!res.ok) throw new Error('This product could not be loaded.')
        return res.json()
      })
      .then(setProduct)
      .catch((err) => setError(err.message))
  }, [productId])

  // Close with the Escape key.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  function goToCheckout() {
    logStep('go_to_checkout', { product_id: productId })
    navigate('/checkout')
  }

  const available = product?.inventory.filter((s) => s.quantity > 0).map((s) => s.size) ?? []
  const soldOut = product?.inventory.filter((s) => s.quantity === 0).map((s) => s.size) ?? []

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="modal quick-view"
        role="dialog"
        aria-modal="true"
        aria-label={product?.name ?? 'Product'}
        onClick={(e) => e.stopPropagation()}
      >
        <button type="button" className="quick-view-close" onClick={onClose} aria-label="Close">
          ×
        </button>
        {error && <p className="error">{error}</p>}
        {!product && !error && <p>Loading…</p>}
        {product && (
          <div className="quick-view-body">
            <div className="quick-view-image">
              <ZoomImage src={product.image_url} alt={product.name} />
            </div>
            <div className="quick-view-text">
              <p className="garment-type">{product.garment_type}</p>
              <h2>{product.name}</h2>
              <p className="detail-price">${product.price.toFixed(2)}</p>
              <p className="quick-view-description">{product.description}</p>
              <p className="quick-view-sizes">
                <strong>Sizes available:</strong>{' '}
                {available.length > 0 ? available.join(', ') : 'Sold out in all sizes'}
                {soldOut.length > 0 && available.length > 0 && (
                  <span className="quick-view-soldout"> · Sold out: {soldOut.join(', ')}</span>
                )}
              </p>

              <StockFreshness checkedAt={checkedAt} />
              <PurchasePanel
                product={product}
                onAdded={(size, quantity) =>
                  logStep('added_to_cart', { product_id: product.product_id, size, quantity })
                }
                onCheckout={() => logStep('go_to_checkout', { product_id: product.product_id })}
                onContinueShopping={onClose}
              />

              <div className="quick-view-footer">
                {count > 0 && (
                  <button type="button" className="button" onClick={goToCheckout}>
                    Go to checkout ({count})
                  </button>
                )}
                <Link
                  to={`/products/${product.product_id}`}
                  className="quick-view-full-link"
                  onClick={() => logStep('full_page_opened', { product_id: product.product_id })}
                >
                  View full item page →
                </Link>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
