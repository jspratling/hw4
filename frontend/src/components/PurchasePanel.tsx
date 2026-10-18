import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { MAX_QTY_PER_LINE, useCart } from '../cart'
import type { ProductDetail } from '../types'

type Props = {
  product: ProductDetail
  /** Optional hooks used by the chat item popup (Problem 7) to log the search path. */
  onAdded?: (size: string, quantity: number) => void
  onCheckout?: () => void
  /** If given, "Continue shopping" calls this (e.g. close the popup) instead of going to Products. */
  onContinueShopping?: () => void
}

/** Size picker, quantity, Add to cart and Buy now for the single-item page and the chat item popup. */
export default function PurchasePanel({ product, onAdded, onCheckout, onContinueShopping }: Props) {
  const { add, items } = useCart()
  const navigate = useNavigate()
  const [size, setSize] = useState<string | null>(null)
  const [quantity, setQuantity] = useState(1)
  const [added, setAdded] = useState<{ size: string; quantity: number } | null>(null)

  const stockFor = (s: string) => product.inventory.find((i) => i.size === s)?.quantity ?? 0
  const inCart = size
    ? items.find((i) => i.product_id === product.product_id && i.size === size)?.quantity ?? 0
    : 0
  const maxQty = size ? Math.max(0, Math.min(stockFor(size) - inCart, MAX_QTY_PER_LINE)) : 1
  const soldOut = product.total_stock === 0

  function addToCart() {
    if (!size || maxQty < 1) return null
    const qty = Math.min(quantity, maxQty)
    add({
      product_id: product.product_id,
      name: product.name,
      price: product.price,
      image_url: product.image_url,
      size,
      quantity: qty,
    })
    onAdded?.(size, qty)
    return { size, quantity: qty }
  }

  if (soldOut) {
    return <p className="purchase-note">This item is sold out in every size.</p>
  }

  return (
    <div className="purchase-panel">
      <p className="purchase-label">Choose a size</p>
      <div className="size-picker" role="radiogroup" aria-label="Size">
        {product.inventory.map((s) => (
          <button
            key={s.size}
            type="button"
            role="radio"
            aria-checked={size === s.size}
            className={size === s.size ? 'size-option selected' : 'size-option'}
            disabled={s.quantity === 0}
            title={s.quantity === 0 ? 'Sold out' : `${s.quantity} in stock`}
            onClick={() => {
              setSize(s.size)
              setQuantity(1)
            }}
          >
            {s.size}
          </button>
        ))}
      </div>

      <label className="qty-label">
        Quantity
        <input
          type="number"
          min={1}
          max={Math.max(maxQty, 1)}
          value={quantity}
          disabled={!size || maxQty < 1}
          onChange={(e) => setQuantity(Math.max(1, Math.min(Number(e.target.value) || 1, maxQty || 1)))}
        />
      </label>
      {size && maxQty < 1 && (
        <p className="purchase-note">You already have all available {size} stock in your cart.</p>
      )}

      <div className="purchase-buttons">
        <button
          type="button"
          className="button"
          disabled={!size || maxQty < 1}
          onClick={() => {
            setAdded(addToCart())
          }}
        >
          Add to cart
        </button>
        <button
          type="button"
          className="button button-secondary"
          disabled={!size || maxQty < 1}
          onClick={() => {
            addToCart()
            onCheckout?.()
            navigate('/checkout')
          }}
        >
          Buy now
        </button>
      </div>
      {!size && <p className="purchase-note">Pick a size to add this item to your cart.</p>}

      {added && (
        <div className="modal-backdrop" role="presentation" onClick={() => setAdded(null)}>
          <div
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="added-title"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 id="added-title">Added to your cart</h2>
            <div className="modal-item">
              <img src={product.image_url} alt="" />
              <div>
                <strong>{product.name}</strong>
                <p>
                  Size {added.size} · Qty {added.quantity} · ${product.price.toFixed(2)} each
                </p>
              </div>
            </div>
            <p>Would you like to check out now or keep shopping?</p>
            <div className="purchase-buttons">
              <button
                type="button"
                className="button"
                onClick={() => {
                  onCheckout?.()
                  navigate('/checkout')
                }}
              >
                Checkout now
              </button>
              <button
                type="button"
                className="button button-secondary"
                onClick={() => {
                  setAdded(null)
                  if (onContinueShopping) onContinueShopping()
                  else navigate('/products')
                }}
              >
                Continue shopping
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
