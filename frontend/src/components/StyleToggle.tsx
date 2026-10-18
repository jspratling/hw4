/** Problem 9: All styles / Casual / Formal toggle, driven by the backend's style tags. */
export type StyleChoice = 'All' | 'Casual' | 'Formal'

const OPTIONS: { value: StyleChoice; label: string; hint: string }[] = [
  { value: 'All', label: 'All styles', hint: 'Everything we carry' },
  { value: 'Casual', label: 'Casual', hint: 'Hoodies, tees and everyday crewnecks' },
  { value: 'Formal', label: 'Formal', hint: 'Quarter-zips, fleece and jackets for events and interviews' },
]

export default function StyleToggle({
  value,
  onChange,
}: {
  value: StyleChoice
  onChange: (value: StyleChoice) => void
}) {
  return (
    <div className="style-toggle" role="radiogroup" aria-label="Style">
      {OPTIONS.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={value === o.value}
          title={o.hint}
          className={value === o.value ? 'style-option selected' : 'style-option'}
          onClick={() => onChange(o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}
