import { useState } from 'react';
import { COLORS, TOOLS_LIST as DEFAULT_TOOLS, DATA_PORTALS as DEFAULT_PORTALS } from '../constants/theme';
import { Section, SectionTitle } from '../components/Section';
import MidwestMapSVG from '../components/MidwestMapSVG';

const SUB_TABS = [
  { id: 'guide', label: 'Data Catalog Guide' },
  { id: 'map', label: 'Map Visualization' },
  { id: 'catalog', label: 'Data Catalog' },
  { id: 'tools', label: 'Tools' },
  { id: 'portals', label: 'Data Portals' },
];

const CATALOG_ITEMS = [
  { name: 'AORC Climate Data', type: 'Climate', desc: 'Analysis of Record for Calibration \u2014 high-resolution weather forcing data.' },
  { name: 'ClimRR Projections', type: 'Climate', desc: 'Local climate risk and resilience projections from Argonne National Lab.' },
  { name: 'NOAA Real-Time Weather', type: 'Weather', desc: 'Real-time weather monitoring data for the Midwest region.' },
  { name: 'GLARM Model Output', type: 'Weather', desc: 'Great Lakes Atmosphere Regional Model data for lake-effect projections.' },
  { name: 'NLDAS Forcing Data', type: 'Climate', desc: 'North American Land Data Assimilation System near-surface meteorology.' },
  { name: 'FERC Utility Data', type: 'Infrastructure', desc: 'Cooperative and municipal utility operational data from FERC filings.' },
];

export default function DataToolsPage({ toolsData, portalsData }) {
  const [dtTab, setDtTab] = useState('guide');
  const [search, setSearch] = useState('');

  const tools = toolsData || DEFAULT_TOOLS;
  const portals = portalsData || DEFAULT_PORTALS;

  const filteredCatalog = search
    ? CATALOG_ITEMS.filter(d => d.name.toLowerCase().includes(search.toLowerCase()) || d.type.toLowerCase().includes(search.toLowerCase()))
    : CATALOG_ITEMS;

  return (
    <div style={{ paddingTop: 90 }}>
      <Section>
        <SectionTitle sub="Explore climate data, infrastructure maps, and resilience tools for electric utility planning.">
          Data &amp; Tools
        </SectionTitle>

        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 32, borderBottom: `2px solid ${COLORS.electric}15`, paddingBottom: 4 }}>
          {SUB_TABS.map(t => (
            <button key={t.id} onClick={() => setDtTab(t.id)} style={{
              padding: '10px 16px', borderRadius: '8px 8px 0 0',
              border: 'none', cursor: 'pointer',
              background: dtTab === t.id ? COLORS.electric : 'transparent',
              color: dtTab === t.id ? COLORS.white : COLORS.slate,
              fontSize: 13, fontWeight: 700, fontFamily: "'DM Sans', sans-serif",
            }}>{t.label}</button>
          ))}
        </div>

        {dtTab === 'guide' && (
          <div>
            <div style={{ padding: 28, borderRadius: 12, background: COLORS.frost, border: `1px solid ${COLORS.electric}12`, marginBottom: 24 }}>
              <h3 style={{ fontSize: 20, fontWeight: 700, color: COLORS.darkSlate, fontFamily: "'Libre Baskerville', serif", marginBottom: 12 }}>
                Data Catalog Guide
              </h3>
              <p style={{ fontSize: 14.5, color: COLORS.slate, lineHeight: 1.7, fontFamily: "'DM Sans', sans-serif", marginBottom: 16 }}>
                This guide explains what is in the data catalog, how to use the interactive map, and the types of data
                available for winter resilience planning. Use the tabs above to switch between the map visualization
                and the searchable data catalog.
              </p>
              {[
                { title: 'Map Visualization', desc: 'Interactive map featuring distribution and transmission lines, climate data layers (AORC, ClimRR, NOAA), real-time weather monitoring, and study area boundaries.' },
                { title: 'Data Catalog', desc: 'Searchable catalog of datasets related to winter weather, electric power infrastructure, climate projections, and utility operations across the Midwest.' },
                { title: 'Data Dictionary', desc: 'Definitions, standards, and naming conventions for all data types used in the project, including SQL formatting and server storage specifications.' },
                { title: 'Data Formatting', desc: 'Standards for data hosted on team servers, pointers to external datasets, case studies, and server formatting using SQL with standard naming conventions.' },
              ].map((item, i) => (
                <div key={i} style={{
                  padding: 16, borderRadius: 8, background: COLORS.white,
                  border: `1px solid ${COLORS.electric}10`, marginBottom: 10,
                }}>
                  <h4 style={{ fontSize: 14, fontWeight: 700, color: COLORS.electric, margin: '0 0 4px', fontFamily: "'DM Sans', sans-serif" }}>{item.title}</h4>
                  <p style={{ fontSize: 13, color: COLORS.slate, lineHeight: 1.5, margin: 0, fontFamily: "'DM Sans', sans-serif" }}>{item.desc}</p>
                </div>
              ))}
            </div>
            <div style={{ fontSize: 13, color: COLORS.slate, fontFamily: "'DM Sans', sans-serif" }}>
              <strong>Reference examples:</strong>{' '}
              <a href="https://climrr.anl.gov/datacatalogguide" target="_blank" rel="noreferrer" style={{ color: COLORS.electric }}>ClimRR Data Catalog Guide</a>{' \u00B7 '}
              <a href="https://www.wuppdr.org/rhrt" target="_blank" rel="noreferrer" style={{ color: COLORS.electric }}>WUPPDR RHRT</a>
            </div>
          </div>
        )}

        {dtTab === 'map' && (
          <div>
            <div style={{
              width: '100%', minHeight: 480, borderRadius: 12,
              background: `linear-gradient(135deg, ${COLORS.deepBlue}, ${COLORS.midnightGreen})`,
              display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
              border: `1px solid ${COLORS.electric}22`, position: 'relative', overflow: 'hidden',
            }}>
              <MidwestMapSVG />
              <div style={{ position: 'absolute', bottom: 20, left: 20, right: 20 }}>
                <div style={{
                  display: 'flex', gap: 8, flexWrap: 'wrap',
                  padding: 12, borderRadius: 8, background: 'rgba(0,0,0,0.5)',
                  backdropFilter: 'blur(8px)',
                }}>
                  <span style={{ fontSize: 11, color: COLORS.ice, fontFamily: "'DM Sans', sans-serif", fontWeight: 600 }}>Map Layers:</span>
                  {['Transmission Lines', 'Climate Data (ClimRR)', 'NOAA Weather', 'AORC', 'Study Area'].map((l, i) => (
                    <span key={i} style={{
                      padding: '2px 8px', borderRadius: 10,
                      background: `${COLORS.electric}25`, color: COLORS.ice,
                      fontSize: 10.5, fontFamily: "'DM Sans', sans-serif",
                    }}>{l}</span>
                  ))}
                </div>
              </div>
            </div>
            <div style={{ marginTop: 16, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              <a href="https://openinframap.org/#3.58/37.88/-100.36" target="_blank" rel="noreferrer" style={{
                padding: '8px 16px', borderRadius: 6,
                background: `${COLORS.electric}10`, border: `1px solid ${COLORS.electric}22`,
                color: COLORS.electric, fontSize: 12.5, fontWeight: 600,
                textDecoration: 'none', fontFamily: "'DM Sans', sans-serif",
              }}>Open Infrastructure Map &rarr;</a>
              <a href="https://r2i2.umn.edu/r2i2-project-teams/project-map" target="_blank" rel="noreferrer" style={{
                padding: '8px 16px', borderRadius: 6,
                background: `${COLORS.electric}10`, border: `1px solid ${COLORS.electric}22`,
                color: COLORS.electric, fontSize: 12.5, fontWeight: 600,
                textDecoration: 'none', fontFamily: "'DM Sans', sans-serif",
              }}>R2I2 National Project Map &rarr;</a>
            </div>
          </div>
        )}

        {dtTab === 'catalog' && (
          <div>
            <div style={{
              padding: 16, borderRadius: 8, background: COLORS.frost,
              border: `1px solid ${COLORS.electric}12`, marginBottom: 24,
              display: 'flex', gap: 12, alignItems: 'center',
            }}>
              <span style={{ fontSize: 18 }}>{'\uD83D\uDD0D'}</span>
              <input
                type="text"
                placeholder="Search datasets..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                style={{
                  flex: 1, padding: '10px 14px', borderRadius: 6,
                  border: `1px solid ${COLORS.electric}22`, fontSize: 14,
                  fontFamily: "'DM Sans', sans-serif", outline: 'none',
                }}
              />
            </div>
            <p style={{ fontSize: 14, color: COLORS.slate, lineHeight: 1.6, fontFamily: "'DM Sans', sans-serif", marginBottom: 20 }}>
              This data catalog serves as a collection of datasets related to winter resilience research, electric cooperatives, and
              municipalities &mdash; especially rural, small, and less-resourced electric utilities that are not privately owned.
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 14 }}>
              {filteredCatalog.map((d, i) => (
                <div key={i} style={{
                  padding: 20, borderRadius: 10, background: COLORS.white,
                  border: `1px solid ${COLORS.electric}10`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <span style={{ fontSize: 14, fontWeight: 700, color: COLORS.darkSlate, fontFamily: "'DM Sans', sans-serif" }}>{d.name}</span>
                    <span style={{
                      padding: '2px 8px', borderRadius: 10, fontSize: 10.5,
                      background: d.type === 'Climate' ? `${COLORS.electric}15` : d.type === 'Weather' ? `${COLORS.teal}15` : `${COLORS.amber}15`,
                      color: d.type === 'Climate' ? COLORS.electric : d.type === 'Weather' ? COLORS.teal : COLORS.amber,
                      fontWeight: 700, fontFamily: "'DM Sans', sans-serif",
                    }}>{d.type}</span>
                  </div>
                  <p style={{ fontSize: 12.5, color: COLORS.slate, lineHeight: 1.5, margin: 0, fontFamily: "'DM Sans', sans-serif" }}>{d.desc}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {dtTab === 'tools' && (
          <div>
            <h3 style={{ fontSize: 18, fontWeight: 700, color: COLORS.darkSlate, fontFamily: "'Libre Baskerville', serif", marginBottom: 16 }}>
              Existing Tools &amp; Resources
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {tools.map((t, i) => (
                <a key={i} href={t.link} target="_blank" rel="noreferrer" style={{
                  padding: 22, borderRadius: 10, background: COLORS.white,
                  border: `1px solid ${COLORS.electric}12`,
                  textDecoration: 'none', display: 'block',
                  transition: 'transform 0.15s',
                }}>
                  <div style={{ fontSize: 15, fontWeight: 700, color: COLORS.darkSlate, fontFamily: "'DM Sans', sans-serif", marginBottom: 4 }}>
                    {'\uD83D\uDD27'} {t.name}
                  </div>
                  <p style={{ fontSize: 13, color: COLORS.slate, lineHeight: 1.5, margin: '0 0 6px', fontFamily: "'DM Sans', sans-serif" }}>{t.desc}</p>
                  <span style={{ fontSize: 12, color: COLORS.electric, fontWeight: 600, fontFamily: "'DM Sans', sans-serif" }}>Visit tool &rarr;</span>
                </a>
              ))}
            </div>
          </div>
        )}

        {dtTab === 'portals' && (
          <div>
            <p style={{ fontSize: 14.5, color: COLORS.slate, lineHeight: 1.7, fontFamily: "'DM Sans', sans-serif", marginBottom: 24 }}>
              Access external data portals from federal agencies and organizations with data relevant to
              winter resilience and electric utility planning.
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 14 }}>
              {portals.map((p, i) => (
                <a key={i} href={p.link} target="_blank" rel="noreferrer" style={{
                  padding: 20, borderRadius: 10, background: COLORS.white,
                  border: `1px solid ${COLORS.electric}10`,
                  textDecoration: 'none', textAlign: 'center',
                }}>
                  <div style={{ fontSize: 14, fontWeight: 700, color: COLORS.darkSlate, fontFamily: "'DM Sans', sans-serif" }}>{p.name}</div>
                  <div style={{ fontSize: 11.5, color: COLORS.electric, marginTop: 6, fontWeight: 600, fontFamily: "'DM Sans', sans-serif" }}>Browse &rarr;</div>
                </a>
              ))}
            </div>
          </div>
        )}
      </Section>
    </div>
  );
}
