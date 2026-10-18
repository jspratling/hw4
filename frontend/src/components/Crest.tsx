/** Problem 10: original Campus Customs crest (not a Yale mark): shield, chevron, open book, CC. */
export default function Crest({ size = 40 }: { size?: number }) {
  return (
    <svg className="crest" width={size} height={size * 1.15} viewBox="0 0 40 46" aria-hidden="true">
      <path d="M4 3 H36 V22 C36 34 28 40 20 44 C12 40 4 34 4 22 Z" fill="#00356B" stroke="#F9F9F9" strokeWidth="1.6" />
      <path d="M4 3 H36 V22 C36 34 28 40 20 44 C12 40 4 34 4 22 Z" fill="none" stroke="#63AAFF" strokeWidth="0.8" transform="translate(2.2 2.4) scale(0.89)" />
      <path d="M8 21 L20 13 L32 21" stroke="#F9F9F9" strokeWidth="2.6" fill="none" />
      <path d="M12 26 Q16 24 20 26 Q24 24 28 26 V33 Q24 31 20 33 Q16 31 12 33 Z" fill="#F9F9F9" />
      <path d="M20 26 V33" stroke="#00356B" strokeWidth="0.8" />
      <text x="20" y="11" textAnchor="middle" fontSize="7" fontFamily="Graduate, serif" fill="#F9F9F9">CC</text>
    </svg>
  )
}
