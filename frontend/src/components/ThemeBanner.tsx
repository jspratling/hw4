import type { Theme } from '../types'
import ThemeArt from './ThemeArt'

/**
 * Problem 10: banner shown when a search is about a sport or a field of study.
 * Sports show their playing surface; schools and majors show professionals at work.
 */
export default function ThemeBanner({ theme, onClear }: { theme: Theme; onClear?: () => void }) {
  return (
    <section className={`theme-banner theme-${theme.kind}`} aria-label={`${theme.label} theme`}>
      <ThemeArt scene={theme.scene} label={theme.label} />
      <div className="theme-banner-text">
        <p className="theme-banner-kicker">{theme.kind === 'sport' ? 'Team spirit' : 'Field of study'}</p>
        <h2>{theme.label}</h2>
        <p className="theme-banner-tagline">{theme.tagline}</p>
        <p className="theme-banner-persona">
          Chat with {theme.persona}, our {theme.persona_role}, in the corner.
        </p>
      </div>
      {onClear && (
        <button type="button" className="theme-banner-close" onClick={onClear} aria-label="Hide theme">
          ×
        </button>
      )}
    </section>
  )
}
