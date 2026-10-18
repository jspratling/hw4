import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { recordView, useAuth } from '../auth'
import PurchasePanel from '../components/PurchasePanel'
import ZoomImage from '../components/ZoomImage'
import { StockFreshness, useLiveStock } from '../liveStock'
import type { ProductDetail } from '../types'

export default function ProductDetailPage() {
  const { productId } = useParams()
  const [product, setProduct] = useState<ProductDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const { token } = useAuth()
  // Problem 9: price and stock re-checked every 30 seconds.
  const checkedAt = useLiveStock(product, setProduct)

  // Problem 8: remember the last product a logged-in shopper looked at.
  useEffect(() => {
    if (product) recordView(token, product.product_id)
  }, [product?.product_id, token]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    setProduct(null)
    setError(null)
    fetch(`/api/products/${encodeURIComponent(productId ?? '')}`)
      .then((res) => {
        if (res.status === 404) throw new Error('This product could not be found.')
        if (!res.ok) throw new Error(`Request failed: ${res.status}`)
        return res.json()
      })
      .then(setProduct)
      .catch((err) => setError(err.message))
  }, [productId])

  return (
    <main className="page">
      <Link to="/products" className="back-link">
        ← Back to products
      </Link>
      {error && <p className="error">{error}</p>}
      {!product && !error && <p>Loading…</p>}
      {product && (
        <div className="product-detail">
          <div className="detail-image">
            <ZoomImage src={product.image_url} alt={product.name} />
          </div>
          <div className="detail-text">
            <p className="garment-type">{product.garment_type}</p>
            <h1>{product.name}</h1>
            <p className="detail-price">${product.price.toFixed(2)}</p>
            <p>{product.description}</p>
            {product.colors.length > 0 && (
              <p>
                <strong>Colors:</strong> {product.colors.join(', ')}
              </p>
            )}

            <StockFreshness checkedAt={checkedAt} />
            <PurchasePanel product={product} />

            <h2>Sizes and stock</h2>
            {product.inventory.length === 0 ? (
              <p>No size information available.</p>
            ) : (
              <table className="stock-table">
                <thead>
                  <tr>
                    <th>Size</th>
                    <th>In stock</th>
                  </tr>
                </thead>
                <tbody>
                  {product.inventory.map((s) => (
                    <tr key={s.size} className={s.quantity === 0 ? 'sold-out' : undefined}>
                      <td>{s.size}</td>
                      <td>{s.quantity === 0 ? 'Sold out' : s.quantity}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <p className="total-stock">
              {product.total_stock > 0
                ? `${product.total_stock} total in stock`
                : 'Currently sold out in all sizes'}
            </p>
          </div>
        </div>
      )}
    </main>
  )
}
