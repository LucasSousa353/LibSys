import { useEffect, useState } from 'react';
import {
  BookOpen,
  ArrowLeftRight,
  AlertTriangle,
  DollarSign,
} from 'lucide-react';
import { Card, Badge } from '../../components/ui';
import { analyticsApi } from '../../services/api';
import type { DashboardSummary, Book } from '../../types';

interface MetricCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  iconBgColor: string;
}

function MetricCard({ title, value, icon, iconBgColor }: MetricCardProps) {
  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <div className={`size-10 rounded-lg ${iconBgColor} flex items-center justify-center`}>
          {icon}
        </div>
      </div>
      <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{title}</p>
      <h3 className="text-2xl font-bold text-slate-900 dark:text-white mt-1">{value}</h3>
    </Card>
  );
}

const getStatusBadge = (book: Book) => {
  const available = book.available_copies ?? book.total_copies;
  if (available > 0) {
    return <Badge variant="success">Available</Badge>;
  }
  return <Badge variant="warning">Borrowed</Badge>;
};

export default function DashboardPage() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        const summary = await analyticsApi.dashboard();
        setData(summary);
      } catch (err) {
        console.error('Error loading dashboard:', err);
        setError('Unable to load dashboard data.');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-sm text-rose-500">{error || 'No data available.'}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Dashboard Overview</h1>
        <p className="text-slate-500 dark:text-slate-400 mt-1">Welcome back! Here's what's happening in your library.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        <MetricCard
          title="Total Books"
          value={data.total_books.toLocaleString()}
          icon={<BookOpen size={20} className="text-primary" />}
          iconBgColor="bg-blue-50 dark:bg-blue-900/20"
        />
        <MetricCard
          title="Active Loans"
          value={data.active_loans.toLocaleString()}
          icon={<ArrowLeftRight size={20} className="text-indigo-600 dark:text-indigo-400" />}
          iconBgColor="bg-indigo-50 dark:bg-indigo-900/20"
        />
        <MetricCard
          title="Overdue Loans"
          value={data.overdue_loans}
          icon={<AlertTriangle size={20} className="text-orange-600 dark:text-orange-400" />}
          iconBgColor="bg-orange-50 dark:bg-orange-900/20"
        />
        <MetricCard
          title="Total Fines"
          value={`R$ ${Number(data.total_fines).toFixed(2)}`}
          icon={<DollarSign size={20} className="text-emerald-600 dark:text-emerald-400" />}
          iconBgColor="bg-emerald-50 dark:bg-emerald-900/20"
        />
      </div>

      <div className="grid grid-cols-1 gap-6">
        <Card padding="none" className="overflow-hidden flex flex-col">
          <div className="px-6 py-4 border-b border-slate-200 dark:border-border-dark flex items-center justify-between">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">Recently Added Books</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead className="bg-slate-50 dark:bg-[#111a22] border-b border-slate-200 dark:border-border-dark">
                <tr>
                  <th className="px-6 py-3 font-medium text-slate-500 dark:text-slate-400">Title</th>
                  <th className="px-6 py-3 font-medium text-slate-500 dark:text-slate-400">Author</th>
                  <th className="px-6 py-3 font-medium text-slate-500 dark:text-slate-400">ISBN</th>
                  <th className="px-6 py-3 font-medium text-slate-500 dark:text-slate-400">Status</th>
                  <th className="px-6 py-3 font-medium text-slate-500 dark:text-slate-400 text-center">Stock</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-border-dark">
                {data.recent_books.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-6 py-6 text-center text-sm text-slate-500 dark:text-slate-400">
                      No books registered yet.
                    </td>
                  </tr>
                )}
                {data.recent_books.map((book) => (
                  <tr key={book.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                    <td className="px-6 py-4 font-medium text-slate-900 dark:text-white">{book.title}</td>
                    <td className="px-6 py-4 text-slate-500 dark:text-slate-400">{book.author}</td>
                    <td className="px-6 py-4 text-slate-500 dark:text-slate-400 font-mono text-xs">{book.isbn}</td>
                    <td className="px-6 py-4">{getStatusBadge(book)}</td>
                    <td className="px-6 py-4 text-center font-medium text-slate-900 dark:text-white">
                      {book.available_copies ?? book.total_copies}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </div>
  );
}
