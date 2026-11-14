// The Aegis wordmark: "Ae" white, "g" split white/cyan on the diagonal, "is" cyan.
// Text, not an image, so it scales with font-size and screen readers read "Aegis".
export function Wordmark({ className = '' }: { className?: string }) {
  return (
    <span
      className={`inline-flex items-baseline font-extrabold tracking-[-0.03em] ${className}`}
      aria-label="Aegis"
      role="img"
    >
      <span aria-hidden style={{ color: '#FFFFFF' }}>Ae</span>
      <span
        aria-hidden
        style={{
          backgroundImage: 'linear-gradient(135deg, #FFFFFF 49.5%, #00D4FF 50.5%)',
          WebkitBackgroundClip: 'text',
          backgroundClip: 'text',
          color: 'transparent',
        }}
      >
        g
      </span>
      <span aria-hidden style={{ color: '#00D4FF' }}>is</span>
    </span>
  )
}
