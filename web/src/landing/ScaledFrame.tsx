import { useEffect, useRef, useState } from 'react'

/**
 * Shows a page at its real size (e.g. the 1280×800 laptop or 390×844 phone) scaled down to fit
 * its box, so the demo looks exactly like the real screen instead of a squeezed layout.
 */
export function ScaledFrame({
  src,
  title,
  width,
  height,
  className = '',
}: {
  src: string
  title: string
  width: number
  height: number
  className?: string
}) {
  const box = useRef<HTMLDivElement>(null)
  const [scale, setScale] = useState(0.5)

  useEffect(() => {
    const el = box.current
    if (!el) return
    const ro = new ResizeObserver(([e]) => setScale(e.contentRect.width / width))
    ro.observe(el)
    return () => ro.disconnect()
  }, [width])

  return (
    <div
      ref={box}
      className={`glass relative overflow-hidden ${className}`}
      style={{ aspectRatio: `${width} / ${height}` }}
    >
      <iframe
        src={src}
        title={title}
        width={width}
        height={height}
        className="absolute top-0 left-0 origin-top-left border-0"
        style={{ transform: `scale(${scale})` }}
      />
    </div>
  )
}
