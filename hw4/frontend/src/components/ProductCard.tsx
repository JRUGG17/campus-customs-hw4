import type { CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import { formatPrice, type ProductSummary } from '../api'

const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']

/**
 * A product card that feels like picking up a folded garment: it lifts slowly with a deep
 * shadow, the photo leans in, the price hangs on a clothing tag, and hovering reveals which
 * sizes are in stock. `index` staggers the entrance animation across a grid.
 */
export default function ProductCard({ product, index = 0 }: { product: ProductSummary; index?: number }) {
  const inStock = new Set(product.sizes_in_stock)
  const soldOut = product.total_stock === 0
  return (
    <Link
      to={`/products/${product.product_id}`}
      className="product-card"
      style={{ '--i': Math.min(index, 11) } as CSSProperties}
    >
      <div className="product-card-image">
        <img src={product.image_url} alt={product.name} loading="lazy" />
        <span className="hang-tag" aria-label={`Price ${formatPrice(product.price)}`}>
          {formatPrice(product.price)}
        </span>
        <div className="size-strip" aria-label={`Sizes in stock: ${product.sizes_in_stock.join(', ') || 'none'}`}>
          {soldOut ? (
            <span className="size-strip-note">Sold out</span>
          ) : (
            SIZES.map((s) => (
              <span key={s} className={inStock.has(s) ? 'in' : 'out'}>
                {s}
              </span>
            ))
          )}
        </div>
      </div>
      <div className="product-card-body">
        <p className="product-card-type">{product.garment_type}</p>
        <h3>{product.name}</h3>
        <p className="product-card-desc">{product.short_description}</p>
      </div>
    </Link>
  )
}
