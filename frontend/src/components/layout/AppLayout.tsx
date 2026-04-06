import { useCallback } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import SearchBar from '../common/SearchBar';
import { fetchStats } from '../../api/client';
import type { GraphStats } from '../../types';

export default function AppLayout() {
  const navigate = useNavigate();

  const { data: stats } = useQuery<GraphStats>({
    queryKey: ['stats'],
    queryFn: fetchStats,
  });

  const handleSearchSelect = useCallback((id: string) => {
    if (id.startsWith('person:')) {
      const shortId = id.replace(/^person:/, '');
      navigate(`/person/${shortId}`);
    }
  }, [navigate]);

  const handleHomeClick = useCallback(() => {
    navigate('/');
  }, [navigate]);

  return (
    <div className="h-screen flex flex-col" style={{ backgroundColor: 'var(--color-bg)' }}>
      <header
        className="border-b px-4 py-2.5 flex items-center justify-between flex-shrink-0"
        style={{ borderColor: 'var(--color-border)' }}
      >
        <div className="flex items-center gap-4">
          <button
            onClick={handleHomeClick}
            className="flex items-center gap-2 cursor-pointer"
          >
            <h1 className="text-xl font-semibold" style={{ color: 'var(--color-accent)' }}>
              Lamp
            </h1>
          </button>

          {/* View nav */}
          <nav className="flex gap-1">
            <NavLink
              to="/"
              end
              className="px-3 py-1 text-xs rounded border transition-colors"
              style={({ isActive }) => ({
                backgroundColor: isActive ? 'var(--color-accent-dim)' : 'var(--color-bg-secondary)',
                borderColor: isActive ? 'var(--color-accent)' : 'var(--color-border)',
                color: isActive ? 'var(--color-accent)' : 'var(--color-text-secondary)',
              })}
            >
              Tree
            </NavLink>
            <NavLink
              to="/timeline"
              className="px-3 py-1 text-xs rounded border transition-colors"
              style={({ isActive }) => ({
                backgroundColor: isActive ? 'var(--color-accent-dim)' : 'var(--color-bg-secondary)',
                borderColor: isActive ? 'var(--color-accent)' : 'var(--color-border)',
                color: isActive ? 'var(--color-accent)' : 'var(--color-text-secondary)',
              })}
            >
              Timeline
            </NavLink>
            <NavLink
              to="/places"
              className="px-3 py-1 text-xs rounded border transition-colors"
              style={({ isActive }) => ({
                backgroundColor: isActive ? 'var(--color-accent-dim)' : 'var(--color-bg-secondary)',
                borderColor: isActive ? 'var(--color-accent)' : 'var(--color-border)',
                color: isActive ? 'var(--color-accent)' : 'var(--color-text-secondary)',
              })}
            >
              Places
            </NavLink>
          </nav>
        </div>

        <div className="flex items-center gap-4">
          <SearchBar onSelect={handleSearchSelect} />
          {stats && (
            <div className="text-xs text-text-secondary hidden sm:block">
              {stats.persons} persons · {stats.nations} nations · {stats.edges} links
            </div>
          )}
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        <Outlet />
      </div>
    </div>
  );
}
