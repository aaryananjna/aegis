// The Aegis wordmark. Accessible name "Aegis"; everything drawn inside is aria-hidden.
// split="g": "Ae" light, the g split on the diagonal (upper-left light, lower-right blue), "is" blue.
// split="word": the whole word split as one shape.
// The split is two copies of the text: the span in blue, and a ::before copy in the light color
// clipped to the upper-left triangle (see .wm-split in index.css). No background-clip.
type Size = 'hero' | 'nav' | 'card'

export function AegisWordmark({
  size = 'nav',
  split = 'g',
  className = '',
}: {
  size?: Size
  split?: 'g' | 'word'
  className?: string
}) {
  return (
    <span role="img" aria-label="Aegis" className={`wm wm-${size} ${className}`}>
      {split === 'word' ? (
        <span aria-hidden className="wm-split" data-text="Aegis">
          Aegis
        </span>
      ) : (
        <>
          <span aria-hidden className="wm-light">Ae</span>
          <span aria-hidden className="wm-split" data-text="g">
            g
          </span>
          <span aria-hidden className="wm-blue">is</span>
        </>
      )}
    </span>
  )
}
