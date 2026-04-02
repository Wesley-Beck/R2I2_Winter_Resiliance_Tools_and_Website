import { fetchPortalPermissions, fetchPortalFiles } from './googleSheets';

export async function getUserGroup(email) {
  if (!email) return null;
  const perms = await fetchPortalPermissions();
  if (!perms) return null;
  const entry = perms.find(p => p.email === email.toLowerCase());
  return entry ? entry.group : null;
}

export async function getFilesForGroup(group) {
  const files = await fetchPortalFiles();
  if (!files) return null;
  return files.filter(f => f.group === 'all' || f.group === group);
}

export function groupFilesByFolder(files) {
  const folders = {};
  for (const f of files) {
    if (!folders[f.folder]) folders[f.folder] = [];
    folders[f.folder].push(f);
  }
  return folders;
}
