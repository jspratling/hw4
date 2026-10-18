import { useState, type MouseEvent } from 'react'

/**
 * Problem 9: product photo that magnifies wherever the mouse points, so shoppers can
 * inspect lettering, crests and fabric. On touch screens it simply shows the photo.
 */
export default function ZoomImage({ src, alt }: { src: string; alt: string }) {
  const [origin, setOrigin] = useState<string | null>(null)

  function move(e: MouseEvent<HTMLDivElement>) {
    const box = e.currentTarget.getBoundingClientRect()
    const x = ((e.clientX - box.left) / box.width) * 100
    const y = ((e.clientY - box.top) / box.height) * 100
    setOrigin(`${x}% ${y}%`)
  }

  return (
    <div
      className={origin ? 'zoom-image zoomed' : 'zoom-image'}
      onMouseMove={move}
      onMouseLeave={() => setOrigin(null)}
    >
      <img src={src} alt={alt} style={origin ? { transformOrigin: origin } : undefined} />
      <span className="zoom-hint" aria-hidden="true">
        Hover to zoom
      </span>
    </div>
  )
}
