import { useState, useEffect } from 'react';
import { COLORS } from '../constants/theme';
import { GOOGLE_CONFIG } from '../config';
import { Section, SectionTitle } from '../components/Section';
import GoogleDocEmbed from '../components/GoogleDocEmbed';
import { getUserGroup, getFilesForGroup, groupFilesByFolder } from '../services/portalPermissions';

export default function PortalPage({ user, onSignOut, setPage }) {
  const [group, setGroup] = useState(null);
  const [folders, setFolders] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState({});

  useEffect(() => {
    if (!user) return;

    async function load() {
      const userGroup = await getUserGroup(user.email);
      setGroup(userGroup);

      if (userGroup) {
        const files = await getFilesForGroup(userGroup);
        if (files && files.length > 0) {
          setFolders(groupFilesByFolder(files));
        }
      }
      setLoading(false);
    }

    load();
  }, [user]);

  if (!user) {
    return (
      <div style={{ paddingTop: 90 }}>
        <Section>
          <div style={{ textAlign: 'center', padding: 48 }}>
            <h2 style={{ fontSize: 24, fontWeight: 700, color: COLORS.darkSlate, fontFamily: "'Libre Baskerville', serif", marginBottom: 12 }}>
              Authentication Required
            </h2>
            <p style={{ fontSize: 14, color: COLORS.slate, fontFamily: "'DM Sans', sans-serif", marginBottom: 24 }}>
              Please sign in to access the team portal.
            </p>
            <button onClick={() => setPage('login')} style={{
              padding: '12px 28px', borderRadius: 8, border: 'none',
              background: `linear-gradient(135deg, ${COLORS.electric}, ${COLORS.electricDark})`,
              color: COLORS.white, fontSize: 14.5, fontWeight: 700,
              cursor: 'pointer', fontFamily: "'DM Sans', sans-serif",
            }}>Go to Login &rarr;</button>
          </div>
        </Section>
      </div>
    );
  }

  const toggleFolder = (folder) => {
    setExpanded(prev => ({ ...prev, [folder]: !prev[folder] }));
  };

  return (
    <div style={{ paddingTop: 90 }}>
      <Section>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16, marginBottom: 24 }}>
          <SectionTitle sub={`Signed in as ${user.email}${group ? ` \u2014 ${group} group` : ''}`}>
            Team Portal
          </SectionTitle>
          <button onClick={onSignOut} style={{
            padding: '8px 16px', borderRadius: 6,
            border: `1px solid ${COLORS.slate}33`, background: 'transparent',
            color: COLORS.slate, fontSize: 12.5, fontWeight: 600,
            cursor: 'pointer', fontFamily: "'DM Sans', sans-serif",
          }}>Sign Out</button>
        </div>

        {/* Quick links */}
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: 12, marginBottom: 32,
        }}>
          <a href={`https://drive.google.com/drive/folders/${GOOGLE_CONFIG.driveFolderId}`}
            target="_blank" rel="noreferrer" style={{
              padding: 20, borderRadius: 10, background: COLORS.frost,
              border: `1px solid ${COLORS.electric}15`, textDecoration: 'none', textAlign: 'center',
            }}>
            <div style={{ fontSize: 24, marginBottom: 6 }}>{'\uD83D\uDCC1'}</div>
            <div style={{ fontSize: 13, fontWeight: 700, color: COLORS.darkSlate, fontFamily: "'DM Sans', sans-serif" }}>Shared Drive</div>
            <div style={{ fontSize: 11, color: COLORS.electric, fontFamily: "'DM Sans', sans-serif", marginTop: 4 }}>Open in Google Drive</div>
          </a>
          <div onClick={() => setPage('calendar')} style={{
            padding: 20, borderRadius: 10, background: COLORS.frost,
            border: `1px solid ${COLORS.electric}15`, textAlign: 'center', cursor: 'pointer',
          }}>
            <div style={{ fontSize: 24, marginBottom: 6 }}>{'\uD83D\uDCC5'}</div>
            <div style={{ fontSize: 13, fontWeight: 700, color: COLORS.darkSlate, fontFamily: "'DM Sans', sans-serif" }}>Calendar</div>
            <div style={{ fontSize: 11, color: COLORS.electric, fontFamily: "'DM Sans', sans-serif", marginTop: 4 }}>View project calendar</div>
          </div>
          <div onClick={() => setPage('workshops')} style={{
            padding: 20, borderRadius: 10, background: COLORS.frost,
            border: `1px solid ${COLORS.electric}15`, textAlign: 'center', cursor: 'pointer',
          }}>
            <div style={{ fontSize: 24, marginBottom: 6 }}>{'\u25C8'}</div>
            <div style={{ fontSize: 13, fontWeight: 700, color: COLORS.darkSlate, fontFamily: "'DM Sans', sans-serif" }}>Workshops</div>
            <div style={{ fontSize: 11, color: COLORS.electric, fontFamily: "'DM Sans', sans-serif", marginTop: 4 }}>View workshop details</div>
          </div>
        </div>

        {loading && (
          <div style={{ textAlign: 'center', padding: 48, color: COLORS.slate, fontFamily: "'DM Sans', sans-serif" }}>
            Loading portal files...
          </div>
        )}

        {!loading && !group && (
          <div style={{
            padding: 32, borderRadius: 12, background: COLORS.frost,
            border: `1px solid ${COLORS.electric}15`, textAlign: 'center',
          }}>
            <h3 style={{ fontSize: 18, fontWeight: 700, color: COLORS.darkSlate, fontFamily: "'DM Sans', sans-serif", marginBottom: 8 }}>
              No Group Assignment Found
            </h3>
            <p style={{ fontSize: 14, color: COLORS.slate, fontFamily: "'DM Sans', sans-serif", lineHeight: 1.6 }}>
              Your email ({user.email}) has not been assigned to a group in the permissions sheet yet.
              Contact a project administrator to be added to the PortalPermissions sheet.
            </p>
          </div>
        )}

        {!loading && group && !folders && (
          <div style={{
            padding: 32, borderRadius: 12, background: COLORS.frost,
            border: `1px solid ${COLORS.electric}15`, textAlign: 'center',
          }}>
            <h3 style={{ fontSize: 18, fontWeight: 700, color: COLORS.darkSlate, fontFamily: "'DM Sans', sans-serif", marginBottom: 8 }}>
              No Files Available
            </h3>
            <p style={{ fontSize: 14, color: COLORS.slate, fontFamily: "'DM Sans', sans-serif", lineHeight: 1.6 }}>
              No portal files have been configured for the <strong>{group}</strong> group yet.
              Files can be added through the PortalFiles tab in the CMS Google Sheet.
            </p>
          </div>
        )}

        {!loading && folders && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {Object.entries(folders).map(([folderName, files]) => (
              <div key={folderName} style={{
                borderRadius: 12, background: COLORS.white,
                border: `1px solid ${COLORS.electric}12`,
                overflow: 'hidden',
              }}>
                <button
                  onClick={() => toggleFolder(folderName)}
                  style={{
                    width: '100%', textAlign: 'left',
                    padding: '16px 24px', border: 'none',
                    background: expanded[folderName] ? `${COLORS.electric}08` : 'transparent',
                    cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 12,
                  }}
                >
                  <span style={{
                    fontSize: 14, transition: 'transform 0.2s',
                    transform: expanded[folderName] ? 'rotate(90deg)' : 'rotate(0deg)',
                  }}>{'\u25B6'}</span>
                  <span style={{ fontSize: 15, fontWeight: 700, color: COLORS.darkSlate, fontFamily: "'DM Sans', sans-serif" }}>
                    {folderName}
                  </span>
                  <span style={{
                    fontSize: 11, color: COLORS.slate, fontFamily: "'DM Sans', sans-serif",
                    background: `${COLORS.electric}10`, padding: '2px 8px', borderRadius: 10,
                  }}>{files.length} file{files.length !== 1 ? 's' : ''}</span>
                </button>

                {expanded[folderName] && (
                  <div style={{ padding: '0 24px 24px' }}>
                    {files.map((f, i) => (
                      <GoogleDocEmbed
                        key={i}
                        fileId={f.googleFileId}
                        fileType={f.fileType}
                        title={f.title}
                      />
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </Section>
    </div>
  );
}
