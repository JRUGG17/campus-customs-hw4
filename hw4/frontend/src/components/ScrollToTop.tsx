import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

/**
 * Start each page at the top, like a normal website. Only the path is watched, so changes
 * that just touch the query string (Products filters, tabs, search) keep your place.
 */
export default function ScrollToTop() {
  const { pathname } = useLocation()

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])

  return null
}
