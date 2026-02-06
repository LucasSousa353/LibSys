import { useState } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  BookOpen,
  Users,
  ArrowLeftRight,
  FileText,
  LogOut,
  Menu,
  Search,
  Bell,
  Sun,
  Moon,
  Library
} from 'lucide-react';
import { useTheme } from '../../contexts/ThemeContext';
import { useAuth } from '../../contexts/AuthContext';

export default function DashboardLayout() {
  const [isSidebarOpen, setSidebarOpen] = useState(true);
  const { theme, toggleTheme } = useTheme();
  const { logout, role } = useAuth();
  const navigate = useNavigate();

  const isDarkMode = theme === 'dark';

  const allItems = [
    { icon: LayoutDashboard, label: 'Dashboard', path: '/dashboard' },
    { icon: BookOpen, label: 'Catalog', path: '/books' },
    { icon: Users, label: 'Members', path: '/users' },
    { icon: ArrowLeftRight, label: 'Loans', path: '/loans' },
    { icon: FileText, label: 'Reports', path: '/reports' },
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
            {isSidebarOpen && <span className="text-sm font-medium">Logout</span>}
          </button>
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">

        <header className="h-16 bg-white dark:bg-surface-dark border-b border-border-light dark:border-border-dark flex items-center justify-between px-6 z-10">
          <div className="flex items-center gap-4">
            <button onClick={() => setSidebarOpen(!isSidebarOpen)} className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500">
              <Menu size={20} />
            </button>
            <div className="hidden md:flex items-center bg-slate-100 dark:bg-background-dark rounded-lg px-3 py-2 w-64 lg:w-96 border border-transparent focus-within:border-primary transition-all">
              <Search size={18} className="text-slate-400" />
              <input
                type="text"
                placeholder="Search for books, ISBN, users..."
                className="bg-transparent border-none outline-none text-sm ml-2 w-full placeholder-slate-400 dark:text-white focus:ring-0"
              />
            </div>
          </div>

          <div className="flex items-center gap-4">
            <button onClick={toggleTheme} className="p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400">
              {isDarkMode ? <Sun size={20} /> : <Moon size={20} />}
            </button>
            <button className="relative p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400">
              <Bell size={20} />
              <span className="absolute top-2 right-2 size-2 bg-red-500 rounded-full border-2 border-white dark:border-surface-dark"></span>
            </button>
            <div className="size-9 rounded-full bg-primary/20 flex items-center justify-center text-primary font-bold border border-primary/30 cursor-pointer">
              TL
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