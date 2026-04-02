import { useState } from 'react';
import { COLORS, NAV_ITEMS } from '../constants/theme';

export default function Header({ page, setPage, scrolled, user }) {
  const [mobileOpen, setMobileOpen] = useState(false);

  const navItems = user
    ? [...NAV_ITEMS.filter(i => i.id !== 'login'), { id: 'portal', label: 'Portal', icon: '\u229E' }]
    : NAV_ITEMS;

  return (
    <header style={{
      position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100,
      background: scrolled ? 'rgba(11,29,58,0.97)' : COLORS.navy,
      backdropFilter: 'blur(12px)',
      transition: 'all 0.4s cubic-bezier(.4,0,.2,1)',
      padding: scrolled ? '6px 0' : '10px 0',
      boxShadow: scrolled ? '0 2px 24px rgba(0,0,0,0.3)' : 'none',
      borderBottom: `2px solid ${COLORS.electric}22`,
    }}>
      <div style={{
        maxWidth: 1280, margin: '0 auto', padding: '0 24px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        {/* Logo */}
        <div
          onClick={() => setPage('home')}
          style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 12, transition: 'all 0.3s' }}
        >
          <div style={{
            width: scrolled ? 36 : 48, height: scrolled ? 36 : 48,
            borderRadius: 8, background: `linear-gradient(135deg, ${COLORS.electric}, ${COLORS.teal})`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: scrolled ? 14 : 18, fontWeight: 800, color: COLORS.white,
            transition: 'all 0.4s', letterSpacing: '-0.5px',
            boxShadow: `0 0 20px ${COLORS.electric}44`,
          }}>R2I2</div>
          <div style={{ transition: 'all 0.3s' }}>
            <div style={{
              fontSize: scrolled ? 14 : 16, fontWeight: 700, color: COLORS.white,
              fontFamily: "'DM Sans', sans-serif", letterSpacing: '-0.3px',
            }}>Winter Resilience</div>
            {!scrolled && (
              <div style={{ fontSize: 11, color: COLORS.ice, opacity: 0.8, fontFamily: "'DM Sans', sans-serif" }}>
                Electric Power Systems
              </div>
            )}
          </div>
        </div>

        {/* Desktop nav */}
        <nav style={{ display: 'flex', gap: 2, alignItems: 'center' }} className="desktop-nav">
          {navItems.map(item => (
            <button
              key={item.id}
              onClick={() => setPage(item.id)}
              style={{
                background: page === item.id ? `${COLORS.electric}22` : 'transparent',
                border: 'none', borderRadius: 6,
                padding: scrolled ? '6px 12px' : '8px 14px',
                color: page === item.id ? COLORS.electric : COLORS.ice,
                fontSize: scrolled ? 12.5 : 13.5, fontWeight: 600,
                cursor: 'pointer', transition: 'all 0.2s',
                fontFamily: "'DM Sans', sans-serif",
                display: 'flex', alignItems: 'center', gap: 5,
                borderBottom: page === item.id ? `2px solid ${COLORS.electric}` : '2px solid transparent',
              }}
            >
              <span style={{ fontSize: scrolled ? 11 : 13 }}>{item.icon}</span>
              {item.label}
            </button>
          ))}
          {user && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: 6, marginLeft: 8,
              padding: '4px 10px', borderRadius: 6,
              background: `${COLORS.teal}22`, border: `1px solid ${COLORS.teal}44`,
            }}>
              <div style={{
                width: 24, height: 24, borderRadius: '50%',
                background: `linear-gradient(135deg, ${COLORS.electric}, ${COLORS.teal})`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 10, fontWeight: 800, color: COLORS.white,
              }}>{user.name?.split(' ').map(w => w[0]).join('') || '?'}</div>
              <span style={{ fontSize: 11, color: COLORS.ice, fontFamily: "'DM Sans', sans-serif" }}>
                {user.name?.split(' ')[0]}
              </span>
            </div>
          )}
        </nav>

        {/* Mobile menu button */}
        <button
          className="mobile-menu-btn"
          onClick={() => setMobileOpen(!mobileOpen)}
          style={{
            display: 'none', background: 'none', border: `1px solid ${COLORS.electric}44`,
            borderRadius: 6, padding: '6px 10px', color: COLORS.ice,
            fontSize: 18, cursor: 'pointer',
          }}
        >{'\u2630'}</button>
      </div>

      {/* Mobile dropdown */}
      {mobileOpen && (
        <div style={{
          background: COLORS.deepBlue, borderTop: `1px solid ${COLORS.electric}22`,
          padding: '8px 24px',
        }} className="mobile-nav">
          {navItems.map(item => (
            <button
              key={item.id}
              onClick={() => { setPage(item.id); setMobileOpen(false); }}
              style={{
                display: 'block', width: '100%', textAlign: 'left',
                background: page === item.id ? `${COLORS.electric}15` : 'transparent',
                border: 'none', padding: '10px 12px', borderRadius: 6,
                color: page === item.id ? COLORS.electric : COLORS.ice,
                fontSize: 14, fontWeight: 600, cursor: 'pointer',
                fontFamily: "'DM Sans', sans-serif",
              }}
            >{item.icon} {item.label}</button>
          ))}
        </div>
      )}
    </header>
  );
}
