/**
 * Problem 10: the home page's campus at dusk — Gothic towers, lit windows, ivy, and three
 * happy students in Campus Customs gear. Original vector art drawn for this site (no photos or
 * trademarked marks), in the Yale palette.
 */

type StudentProps = {
  x: number
  skin: string
  hair: string
  top: string
  topText: string
  textColor: string
  pants: string
  scale?: number
  wave?: boolean
  pennant?: boolean
  hood?: boolean
  long?: boolean // long hair
}

function Student({ x, skin, hair, top, topText, textColor, pants, scale = 1, wave, pennant, hood, long }: StudentProps) {
  return (
    <g transform={`translate(${x} 0) scale(${scale})`} className="student">
      {/* legs */}
      <rect x={-17} y={420} width={14} height={78} rx={6} fill={pants} />
      <rect x={3} y={420} width={14} height={78} rx={6} fill={pants} />
      <ellipse cx={-10} cy={500} rx={13} ry={6} fill="#222222" />
      <ellipse cx={10} cy={500} rx={13} ry={6} fill="#222222" />
      {/* arms */}
      <rect x={-44} y={330} width={16} height={74} rx={8} fill={top} transform={wave ? 'rotate(150 -36 336)' : 'rotate(8 -36 336)'} />
      <rect x={28} y={330} width={16} height={74} rx={8} fill={top} transform={pennant ? 'rotate(-150 36 336)' : 'rotate(-8 36 336)'} />
      {/* hands sit at the end of each arm (arms rotate around the shoulders) */}
      <circle cx={wave ? -70 : -46} cy={wave ? 274 : 404} r={8} fill={skin} />
      <circle cx={pennant ? 70 : 46} cy={pennant ? 274 : 404} r={8} fill={skin} />
      {pennant && (
        <g>
          <rect x={68} y={196} width={4} height={92} fill="#978D85" />
          <path d="M72 198 L156 214 L72 232 Z" fill="#00356B" />
          <text x={80} y={219} fontSize={11} fontFamily="Graduate, serif" fill="#FFFFFF">GO YALE</text>
        </g>
      )}
      {/* body */}
      <path d={`M-32 340 Q-34 322 -16 318 L16 318 Q34 322 32 340 L30 428 Q0 436 -30 428 Z`} fill={top} />
      {hood && <path d="M-20 318 Q0 342 20 318 Q12 306 0 306 Q-12 306 -20 318 Z" fill={top} stroke="#00000022" />}
      <text x={0} y={378} textAnchor="middle" fontSize={topText.length > 5 ? 10 : 15} fontFamily="Graduate, serif" fill={textColor}>
        {topText}
      </text>
      {/* head */}
      <rect x={-6} y={300} width={12} height={14} fill={skin} />
      <circle cx={0} cy={282} r={24} fill={skin} />
      <path
        d={long ? 'M-26 286 Q-28 252 0 254 Q28 252 26 286 L26 318 Q18 300 18 278 Q0 268 -18 278 Q-18 300 -26 318 Z' : 'M-25 280 Q-24 254 0 255 Q26 254 25 280 Q16 266 0 267 Q-16 266 -25 280 Z'}
        fill={hair}
      />
      <circle cx={-8} cy={284} r={2.6} fill="#222222" />
      <circle cx={8} cy={284} r={2.6} fill="#222222" />
      <path d="M-9 293 Q0 302 9 293" stroke="#222222" strokeWidth={2.4} fill="none" strokeLinecap="round" />
      <circle cx={-14} cy={292} r={4} fill="#BD5319" opacity={0.18} />
      <circle cx={14} cy={292} r={4} fill="#BD5319" opacity={0.18} />
    </g>
  )
}

function Window({ x, y, w = 14, h = 30 }: { x: number; y: number; w?: number; h?: number }) {
  return <path d={`M${x} ${y + h} V${y + w / 2} Q${x + w / 2} ${y - w / 3} ${x + w} ${y + w / 2} V${y + h} Z`} className="lit-window" />
}

export default function CampusScene() {
  return (
    <svg className="campus-scene" viewBox="0 0 1200 520" preserveAspectRatio="xMidYMax slice" role="img"
      aria-label="Illustration of a Gothic college campus at dusk with three smiling students in Campus Customs hoodies">
      <defs>
        <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#00356B" />
          <stop offset="0.55" stopColor="#286DC0" />
          <stop offset="0.85" stopColor="#63AAFF" />
          <stop offset="1" stopColor="#E9C9A6" />
        </linearGradient>
        <linearGradient id="stone" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#4A4A4A" />
          <stop offset="1" stopColor="#222222" />
        </linearGradient>
        <linearGradient id="lawn" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#5F712D" />
          <stop offset="1" stopColor="#3d4a1c" />
        </linearGradient>
      </defs>
      <rect width="1200" height="520" fill="url(#sky)" />
      {/* stars */}
      {[[80, 40], [190, 90], [320, 30], [470, 70], [640, 28], [760, 96], [900, 44], [1040, 80], [1150, 30], [560, 120]].map(([x, y]) => (
        <circle key={`${x}-${y}`} cx={x} cy={y} r={1.6} fill="#FFFFFF" opacity={0.75} />
      ))}
      <circle cx="1030" cy="110" r="26" fill="#F9F9F9" opacity="0.9" />
      <circle cx="1040" cy="104" r="24" fill="#286DC0" opacity="0.35" />

      {/* distant rooftops */}
      <path d="M0 360 L60 340 L60 320 L90 320 L90 300 L110 300 L110 330 L170 330 L200 300 L230 330 L300 330 L300 310 L330 296 L360 310 L360 340 L470 340 L470 318 L520 318 L520 345 L640 345 L680 318 L720 345 L860 345 L860 322 L900 322 L900 300 L930 322 L930 345 L1200 345 L1200 520 L0 520 Z" fill="#1d4f86" opacity="0.55" />

      {/* left hall with crenellations */}
      <path d="M40 520 V330 h20 v-14 h16 v14 h20 v-14 h16 v14 h20 v-14 h16 v14 h20 v-14 h16 v14 h20 V520 Z" fill="url(#stone)" />
      {[60, 100, 140, 180].map((x) => <Window key={x} x={x} y={360} />)}
      {[60, 100, 140, 180].map((x) => <Window key={x} x={x} y={420} />)}

      {/* central Gothic tower */}
      <g>
        <path d="M470 520 V250 L480 236 V200 L500 180 L520 200 V236 L540 236 V200 L560 180 L580 200 V236 L600 250 V520 Z" fill="url(#stone)" />
        <path d="M480 236 L470 210 L478 210 Z M600 250 L606 214 L596 214 Z" fill="#4A4A4A" />
        {/* spires */}
        <path d="M486 200 L500 128 L514 200 Z M546 200 L560 128 L574 200 Z" fill="#4A4A4A" />
        <path d="M520 236 L535 96 L550 236 Z" fill="#222222" />
        <circle cx="535" cy="290" r="18" fill="#F6D58E" opacity="0.9" />
        <circle cx="535" cy="290" r="18" fill="none" stroke="#222222" strokeWidth="3" />
        <path d="M535 274 V306 M519 290 H551" stroke="#222222" strokeWidth="2" />
        <Window x={496} y={340} w={16} h={40} />
        <Window x={558} y={340} w={16} h={40} />
        {/* gate */}
        <path d="M505 520 V462 Q535 420 565 462 V520 Z" fill="#F6D58E" opacity="0.85" />
        <path d="M505 520 V462 Q535 420 565 462 V520" fill="none" stroke="#222222" strokeWidth="4" />
      </g>

      {/* right hall with gables */}
      <path d="M640 520 V350 L680 310 L720 350 L760 310 L800 350 L840 310 L880 350 V520 Z" fill="url(#stone)" />
      {[660, 700, 740, 780, 820, 852].map((x) => <Window key={x} x={x} y={385} w={12} h={26} />)}
      {[660, 700, 740, 780, 820, 852].map((x) => <Window key={x} x={x} y={440} w={12} h={26} />)}

      {/* far-right chapel */}
      <path d="M940 520 V340 L1000 290 L1060 340 V520 Z" fill="url(#stone)" />
      <circle cx="1000" cy="360" r="20" className="lit-window" />
      <path d="M1000 340 V380 M980 360 H1020" stroke="#222222" strokeWidth="2" />
      <Window x={975} y={410} w={14} h={36} />
      <Window x={1011} y={410} w={14} h={36} />

      {/* ivy */}
      <g fill="#5F712D">
        {[[48, 360], [60, 395], [52, 430], [70, 470], [215, 380], [228, 420], [222, 460], [474, 400], [480, 440], [594, 420], [600, 470], [646, 400], [652, 450], [874, 420], [870, 470]].map(([x, y]) => (
          <g key={`${x}-${y}`}>
            <circle cx={x} cy={y} r={9} />
            <circle cx={x + 8} cy={y + 9} r={7} />
            <circle cx={x - 6} cy={y + 12} r={6} />
          </g>
        ))}
      </g>

      {/* trees */}
      <g>
        <rect x="318" y="410" width="10" height="80" fill="#4A4A4A" />
        <circle cx="323" cy="392" r="44" fill="#5F712D" />
        <circle cx="300" cy="410" r="30" fill="#4c5b23" />
        <rect x="1110" y="410" width="10" height="80" fill="#4A4A4A" />
        <circle cx="1115" cy="390" r="46" fill="#4c5b23" />
        <circle cx="1140" cy="412" r="28" fill="#5F712D" />
      </g>

      {/* lawn and path */}
      <path d="M0 480 Q600 448 1200 480 V520 H0 Z" fill="url(#lawn)" />
      <path d="M470 520 Q535 470 600 520 Z" fill="#DDDDDD" opacity="0.55" />

      {/* students */}
      <g transform="translate(0 4)">
        <Student x={760} skin="#F1C7A3" hair="#4A2E1C" top="#00356B" topText="YALE" textColor="#FFFFFF" pants="#222222" wave hood />
        <Student x={850} skin="#8D5A3B" hair="#1b1210" top="#DDDDDD" topText="YALE" textColor="#00356B" pants="#286DC0" scale={0.96} long pennant />
        <Student x={945} skin="#D9A57B" hair="#222222" top="#286DC0" topText="BULLDOGS" textColor="#F9F9F9" pants="#4A4A4A" scale={1.02} />
      </g>
    </svg>
  )
}
