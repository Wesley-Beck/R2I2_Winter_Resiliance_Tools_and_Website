import { useState, useEffect } from 'react';
import { COLORS } from './constants/theme';
import './App.css';

import SnowflakesBG from './components/SnowflakesBG';
import Header from './components/Header';
import Footer from './components/Footer';

import HomePage from './pages/HomePage';
import TeamPage from './pages/TeamPage';
import WorkshopsPage from './pages/WorkshopsPage';
import DataToolsPage from './pages/DataToolsPage';
import NewsPage from './pages/NewsPage';
import CalendarPage from './pages/CalendarPage';
import LoginPage from './pages/LoginPage';
import PortalPage from './pages/PortalPage';

import useScrollPosition from './hooks/useScrollPosition';
import useGoogleSheets from './hooks/useGoogleSheets';
import useGoogleAuth from './hooks/useGoogleAuth';

export default function App() {
  const [page, setPage] = useState('home');
  const scrolled = useScrollPosition();
  const sheetsData = useGoogleSheets();
  const { user, signIn, signOut } = useGoogleAuth();

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [page]);

  const renderPage = () => {
    switch (page) {
      case 'home':
        return <HomePage setPage={setPage} />;
      case 'team':
        return <TeamPage teamData={sheetsData.team} />;
      case 'workshops':
        return <WorkshopsPage workshopData={sheetsData.workshops} />;
      case 'data-tools':
        return <DataToolsPage toolsData={sheetsData.tools} portalsData={sheetsData.portals} />;
      case 'news':
        return <NewsPage newsData={sheetsData.news} />;
      case 'calendar':
        return <CalendarPage />;
      case 'login':
        return <LoginPage onSignIn={signIn} user={user} setPage={setPage} />;
      case 'portal':
        return <PortalPage user={user} onSignOut={() => { signOut(); setPage('home'); }} setPage={setPage} />;
      default:
        return <HomePage setPage={setPage} />;
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: COLORS.snow,
      fontFamily: "'DM Sans', system-ui, sans-serif",
    }}>
      <SnowflakesBG />
      <Header page={page} setPage={setPage} scrolled={scrolled} user={user} />
      <main style={{ position: 'relative', zIndex: 1 }}>
        {renderPage()}
      </main>
      <Footer setPage={setPage} />
    </div>
  );
}
