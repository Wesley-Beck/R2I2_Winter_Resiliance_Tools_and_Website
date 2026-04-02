import { useState } from 'react';
import { COLORS } from '../constants/theme';
import { GOOGLE_CONFIG } from '../config';
import { Section, SectionTitle } from '../components/Section';

const MONTH_NAMES = ['January','February','March','April','May','June','July','August','September','October','November','December'];

export default function CalendarPage() {
  const today = new Date();
  const [month, setMonth] = useState(today.getMonth());
  const [year, setYear] = useState(today.getFullYear());

  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const startDay = new Date(year, month, 1).getDay();

  const prevMonth = () => {
    if (month === 0) { setMonth(11); setYear(year - 1); }
    else setMonth(month - 1);
  };
  const nextMonth = () => {
    if (month === 11) { setMonth(0); setYear(year + 1); }
    else setMonth(month + 1);
  };

  const hasCalendar = GOOGLE_CONFIG.calendarId && !GOOGLE_CONFIG.calendarId.startsWith('YOUR_');

  return (
    <div style={{ paddingTop: 90 }}>
      <Section>
        <SectionTitle sub="Project timeline, workshop dates, and important milestones. Connect with our shared Google Calendar for live updates.">
          Calendar
        </SectionTitle>

        <div style={{
          padding: 20, borderRadius: 12, background: COLORS.frost,
          border: `1px solid ${COLORS.electric}12`, marginBottom: 28,
        }}>
          <p style={{ fontSize: 14, color: COLORS.slate, lineHeight: 1.6, margin: 0, fontFamily: "'DM Sans', sans-serif" }}>
            {hasCalendar
              ? 'View the shared Google Calendar below with project milestones, workshop dates, and stakeholder events.'
              : 'A shared Google Calendar will be embedded here with project milestones, workshop dates, and stakeholder events.'}
            <br />
            <a href={`https://drive.google.com/drive/folders/${GOOGLE_CONFIG.driveFolderId}`} target="_blank" rel="noreferrer" style={{
              color: COLORS.electric, fontWeight: 600, textDecoration: 'none',
            }}>Access shared Google Drive resources &rarr;</a>
          </p>
        </div>

        {hasCalendar && (
          <div style={{ marginBottom: 32 }}>
            <iframe
              src={`https://calendar.google.com/calendar/embed?src=${encodeURIComponent(GOOGLE_CONFIG.calendarId)}&ctz=America/Detroit`}
              title="R2I2 Shared Calendar"
              style={{
                width: '100%', height: 600, border: 'none', borderRadius: 12,
                boxShadow: `0 2px 12px ${COLORS.navy}08`,
              }}
            />
          </div>
        )}

        {/* Simple calendar widget */}
        <div style={{ maxWidth: 500, margin: '0 auto' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <button onClick={prevMonth}
              style={{ background: 'none', border: `1px solid ${COLORS.electric}33`, borderRadius: 6, padding: '6px 12px', cursor: 'pointer', color: COLORS.electric, fontWeight: 700 }}>{'\u2039'}</button>
            <span style={{ fontSize: 18, fontWeight: 700, color: COLORS.darkSlate, fontFamily: "'Libre Baskerville', serif" }}>
              {MONTH_NAMES[month]} {year}
            </span>
            <button onClick={nextMonth}
              style={{ background: 'none', border: `1px solid ${COLORS.electric}33`, borderRadius: 6, padding: '6px 12px', cursor: 'pointer', color: COLORS.electric, fontWeight: 700 }}>{'\u203A'}</button>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 2, textAlign: 'center' }}>
            {['Su','Mo','Tu','We','Th','Fr','Sa'].map(d => (
              <div key={d} style={{ padding: 8, fontSize: 12, fontWeight: 700, color: COLORS.slate, fontFamily: "'DM Sans', sans-serif" }}>{d}</div>
            ))}
            {Array.from({ length: startDay }, (_, i) => (
              <div key={`e${i}`} />
            ))}
            {Array.from({ length: daysInMonth }, (_, i) => {
              const day = i + 1;
              const isToday = day === today.getDate() && month === today.getMonth() && year === today.getFullYear();
              return (
                <div key={day} style={{
                  padding: 8, fontSize: 13, borderRadius: 6,
                  background: isToday ? COLORS.electric : 'transparent',
                  color: isToday ? COLORS.white : COLORS.darkSlate,
                  fontWeight: isToday ? 700 : 400,
                  fontFamily: "'DM Sans', sans-serif",
                }}>{day}</div>
              );
            })}
          </div>
        </div>
      </Section>
    </div>
  );
}
