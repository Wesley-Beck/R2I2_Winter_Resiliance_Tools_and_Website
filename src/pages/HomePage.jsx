import { COLORS } from '../constants/theme';
import { Section, SectionTitle } from '../components/Section';

export default function HomePage({ setPage }) {
  return (
    <div>
      {/* Hero */}
      <div style={{
        minHeight: '85vh',
        background: `linear-gradient(170deg, ${COLORS.navy} 0%, ${COLORS.midnightGreen} 50%, ${COLORS.deepBlue} 100%)`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '120px 24px 80px', position: 'relative', overflow: 'hidden',
      }}>
        <div style={{
          position: 'absolute', inset: 0,
          backgroundImage: `radial-gradient(${COLORS.electric}08 1px, transparent 1px)`,
          backgroundSize: '32px 32px',
        }} />
        <div style={{
          position: 'absolute', top: '20%', right: '10%', width: 400, height: 400,
          background: `radial-gradient(circle, ${COLORS.electric}15, transparent 70%)`,
          borderRadius: '50%',
        }} />

        <div style={{ maxWidth: 900, textAlign: 'center', position: 'relative', zIndex: 1 }}>
          <div style={{
            display: 'inline-block',
            padding: '6px 18px', borderRadius: 20,
            background: `${COLORS.electric}18`,
            border: `1px solid ${COLORS.electric}33`,
            marginBottom: 24,
          }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: COLORS.ice, fontFamily: "'DM Sans', sans-serif", letterSpacing: '0.5px' }}>
              R2I2 &mdash; Resilient &amp; Responsive Infrastructure Incubators
            </span>
          </div>

          <h1 style={{
            fontSize: 'clamp(32px, 5vw, 56px)', fontWeight: 800,
            color: COLORS.white, lineHeight: 1.1,
            fontFamily: "'Libre Baskerville', 'Georgia', serif",
            letterSpacing: '-1px', marginBottom: 24,
          }}>
            Maximizing Resilience to{' '}
            <span style={{ color: COLORS.electric }}>Winter Weather</span>{' '}
            in Future Electric Power Systems
          </h1>

          <p style={{
            fontSize: 'clamp(15px, 2vw, 18px)', color: COLORS.ice,
            lineHeight: 1.7, maxWidth: 720, margin: '0 auto 36px',
            fontFamily: "'DM Sans', sans-serif", opacity: 0.9,
          }}>
            Translating Earth system science to strengthen the winter resilience of electric power
            systems for small municipal and cooperative utilities across the Midwest &mdash; connecting
            climate research with the communities that need it most.
          </p>

          <div style={{ display: 'flex', gap: 14, justifyContent: 'center', flexWrap: 'wrap' }}>
            <button onClick={() => setPage('workshops')} style={{
              padding: '13px 28px', borderRadius: 8, border: 'none',
              background: `linear-gradient(135deg, ${COLORS.electric}, ${COLORS.electricDark})`,
              color: COLORS.white, fontSize: 14.5, fontWeight: 700,
              cursor: 'pointer', fontFamily: "'DM Sans', sans-serif",
              boxShadow: `0 4px 20px ${COLORS.electric}44`,
            }}>{'\u25C8'} &nbsp;View Workshops</button>
            <button onClick={() => setPage('team')} style={{
              padding: '13px 28px', borderRadius: 8,
              border: `1.5px solid ${COLORS.electric}66`,
              background: 'transparent',
              color: COLORS.ice, fontSize: 14.5, fontWeight: 700,
              cursor: 'pointer', fontFamily: "'DM Sans', sans-serif",
            }}>{'\u25CE'} &nbsp;Meet the Team</button>
          </div>
        </div>
      </div>

      {/* About R2I2 */}
      <Section bg={COLORS.snow}>
        <SectionTitle sub="Learn about the NSF Resilient & Responsive Infrastructure Incubators program and our winter resilience subproject.">
          About R2I2
        </SectionTitle>
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 32,
        }}>
          <div style={{
            aspectRatio: '16/9', borderRadius: 12,
            background: `linear-gradient(135deg, ${COLORS.deepBlue}, ${COLORS.midnightGreen})`,
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
            border: `1px solid ${COLORS.electric}22`,
            position: 'relative', overflow: 'hidden',
          }}>
            <div style={{
              position: 'absolute', inset: 0, opacity: 0.04,
              backgroundImage: `repeating-linear-gradient(0deg, transparent, transparent 20px, ${COLORS.electric} 20px, ${COLORS.electric} 21px)`,
            }} />
            <div style={{
              width: 64, height: 64, borderRadius: '50%',
              background: `${COLORS.electric}33`, display: 'flex',
              alignItems: 'center', justifyContent: 'center',
              fontSize: 28, color: COLORS.electric, marginBottom: 12,
              border: `2px solid ${COLORS.electric}55`,
            }}>{'\u25B6'}</div>
            <span style={{ color: COLORS.ice, fontSize: 14, fontWeight: 600, fontFamily: "'DM Sans', sans-serif" }}>
              R2I2 Introduction Video
            </span>
            <span style={{ color: COLORS.ice, fontSize: 11.5, opacity: 0.6, marginTop: 4, fontFamily: "'DM Sans', sans-serif" }}>
              Placeholder &mdash; video coming soon
            </span>
          </div>

          <div>
            <h3 style={{ fontSize: 20, fontWeight: 700, color: COLORS.darkSlate, fontFamily: "'Libre Baskerville', serif", marginBottom: 12 }}>
              What is R2I2?
            </h3>
            <p style={{ fontSize: 14.5, color: COLORS.slate, lineHeight: 1.7, fontFamily: "'DM Sans', sans-serif", margin: '0 0 16px' }}>
              The <strong>Resilient &amp; Responsive Infrastructure Incubators (R2I2)</strong> program, funded by the
              National Science Foundation, connects regional teams of researchers, practitioners, and community
              partners to build resilient infrastructure across the United States.
            </p>
            <p style={{ fontSize: 14.5, color: COLORS.slate, lineHeight: 1.7, fontFamily: "'DM Sans', sans-serif", margin: '0 0 16px' }}>
              Our subproject focuses on <strong>winter resilience for electric power systems</strong> in the Midwest,
              working with cooperative and municipal utilities across Minnesota, Michigan, Wisconsin, Iowa,
              Illinois, Indiana, Ohio, and Missouri.
            </p>
            <a href="https://r2i2.umn.edu/" target="_blank" rel="noreferrer" style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              padding: '10px 20px', borderRadius: 6,
              background: `${COLORS.electric}10`, border: `1px solid ${COLORS.electric}33`,
              color: COLORS.electric, fontSize: 13.5, fontWeight: 600,
              textDecoration: 'none', fontFamily: "'DM Sans', sans-serif",
            }}>Visit R2I2 National Office &rarr;</a>
          </div>
        </div>
      </Section>

      {/* Stats */}
      <Section>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 20 }}>
          {[
            { num: '8', label: 'Midwest States', desc: 'MN, MI, WI, IA, IL, IN, OH, MO' },
            { num: '277', label: 'Small Utilities', desc: 'Cooperative & municipal in region' },
            { num: '4', label: 'Workshops Planned', desc: 'Virtual stakeholder engagement' },
            { num: '7', label: 'Partner Orgs', desc: 'Labs, universities & associations' },
          ].map((s, i) => (
            <div key={i} style={{
              padding: 28, borderRadius: 12, textAlign: 'center',
              background: COLORS.white,
              border: `1px solid ${COLORS.electric}15`,
              boxShadow: `0 2px 12px ${COLORS.navy}08`,
            }}>
              <div style={{ fontSize: 36, fontWeight: 800, color: COLORS.electric, fontFamily: "'DM Sans', sans-serif" }}>{s.num}</div>
              <div style={{ fontSize: 14, fontWeight: 700, color: COLORS.darkSlate, marginTop: 4, fontFamily: "'DM Sans', sans-serif" }}>{s.label}</div>
              <div style={{ fontSize: 12, color: COLORS.slate, marginTop: 4, fontFamily: "'DM Sans', sans-serif" }}>{s.desc}</div>
            </div>
          ))}
        </div>
      </Section>

      {/* Project Overview */}
      <Section bg={COLORS.frost}>
        <SectionTitle sub="Phase 1 establishes community needs through stakeholder engagement, workshops, and collaborative planning.">
          Project Overview
        </SectionTitle>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 20 }}>
          {[
            { icon: '1A', title: 'Planning Committee Visioning', desc: 'Establish a collaborative expert group across Earth system sciences, electric power, and social science.' },
            { icon: '1B', title: 'Utility Workshops & Survey', desc: 'Four virtual workshops engaging small utilities to understand resilience needs and gather structured feedback.' },
            { icon: '1C', title: 'Workshop Reporting', desc: 'Summary reports and publications translating workshop insights for both utility and research audiences.' },
            { icon: '1D', title: 'Research Development Workshop', desc: 'Hybrid in-person meeting to scope Phase 2 based on stakeholder engagement results.' },
          ].map((c, i) => (
            <div key={i} style={{
              padding: 28, borderRadius: 12, background: COLORS.white,
              border: `1px solid ${COLORS.electric}12`,
              boxShadow: `0 2px 12px ${COLORS.navy}06`,
            }}>
              <div style={{
                width: 44, height: 44, borderRadius: 10,
                background: `linear-gradient(135deg, ${COLORS.electric}20, ${COLORS.teal}20)`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 15, fontWeight: 800, color: COLORS.electric,
                marginBottom: 14, fontFamily: "'DM Sans', sans-serif",
              }}>{c.icon}</div>
              <h4 style={{ fontSize: 16, fontWeight: 700, color: COLORS.darkSlate, margin: '0 0 8px', fontFamily: "'DM Sans', sans-serif" }}>{c.title}</h4>
              <p style={{ fontSize: 13.5, color: COLORS.slate, lineHeight: 1.6, margin: 0, fontFamily: "'DM Sans', sans-serif" }}>{c.desc}</p>
            </div>
          ))}
        </div>
      </Section>
    </div>
  );
}
