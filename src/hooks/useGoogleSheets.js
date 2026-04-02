import { useState, useEffect } from 'react';
import {
  fetchTeamMembers,
  fetchNews,
  fetchWorkshops,
  fetchTools,
  fetchDataPortals,
} from '../services/googleSheets';

export default function useGoogleSheets() {
  const [data, setData] = useState({
    team: null,
    news: null,
    workshops: null,
    tools: null,
    portals: null,
    loading: true,
  });

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const [team, news, workshops, tools, portals] = await Promise.all([
        fetchTeamMembers(),
        fetchNews(),
        fetchWorkshops(),
        fetchTools(),
        fetchDataPortals(),
      ]);

      if (!cancelled) {
        setData({ team, news, workshops, tools, portals, loading: false });
      }
    }

    load();
    return () => { cancelled = true; };
  }, []);

  return data;
}
