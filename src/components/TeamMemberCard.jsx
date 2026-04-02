import { COLORS, initials } from '../constants/theme';

export default function TeamMemberCard({ member }) {
  const m = member;
  return (
    <div style={{
      padding: 24, borderRadius: 12, background: COLORS.white,
      border: `1px solid ${COLORS.electric}10`,
      boxShadow: `0 2px 8px ${COLORS.navy}06`,
      display: 'flex', gap: 16, alignItems: 'flex-start',
      transition: 'transform 0.2s, box-shadow 0.2s',
    }}>
      <div style={{
        width: 52, height: 52, borderRadius: 12, flexShrink: 0,
        background: `linear-gradient(135deg, ${COLORS.electric}25, ${COLORS.teal}25)`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 18, fontWeight: 800, color: COLORS.electric,
        fontFamily: "'DM Sans', sans-serif",
      }}>{initials(m.name)}</div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 15, fontWeight: 700, color: COLORS.darkSlate, fontFamily: "'DM Sans', sans-serif" }}>{m.name}</div>
        <div style={{ fontSize: 12.5, color: COLORS.electric, fontWeight: 600, fontFamily: "'DM Sans', sans-serif" }}>{m.role}</div>
        <div style={{ fontSize: 12, color: COLORS.slate, marginTop: 2, fontFamily: "'DM Sans', sans-serif" }}>{m.org}</div>
        <div style={{ fontSize: 12, color: COLORS.slate, marginTop: 6, lineHeight: 1.5, fontFamily: "'DM Sans', sans-serif", opacity: 0.8 }}>
          <em>{m.interests}</em>
        </div>
        {m.link && (
          <a href={m.link} target="_blank" rel="noreferrer" style={{
            display: 'inline-block', marginTop: 8,
            fontSize: 12, color: COLORS.electric, textDecoration: 'none',
            fontWeight: 600, fontFamily: "'DM Sans', sans-serif",
          }}>View Profile &rarr;</a>
        )}
      </div>
    </div>
  );
}
