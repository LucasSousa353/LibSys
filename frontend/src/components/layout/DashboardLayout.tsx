import { useState } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  BookOpen,
  Users,
  ArrowLeftRight,
  LogOut,
  Menu,
  Sun,
  Moon,
  Library
} from 'lucide-react';
import { useTheme } from '../../contexts/ThemeContext';
import { useAuth } from '../../contexts/AuthContext';
import { useLanguage } from '../../contexts/LanguageContext';

export default function DashboardLayout() {
  const [isSidebarOpen, setSidebarOpen] = useState(true);
  const { theme, toggleTheme } = useTheme();
  const { logout, role, user } = useAuth();
  const { t, language, setLanguage } = useLanguage();

  const userInitials = (() => {
    if (!user?.name) return '?';
    const parts = user.name.trim().split(/\s+/);
    if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    return parts[0].substring(0, 2).toUpperCase();
  })();

  const roleLabel = role ? role.charAt(0).toUpperCase() + role.slice(1) : '';
  const navigate = useNavigate();

  const isDarkMode = theme === 'dark';

  const allItems = [
    { icon: LayoutDashboard, label: t('nav.dashboard'), path: '/dashboard' },
    { icon: BookOpen, label: t('nav.catalog'), path: '/books' },
    { icon: Users, label: t('nav.members'), path: '/users' },
    { icon: ArrowLeftRight, label: t('nav.loans'), path: '/loans' },
  ];

  const navItems = allItems.filter((item) => {
    if (role === 'admin') return true;
    if (role === 'librarian') return item.path === '/books' || item.path === '/loans';
    if (role === 'user') return item.path === '/books' || item.path === '/loans';
    return true;
  });

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className={`flex h-screen overflow-hidden bg-background-light dark:bg-background-dark text-slate-900 dark:text-white transition-colors duration-200 font-display`}>

      <aside className={`${isSidebarOpen ? 'w-64' : 'w-20'} bg-white dark:bg-surface-dark border-r border-border-light dark:border-border-dark flex flex-col transition-all duration-300 z-20 hidden md:flex`}>
        <div className="h-16 flex items-center justify-center border-b border-border-light dark:border-border-dark">
          <div className="flex items-center gap-3">
            <div className="size-8 rounded-lg bg-primary flex items-center justify-center text-white">
              <Library size={18} />
            </div>
            {isSidebarOpen && <span className="font-bold text-lg">LibSys</span>}
          </div>
        </div>

        <nav className="flex-1 py-6 px-3 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => `
                flex items-center gap-3 px-3 py-3 rounded-lg transition-colors group
                ${isActive
                  ? 'bg-primary text-white'
                  : 'text-text-secondary hover:bg-slate-100 dark:hover:bg-slate-800 dark:text-slate-400 dark:hover:text-white'}
              `}
            >
              <item.icon size={20} />
              {isSidebarOpen && <span className="font-medium text-sm">{item.label}</span>}
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-border-light dark:border-border-dark">
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 w-full p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 transition-colors"
          >
            <LogOut size={20} />
            {isSidebarOpen && <span className="text-sm font-medium">{t('nav.logout')}</span>}
          </button>
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">

        <header className="h-16 bg-white dark:bg-surface-dark border-b border-border-light dark:border-border-dark flex items-center justify-between px-6 z-10">
          <div className="flex items-center gap-4">
            <button onClick={() => setSidebarOpen(!isSidebarOpen)} className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500">
              <Menu size={20} />
            </button>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1 rounded-full bg-slate-100 dark:bg-slate-800 p-1">
              <button
                type="button"
                onClick={() => setLanguage('pt-BR')}
                className={`px-2.5 py-1 text-xs font-semibold rounded-full transition-colors ${
                  language === 'pt-BR'
                    ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
                    : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                }`}
                aria-label="PT-BR"
              >
                PT-BR
              </button>
              <button
                type="button"
                onClick={() => setLanguage('en-US')}
                className={`px-2.5 py-1 text-xs font-semibold rounded-full transition-colors ${
                  language === 'en-US'
                    ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
                    : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                }`}
                aria-label="EN-US"
              >
                EN-US
              </button>
            </div>
            <button onClick={toggleTheme} className="p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400">
              {isDarkMode ? <Sun size={20} /> : <Moon size={20} />}
            </button>
            <div className="flex items-center gap-3">
              <div className="size-9 rounded-full bg-primary/20 flex items-center justify-center text-primary font-bold text-sm border border-primary/30">
                {userInitials}
              </div>
              {roleLabel && (
                <span className="hidden sm:inline text-xs font-semibold px-2 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                  {roleLabel}
                </span>
              )}
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-auto bg-background-light dark:bg-background-dark p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}