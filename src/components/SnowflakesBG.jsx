import { useMemo } from 'react';
import { COLORS } from '../constants/theme';

export default function SnowflakesBG() {
  const flakes = useMemo(() =>
    Array.from({ length: 18 }, (_, i) => ({
      id: i,
      left: Math.random() * 100,
      delay: Math.random() * 12,
      dur: 10 + Math.random() * 15,
      size: 6 + Math.random() * 14,
      opacity: 0.08 + Math.random() * 0.12,
    })), []);

  return (
    <div style={{ position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0, overflow: 'hidden' }}>
      {flakes.map(f => (
        <div key={f.id} style={{
          position: 'absolute', left: `${f.left}%`, top: '-20px',
          fontSize: `${f.size}px`, opacity: f.opacity, color: COLORS.electric,
          animation: `snowfall ${f.dur}s linear ${f.delay}s infinite`,
        }}>{'\u2744'}</div>
      ))}
      <style>{`
        @keyframes snowfall {
          0% { transform: translateY(-20px) rotate(0deg); }
          100% { transform: translateY(110vh) rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
