import { useEffect, useRef } from 'react'

/**
 * Problem 10: cards rise into place the first time a row scrolls into view (one staggered
 * motion per row). Skipped entirely when the shopper prefers reduced motion.
 */
export function useReveal<T extends HTMLElement>(deps: unknown[] = []) {
  const ref = useRef<T>(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches || !('IntersectionObserver' in window)) {
      el.classList.add('revealed')
      return
    }
    el.classList.add('reveal')
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          el.classList.add('revealed')
          io.disconnect()
        }
      },
      { threshold: 0.12 },
    )
    io.observe(el)
    return () => io.disconnect()
  }, deps) // eslint-disable-line react-hooks/exhaustive-deps
  return ref
}
