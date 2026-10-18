import { Link, useNavigate } from 'react-router-dom'
import { MAX_QTY_PER_LINE, useCart } from '../cart'

export default function CartPage() {
  const { items, subtotal, setQuantity, remove } = useCart()
  const navigate = useNavigate()

  if (items.length === 0) {
    return (
      <main className="page narrow">
        <h1>Your cart</h1>
        <p>Your cart is empty.</p>
        <Link to="/products" className="button">
          Start shopping
        </Link>
      </main>
    )
  }

  return (
    <main className="page narrow">
      <h1>Your cart</h1>
      <ul className="cart-list">
        {items.map((i) => (
          <li key={`${i.product_id}-${i.size}`} className="cart-line">
            <img src={i.image_url} alt="" />
            <div className="cart-line-info">
              <Link to={`/products/${i.product_id}`}>{i.name}</Link>
              <span>Size {i.size} · ${i.price.toFixed(2)} each</span>
            </div>
            <label className="cart-qty">
              <span className="visually-hidden">Quantity</span>
              <input
                type="number"
                min={1}
                max={MAX_QTY_PER_LINE}
                value={i.quantity}
                onChange={(e) => setQuantity(i.product_id, i.size, Number(e.target.value) || 1)}
              />
            </label>
            <strong className="cart-line-total">${(i.price * i.quantity).toFixed(2)}</strong>
            <button type="button" className="link-button" onClick={() => remove(i.product_id, i.size)}>
              Remove
            </button>
          </li>
        ))}
      </ul>

      <p className="cart-subtotal">
        Subtotal: <strong>${subtotal.toFixed(2)}</strong>
      </p>
      <p className="purchase-note">Stock is confirmed when you place your order.</p>
      <div className="purchase-buttons">
        <button type="button" className="button" onClick={() => navigate('/checkout')}>
          Checkout now
        </button>
        <button type="button" className="button button-secondary" onClick={() => navigate('/products')}>
          Continue shopping
        </button>
      </div>
    </main>
  )
}
