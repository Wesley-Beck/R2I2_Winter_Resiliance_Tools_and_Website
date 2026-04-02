import { COLORS } from '../constants/theme';
import { Section } from '../components/Section';

export default function LoginPage({ onSignIn, user, setPage }) {
  if (user) {
    return (
      <div style={{ paddingTop: 90 }}>
        <Section>
          <div style={{
            maxWidth: 480, margin: '0 auto', textAlign: 'center',
            padding: 48, borderRadius: 16, background: COLORS.white,
            border: `1px solid ${COLORS.electric}15`,
            boxShadow: `0 8px 32px ${COLORS.navy}10`,
          }}>
            <div style={{
              width: 64, height: 64, borderRadius: '50%', margin: '0 auto 20px',
              background: `linear-gradient(135deg, ${COLORS.electric}, ${COLORS.teal})`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 24, fontWeight: 800, color: COLORS.white,
              fontFamily: "'DM Sans', sans-serif",
            }}>{user.name?.split(' ').map(w => w[0]).join('') || '?'}</div>
            <h2 style={{ fontSize: 24, fontWeight: 700, color: COLORS.darkSlate, fontFamily: "'Libre Baskerville', serif", marginBottom: 8 }}>
              Welcome, {user.name?.split(' ')[0]}
            </h2>
            <p style={{ fontSize: 14, color: COLORS.slate, lineHeight: 1.6, fontFamily: "'DM Sans', sans-serif", marginBottom: 24 }}>
              You are signed in as {user.email}
            </p>
            <button onClick={() => setPage('portal')} style={{
              padding: '12px 28px', borderRadius: 8, border: 'none',
              background: `linear-gradient(135deg, ${COLORS.electric}, ${COLORS.electricDark})`,
              color: COLORS.white, fontSize: 14.5, fontWeight: 700,
              cursor: 'pointer', fontFamily: "'DM Sans', sans-serif",
              boxShadow: `0 4px 20px ${COLORS.electric}44`,
            }}>Go to Team Portal &rarr;</button>
          </div>
        </Section>
      </div>
    );
  }

  return (
    <div style={{ paddingTop: 90 }}>
      <Section>
        <div style={{
          maxWidth: 480, margin: '0 auto', textAlign: 'center',
          padding: 48, borderRadius: 16, background: COLORS.white,
          border: `1px solid ${COLORS.electric}15`,
          boxShadow: `0 8px 32px ${COLORS.navy}10`,
        }}>
          <div style={{
            width: 64, height: 64, borderRadius: 16, margin: '0 auto 20px',
            background: `linear-gradient(135deg, ${COLORS.electric}20, ${COLORS.teal}20)`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 28,
          }}>{'\u22A1'}</div>
          <h2 style={{ fontSize: 24, fontWeight: 700, color: COLORS.darkSlate, fontFamily: "'Libre Baskerville', serif", marginBottom: 12 }}>
            Team Login
          </h2>
          <p style={{ fontSize: 14, color: COLORS.slate, lineHeight: 1.6, fontFamily: "'DM Sans', sans-serif", marginBottom: 28 }}>
            R2I2 project team members can sign in with their Google account to access planning documents,
            shared files, and collaboration tools.
          </p>

          <button onClick={onSignIn} style={{
            display: 'inline-flex', alignItems: 'center', gap: 12,
            padding: '12px 28px', borderRadius: 8,
            background: COLORS.white,
            border: `1.5px solid ${COLORS.electric}33`,
            fontSize: 14.5, fontWeight: 600, color: COLORS.darkSlate,
            cursor: 'pointer', fontFamily: "'DM Sans', sans-serif",
            boxShadow: `0 2px 8px ${COLORS.navy}08`,
          }}>
            <svg width="18" height="18" viewBox="0 0 48 48">
              <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
              <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
              <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
              <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
            </svg>
            Sign in with Google
          </button>

          <p style={{ fontSize: 12, color: COLORS.slate, marginTop: 20, opacity: 0.6, fontFamily: "'DM Sans', sans-serif" }}>
            Once logged in, you'll have access to additional collaboration tools and project documents.
          </p>
        </div>
      </Section>
    </div>
  );
}
