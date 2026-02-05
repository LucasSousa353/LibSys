import { useState } from 'react';
import {
  BookOpen,
  ArrowLeftRight,
  AlertTriangle,
  DollarSign,
  TrendingUp,
  TrendingDown,
  BookMarked,
  Check,
  UserPlus,
  Clock
} from 'lucide-react';
import { Card, Badge } from '../../components/ui';

interface MetricCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  iconBgColor: string;
  trend?: { value: string; positive: boolean };
}

function MetricCard({ title, value, icon, iconBgColor, trend }: MetricCardProps) {
  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <div className={`size-10 rounded-lg ${iconBgColor} flex items-center justify-center`}>
          {icon}
        </div>
        {trend && (
          <span className={`
            flex items-center text-xs font-medium px-2 py-1 rounded-full
            ${trend.positive
              ? 'text-green-600 bg-green-50 dark:bg-green-900/20 dark:text-green-400'
              : 'text-red-600 bg-red-50 dark:bg-red-900/20 dark:text-red-400'
            }
          `}>
            {trend.positive ? <TrendingUp size={14} className="mr-1" /> : <TrendingDown size={14} className="mr-1" />}
            {trend.value}
          </span>
        )}
      </div>
      <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{title}</p>
      <h3 className="text-2xl font-bold text-slate-900 dark:text-white mt-1">{value}</h3>
    </Card>
  );
}

const recentBooks = [
  { id: 1, title: 'The Great Gatsby', author: 'F. Scott Fitzgerald', isbn: '978-0743273565', category: 'Fiction', status: 'Available' },
  { id: 2, title: 'To Kill a Mockingbird', author: 'Harper Lee', isbn: '978-0061120084', category: 'Classic', status: 'Checked Out' },
  { id: 3, title: '1984', author: 'George Orwell', isbn: '978-0451524935', category: 'Dystopian', status: 'Available' },
  { id: 4, title: 'The Catcher in the Rye', author: 'J.D. Salinger', isbn: '978-0316769480', category: 'Fiction', status: 'Reserved' },
  { id: 5, title: 'Sapiens', author: 'Yuval Noah Harari', isbn: '978-0062316097', category: 'Non-Fiction', status: 'Available' },
];

const recentActivity = [
  { id: 1, type: 'loan', title: 'New Loan Created', description: '"Sapiens" borrowed by', user: 'Sarah Jenkins', time: 'Just now', icon: BookMarked, color: 'blue' },
  { id: 2, type: 'return', title: 'Book Returned', description: '"The Hobbit" returned by', user: 'Mike Ross', time: '25 minutes ago', icon: Check, color: 'green' },
  { id: 3, type: 'overdue', title: 'Overdue Alert', description: '"Dune" is now 3 days overdue.', user: '', time: '2 hours ago', icon: AlertTriangle, color: 'red' },
  { id: 4, type: 'member', title: 'New Member', description: 'Jessica Pearson registered.', user: '', time: '5 hours ago', icon: UserPlus, color: 'purple' },
];

const getStatusBadge = (status: string) => {
  const variants: Record<string, 'success' | 'warning' | 'danger' | 'default'> = {
    'Available': 'success',
    'Checked Out': 'warning',
    'Reserved': 'info' as any,
    'Overdue': 'danger',
  };
  return <Badge variant={variants[status] || 'default'}>{status}</Badge>;
};

const getCategoryBadge = (category: string) => {
  const colors: Record<string, string> = {
    'Fiction': 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
    'Classic': 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300',
    'Dystopian': 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
    'Non-Fiction': 'bg-gray-100 text-gray-800 dark:bg-slate-700 dark:text-gray-300',
  };
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colors[category] || colors['Non-Fiction']}`}>
      {category}
    </span>
  );
};

const getActivityIcon = (color: string, Icon: React.ElementType) => {
  const colors: Record<string, string> = {
    blue: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400',
    green: 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400',
    red: 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400',
    purple: 'bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400',
  };
  return (
    <span className={`absolute flex items-center justify-center w-8 h-8 rounded-full -left-4 ring-4 ring-white dark:ring-surface-dark ${colors[color]}`}>
      <Icon size={14} />
    </span>
  );
};

export default function DashboardPage() {
  const [stats] = useState({
    totalBooks: 12450,
    activeLoans: 342,
    overdueBooks: 15,
    totalFines: 420.50,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Dashboard Overview</h1>
        <p className="text-slate-500 dark:text-slate-400 mt-1">Welcome back! Here's what's happening in your library.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        <MetricCard
          title="Total Books"
          value={stats.totalBooks.toLocaleString()}
          icon={<BookOpen size={20} className="text-primary" />}
          iconBgColor="bg-blue-50 dark:bg-blue-900/20"
          trend={{ value: '+5%', positive: true }}
        />
        <MetricCard
          title="Active Loans"
          value={stats.activeLoans.toLocaleString()}
          icon={<ArrowLeftRight size={20} className="text-indigo-600 dark:text-indigo-400" />}
          iconBgColor="bg-indigo-50 dark:bg-indigo-900/20"
          trend={{ value: '+12%', positive: true }}
        />
        <MetricCard
          title="Overdue Books"
          value={stats.overdueBooks}
          icon={<AlertTriangle size={20} className="text-orange-600 dark:text-orange-400" />}
          iconBgColor="bg-orange-50 dark:bg-orange-900/20"
          trend={{ value: '-2%', positive: false }}
        />
        <MetricCard
          title="Total Fines"
          value={`$${stats.totalFines.toFixed(2)}`}
          icon={<DollarSign size={20} className="text-emerald-600 dark:text-emerald-400" />}
          iconBgColor="bg-emerald-50 dark:bg-emerald-900/20"
          trend={{ value: '+8%', positive: true }}
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2">
          <Card padding="none" className="overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-slate-200 dark:border-border-dark flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">Recently Added Books</h3>
              <button className="text-sm font-medium text-primary hover:text-primary/80 transition-colors">
                View All
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm whitespace-nowrap">
                <thead className="bg-slate-50 dark:bg-[#111a22] border-b border-slate-200 dark:border-border-dark">
                  <tr>
                    <th className="px-6 py-3 font-medium text-slate-500 dark:text-slate-400">Title</th>
                    <th className="px-6 py-3 font-medium text-slate-500 dark:text-slate-400">Author</th>
                    <th className="px-6 py-3 font-medium text-slate-500 dark:text-slate-400">ISBN</th>
                    <th className="px-6 py-3 font-medium text-slate-500 dark:text-slate-400">Category</th>
                    <th className="px-6 py-3 font-medium text-slate-500 dark:text-slate-400">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-border-dark">
                  {recentBooks.map((book) => (
                    <tr key={book.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                      <td className="px-6 py-4 font-medium text-slate-900 dark:text-white">{book.title}</td>
                      <td className="px-6 py-4 text-slate-500 dark:text-slate-400">{book.author}</td>
                      <td className="px-6 py-4 text-slate-500 dark:text-slate-400 font-mono text-xs">{book.isbn}</td>
                      <td className="px-6 py-4">{getCategoryBadge(book.category)}</td>
                      <td className="px-6 py-4">{getStatusBadge(book.status)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>

        <Card padding="none" className="flex flex-col h-full">
          <div className="px-6 py-4 border-b border-slate-200 dark:border-border-dark">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">Recent Activity</h3>
          </div>
          <div className="p-6 flex-1 overflow-y-auto">
            <ul className="relative border-l border-slate-200 dark:border-slate-700 space-y-6 ml-3">
              {recentActivity.map((activity) => (
                <li key={activity.id} className="ml-6">
                  {getActivityIcon(activity.color, activity.icon)}
                  <div className="flex flex-col gap-1">
                    <h4 className="text-sm font-semibold text-slate-900 dark:text-white">{activity.title}</h4>
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                      {activity.description}
                      {activity.user && <span className="text-primary font-medium"> {activity.user}</span>}
                    </p>
                    <time className="text-xs text-slate-400 dark:text-slate-500 flex items-center gap-1">
                      <Clock size={12} /> {activity.time}
                    </time>
                  </div>
                </li>
              ))}
            </ul>
          </div>
          <div className="px-6 py-4 border-t border-slate-200 dark:border-border-dark mt-auto">
            <button className="w-full text-center text-sm font-medium text-slate-500 hover:text-slate-800 dark:hover:text-white transition-colors">
              View All Activity
            </button>
          </div>
        </Card>
      </div>
    </div>
  );
}
