import { COLORS, WORKSHOPS as DEFAULT_WORKSHOPS } from '../constants/theme';
import { Section, SectionTitle } from '../components/Section';

export default function WorkshopsPage({ workshopData }) {
  const workshops = workshopData || DEFAULT_WORKSHOPS;

  return (
    <div style={{ paddingTop: 90 }}>
      <Section>
        <SectionTitle sub="A series of virtual workshops engaging small utilities to understand resilience needs for winter weather planning.">
          Workshops
        </SectionTitle>

        {/* Signup banner */}
        <div style={{
          padding: 28, borderRadius: 12, marginBottom: 36,
          background: `linear-gradient(135deg, ${COLORS.electric}10, ${COLORS.teal}08)`,
          border: `1.5px solid ${COLORS.electric}25`,
        }}>
          <h3 style={{ fontSize: 18, fontWeight: 700, color: COLORS.darkSlate, margin: '0 0 8px', fontFamily: "'DM Sans', sans-serif" }}>
            {'\u25C8'} Workshop Registration
          </h3>
          <p style={{ fontSize: 14, color: COLORS.slate, lineHeight: 1.6, margin: '0 0 16px', fontFamily: "'DM Sans', sans-serif" }}>
            Registration for upcoming workshops will be available through an embedded Google Form below.
            Each workshop stands alone &mdash; attend one or all.
          </p>
          <div style={{
            width: '100%', minHeight: 200, borderRadius: 8,
            background: COLORS.white, border: `1px dashed ${COLORS.electric}33`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: COLORS.slate, fontSize: 14, fontFamily: "'DM Sans', sans-serif",
          }}>
            Google Form registration will be embedded here
          </div>
        </div>

        {/* Workshop cards */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {workshops.map((w) => (
            <div key={w.id} style={{
              padding: 28, borderRadius: 12, background: COLORS.white,
              border: `1px solid ${COLORS.electric}12`,
              boxShadow: `0 2px 12px ${COLORS.navy}06`,
              display: 'grid', gridTemplateColumns: 'auto 1fr', gap: 24,
              alignItems: 'flex-start',
            }}>
              <div style={{
                width: 56, height: 56, borderRadius: 14,
                background: w.status === 'upcoming'
                  ? `linear-gradient(135deg, ${COLORS.electric}, ${COLORS.teal})`
                  : `linear-gradient(135deg, ${COLORS.electric}20, ${COLORS.teal}20)`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 22, fontWeight: 800,
                color: w.status === 'upcoming' ? COLORS.white : COLORS.electric,
                fontFamily: "'DM Sans', sans-serif",
              }}>#{w.id}</div>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', marginBottom: 6 }}>
                  <h3 style={{ fontSize: 18, fontWeight: 700, color: COLORS.darkSlate, margin: 0, fontFamily: "'DM Sans', sans-serif" }}>
                    {w.title}
                  </h3>
                  <span style={{
                    padding: '3px 10px', borderRadius: 12,
                    background: w.status === 'upcoming' ? `${COLORS.electric}15` : `${COLORS.slate}10`,
                    color: w.status === 'upcoming' ? COLORS.electric : COLORS.slate,
                    fontSize: 11, fontWeight: 700, textTransform: 'uppercase',
                    fontFamily: "'DM Sans', sans-serif",
                  }}>{w.status}</span>
                </div>
                <div style={{ fontSize: 13, color: COLORS.electric, fontWeight: 600, marginBottom: 8, fontFamily: "'DM Sans', sans-serif" }}>
                  {w.date}
                </div>
                <p style={{ fontSize: 14, color: COLORS.slate, lineHeight: 1.6, margin: 0, fontFamily: "'DM Sans', sans-serif" }}>
                  {w.desc}
                </p>
              </div>
            </div>
          ))}
        </div>
      </Section>
    </div>
  );
}
