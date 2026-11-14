import { useSearchParams } from 'react-router'
import { feedFromSearch, useEvents } from '../events/useEvents'
import type { Role } from '../events/types'

// Placeholder for /elder, /family and /evidence: lists incoming events, nothing else yet.
export function EventLog({ title, role }: { title: string; role: Role }) {
  const [search] = useSearchParams()
  const feed = feedFromSearch(search, role)
  const { events, connection, error } = useEvents(feed)

  return (
    <main>
      <h1>{title}</h1>
      <p>
        Source:{' '}
        {feed.kind === 'fixture'
          ? `fixture "${feed.name}" (sample data, ${feed.speed}x)`
          : feed.kind === 'live'
            ? `live session "${feed.sessionId}" as ${feed.role}`
            : 'none. Add ?fixture=scam-grandson or ?session=<id>&token=<token>'}
        {' · '}
        {connection}
        {error ? ` · ${error}` : ''}
        {' · '}
        {events.length} events
      </p>
      <ol>
        {events.map((e, i) => (
          <li key={i}>
            <code>{JSON.stringify(e)}</code>
          </li>
        ))}
      </ol>
    </main>
  )
}
