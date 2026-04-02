import { COLORS, NAV_ITEMS } from '../constants/theme';

export default function Footer({ setPage }) {
  return (
    <footer style={{
      background: COLORS.navy,
      borderTop: `3px solid ${COLORS.electric}`,
      padding: '48px 24px 32px',
      color: COLORS.ice,
      marginTop: 80,
    }}>
      <div style={{ maxWidth: 1200, margin: '0 auto', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 36 }}>
        <div>
          <div
            onClick={() => setPage('home')}
            style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}
          >
            <div style={{
              width: 40, height: 40, borderRadius: 8,
              background: `linear-gradient(135deg, ${COLORS.electric}, ${COLORS.teal})`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 15, fontWeight: 800, color: COLORS.white,
            }}>R2I2</div>
            <div>
              <div style={{ fontWeight: 700, fontSize: 15, fontFamily: "'DM Sans', sans-serif" }}>R2I2 Winter Resilience</div>
              <div style={{ fontSize: 11, opacity: 0.7 }}>Electric Power Systems</div>
            </div>
          </div>
          <p style={{ fontSize: 12.5, lineHeight: 1.6, opacity: 0.7, margin: 0 }}>
            NSF Award #2519254 &middot; August 2025&ndash;July 2027<br />
            Led by Michigan Technological University with Cornell University
          </p>
        </div>
        <div>
          <h4 style={{ fontSize: 13, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 12, color: COLORS.electric }}>Navigate</h4>
          {NAV_ITEMS.map(item => (
            <div key={item.id}
              onClick={() => setPage(item.id)}
              style={{ padding: '4px 0', fontSize: 13, opacity: 0.75, cursor: 'pointer', fontFamily: "'DM Sans', sans-serif" }}
            >{item.label}</div>
          ))}
        </div>
        <div>
          <h4 style={{ fontSize: 13, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 12, color: COLORS.electric }}>Partners</h4>
          {['Michigan Tech', 'Cornell University', 'Argonne National Lab', 'NRECA', 'Center for Energy & Environment'].map(p => (
            <div key={p} style={{ padding: '4px 0', fontSize: 13, opacity: 0.75 }}>{p}</div>
          ))}
        </div>
        <div>
          <h4 style={{ fontSize: 13, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 12, color: COLORS.electric }}>Links</h4>
          <a href="https://r2i2.umn.edu/" target="_blank" rel="noreferrer" style={{ display: 'block', padding: '4px 0', fontSize: 13, opacity: 0.75, color: COLORS.ice, textDecoration: 'none' }}>R2I2 National Office</a>
          <a href="https://www.nsf.gov/awardsearch/showAward?AWD_ID=2519254" target="_blank" rel="noreferrer" style={{ display: 'block', padding: '4px 0', fontSize: 13, opacity: 0.75, color: COLORS.ice, textDecoration: 'none' }}>NSF Award Page</a>
          <a href="https://c-charm.org/" target="_blank" rel="noreferrer" style={{ display: 'block', padding: '4px 0', fontSize: 13, opacity: 0.75, color: COLORS.ice, textDecoration: 'none' }}>C-CHARM</a>
        </div>
      </div>
      <div style={{
        maxWidth: 1200, margin: '36px auto 0', paddingTop: 20,
        borderTop: `1px solid ${COLORS.electric}22`,
        fontSize: 11.5, opacity: 0.5, textAlign: 'center',
      }}>
        &copy; 2025&ndash;2027 R2I2 Winter Resilient Electric Power Systems &middot; Funded by the National Science Foundation
      </div>
    </footer>
  );
}
