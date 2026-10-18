/**
 * Problem 10: banner illustrations for sport and field-of-study themes.
 * Sports get their playing surface (rink, field, court, water, track, diamond, green);
 * schools and majors get a scene from that profession with a professional at work.
 * Original vector art in the Yale palette.
 */

import type { ReactElement } from 'react'

const BLUE = '#00356B'
const MID = '#286DC0'
const LIGHT = '#63AAFF'
const GREEN = '#5F712D'
const ORANGE = '#BD5319'
const STONE = '#978D85'
const PAPER = '#F9F9F9'
const INK = '#222222'

type Outfit = { coat: string; shirt: string; prop?: 'briefcase' | 'book' | 'clipboard' | 'stethoscope' | 'baton' | 'brush' | 'roll' }

/** A professional figure (the "person in that field" the shopper is chatting with). */
function Pro({ x, outfit, skin = '#D9A57B' }: { x: number; outfit: Outfit; skin?: string }) {
  return (
    <g transform={`translate(${x} 0)`}>
      <rect x={-12} y={148} width={10} height={46} rx={4} fill={INK} />
      <rect x={2} y={148} width={10} height={46} rx={4} fill={INK} />
      <path d="M-24 104 Q-24 92 -12 90 L12 90 Q24 92 24 104 L22 152 L-22 152 Z" fill={outfit.coat} />
      <path d="M-6 90 L0 112 L6 90 Z" fill={outfit.shirt} />
      <rect x={-32} y={96} width={10} height={48} rx={5} fill={outfit.coat} transform="rotate(10 -27 98)" />
      <rect x={22} y={96} width={10} height={48} rx={5} fill={outfit.coat} transform="rotate(-10 27 98)" />
      <circle cx={0} cy={72} r={16} fill={skin} />
      <path d="M-16 70 Q-14 52 0 53 Q15 52 16 70 Q8 61 0 62 Q-8 61 -16 70 Z" fill={INK} />
      <path d="M-6 78 Q0 83 6 78" stroke={INK} strokeWidth={1.8} fill="none" strokeLinecap="round" />
      {outfit.prop === 'briefcase' && <g><rect x={26} y={140} width={26} height={20} rx={3} fill="#4A4A4A" /><path d="M33 140 v-5 h12 v5" stroke="#4A4A4A" strokeWidth={3} fill="none" /></g>}
      {outfit.prop === 'book' && <rect x={24} y={128} width={20} height={26} rx={2} fill={ORANGE} />}
      {outfit.prop === 'clipboard' && <g><rect x={24} y={124} width={20} height={28} rx={2} fill={PAPER} stroke={INK} /><path d="M28 132h12M28 138h12M28 144h8" stroke={STONE} /></g>}
      {outfit.prop === 'stethoscope' && <path d="M-8 92 Q-10 118 0 122 Q10 118 8 92 M0 122 V132" stroke={INK} strokeWidth={2.4} fill="none" />}
      {outfit.prop === 'baton' && <path d="M30 120 L58 92" stroke={PAPER} strokeWidth={3} strokeLinecap="round" />}
      {outfit.prop === 'brush' && <path d="M30 124 L54 98" stroke={ORANGE} strokeWidth={4} strokeLinecap="round" />}
      {outfit.prop === 'roll' && <rect x={24} y={128} width={34} height={9} rx={4} fill={LIGHT} />}
    </g>
  )
}

function Field({ lines = true, posts = false, goal = false }: { lines?: boolean; posts?: boolean; goal?: boolean }) {
  return (
    <g>
      <rect width="600" height="200" fill={GREEN} />
      {[0, 1, 2, 3, 4, 5, 6].map((i) => <rect key={i} x={i * 90} width="45" height="200" fill="#56662a" />)}
      {lines && [60, 150, 240, 330, 420, 510].map((x) => <rect key={x} x={x} y="20" width="3" height="160" fill={PAPER} opacity="0.85" />)}
      {posts && <path d="M560 40 V110 M540 40 V70 H580 V40" stroke="#F6D58E" strokeWidth="5" fill="none" />}
      {goal && <rect x="548" y="70" width="40" height="60" fill="none" stroke={PAPER} strokeWidth="4" />}
    </g>
  )
}

function Rink() {
  return (
    <g>
      <rect width="600" height="200" fill="#EEF4FB" />
      <rect x="296" width="8" height="200" fill="#B5121B" opacity="0.7" />
      <rect x="180" width="8" height="200" fill={MID} />
      <rect x="412" width="8" height="200" fill={MID} />
      <circle cx="300" cy="100" r="44" fill="none" stroke={MID} strokeWidth="4" />
      <circle cx="300" cy="100" r="5" fill={BLUE} />
      <rect x="548" y="74" width="34" height="52" fill="none" stroke="#B5121B" strokeWidth="4" />
    </g>
  )
}

function Court({ color = '#C8915A', net = false }: { color?: string; net?: boolean }) {
  return (
    <g>
      <rect width="600" height="200" fill={color} />
      {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11].map((i) => <rect key={i} x={i * 50} width="2" height="200" fill="#00000014" />)}
      <rect x="20" y="20" width="560" height="160" fill="none" stroke={PAPER} strokeWidth="4" />
      <path d="M300 20 V180" stroke={PAPER} strokeWidth="4" />
      <circle cx="300" cy="100" r="36" fill="none" stroke={PAPER} strokeWidth="4" />
      {net && <path d="M300 10 V190" stroke={INK} strokeWidth="6" strokeDasharray="3 3" />}
    </g>
  )
}

function Water({ boat = false, lanes = false, sail = false }: { boat?: boolean; lanes?: boolean; sail?: boolean }) {
  return (
    <g>
      <rect width="600" height="200" fill={MID} />
      {[30, 70, 110, 150].map((y) => (
        <path key={y} d={`M0 ${y} q25 -10 50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0`} stroke={LIGHT} strokeWidth="3" fill="none" opacity="0.7" />
      ))}
      {lanes && [50, 100, 150].map((y) => <path key={y} d={`M0 ${y} H600`} stroke={ORANGE} strokeWidth="4" strokeDasharray="10 8" />)}
      {boat && <g><path d="M120 120 H520 L500 134 H140 Z" fill={PAPER} />{[180, 260, 340, 420].map((x) => <path key={x} d={`M${x} 120 L${x - 30} 160`} stroke={INK} strokeWidth="3" />)}</g>}
      {sail && <g><path d="M300 150 H420 L404 168 H316 Z" fill={PAPER} /><path d="M360 146 V40 L420 140 Z" fill={PAPER} /><path d="M356 146 V60 L310 140 Z" fill={LIGHT} /></g>}
    </g>
  )
}

function Track() {
  return (
    <g>
      <rect width="600" height="200" fill={GREEN} />
      {[0, 1, 2, 3].map((i) => (
        <rect key={i} x={30 + i * 14} y={20 + i * 14} width={540 - i * 28} height={160 - i * 28} rx={(80 - i * 14)} fill="none" stroke={i % 2 ? '#c4581f' : ORANGE} strokeWidth="14" />
      ))}
      <path d="M300 20 V76" stroke={PAPER} strokeWidth="3" />
    </g>
  )
}

function Diamond() {
  return (
    <g>
      <rect width="600" height="200" fill={GREEN} />
      <path d="M300 30 L400 110 L300 190 L200 110 Z" fill="#C8915A" />
      <path d="M300 60 L362 110 L300 160 L238 110 Z" fill={GREEN} />
      {[[300, 30], [400, 110], [200, 110], [300, 190]].map(([x, y]) => <rect key={`${x}${y}`} x={x - 6} y={y - 6} width="12" height="12" fill={PAPER} transform={`rotate(45 ${x} ${y})`} />)}
    </g>
  )
}

function Golf() {
  return (
    <g>
      <rect width="600" height="200" fill={GREEN} />
      <ellipse cx="420" cy="130" rx="170" ry="54" fill="#6f8536" />
      <path d="M440 130 V40 L490 56 L440 72" stroke={PAPER} strokeWidth="3" fill={ORANGE} />
      <circle cx="440" cy="132" r="5" fill={INK} />
    </g>
  )
}

function Strip() {
  // fencing piste
  return (
    <g>
      <rect width="600" height="200" fill={BLUE} />
      <rect x="20" y="80" width="560" height="40" fill="#DDDDDD" />
      {[120, 300, 480].map((x) => <rect key={x} x={x} y="80" width="3" height="40" fill={ORANGE} />)}
      <path d="M200 60 L360 140 M400 60 L240 140" stroke={PAPER} strokeWidth="3" />
    </g>
  )
}

function Skyline() {
  return (
    <g fill="#1d4f86">
      {[[20, 70], [70, 100], [130, 50], [180, 120], [250, 80], [310, 140], [380, 60], [430, 110], [500, 90], [550, 130]].map(([x, h]) => (
        <rect key={x} x={x} y={200 - h} width="44" height={h} />
      ))}
    </g>
  )
}

function Columns() {
  return (
    <g>
      <path d="M180 40 L420 40 L440 60 H160 Z" fill={STONE} />
      {[180, 230, 280, 330, 380].map((x) => <rect key={x} x={x} y="60" width="22" height="110" fill="#DDDDDD" />)}
      <rect x="160" y="170" width="280" height="14" fill={STONE} />
    </g>
  )
}

const FIELD_SCENES: Record<string, { bg: string; backdrop: ReactElement; pros: Outfit[] }> = {
  management: { bg: BLUE, backdrop: <Skyline />, pros: [{ coat: '#222222', shirt: PAPER, prop: 'briefcase' }, { coat: MID, shirt: PAPER, prop: 'clipboard' }] },
  law: { bg: '#2b2b2b', backdrop: <Columns />, pros: [{ coat: '#222222', shirt: PAPER, prop: 'book' }, { coat: BLUE, shirt: PAPER, prop: 'briefcase' }] },
  medicine: { bg: '#e8f0f8', backdrop: <g><rect x="250" y="40" width="100" height="100" rx="12" fill={PAPER} /><path d="M300 60 V120 M270 90 H330" stroke={MID} strokeWidth="18" /></g>, pros: [{ coat: PAPER, shirt: LIGHT, prop: 'stethoscope' }, { coat: PAPER, shirt: BLUE, prop: 'clipboard' }] },
  nursing: { bg: '#e8f0f8', backdrop: <path d="M300 150 C220 100 230 40 280 50 Q300 56 300 76 Q300 56 320 50 C370 40 380 100 300 150 Z" fill={LIGHT} />, pros: [{ coat: MID, shirt: PAPER, prop: 'stethoscope' }, { coat: LIGHT, shirt: PAPER, prop: 'clipboard' }] },
  'public-health': { bg: '#dce9f6', backdrop: <g><circle cx="300" cy="96" r="62" fill={LIGHT} /><path d="M238 96 H362 M300 34 V158 M256 56 Q300 96 256 136 M344 56 Q300 96 344 136" stroke={PAPER} strokeWidth="3" fill="none" /></g>, pros: [{ coat: GREEN, shirt: PAPER, prop: 'clipboard' }, { coat: MID, shirt: PAPER, prop: 'book' }] },
  engineering: { bg: '#2b2b2b', backdrop: <g fill="none" stroke={LIGHT} strokeWidth="10"><circle cx="270" cy="90" r="40" /><circle cx="350" cy="120" r="26" /></g>, pros: [{ coat: ORANGE, shirt: PAPER, prop: 'roll' }, { coat: '#4A4A4A', shirt: PAPER, prop: 'clipboard' }] },
  architecture: { bg: BLUE, backdrop: <g stroke={LIGHT} strokeWidth="1" opacity="0.6">{Array.from({ length: 24 }, (_, i) => <path key={i} d={`M${i * 25} 0 V200`} />)}{Array.from({ length: 8 }, (_, i) => <path key={i} d={`M0 ${i * 25} H600`} />)}<path d="M240 180 V90 Q300 20 360 90 V180" stroke={PAPER} strokeWidth="4" fill="none" /></g>, pros: [{ coat: '#222222', shirt: PAPER, prop: 'roll' }, { coat: STONE, shirt: PAPER, prop: 'clipboard' }] },
  art: { bg: '#f3ece4', backdrop: <g><ellipse cx="300" cy="96" rx="90" ry="60" fill={STONE} />{[[250, 80, ORANGE], [290, 60, MID], [335, 75, GREEN], [345, 115, LIGHT], [270, 120, BLUE]].map(([x, y, c]) => <circle key={`${x}`} cx={x as number} cy={y as number} r="14" fill={c as string} />)}</g>, pros: [{ coat: GREEN, shirt: PAPER, prop: 'brush' }, { coat: ORANGE, shirt: PAPER, prop: 'brush' }] },
  music: { bg: BLUE, backdrop: <g stroke={PAPER} strokeWidth="2" opacity="0.8">{[50, 65, 80, 95, 110].map((y) => <path key={y} d={`M60 ${y} H540`} />)}{[150, 230, 330, 430].map((x, i) => <g key={x}><ellipse cx={x} cy={95 - i * 8} rx="9" ry="7" fill={PAPER} /><path d={`M${x + 8} ${95 - i * 8} V${50 - i * 8}`} /></g>)}</g>, pros: [{ coat: '#222222', shirt: PAPER, prop: 'baton' }, { coat: '#222222', shirt: PAPER, prop: 'book' }] },
  divinity: { bg: '#2b2b2b', backdrop: <g><circle cx="300" cy="90" r="64" fill={MID} />{Array.from({ length: 8 }, (_, i) => <path key={i} d={`M300 90 L${300 + 64 * Math.cos((i * Math.PI) / 4)} ${90 + 64 * Math.sin((i * Math.PI) / 4)}`} stroke="#F6D58E" strokeWidth="4" />)}<circle cx="300" cy="90" r="18" fill="#F6D58E" /></g>, pros: [{ coat: '#222222', shirt: PAPER, prop: 'book' }, { coat: STONE, shirt: PAPER, prop: 'book' }] },
  environment: { bg: '#dfe8cf', backdrop: <g fill={GREEN}>{[120, 200, 290, 380, 460].map((x, i) => <path key={x} d={`M${x} ${40 + (i % 2) * 20} L${x + 40} 180 H${x - 40} Z`} />)}</g>, pros: [{ coat: GREEN, shirt: PAPER, prop: 'clipboard' }, { coat: '#4A4A4A', shirt: PAPER, prop: 'book' }] },
}

function SportSurface({ sport }: { sport: string }) {
  switch (sport) {
    case 'hockey': return <Rink />
    case 'football': return <Field posts />
    case 'soccer': case 'lacrosse': case 'field-hockey': return <Field goal />
    case 'basketball': return <Court />
    case 'volleyball': return <Court color="#2f6fb5" net />
    case 'tennis': return <Court color={GREEN} net />
    case 'squash': return <Court color="#d9b48a" />
    case 'baseball': return <Diamond />
    case 'crew': return <Water boat />
    case 'sailing': return <Water sail />
    case 'swimming': return <Water lanes />
    case 'track': return <Track />
    case 'golf': return <Golf />
    case 'fencing': return <Strip />
    default: return <Field />
  }
}

export default function ThemeArt({ scene, label }: { scene: string; label: string }) {
  const [kind, ...rest] = scene.split('-')
  const key = rest.join('-')
  if (kind === 'sport') {
    return (
      <svg className="theme-art" viewBox="0 0 600 200" preserveAspectRatio="xMidYMid slice" role="img" aria-label={`${label} illustration`}>
        <SportSurface sport={key} />
      </svg>
    )
  }
  const s = FIELD_SCENES[key] ?? FIELD_SCENES.management
  return (
    <svg className="theme-art" viewBox="0 0 600 200" preserveAspectRatio="xMidYMid slice" role="img" aria-label={`${label} illustration with professionals at work`}>
      <rect width="600" height="200" fill={s.bg} />
      {s.backdrop}
      <g transform="translate(0 6)">
        {/* Kept near the middle: the banner crops the sides of this 600-wide drawing. */}
        <Pro x={220} outfit={s.pros[0]} skin="#8D5A3B" />
        <Pro x={380} outfit={s.pros[1]} skin="#F1C7A3" />
      </g>
    </svg>
  )
}
