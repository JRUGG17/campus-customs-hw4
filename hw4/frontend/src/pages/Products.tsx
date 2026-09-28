import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { searchProducts, type SearchResponse } from '../api'
import { useChatControl } from '../chatControl'
import { useChatResults } from '../chatResults'
import ProductCard from '../components/ProductCard'

const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
const SORTS: Record<string, string> = {
  relevance: 'Best match',
  price_asc: 'Price: low to high',
  price_desc: 'Price: high to low',
  name: 'Name: A–Z',
}
const FILTER_KEYS = ['q', 'category', 'size', 'color', 'price'] as const

export default function Products() {
  // Filters live in the URL: Back/refresh keep them, and links like
  // /products?category=hoodies&size=M can be shared or used by the search bar.
  const [params, setParams] = useSearchParams()
  const [data, setData] = useState<SearchResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const { results, clearResults } = useChatResults()
  const { askAssistant } = useChatControl()

  const get = (k: string) => params.get(k) ?? ''
  const q = get('q')
  const category = get('category')
  const size = get('size')
  const color = get('color')
  const price = get('price')
  const sort = get('sort') || (q ? 'relevance' : 'name')

  useEffect(() => {
    const ctrl = new AbortController()
    searchProducts({ q, category, size, color, price, sort }, ctrl.signal)
      .then((d) => {
        setData(d)
        setError(null)
      })
      .catch((e: Error) => e.name !== 'AbortError' && setError(e.message))
    return () => ctrl.abort()
  }, [q, category, size, color, price, sort])

  function setParam(key: string, value: string) {
    // Start from the browser's live URL, not this render's copy, so quick successive
    // changes (tab, then size, then color) all stick.
    const next = new URLSearchParams(window.location.search)
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next, { replace: key !== 'category' && key !== 'q' })
  }

  const clearAll = () => setParams(new URLSearchParams(sort !== 'name' ? { sort } : {}))

  const labels = data?.category_labels ?? {}
  const colorLabels = data?.color_labels ?? {}
  const priceLabels = data?.price_labels ?? {}
  const categoryTotal = data ? Object.values(data.category_counts).reduce((a, b) => a + b, 0) : 0
  const active = FILTER_KEYS.filter((k) => get(k))
  const chipLabel = (k: string) => {
    const v = get(k)
    if (k === 'q') return `“${v}”`
    if (k === 'category') return labels[v] ?? v
    if (k === 'size') return `In stock in ${v}`
    if (k === 'color') return colorLabels[v] ?? v
    return priceLabels[v] ?? v
  }

  const heading = q ? `Results for “${q}”` : category ? labels[category] ?? 'Products' : 'All products'
  const describe = [category && labels[category], color && colorLabels[color], size && `size ${size}`, q && `“${q}”`]
    .filter(Boolean)
    .join(', ')
  // e.g. "Do you have any gray hoodies in size XXL under $60?"
  const askText = [
    'Do you have any',
    color && colorLabels[color]?.split(' /')[0].toLowerCase(),
    q,
    category ? labels[category]?.toLowerCase() : !q && 'items',
    size && `in size ${size}`,
    price && (priceLabels[price]?.startsWith('Under') ? priceLabels[price].toLowerCase() : `priced ${priceLabels[price]}`),
  ]
    .filter(Boolean)
    .join(' ') + '?'

  return (
    <div className="container">
      {results && (
        // key re-mounts the section for each new search so the highlight animation replays
        <section key={results.query + results.heading} className="chat-results" aria-live="polite">
          <div className="section-head">
            <div>
              <p className="eyebrow">From your chat · “{results.query}”</p>
              <h2>{results.heading}</h2>
            </div>
            <button className="link-button" onClick={clearResults}>
              Clear results
            </button>
          </div>
          <div className="product-grid">
            {results.products.map((p, i) => (
              <ProductCard key={p.product_id} product={p} index={i} />
            ))}
          </div>
        </section>
      )}

      <div className="section-head">
        <h1>{heading}</h1>
        {data && (
          <span className="muted">
            {data.total} {data.total === 1 ? 'item' : 'items'}
          </span>
        )}
      </div>

      {/* Category tabs, with counts that respect the other filters */}
      <nav className="category-tabs" aria-label="Categories">
        <button className={!category ? 'active' : ''} onClick={() => setParam('category', '')}>
          All <span>{categoryTotal}</span>
        </button>
        {Object.entries(labels)
          .filter(([key]) => (data?.category_counts[key] ?? 0) > 0 || key === category)
          .map(([key, label]) => (
            <button key={key} className={category === key ? 'active' : ''} onClick={() => setParam('category', key)}>
              {label} <span>{data?.category_counts[key] ?? 0}</span>
            </button>
          ))}
      </nav>

      {/* One row of dropdowns: each shows how many items you'd get, given the other filters */}
      <div className="filter-bar">
        <label className="filter-select">
          <span className="filter-label">Size in stock</span>
          <select value={size} onChange={(e) => setParam('size', e.target.value)}>
            <option value="">Any size</option>
            {SIZES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="filter-select">
          <span className="filter-label">Color</span>
          <select value={color} onChange={(e) => setParam('color', e.target.value)}>
            <option value="">Any color</option>
            {Object.entries(colorLabels)
              .filter(([key]) => (data?.color_counts[key] ?? 0) > 0 || key === color)
              .map(([key, label]) => (
                <option key={key} value={key}>
                  {label} ({data?.color_counts[key] ?? 0})
                </option>
              ))}
          </select>
        </label>
        <label className="filter-select">
          <span className="filter-label">Price</span>
          <select value={price} onChange={(e) => setParam('price', e.target.value)}>
            <option value="">Any price</option>
            {Object.entries(priceLabels).map(([key, label]) => (
              <option key={key} value={key} disabled={(data?.price_counts[key] ?? 0) === 0 && price !== key}>
                {label} ({data?.price_counts[key] ?? 0})
              </option>
            ))}
          </select>
        </label>
        <label className="filter-select filter-sort">
          <span className="filter-label">Sort</span>
          <select id="sort" value={sort} onChange={(e) => setParam('sort', e.target.value)}>
            {Object.entries(SORTS)
              .filter(([key]) => key !== 'relevance' || q)
              .map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
          </select>
        </label>
      </div>

      {active.length > 0 && (
        <div className="active-filters">
          {active.map((k) => (
            <button key={k} className="filter-chip" onClick={() => setParam(k, '')} aria-label={`Remove ${chipLabel(k)}`}>
              {chipLabel(k)} ×
            </button>
          ))}
          <button className="link-button" onClick={clearAll}>
            Clear all
          </button>
        </div>
      )}

      {error && <p className="error">Couldn't load products ({error}). Is the backend running?</p>}
      {!data && !error && <p className="muted">Loading products…</p>}
      {data && data.total === 0 && (
        <div className="empty-state">
          <h3>No matches for {describe || 'those filters'}.</h3>
          <p>
            {data.unmatched_terms.length > 0
              ? `We don't carry anything matching “${data.unmatched_terms.join('”, “')}”.`
              : 'Try removing a filter.'}{' '}
            Our assistant can suggest the closest things we do have.
          </p>
          <div className="empty-actions">
            {active.length > 0 && (
              <button className="btn btn-outline-dark" onClick={clearAll}>
                Clear filters
              </button>
            )}
            <button className="btn btn-primary" onClick={() => askAssistant(askText)}>
              Ask the assistant
            </button>
          </div>
        </div>
      )}
      {data && data.total > 0 && (
        <div className="product-grid">
          {data.products.map((p, i) => (
            <ProductCard key={p.product_id} product={p} index={i} />
          ))}
        </div>
      )}
    </div>
  )
}
