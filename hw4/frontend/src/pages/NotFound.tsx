import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="container prose">
      <h1>Page not found</h1>
      <p>
        That page doesn't exist. <Link to="/products">Browse all products</Link> instead.
      </p>
    </div>
  )
}
