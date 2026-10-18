export type Product = {
  product_id: string
  name: string
  garment_type: string
  description: string
  colors: string[]
  price: number
  image_url: string
  // Problem 9: metadata tags from the backend (backend/tagging.py) and live stock.
  category?: string
  brand?: string
  style?: 'Casual' | 'Formal'
  color_groups?: string[]
  seasons?: string[]
  in_season?: boolean
  sizes_in_stock?: string[]
  total_stock?: number
}

/** A tailored pick from GET /api/me/recommendations (Problem 9). */
export type Recommendation = Product & {
  reason: string
  sizes_in_stock: string[]
}

/** Response from GET /api/products/{id}/stock (Problem 9). */
export type LiveStock = {
  product_id: string
  price: number
  inventory: StockLevel[]
  total_stock: number
  checked_at: string
}

export type StockLevel = {
  size: string
  quantity: number
}

export type ProductDetail = Product & {
  inventory: StockLevel[]
  total_stock: number
}

/** Product card attached to a chat reply (see ProductCard in backend/models.py). */
export type ChatProductCard = ProductDetail & {
  in_stock: boolean
  sizes_in_stock: string[]
  low_stock_sizes: string[]
}

/** Response from POST /api/chat (see ChatResponse in backend/models.py). */
export type ChatReply = {
  reply: string
  follow_up_question: string | null
  products: ChatProductCard[]
  /** Id of this search in backend/logs/search_path.jsonl (Problem 7). */
  search_id: string | null
  /** Problem 10: theme for the page banner and the chat persona. */
  theme?: Theme | null
}

/** A saved chat message from GET /api/chat/history (Problem 8). */
export type SavedChatMessage = {
  role: 'user' | 'assistant'
  content: string
  products: ChatProductCard[]
  created_at: string
}

/** Response from GET /api/chat/history (see ChatMemory in backend/memory.py). */
export type ChatMemory = {
  customer: { user_id: number; first_name: string; last_name: string; email: string }
  messages: SavedChatMessage[]
  last_viewed_product_id: string | null
  last_viewed_product_name: string | null
  last_search: string | null
  /** The item recalled at login, with current price, description, sizes and stock. */
  recalled_product: ChatProductCard | null
  welcome_back: string
  suggestions: string[]
}

/** Problem 10: sport or field-of-study theme from the backend (backend/themes.py). */
export type Theme = {
  key: string
  kind: 'sport' | 'field'
  label: string
  persona: string
  persona_role: string
  voice: string
  tagline: string
  scene: string
}
