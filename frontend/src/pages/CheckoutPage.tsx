import { useState } from 'react'
import { Link } from 'react-router-dom'
import { errorMessage, useAuth } from '../auth'
import { useCart } from '../cart'

type OrderResult = {
  order_id: number
  total: number
  created_at: string
  items: { product_id: string; name: string; size: string; quantity: number; unit_price: number; line_total: number }[]
  inventory_check: { passed: boolean } | null
}

export default function CheckoutPage() {
  const { user, token } = useAuth()
  const { items, subtotal, clear } = useCart()
  const [placing, setPlacing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [order, setOrder] = useState<OrderResult | null>(null)

  async function placeOrder() {
    setPlacing(true)
    setError(null)
    try {
      const res = await fetch('/api/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          items: items.map(({ product_id, size, quantity }) => ({ product_id, size, quantity })),
        }),
      })
      if (!res.ok) throw new Error(await errorMessage(res))
      setOrder(await res.json())
      clear()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not place your order.')
    } finally {
      setPlacing(false)
    }
  }

  if (order) {
    return (
      <main className="page narrow">
        <h1>Thank you for your order!</h1>
        <p className="form-success">
          Order #{order.order_id} is confirmed. Total: <strong>${order.total.toFixed(2)}</strong>
        </p>
        <ul className="order-summary">
          {order.items.map((i) => (
            <li key={`${i.product_id}-${i.size}`}>
              {i.quantity} × {i.name} (size {i.size}) — ${i.line_total.toFixed(2)}
            </li>
          ))}
        </ul>
        {order.inventory_check && (
          <p className="purchase-note">
            Inventory check after purchase: {order.inventory_check.passed ? 'passed ✓' : 'needs review'}
          </p>
        )}
        <Link to="/products" className="button">
          Continue shopping
        </Link>
      </main>
    )
  }

  if (items.length === 0) {
    return (
      <main className="page narrow">
        <h1>Checkout</h1>
        <p>Your cart is empty.</p>
        <Link to="/products" className="button">
          Start shopping
        </Link>
      </main>
    )
  }

  return (
    <main className="page narrow">
      <h1>Checkout</h1>
      <ul className="order-summary">
        {items.map((i) => (
          <li key={`${i.product_id}-${i.size}`}>
            {i.quantity} × {i.name} (size {i.size}) — ${(i.price * i.quantity).toFixed(2)}
          </li>
        ))}
      </ul>
      <p className="cart-subtotal">
        Total: <strong>${subtotal.toFixed(2)}</strong>
      </p>

      {!user ? (
        <p className="form-notice">
          Please <Link to="/login" state={{ from: '/checkout' }}>log in</Link> or{' '}
          <Link to="/register">create an account</Link> to place your order. Your cart will be saved.
        </p>
      ) : (
        <>
          <p className="purchase-note">
            Ordering as {user.first_name} {user.last_name} ({user.email}). This is a class project
            store, so no payment is collected.
          </p>
          {error && <p className="form-error">{error}</p>}
          <div className="purchase-buttons">
            <button type="button" className="button" onClick={placeOrder} disabled={placing}>
              {placing ? 'Placing order…' : 'Place order'}
            </button>
            <Link to="/cart" className="button button-secondary">
              Back to cart
            </Link>
          </div>
        </>
      )}
    </main>
  )
}
