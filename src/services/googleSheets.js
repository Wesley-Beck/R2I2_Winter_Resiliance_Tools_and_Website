import { GOOGLE_CONFIG } from '../config';

const SHEETS_BASE = `https://docs.google.com/spreadsheets/d/${GOOGLE_CONFIG.sheetId}/gviz/tq`;

function parseGvizResponse(text) {
  // Google Visualization API returns: google.visualization.Query.setResponse({...})
  const match = text.match(/google\.visualization\.Query\.setResponse\(({.*})\)/s);
  if (!match) return [];

  const json = JSON.parse(match[1]);
  if (!json.table) return [];

  const cols = json.table.cols.map(c => c.label || c.id);
  return json.table.rows.map(row => {
    const obj = {};
    row.c.forEach((cell, i) => {
      obj[cols[i]] = cell ? (cell.v ?? '') : '';
    });
    return obj;
  });
}

export async function fetchSheetTab(tabName) {
  if (!GOOGLE_CONFIG.sheetId || GOOGLE_CONFIG.sheetId.startsWith('YOUR_')) {
    return null;
  }

  try {
    const url = `${SHEETS_BASE}?tqx=out:json&sheet=${encodeURIComponent(tabName)}`;
    const res = await fetch(url);
    if (!res.ok) return null;
    const text = await res.text();
    const rows = parseGvizResponse(text);
    // Filter by visible column if it exists
    return rows.filter(r => {
      if ('visible' in r) {
        const v = String(r.visible).toLowerCase();
        return v === 'true' || v === '1' || v === 'yes';
      }
      return true;
    });
  } catch {
    return null;
  }
}

export async function fetchTeamMembers() {
  const rows = await fetchSheetTab('TeamMembers');
  if (!rows) return null;
  return rows.map(r => ({
    name: r.name || '',
    role: r.role || '',
    org: r.org || '',
    interests: r.interests || '',
    link: r.link || '',
    category: (r.category || '').toLowerCase(),
  }));
}

export async function fetchNews() {
  const rows = await fetchSheetTab('News');
  if (!rows) return null;
  return rows.map((r, i) => ({
    id: i + 1,
    title: r.title || '',
    date: r.date || '',
    summary: r.summary || '',
    tag: r.tag || '',
  }));
}

export async function fetchWorkshops() {
  const rows = await fetchSheetTab('Workshops');
  if (!rows) return null;
  return rows.map(r => ({
    id: Number(r.id) || 0,
    title: r.title || '',
    desc: r.description || r.desc || '',
    status: (r.status || 'planned').toLowerCase(),
    date: r.date || '',
    formUrl: r.formUrl || '',
  }));
}

export async function fetchTools() {
  const rows = await fetchSheetTab('Tools');
  if (!rows) return null;
  return rows.map(r => ({
    name: r.name || '',
    link: r.link || '',
    desc: r.description || r.desc || '',
  }));
}

export async function fetchDataPortals() {
  const rows = await fetchSheetTab('DataPortals');
  if (!rows) return null;
  return rows.map(r => ({
    name: r.name || '',
    link: r.link || '',
  }));
}

export async function fetchPortalFiles() {
  const rows = await fetchSheetTab('PortalFiles');
  if (!rows) return null;
  return rows.map(r => ({
    group: (r.group || 'all').toLowerCase(),
    folder: r.folder || 'General',
    title: r.title || '',
    googleFileId: r.googleFileId || '',
    fileType: (r.fileType || 'doc').toLowerCase(),
  }));
}

export async function fetchPortalPermissions() {
  const rows = await fetchSheetTab('PortalPermissions');
  if (!rows) return null;
  return rows.map(r => ({
    email: (r.email || '').toLowerCase(),
    group: (r.group || '').toLowerCase(),
  }));
}
