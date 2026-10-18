import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

export type CartItem = {
  product_id: string
  name: string
  price: number
  image_url: string
  size: string
  quantity: number
}

type CartState = {
  items: CartItem[]
  count: number
  subtotal: number
  add: (item: CartItem) => void
  setQuantity: (product_id: string, size: string, quantity: number) => void
  remove: (product_id: string, size: string) => void
  clear: () => void
}

export const MAX_QTY_PER_LINE = 10
const CART_KEY = 'campus-customs-cart'

const CartContext = createContext<CartState | null>(null)

function readCart(): CartItem[] {
  try {
    const raw = localStorage.getItem(CART_KEY)
    return raw ? (JSON.parse(raw) as CartItem[]) : []
  } catch {
    return []
  }
}

export function CartProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<CartItem[]>(readCart)

  useEffect(() => {
    try {
      localStorage.setItem(CART_KEY, JSON.stringify(items))
    } catch {
      // Storage unavailable: the cart still works for this tab.
    }
  }, [items])

  const same = (a: CartItem, product_id: string, size: string) =>
    a.product_id === product_id && a.size === size

  function add(item: CartItem) {
    setItems((current) => {
      const existing = current.find((i) => same(i, item.product_id, item.size))
      if (!existing) return [...current, { ...item, quantity: Math.min(item.quantity, MAX_QTY_PER_LINE) }]
      return current.map((i) =>
        same(i, item.product_id, item.size)
          ? { ...i, quantity: Math.min(i.quantity + item.quantity, MAX_QTY_PER_LINE) }
          : i,
      )
    })
  }

  function setQuantity(product_id: string, size: string, quantity: number) {
    setItems((current) =>
      current.map((i) =>
        same(i, product_id, size)
          ? { ...i, quantity: Math.max(1, Math.min(quantity, MAX_QTY_PER_LINE)) }
          : i,
      ),
    )
  }

  function remove(product_id: string, size: string) {
    setItems((current) => current.filter((i) => !same(i, product_id, size)))
  }

  const count = items.reduce((n, i) => n + i.quantity, 0)
  const subtotal = Math.round(items.reduce((s, i) => s + i.price * i.quantity, 0) * 100) / 100

  return (
    <CartContext.Provider
      value={{ items, count, subtotal, add, setQuantity, remove, clear: () => setItems([]) }}
    >
      {children}
    </CartContext.Provider>
  )
}

export function useCart(): CartState {
  const ctx = useContext(CartContext)
  if (!ctx) throw new Error('useCart must be used inside <CartProvider>')
  return ctx
}
