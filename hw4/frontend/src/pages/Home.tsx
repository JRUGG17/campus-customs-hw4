import { useEffect, useState, type CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import { fetchProducts, formatPrice, searchProducts, type ProductSummary } from '../api'
import { useChatControl } from '../chatControl'
import ProductCard from '../components/ProductCard'

// Real catalogue photos only; everything else on this page is HTML/CSS.
const HERO_STACK = [
  'saybrook-college-crewneck',
  '2025-yale-vs-harvard-t-shirt',
  'champion-reverse-weave-crewneck',
  'basic-hoodie-big-yale',
]
const FEATURED_IDS = [
  'basic-hoodie-big-yale',
  'champion-reverse-weave-crewneck',
  'district-vit-hoodie-vintage-sailor-bulldog',
  'branford-1-4-zip',
]
const CATEGORY_TILES = [
  { key: 'hoodies', label: 'Hoodies', photo: 'crew-left-chest-hoodie' },
  { key: 'crewnecks', label: 'Crewnecks', photo: 'champion-reverse-weave-crewneck' },
  { key: 't-shirts', label: 'T-shirts', photo: 'boola-boola-t-shirt' },
  { key: 'quarter-zips', label: 'Quarter-zips', photo: 'branford-1-4-zip' },
  { key: 'jackets-fleece', label: 'Jackets & Fleece', photo: 'brooks-brothers-bomber-jacket-yale' },
  { key: 'long-sleeve', label: 'Long Sleeve', photo: 'dry-zone-long-sleeve' },
]
// Residential colleges that have gear in the catalogue.
const COLLEGES = [
  'Benjamin Franklin', 'Berkeley', 'Branford', 'Davenport', 'Grace Hopper', 'Jonathan Edwards',
  'Morse', 'Pierson', 'Saybrook', 'Timothy Dwight', 'Trumbull',
]
const TICKER = [
  'Boola Boola',
  'Bulldog Blue since 1975',
  '57 Broadway, New Haven',
  'Printed & embroidered in-house',
  'Officially licensed Yale apparel',
  'XS–XXL',
]
const GAME_TEE = '2025-yale-vs-harvard-t-shirt'
const photo = (id: string) => `/media/products/${id}.jpg`

export default function Home() {
  const [all, setAll] = useState<ProductSummary[]>([])
  const [counts, setCounts] = useState<Record<string, number>>({})
  const { askAssistant } = useChatControl()

  useEffect(() => {
    fetchProducts().then(setAll).catch(() => setAll([]))
    searchProducts({ limit: 1 })
      .then((d) => setCounts(d.category_counts))
      .catch(() => setCounts({}))
  }, [])

  const featured = FEATURED_IDS.map((id) => all.find((p) => p.product_id === id)).filter(
    (p): p is ProductSummary => Boolean(p),
  )
  const gameTee = all.find((p) => p.product_id === GAME_TEE)

  return (
    <>
      <section className="hero">
        <div className="hero-inner">
          <div className="hero-copy">
            <span className="patch patch-small">Est. 1975</span>
            <h1>
              Bulldog Blue,
              <br />
              <em>head to toe.</em>
            </h1>
            <p className="hero-sub">
              Hoodies, crewnecks, and tees for Yale students, alumni, and families, from the
              family-run shop on Broadway that's been outfitting Elis since 1975.
            </p>
            <div className="hero-actions">
              <Link to="/products" className="btn btn-light">
                Shop all
              </Link>
              <Link to="/about" className="btn btn-outline">
                Our story
              </Link>
            </div>
            <ul className="hero-badges">
              <li>Officially licensed</li>
              <li>Printed on Broadway</li>
              <li>XS–XXL</li>
            </ul>
          </div>

          {/* A folded stack of real products; hovering fans it out like a shop table */}
          <Link to="/products" className="hero-stack" aria-label="Browse products">
            {HERO_STACK.map((id, i) => (
              <span key={id} className="stack-item" style={{ '--n': i } as CSSProperties}>
                <img src={photo(id)} alt="" />
              </span>
            ))}
            <span className="felt-y" aria-hidden="true">
              Y
            </span>
          </Link>
        </div>
      </section>

      <div className="ticker" aria-hidden="true">
        <div className="ticker-track">
          {[...TICKER, ...TICKER, ...TICKER].map((t, i) => (
            <span key={i}>{t}</span>
          ))}
        </div>
      </div>

      <section className="section">
        <div className="section-head">
          <h2>Shop by category</h2>
          <Link to="/products">See everything →</Link>
        </div>
        <div className="category-grid">
          {CATEGORY_TILES.map((c, i) => (
            <Link
              key={c.key}
              to={`/products?category=${c.key}`}
              className="category-tile"
              style={{ '--i': i } as CSSProperties}
            >
              <img src={photo(c.photo)} alt="" loading="lazy" />
              <span className="category-tile-label">
                {c.label}
                {counts[c.key] !== undefined && <small>{counts[c.key]} styles</small>}
              </span>
            </Link>
          ))}
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <h2>Rep your residential college</h2>
        </div>
        <div className="pennants">
          {COLLEGES.map((c) => (
            <Link key={c} to={`/products?q=${encodeURIComponent(c)}`} className="pennant">
              {c}
            </Link>
          ))}
        </div>
      </section>

      <section className="game-band">
        <div className="game-inner">
          <div>
            <p className="eyebrow">Every November</p>
            <h2 className="game-title">
              The <span>Game</span>
            </h2>
            <p>
              Yale vs. Harvard. Wear the 2025 matchup tee to the next kickoff.
            </p>
            <div className="hero-actions">
              <Link to={`/products/${GAME_TEE}`} className="btn btn-light">
                Get The Game tee{gameTee ? ` · ${formatPrice(gameTee.price)}` : ''}
              </Link>
              <button className="btn btn-outline" onClick={() => askAssistant('What game-day gear do you have?')}>
                Ask for game-day picks
              </button>
            </div>
          </div>
          <Link to={`/products/${GAME_TEE}`} className="game-photo" aria-label="2025 Yale vs Harvard T-shirt">
            <img src={photo(GAME_TEE)} alt="" />
          </Link>
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <h2>Fan favorites</h2>
          <Link to="/products">View all →</Link>
        </div>
        <div className="product-grid">
          {featured.map((p, i) => (
            <ProductCard key={p.product_id} product={p} index={i} />
          ))}
        </div>
      </section>

      <section className="section visit">
        <div className="storefront">
          <div className="awning" aria-hidden="true" />
          <div className="storefront-body">
            <h2>Come see us on Broadway</h2>
            <p>
              <strong>57 Broadway, New Haven</strong>: a short walk from campus, with our print
              shop right next door. Can't make it? Our assistant knows every size on the shelf.
            </p>
            <button className="btn btn-primary" onClick={() => askAssistant('What sizes do you have in stock for hoodies?')}>
              Ask the assistant
            </button>
          </div>
        </div>
      </section>
    </>
  )
}
