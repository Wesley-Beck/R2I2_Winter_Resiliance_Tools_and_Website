import { COLORS } from '../constants/theme';

const states = [
  { abbr: 'MN', cx: 160, cy: 100, coops: 25, munis: 16 },
  { abbr: 'WI', cx: 260, cy: 110, coops: 9, munis: 45 },
  { abbr: 'MI', cx: 350, cy: 90, coops: 9, munis: 16 },
  { abbr: 'IA', cx: 170, cy: 200, coops: 16, munis: 6 },
  { abbr: 'IL', cx: 260, cy: 240, coops: 14, munis: 7 },
  { abbr: 'IN', cx: 330, cy: 230, coops: 28, munis: 12 },
  { abbr: 'OH', cx: 400, cy: 200, coops: 15, munis: 15 },
  { abbr: 'MO', cx: 200, cy: 320, coops: 32, munis: 12 },
];

export default function MidwestMapSVG() {
  return (
    <svg viewBox="0 0 520 420" style={{ width: '90%', maxWidth: 500, opacity: 0.95 }}>
      <defs>
        <radialGradient id="glow">
          <stop offset="0%" stopColor={COLORS.electric} stopOpacity="0.3" />
          <stop offset="100%" stopColor={COLORS.electric} stopOpacity="0" />
        </radialGradient>
      </defs>
      <text x="260" y="30" textAnchor="middle" fill={COLORS.ice} fontSize="16" fontWeight="700" fontFamily="DM Sans, sans-serif">
        Midwest Study Region
      </text>
      {states.map((s, i) => states.slice(i + 1).filter(s2 =>
        Math.abs(s.cx - s2.cx) < 150 && Math.abs(s.cy - s2.cy) < 150
      ).map((s2, j) => (
        <line key={`${i}-${j}`} x1={s.cx} y1={s.cy} x2={s2.cx} y2={s2.cy}
          stroke={COLORS.electric} strokeOpacity="0.15" strokeWidth="1" />
      )))}
      {states.map((s, i) => (
        <g key={i}>
          <circle cx={s.cx} cy={s.cy} r={20 + (s.coops + s.munis) / 3} fill="url(#glow)" />
          <circle cx={s.cx} cy={s.cy} r={14} fill={COLORS.electric} fillOpacity="0.25"
            stroke={COLORS.electric} strokeWidth="1.5" />
          <text x={s.cx} y={s.cy + 1} textAnchor="middle" dominantBaseline="middle"
            fill={COLORS.white} fontSize="11" fontWeight="800" fontFamily="DM Sans, sans-serif">
            {s.abbr}
          </text>
          <text x={s.cx} y={s.cy + 26} textAnchor="middle"
            fill={COLORS.ice} fontSize="9" fontFamily="DM Sans, sans-serif" opacity="0.7">
            {s.coops + s.munis} utilities
          </text>
        </g>
      ))}
    </svg>
  );
}
