import { useEffect, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth'
import ArrivalsTicker from '../components/ArrivalsTicker'
import CampusScene from '../components/CampusScene'
import ChatResultsPanel from '../components/ChatResultsPanel'
import ProductCard from '../components/ProductCard'
import StyleToggle, { type StyleChoice } from '../components/StyleToggle'
import { useReveal } from '../reveal'
import type { Product, Recommendation } from '../types'

const ROW_COUNT = 8

/** Problem 10: "Shop by tradition" pennants. Each search also switches on its theme banner. */
const TRADITIONS = [
  { title: 'Game day', line: 'Gear for The Game and every Saturday at the Bowl.', to: '/products?q=harvard', color: 'orange' },
  { title: 'On the ice', line: 'Hockey hoodies for nights at the rink.', to: '/products?q=hockey', color: 'blue' },
  { title: 'In the boardroom', line: 'School of Management pieces, interview-ready.', to: '/products?q=school%20of%20management', color: 'green' },
  { title: 'In the studio', line: 'School of Art and Architecture layers.', to: '/products?q=school%20of%20art', color: 'stone' },
]

function Row({ title, subtitle, children, action }: { title: string; subtitle?: string; children: ReactNode; action?: ReactNode }) {
  return (
    <section className="home-row" aria-label={title}>
      <div className="row-header">
        <div>
          <h2 className="section-title">{title}</h2>
          {subtitle && <p className="row-subtitle">{subtitle}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  )
}

function RevealGrid({ products, notes, deps }: { products: Product[]; notes?: Record<string, string>; deps: unknown[] }) {
  const ref = useReveal<HTMLDivElement>(deps)
  return (
    <div className="product-grid" ref={ref}>
      {products.map((p) => (
        <ProductCard key={p.product_id} product={p} note={notes?.[p.product_id]} short />
      ))}
    </div>
  )
}

export default function HomePage() {
  const [products, setProducts] = useState<Product[]>([])
  const [style, setStyle] = useState<StyleChoice>('All')
  const [seasons, setSeasons] = useState<string[]>([])
  const [picks, setPicks] = useState<{ recommendations: Recommendation[]; usual_size: string | null } | null>(null)
  const { user, token } = useAuth()

  useEffect(() => {
    fetch('/api/products', { cache: 'no-store' })
      .then((res) => (res.ok ? res.json() : []))
      .then(setProducts)
      .catch(() => setProducts([]))
    fetch('/api/seasons/now', { cache: 'no-store' })
      .then((res) => (res.ok ? res.json() : { seasons: [] }))
      .then((data) => setSeasons(data.seasons))
      .catch(() => setSeasons([]))
  }, [])

  // Problem 9, Backend 2: tailored picks from the shopper's orders, views and chats.
  useEffect(() => {
    if (!user || !token) {
      setPicks(null)
      return
    }
    fetch('/api/me/recommendations', { headers: { Authorization: `Bearer ${token}` }, cache: 'no-store' })
      .then((res) => (res.ok ? res.json() : Promise.reject()))
      .then((data) => setPicks({ recommendations: data.recommendations, usual_size: data.profile.usual_size }))
      .catch(() => setPicks(null))
  }, [user?.id, token]) // eslint-disable-line react-hooks/exhaustive-deps

  const inStock = products.filter((p) => (p.total_stock ?? 1) > 0)
  const byStyle = inStock.filter((p) => style === 'All' || p.style === style).slice(0, ROW_COUNT)
  // Game-day items first while it's game season, then the rest of the season.
  const inSeason = inStock
    .filter((p) => p.in_season)
    .sort((a, b) => Number(!!b.seasons?.includes('Game day')) - Number(!!a.seasons?.includes('Game day')))
  const arrivals = inSeason.slice(0, 14)

  function openChat() {
    document.querySelector<HTMLButtonElement>('.chat-launcher')?.click()
  }

  return (
    <>
      <section className="campus-hero">
        <CampusScene />
        <div className="campus-hero-copy">
          <h1>Wear the story of New Haven.</h1>
          <p>
            Hoodies, crewnecks and quarter-zips for students, alumni and the families who cheer
            them on, from move-in day to Commencement.
          </p>
          <div className="hero-actions">
            <Link to="/products" className="button hero-primary">
              Shop the collection
            </Link>
            <button type="button" className="button hero-secondary" onClick={openChat}>
              Ask a Bulldog
            </button>
          </div>
        </div>
      </section>

      <ArrivalsTicker products={arrivals} />

      <main className="page home">
        <ChatResultsPanel />

        <section className="traditions" aria-label="Shop by tradition">
          <h2 className="section-title">Shop by tradition</h2>
          <div className="pennant-row">
            {TRADITIONS.map((t) => (
              <Link key={t.title} to={t.to} className={`pennant pennant-${t.color}`}>
                <span className="pennant-title">{t.title}</span>
                <span className="pennant-line">{t.line}</span>
              </Link>
            ))}
          </div>
        </section>

        {user && picks && picks.recommendations.length > 0 && (
          <Row
            title={`Recommended for you, ${user.first_name}`}
            subtitle={`Picked from your orders and the items you looked at${picks.usual_size ? `, all in stock in your size ${picks.usual_size}` : ''}.`}
          >
            <RevealGrid
              products={picks.recommendations}
              notes={Object.fromEntries(picks.recommendations.map((p) => [p.product_id, p.reason]))}
              deps={[picks.recommendations.length]}
            />
          </Row>
        )}

        <Row title="Shop by style" action={<StyleToggle value={style} onChange={setStyle} />}>
          <RevealGrid products={byStyle} deps={[products.length]} />
          <p className="see-all">
            <Link to={style === 'All' ? '/products' : `/products?style=${style}`}>
              See all {style === 'All' ? 'products' : `${style.toLowerCase()} styles`}
            </Link>
          </p>
        </Row>

        {inSeason.length > 0 && (
          <Row
            title="In season now"
            subtitle={`${seasons.length > 0 ? `Featuring ${seasons.join(' and ').toLowerCase()} picks. ` : ''}Updated automatically as the seasons change.`}
          >
            <RevealGrid products={inSeason.slice(0, ROW_COUNT)} deps={[products.length]} />
            <p className="see-all">
              <Link to="/products?season=now">See everything in season</Link>
            </p>
          </Row>
        )}

        <section className="spirit-band" aria-label="School spirit">
          <p className="spirit-band-big">Go Yale! Beat Harvard!</p>
          <p className="spirit-band-small">Wear it to the Bowl, the library and every reunion after.</p>
        </section>
      </main>
    </>
  )
}
