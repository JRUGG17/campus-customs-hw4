export interface ProductSummary {
  product_id: string
  name: string
  garment_type: string
  category: string
  color_family: string | null
  short_description: string
  price: number
  image_url: string
  total_stock: number
  sizes_in_stock: string[]
}

export interface SizeStock {
  size: string
  quantity: number
}

export interface ProductDetail extends ProductSummary {
  description: string
  colors: string[]
  search_tags: string[]
  sizes: SizeStock[]
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  error?: boolean // error notice, not sent to the agent
  local?: boolean // widget greeting/notice, not sent to the agent
  products?: ProductSummary[] // products returned with this reply
  productsOnPage?: boolean // true: shown on the page as search results; false: small cards in the bubble
  time?: string // display time, e.g. "3:42 PM"
}

export interface User {
  id: number
  first_name: string
  last_name: string
  email: string
}

export interface SignupInput {
  first_name: string
  last_name: string
  email: string
  password: string
  confirm_password: string
}

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

/** POST JSON; on failure throw the backend's `detail` message so forms can show it. */
async function postJson<T>(url: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Something went wrong.')
  return data as T
}

export async function fetchCurrentUser(): Promise<User | null> {
  const res = await fetch('/api/auth/me')
  return res.ok ? ((await res.json()) as User) : null
}

export const signup = (input: SignupInput) => postJson<User>('/api/auth/signup', input)

export const login = (email: string, password: string) =>
  postJson<User>('/api/auth/login', { email, password })

export const logout = () => postJson<{ ok: boolean }>('/api/auth/logout')

export const fetchProducts = () => getJson<ProductSummary[]>('/api/products')

/** GET /api/search: the search bar and Products-page filters share the agent's search engine. */
export interface SearchParams {
  q?: string
  category?: string
  size?: string
  color?: string
  price?: string
  sort?: string
  limit?: number
}

export interface SearchResponse {
  query: string
  total: number
  products: ProductSummary[]
  unmatched_terms: string[]
  matches_all_terms: boolean
  category_counts: Record<string, number>
  color_counts: Record<string, number>
  price_counts: Record<string, number>
  category_labels: Record<string, string>
  color_labels: Record<string, string>
  price_labels: Record<string, string>
}

export function searchProducts(params: SearchParams, signal?: AbortSignal): Promise<SearchResponse> {
  const qs = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== '') qs.set(k, String(v))
  return fetch(`/api/search?${qs}`, { signal }).then((res) => {
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
    return res.json() as Promise<SearchResponse>
  })
}

export const fetchProduct = (id: string) =>
  getJson<ProductDetail>(`/api/products/${encodeURIComponent(id)}`)

export const formatPrice = (price: number) => `$${price.toFixed(2)}`

/**
 * /api/chat response contract.
 * - results_heading set  -> a search: show `products` as cards on the page.
 * - results_heading null -> show any `products` as small cards in the chat bubble.
 */
export interface ChatResponse {
  reply: string
  results_heading: string | null
  products: ProductSummary[]
}

/** Where the shopper is, so "this" / "these" make sense to the agent. The server re-checks it. */
export interface PageContext {
  path: string
  product_id: string | null
  visible_product_ids: string[]
}

/** A saved message from /api/chat/history (logged-in shoppers only). */
export interface HistoryMessage {
  role: 'user' | 'assistant'
  content: string
  results_heading: string | null
  products: ProductSummary[]
  created_at: string
}

export const fetchChatHistory = () => getJson<HistoryMessage[]>('/api/chat/history')

const MAX_HISTORY = 20 // backend rejects longer histories

/**
 * Send one message to the PydanticAI agent. `history` is only used for guests;
 * for logged-in shoppers the server loads their saved chat from the database instead.
 */
export async function sendChatMessage(
  history: ChatMessage[],
  message: string,
  page: PageContext,
): Promise<ChatResponse> {
  return postJson<ChatResponse>('/api/chat', {
    message,
    page,
    history: history.slice(-MAX_HISTORY).map(({ role, content, products }) => ({
      role,
      // Tell the agent which products the shopper was shown, so "is the first one in M?" works.
      content: products?.length
        ? `${content}\n[Products shown: ${products.map((p) => p.product_id).join(', ')}]`
        : content,
    })),
  })
}
