import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useChatResults } from '../chatResults'
import ChatResultsPanel from '../components/ChatResultsPanel'
import ThemeBanner from '../components/ThemeBanner'
import { useReveal } from '../reveal'
import ProductCard from '../components/ProductCard'
import StyleToggle, { type StyleChoice } from '../components/StyleToggle'
import type { Product } from '../types'

/*
 * Problem 9, Front end 1: faceted search and clear category navigation.
 * Filters: category, price, size in stock, color, brand, style, in season.
 * Everything lives in the page address (?category=Hoodies&size=M&color=Navy...), so a
 * filtered view can be bookmarked, shared, and reopened with the Back button.
 */

const CATEGORIES = ['Hoodies', 'Crewnecks & sweatshirts', 'T-shirts', 'Quarter-zips', 'Jackets & fleece', 'Long sleeves']
const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
const PRICE_BANDS = [
  { id: 'under-40', label: 'Under $40', test: (p: number) => p < 40 },
  { id: '40-70', label: '$40 to $70', test: (p: number) => p >= 40 && p <= 70 },
  { id: 'over-70', label: 'Over $70', test: (p: number) => p > 70 },
]
const SORTS = [
  { id: 'featured', label: 'Featured' },
  { id: 'price-asc', label: 'Price: low to high' },
  { id: 'price-desc', label: 'Price: high to low' },
  { id: 'name', label: 'Name: A to Z' },
]

type Facet = 'price' | 'size' | 'color' | 'brand'

/** Does a product pass every filter, optionally ignoring one facet (for that facet's counts)? */
function matches(p: Product, params: URLSearchParams, ignore?: Facet | 'category' | 'style'): boolean {
  const all = (key: string) => params.getAll(key)
  const q = (params.get('q') ?? '').trim().toLowerCase()
  if (q && !`${p.name} ${p.description} ${p.garment_type} ${p.colors.join(' ')}`.toLowerCase().includes(q)) return false
  if (ignore !== 'category' && params.get('category') && p.category !== params.get('category')) return false
  if (ignore !== 'style' && params.get('style') && p.style !== params.get('style')) return false
  if (params.get('season') === 'now' && !p.in_season) return false
  if (ignore !== 'price' && all('price').length &&
      !PRICE_BANDS.some((b) => all('price').includes(b.id) && b.test(p.price))) return false
  if (ignore !== 'size' && all('size').length &&
      !all('size').some((s) => p.sizes_in_stock?.includes(s))) return false
  if (ignore !== 'color' && all('color').length &&
      !all('color').some((c) => p.color_groups?.includes(c))) return false
  if (ignore !== 'brand' && all('brand').length && !all('brand').includes(p.brand ?? '')) return false
  return true
}

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([])
  const [error, setError] = useState<string | null>(null)
  const [params, setParams] = useSearchParams()
  const [filtersOpen, setFiltersOpen] = useState(false)
  const { results, theme, setTheme } = useChatResults()
  const gridRef = useReveal<HTMLDivElement>([products.length])
  const q = params.get('q') ?? ''

  // Problem 10: searching for a sport or a school switches on its theme (banner + chat persona).
  useEffect(() => {
    if (!q.trim()) return
    const timer = window.setTimeout(() => {
      fetch(`/api/themes/detect?q=${encodeURIComponent(q)}`)
        .then((res) => (res.ok ? res.json() : { theme: null }))
        .then((data) => data.theme && setTheme(data.theme))
        .catch(() => {})
    }, 350)
    return () => window.clearTimeout(timer)
  }, [q]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    fetch('/api/products', { cache: 'no-store' })
      .then((res) => {
        if (!res.ok) throw new Error(`Request failed: ${res.status}`)
        return res.json()
      })
      .then(setProducts)
      .catch((err) => setError(err.message))
  }, [])

  function update(change: (p: URLSearchParams) => void) {
    const next = new URLSearchParams(params)
    change(next)
    setParams(next, { replace: false })
  }
  const setSingle = (key: string, value: string | null) =>
    update((p) => (value ? p.set(key, value) : p.delete(key)))
  const toggleMulti = (key: string, value: string) =>
    update((p) => {
      const values = p.getAll(key)
      p.delete(key)
      for (const v of values.includes(value) ? values.filter((x) => x !== value) : [...values, value]) p.append(key, v)
    })

  const colors = useMemo(
    () => [...new Set(products.flatMap((p) => p.color_groups ?? []))].sort(),
    [products],
  )
  const brands = useMemo(() => {
    const set = [...new Set(products.map((p) => p.brand ?? '').filter(Boolean))].sort()
    return ['Campus Customs', ...set.filter((b) => b !== 'Campus Customs')].filter((b) => set.includes(b))
  }, [products])

  const shown = useMemo(() => {
    const list = products.filter((p) => matches(p, params))
    const sort = params.get('sort') ?? 'featured'
    if (sort === 'price-asc') list.sort((a, b) => a.price - b.price || a.name.localeCompare(b.name))
    if (sort === 'price-desc') list.sort((a, b) => b.price - a.price || a.name.localeCompare(b.name))
    if (sort === 'name') list.sort((a, b) => a.name.localeCompare(b.name))
    if (sort === 'featured') list.sort((a, b) => Number(b.in_season) - Number(a.in_season) || Number((b.total_stock ?? 0) > 0) - Number((a.total_stock ?? 0) > 0))
    return list
  }, [products, params])

  /** How many products a facet value would show, given all the other filters. */
  const count = (facet: Facet, test: (p: Product) => boolean) =>
    products.filter((p) => matches(p, params, facet) && test(p)).length
  const categoryCount = (c: string | null) =>
    products.filter((p) => matches(p, params, 'category') && (!c || p.category === c)).length

  const withoutSeason = new URLSearchParams([...params].filter(([k]) => k !== 'season'))
  const seasonCount = products.filter((p) => p.in_season && matches(p, withoutSeason)).length

  const activeCount =
    ['price', 'size', 'color', 'brand'].reduce((n, k) => n + params.getAll(k).length, 0) +
    (params.get('season') ? 1 : 0) + (params.get('q') ? 1 : 0)
  const anyFilter = activeCount > 0 || params.get('category') || params.get('style')

  const checkbox = (key: Facet, value: string, label: string, n: number) => {
    const checked = params.getAll(key).includes(value)
    return (
      <label key={value} className={n === 0 && !checked ? 'facet-option empty' : 'facet-option'}>
        <input type="checkbox" checked={checked} disabled={n === 0 && !checked} onChange={() => toggleMulti(key, value)} />
        <span>{label}</span>
        <span className="facet-count">{n}</span>
      </label>
    )
  }

  return (
    <main className="page">
      <ChatResultsPanel />
      {/* The chat panel shows the banner with its matches; otherwise show it here. */}
      {theme && !results && <ThemeBanner theme={theme} onClear={() => setTheme(null)} />}
      <h1>Products</h1>

      {/* Clear category navigation */}
      <nav className="category-nav" aria-label="Shop by category">
        {[null, ...CATEGORIES].map((c) => {
          const active = (params.get('category') ?? null) === c
          return (
            <button
              key={c ?? 'all'}
              type="button"
              className={active ? 'category-chip active' : 'category-chip'}
              aria-pressed={active}
              onClick={() => setSingle('category', c)}
            >
              {c ?? 'All products'} <span className="facet-count">{categoryCount(c)}</span>
            </button>
          )
        })}
      </nav>

      <div className="shop-toolbar">
        <StyleToggle
          value={(params.get('style') as StyleChoice) ?? 'All'}
          onChange={(v) => setSingle('style', v === 'All' ? null : v)}
        />
        <input
          className="shop-search"
          type="search"
          placeholder="Search products…"
          aria-label="Search products"
          value={params.get('q') ?? ''}
          onChange={(e) => setSingle('q', e.target.value || null)}
        />
        <label className="shop-sort">
          Sort
          <select value={params.get('sort') ?? 'featured'} onChange={(e) => setSingle('sort', e.target.value === 'featured' ? null : e.target.value)}>
            {SORTS.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
        <button type="button" className="filters-toggle" onClick={() => setFiltersOpen((o) => !o)} aria-expanded={filtersOpen}>
          Filters{activeCount > 0 ? ` (${activeCount})` : ''}
        </button>
      </div>

      {error && <p className="error">Could not load products. {error}</p>}

      <div className="shop-layout">
        <aside className={filtersOpen ? 'facets open' : 'facets'} aria-label="Filters">
          <div className="facet-group">
            <h2>Season</h2>
            <label className="facet-option">
              <input
                type="checkbox"
                checked={params.get('season') === 'now'}
                onChange={() => setSingle('season', params.get('season') === 'now' ? null : 'now')}
              />
              <span>In season now</span>
              <span className="facet-count">{seasonCount}</span>
            </label>
          </div>
          <div className="facet-group">
            <h2>Price</h2>
            {PRICE_BANDS.map((b) => checkbox('price', b.id, b.label, count('price', (p) => b.test(p.price))))}
          </div>
          <div className="facet-group">
            <h2>Size in stock</h2>
            <div className="facet-sizes">
              {SIZES.map((s) => {
                const n = count('size', (p) => !!p.sizes_in_stock?.includes(s))
                const on = params.getAll('size').includes(s)
                return (
                  <button
                    key={s}
                    type="button"
                    aria-pressed={on}
                    disabled={n === 0 && !on}
                    title={`${n} items in stock in ${s}`}
                    className={on ? 'size-chip selected' : 'size-chip'}
                    onClick={() => toggleMulti('size', s)}
                  >
                    {s}
                  </button>
                )
              })}
            </div>
          </div>
          <div className="facet-group">
            <h2>Color</h2>
            {colors.map((c) => checkbox('color', c, c, count('color', (p) => !!p.color_groups?.includes(c))))}
          </div>
          <div className="facet-group">
            <h2>Brand</h2>
            {brands.map((b) => checkbox('brand', b, b, count('brand', (p) => p.brand === b)))}
          </div>
        </aside>

        <section className="shop-results" aria-live="polite">
          <div className="results-bar">
            <p>
              <strong>{shown.length}</strong> {shown.length === 1 ? 'item' : 'items'}
              {params.get('category') ? ` in ${params.get('category')}` : ''}
              {params.get('style') ? ` · ${params.get('style')}` : ''}
            </p>
            {anyFilter && (
              <button type="button" className="clear-filters" onClick={() => setParams(new URLSearchParams())}>
                Clear all
              </button>
            )}
          </div>
          {products.length > 0 && shown.length === 0 && (
            <p className="no-results">No items match all of these filters. Try removing one, or ask our chat assistant.</p>
          )}
          <div className="product-grid" ref={gridRef}>
            {shown.map((p) => (
              <ProductCard key={p.product_id} product={p} />
            ))}
          </div>
        </section>
      </div>
    </main>
  )
}
