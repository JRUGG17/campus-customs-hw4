import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { formatPrice, searchProducts, type SearchResponse } from '../api'
import { useChatControl } from '../chatControl'
import { useChatResults } from '../chatResults'

const DEBOUNCE_MS = 200
const PREVIEW_COUNT = 6

/** Live search in the nav: results appear as you type; dead ends hand off to the assistant. */
export default function SearchBar() {
  const navigate = useNavigate()
  const location = useLocation()
  const [params] = useSearchParams()
  const { askAssistant } = useChatControl()
  const { clearResults } = useChatResults()
  const [text, setText] = useState('')
  const [data, setData] = useState<SearchResponse | null>(null)
  const [open, setOpen] = useState(false)
  const [highlight, setHighlight] = useState(-1)
  const boxRef = useRef<HTMLDivElement>(null)

  // Keep the box in sync with /products?q=… (e.g. after pressing Back).
  const urlQuery = location.pathname === '/products' ? params.get('q') ?? '' : ''
  useEffect(() => setText(urlQuery), [urlQuery])

  const query = text.trim()
  useEffect(() => {
    if (query.length < 2) {
      setData(null)
      return
    }
    const ctrl = new AbortController()
    const timer = setTimeout(() => {
      searchProducts({ q: query, limit: PREVIEW_COUNT }, ctrl.signal)
        .then((d) => {
          setData(d)
          setHighlight(-1)
        })
        .catch(() => {})
    }, DEBOUNCE_MS)
    return () => {
      clearTimeout(timer)
      ctrl.abort()
    }
  }, [query])

  // Close when clicking anywhere else.
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (!boxRef.current?.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [])

  const results = data?.products ?? []
  const noMatches = data !== null && data.total === 0
  // Options you can arrow through: each preview, then "see all" or "ask the assistant".
  const optionCount = results.length + 1

  function seeAll() {
    setOpen(false)
    // A new search replaces the chat's earlier picks, so the matches are the first thing on the page.
    clearResults()
    navigate(`/products?q=${encodeURIComponent(query)}`)
  }

  function ask() {
    setOpen(false)
    askAssistant(`Do you have ${query}?`)
  }

  function choose(index: number) {
    if (index >= 0 && index < results.length) {
      setOpen(false)
      setText('')
      navigate(`/products/${results[index].product_id}`)
    } else if (noMatches) ask()
    else seeAll()
  }

  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setOpen(true)
      setHighlight((h) => Math.min(h + 1, optionCount - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setHighlight((h) => Math.max(h - 1, -1))
    } else if (e.key === 'Enter' && query) {
      e.preventDefault()
      choose(highlight)
    } else if (e.key === 'Escape') {
      setOpen(false)
    }
  }

  const showDropdown = open && query.length >= 2 && data !== null

  return (
    <div className="search-bar" ref={boxRef}>
      <input
        type="search"
        placeholder="Search hoodies, colleges, sports…"
        aria-label="Search products"
        aria-expanded={showDropdown}
        aria-controls="search-results"
        role="combobox"
        value={text}
        onChange={(e) => {
          setText(e.target.value)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
      />
      {showDropdown && (
        <div className="search-dropdown" id="search-results" role="listbox">
          {results.map((p, i) => (
            <button
              key={p.product_id}
              role="option"
              aria-selected={highlight === i}
              className={`search-result${highlight === i ? ' highlighted' : ''}`}
              onMouseEnter={() => setHighlight(i)}
              onClick={() => choose(i)}
            >
              <img src={p.image_url} alt="" />
              <span className="search-result-text">
                <strong>{p.name}</strong>
                <span>
                  {formatPrice(p.price)}
                  {p.total_stock === 0 && ' · Sold out'}
                </span>
              </span>
            </button>
          ))}
          {noMatches ? (
            <div className="search-empty">
              <p>
                No products match <strong>“{query}”</strong>.
              </p>
              <button
                className={`search-action${highlight === 0 ? ' highlighted' : ''}`}
                onClick={ask}
                role="option"
                aria-selected={highlight === 0}
              >
                💬 Ask our assistant about “{query}”
              </button>
            </div>
          ) : (
            <button
              className={`search-action${highlight === results.length ? ' highlighted' : ''}`}
              onClick={seeAll}
              role="option"
              aria-selected={highlight === results.length}
            >
              See all {data.total} results for “{query}” →
            </button>
          )}
        </div>
      )}
    </div>
  )
}
