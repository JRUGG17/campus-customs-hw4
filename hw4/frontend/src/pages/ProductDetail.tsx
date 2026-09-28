import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchProduct, formatPrice, type ProductDetail as Product } from '../api'

function stockLabel(quantity: number) {
  if (quantity === 0) return { text: 'Sold out', className: 'stock-out' }
  if (quantity <= 5) return { text: `Only ${quantity} left`, className: 'stock-low' }
  return { text: `${quantity} in stock`, className: 'stock-ok' }
}

export default function ProductDetail() {
  const { productId = '' } = useParams()
  const [product, setProduct] = useState<Product | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setProduct(null)
    setError(null)
    fetchProduct(productId)
      .then(setProduct)
      .catch((e: Error) => setError(e.message))
  }, [productId])

  if (error) {
    return (
      <div className="container">
        <p className="error">We couldn't find that product.</p>
        <Link to="/products">← Back to all products</Link>
      </div>
    )
  }
  if (!product) return <div className="container muted">Loading…</div>

  return (
    <div className="container">
      <Link to="/products" className="back-link">
        ← All products
      </Link>
      <div className="product-detail">
        <div className="product-detail-image">
          <img src={product.image_url} alt={product.name} />
        </div>
        <div className="product-detail-info">
          <p className="eyebrow">{product.garment_type}</p>
          <h1>{product.name}</h1>
          <p className="price price-large">{formatPrice(product.price)}</p>
          <p>{product.description}</p>

          <h3>Colors in this design</h3>
          <div className="chips">
            {product.colors.map((c) => (
              <span key={c} className="chip">
                {c}
              </span>
            ))}
          </div>

          <h3>Sizes &amp; stock</h3>
          <table className="stock-table">
            <tbody>
              {product.sizes.map((s) => {
                const label = stockLabel(s.quantity)
                return (
                  <tr key={s.size}>
                    <th>{s.size}</th>
                    <td className={label.className}>{label.text}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          <p className="muted small">
            {product.total_stock} total in stock across all sizes.
          </p>
        </div>
      </div>
    </div>
  )
}
