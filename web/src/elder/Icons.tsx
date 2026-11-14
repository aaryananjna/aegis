// Simple line icons, drawn inline so nothing loads from the network.
const common = {
  width: '1em',
  height: '1em',
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': true,
} as const

export function KeyIcon() {
  return (
    <svg {...common}>
      <circle cx="7.5" cy="15.5" r="4.5" />
      <path d="M10.7 12.3 20 3M16 7l3 3M14 9l2 2" />
    </svg>
  )
}

export function ShieldIcon() {
  return (
    <svg {...common}>
      <path d="M12 3 4 6v6c0 4.5 3.4 8.3 8 9 4.6-.7 8-4.5 8-9V6l-8-3Z" />
      <path d="M12 8v5M12 16.5v.01" />
    </svg>
  )
}

export function PhoneDownIcon() {
  return (
    <svg {...common}>
      <path d="M3 14.5c5-4.7 13-4.7 18 0l-2 2.5-3.5-1.5V12.6a14 14 0 0 0-7 0v2.9L5 17l-2-2.5Z" />
      <path d="M12 3v4M8.5 4.5 10 7.5M15.5 4.5 14 7.5" />
    </svg>
  )
}

export function PhoneIcon() {
  return (
    <svg {...common}>
      <path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2Z" />
    </svg>
  )
}

export function CheckIcon() {
  return (
    <svg {...common}>
      <path d="m4 12.5 5 5L20 6.5" />
    </svg>
  )
}
