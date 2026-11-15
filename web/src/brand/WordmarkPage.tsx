import { AegisWordmark } from './AegisWordmark'
import { SiteNav } from './SiteNav'

// TEMPORARY: compare the two wordmark splits at every size. Remove once one is chosen.
export function WordmarkPage() {
  const sizes = ['hero', 'card', 'nav'] as const
  return (
    <main className="mx-auto flex max-w-6xl flex-col gap-10 px-[5vw] py-8">
      <SiteNav section="Wordmark" />
      <h1 className="title">Choose a split</h1>
      {(['g', 'word'] as const).map((split) => (
        <section key={split} aria-label={`split ${split}`} className="glass flex flex-col gap-6 rounded-2xl p-8">
          <h2 className="text-[17px] font-semibold text-mist">
            split="{split}" {split === 'g' ? '(only the g is split)' : '(the whole word is one split shape)'}
          </h2>
          {sizes.map((size) => (
            <div key={size} className="flex items-baseline gap-6">
              <span className="w-12 text-[14px] text-mist">{size}</span>
              <AegisWordmark size={size} split={split} />
            </div>
          ))}
        </section>
      ))}
    </main>
  )
}
