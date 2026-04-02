import { COLORS } from '../constants/theme';

export function Section({ children, bg, style: extraStyle }) {
  return (
    <section style={{
      padding: '60px 24px',
      background: bg || 'transparent',
      ...extraStyle,
    }}>
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>
        {children}
      </div>
    </section>
  );
}

export function SectionTitle({ children, sub }) {
  return (
    <div style={{ marginBottom: 36 }}>
      <h2 style={{
        fontSize: 32, fontWeight: 800, color: COLORS.darkSlate,
        fontFamily: "'Libre Baskerville', 'Georgia', serif",
        letterSpacing: '-0.5px', margin: 0,
      }}>{children}</h2>
      {sub && (
        <p style={{
          fontSize: 15, color: COLORS.slate, marginTop: 8,
          lineHeight: 1.6, maxWidth: 680,
          fontFamily: "'DM Sans', sans-serif",
        }}>{sub}</p>
      )}
      <div style={{
        width: 60, height: 3, background: COLORS.electric,
        borderRadius: 2, marginTop: 14,
      }} />
    </div>
  );
}
