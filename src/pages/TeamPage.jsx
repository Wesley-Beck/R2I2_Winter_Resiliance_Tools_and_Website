import { useState } from 'react';
import { COLORS, TEAM_CORE, TEAM_PLANNING, ORGANIZATIONS } from '../constants/theme';
import { Section, SectionTitle } from '../components/Section';
import TeamMemberCard from '../components/TeamMemberCard';

const TABS = [
  { id: 'all', label: 'All Members' },
  { id: 'core', label: 'Core Team' },
  { id: 'planning', label: 'Planning Committee' },
  { id: 'stakeholders', label: 'Stakeholders' },
  { id: 'organizations', label: 'Organizations' },
];

export default function TeamPage({ teamData }) {
  const [tab, setTab] = useState('all');

  const core = teamData?.filter(m => m.category === 'core') || TEAM_CORE;
  const planning = teamData?.filter(m => m.category === 'planning') || TEAM_PLANNING;
  const allMembers = teamData || [...TEAM_CORE, ...TEAM_PLANNING];
  const displayMembers = tab === 'all' ? allMembers : tab === 'core' ? core : tab === 'planning' ? planning : [];

  return (
    <div style={{ paddingTop: 90 }}>
      <Section>
        <SectionTitle sub="Researchers, practitioners, and partners working together on winter resilience for electric power systems.">
          Our Team
        </SectionTitle>

        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 36, borderBottom: `2px solid ${COLORS.electric}15`, paddingBottom: 4 }}>
          {TABS.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)} style={{
              padding: '10px 18px', borderRadius: '8px 8px 0 0',
              border: 'none', cursor: 'pointer',
              background: tab === t.id ? COLORS.electric : 'transparent',
              color: tab === t.id ? COLORS.white : COLORS.slate,
              fontSize: 13.5, fontWeight: 700,
              fontFamily: "'DM Sans', sans-serif",
              transition: 'all 0.2s',
            }}>{t.label}</button>
          ))}
        </div>

        {tab === 'stakeholders' && (
          <div style={{
            padding: 32, borderRadius: 12, background: COLORS.frost,
            border: `1px solid ${COLORS.electric}15`,
          }}>
            <h3 style={{ fontSize: 22, fontWeight: 700, color: COLORS.darkSlate, fontFamily: "'Libre Baskerville', serif", marginBottom: 16 }}>
              Are You a Potential Stakeholder?
            </h3>
            <p style={{ fontSize: 15, color: COLORS.slate, lineHeight: 1.7, fontFamily: "'DM Sans', sans-serif", marginBottom: 16 }}>
              We are seeking professionals who work within and around <strong>electric cooperatives and municipalities</strong> &mdash;
              particularly those involved in distribution, generation, and high-voltage transmission within their regions.
            </p>
            <p style={{ fontSize: 15, color: COLORS.slate, lineHeight: 1.7, fontFamily: "'DM Sans', sans-serif", marginBottom: 20 }}>
              If you work at a rural or smaller electric cooperative or municipal utility in the Midwest, your expertise and
              perspectives are invaluable to this project. We want to understand your needs, challenges, and priorities
              for planning winter-resilient electric power systems.
            </p>
            <div style={{
              padding: 20, borderRadius: 8,
              background: `linear-gradient(135deg, ${COLORS.electric}08, ${COLORS.teal}08)`,
              border: `1px solid ${COLORS.electric}22`,
            }}>
              <h4 style={{ fontSize: 14, fontWeight: 700, color: COLORS.electric, margin: '0 0 8px', fontFamily: "'DM Sans', sans-serif" }}>
                You may be a stakeholder if you:
              </h4>
              {[
                'Work at a cooperative or municipal electric utility',
                'Are involved in electricity distribution, generation, or transmission planning',
                'Operate in the Midwest (MN, MI, WI, IA, IL, IN, OH, MO)',
                'Are interested in climate resilience and winter preparedness for power systems',
                'Work with rural or resource-limited utility organizations',
              ].map((item, i) => (
                <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-start', padding: '4px 0' }}>
                  <span style={{ color: COLORS.electric, fontSize: 14, marginTop: 2 }}>{'\u2726'}</span>
                  <span style={{ fontSize: 13.5, color: COLORS.slate, fontFamily: "'DM Sans', sans-serif" }}>{item}</span>
                </div>
              ))}
            </div>

            <div style={{
              marginTop: 24, width: '100%', minHeight: 220, borderRadius: 8,
              background: `linear-gradient(135deg, ${COLORS.frost}, ${COLORS.white})`,
              border: `1.5px dashed ${COLORS.electric}33`,
              display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
              gap: 10, padding: 24,
            }}>
              <div style={{
                width: 48, height: 48, borderRadius: 12,
                background: `${COLORS.electric}15`, display: 'flex',
                alignItems: 'center', justifyContent: 'center',
                fontSize: 22, border: `1px solid ${COLORS.electric}22`,
              }}>{'\u2726'}</div>
              <span style={{ color: COLORS.darkSlate, fontSize: 15, fontWeight: 700, fontFamily: "'DM Sans', sans-serif" }}>
                Stakeholder Interest Form
              </span>
              <span style={{ color: COLORS.slate, fontSize: 12.5, fontFamily: "'DM Sans', sans-serif", textAlign: 'center', maxWidth: 400 }}>
                A Google Form for stakeholder interest and engagement will be embedded here. If you represent an electric cooperative or municipality, we want to hear from you.
              </span>
            </div>
          </div>
        )}

        {tab === 'organizations' && (
          <div>
            <p style={{ fontSize: 15, color: COLORS.slate, lineHeight: 1.7, fontFamily: "'DM Sans', sans-serif", marginBottom: 28 }}>
              These organizations are directly associated with our NSF R2I2 project, contributing expertise in climate science,
              energy systems, rural utilities, and community engagement.
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 16 }}>
              {ORGANIZATIONS.map((org, i) => (
                <div key={i} style={{
                  padding: 24, borderRadius: 12, background: COLORS.white,
                  border: `1px solid ${COLORS.electric}12`,
                  boxShadow: `0 2px 8px ${COLORS.navy}06`,
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10 }}>
                    <div style={{
                      width: 44, height: 44, borderRadius: 10,
                      background: `linear-gradient(135deg, ${COLORS.electric}15, ${COLORS.teal}15)`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 12, fontWeight: 800, color: COLORS.electric,
                      fontFamily: "'DM Sans', sans-serif",
                    }}>{org.abbr}</div>
                    <div>
                      <div style={{ fontSize: 15, fontWeight: 700, color: COLORS.darkSlate, fontFamily: "'DM Sans', sans-serif" }}>{org.name}</div>
                    </div>
                  </div>
                  <p style={{ fontSize: 13, color: COLORS.slate, lineHeight: 1.5, margin: 0, fontFamily: "'DM Sans', sans-serif" }}>{org.desc}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {(tab === 'all' || tab === 'core' || tab === 'planning') && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
            {displayMembers.map((m, i) => (
              <TeamMemberCard key={i} member={m} />
            ))}
          </div>
        )}
      </Section>
    </div>
  );
}
