import { useState } from 'react';
import { COLORS, NEWS_ITEMS as DEFAULT_NEWS } from '../constants/theme';
import { Section, SectionTitle } from '../components/Section';

const BG_GRADIENTS = [
  `linear-gradient(135deg, #102A4Cee, #0A3042cc)`,
  `linear-gradient(135deg, #0A3042ee, #0B1D3Acc)`,
  `linear-gradient(135deg, #0B1D3Aee, #102A4Ccc)`,
  `linear-gradient(135deg, #00A6ED22, #0D948822)`,
];

export default function NewsPage({ newsData }) {
  const [hovered, setHovered] = useState(null);
  const news = newsData || DEFAULT_NEWS;

  return (
    <div style={{ paddingTop: 90 }}>
      <Section>
        <SectionTitle sub="Latest updates, announcements, and publications from the R2I2 Winter Resilience project.">
          News
        </SectionTitle>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 20 }}>
          {news.map((n, i) => (
            <div
              key={n.id}
              onMouseEnter={() => setHovered(n.id)}
              onMouseLeave={() => setHovered(null)}
              style={{
                borderRadius: 14, overflow: 'hidden',
                background: BG_GRADIENTS[i % BG_GRADIENTS.length],
                position: 'relative', minHeight: 240,
                cursor: 'pointer', transition: 'transform 0.3s',
                transform: hovered === n.id ? 'translateY(-4px)' : 'none',
                boxShadow: hovered === n.id ? `0 12px 32px ${COLORS.navy}33` : `0 4px 16px ${COLORS.navy}15`,
                border: `1px solid ${COLORS.electric}15`,
              }}
            >
              <div style={{
                position: 'absolute', inset: 0,
                background: hovered === n.id ? 'rgba(0,166,237,0.12)' : 'transparent',
                transition: 'background 0.3s',
              }} />
              <div style={{
                position: 'relative', zIndex: 1, padding: 24,
                display: 'flex', flexDirection: 'column', height: '100%',
                justifyContent: 'flex-end',
              }}>
                <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
                  <span style={{
                    padding: '3px 10px', borderRadius: 10,
                    background: `${COLORS.electric}30`,
                    color: COLORS.ice, fontSize: 11, fontWeight: 700,
                    fontFamily: "'DM Sans', sans-serif",
                  }}>{n.tag}</span>
                  <span style={{ fontSize: 11.5, color: COLORS.ice, opacity: 0.7, fontFamily: "'DM Sans', sans-serif", alignSelf: 'center' }}>{n.date}</span>
                </div>
                <h3 style={{ fontSize: 17, fontWeight: 700, color: COLORS.white, margin: '0 0 8px', fontFamily: "'DM Sans', sans-serif", lineHeight: 1.3 }}>
                  {n.title}
                </h3>
                <p style={{ fontSize: 13, color: COLORS.ice, lineHeight: 1.5, margin: 0, opacity: 0.85, fontFamily: "'DM Sans', sans-serif" }}>
                  {n.summary}
                </p>
                <div style={{
                  marginTop: 14, padding: '6px 0',
                  color: COLORS.electric,
                  fontSize: 12.5, fontWeight: 700,
                  fontFamily: "'DM Sans', sans-serif",
                  opacity: hovered === n.id ? 1 : 0,
                  transform: hovered === n.id ? 'translateY(0)' : 'translateY(8px)',
                  transition: 'all 0.3s',
                }}>Learn more &rarr;</div>
              </div>
            </div>
          ))}
        </div>
      </Section>
    </div>
  );
}
