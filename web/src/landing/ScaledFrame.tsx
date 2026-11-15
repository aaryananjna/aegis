import { useEffect, useRef, useState } from 'react'

/**
 * Shows a page at its real width (e.g. the 1280 px laptop or 390 px phone) scaled down to fit
 * its box, so the demo looks exactly like the real screen instead of a squeezed layout.
 * `height` fixes the screen's height; `fit` instead makes the frame exactly as tall as the page
 * inside it, so an empty phone is short and it grows as alerts arrive.
 */
export function ScaledFrame({
  src,
  title,
  width,
  height,
  fit = false,
  className = '',
}: {
  src: string
  title: string
  width: number
  height: number
  fit?: boolean
  className?: string
}) {
  const box = useRef<HTMLDivElement>(null)
  const frame = useRef<HTMLIFrameElement>(null)
  const [scale, setScale] = useState(0.5)
  const [inner, setInner] = useState(fit ? 320 : height) // the page's own height, unscaled

  useEffect(() => {
    const el = box.current
    if (!el) return
    const ro = new ResizeObserver(([e]) => setScale(e.contentRect.width / width))
    ro.observe(el)
    return () => ro.disconnect()
  }, [width])

  // The framed page takes the theme in force out here (it may not have been saved).
  useEffect(() => {
    const f = frame.current
    if (!f) return
    const copy = () => {
      const theme = document.documentElement.dataset.theme
      const root = f.contentDocument?.documentElement
      if (theme && root) root.dataset.theme = theme
    }
    f.addEventListener('load', copy)
    return () => f.removeEventListener('load', copy)
  }, [])

  // Same-origin page: watch its content and size the frame to it.
  useEffect(() => {
    const f = frame.current
    if (!fit || !f) return
    let ro: ResizeObserver | null = null
    const watch = () => {
      ro?.disconnect()
      const root = f.contentDocument?.getElementById('root')
      if (!root) return
      ro = new ResizeObserver(() => setInner(Math.ceil(root.getBoundingClientRect().height)))
      ro.observe(root)
    }
    f.addEventListener('load', watch)
    watch()
    return () => {
      f.removeEventListener('load', watch)
      ro?.disconnect()
    }
  }, [fit])

  const h = fit ? inner : height
  return (
    <div
      ref={box}
      className={`glass relative overflow-hidden motion-safe:transition-[height] motion-safe:duration-500 ${className}`}
      style={fit ? { height: h * scale } : { aspectRatio: `${width} / ${height}` }}
    >
      <iframe
        ref={frame}
        src={src}
        title={title}
        width={width}
        height={h}
        className="absolute top-0 left-0 origin-top-left border-0"
        style={{ transform: `scale(${scale})` }}
      />
    </div>
  )
}
