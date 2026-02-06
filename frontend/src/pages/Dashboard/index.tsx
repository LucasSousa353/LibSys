import { useEffect, useState } from 'react';
import {
  BookOpen,
  Users,
  ArrowLeftRight,
  AlertTriangle,
  DollarSign,
  Download,
  FileText,
} from 'lucide-react';
import { Card, Badge, Button } from '../../components/ui';
import { analyticsApi, loansApi } from '../../services/api';
import type { DashboardSummary, Book } from '../../types';

const downloadBlob = (blob: Blob, filename: string) => {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};

interface MetricCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  iconBgColor: string;
}

function MetricCard({ title, value, icon, iconBgColor }: MetricCardProps) {
  return (
    <Card>
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{title}</p>
        <div className={`size-9 rounded-lg ${iconBgColor} flex items-center justify-center`}>
          {icon}
        </div>
      </div>
      <p className="text-3xl font-bold text-slate-900 dark:text-white">{value}</p>
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

  const handleExportCsv = async () => {
    const today = new Date().toISOString().split('T')[0];
    try {
      const blob = await loansApi.exportCsv();
      downloadBlob(blob, `loans_report_${today}.csv`);
    } catch (err) {
      console.error('Export CSV error:', err);
    }
  };

  const handleExportPdf = async () => {
    const today = new Date().toISOString().split('T')[0];
    try {
      const blob = await loansApi.exportPdf();
      downloadBlob(blob, `loans_report_${today}.pdf`);
    } catch (err) {
      console.error('Export PDF error:', err);
    }
  };

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

  const maxLoanCount = data.most_borrowed_books.length > 0
    ? Math.max(...data.most_borrowed_books.map((b) => b.loan_count))
    : 1;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Dashboard</h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">Overview of your library performance, loans, and reports.</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" icon={<Download size={18} />} onClick={handleExportCsv}>
            Export CSV
          </Button>
          <Button icon={<FileText size={18} />} onClick={handleExportPdf}>
            Export PDF
          </Button>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <MetricCard
          title="Total Books"
          value={data.total_books.toLocaleString()}
          icon={<BookOpen size={18} className="text-blue-600 dark:text-blue-400" />}
          iconBgColor="bg-blue-50 dark:bg-blue-900/20"
        />
        <MetricCard
          title="Total Users"
          value={data.total_users.toLocaleString()}
          icon={<Users size={18} className="text-purple-600 dark:text-purple-400" />}
          iconBgColor="bg-purple-50 dark:bg-purple-900/20"
        />
        <MetricCard
          title="Active Loans"
          value={data.active_loans.toLocaleString()}
          icon={<ArrowLeftRight size={18} className="text-indigo-600 dark:text-indigo-400" />}
          iconBgColor="bg-indigo-50 dark:bg-indigo-900/20"
        />
        <MetricCard
          title="Overdue Loans"
          value={data.overdue_loans}
          icon={<AlertTriangle size={18} className="text-orange-600 dark:text-orange-400" />}
          iconBgColor="bg-orange-50 dark:bg-orange-900/20"
        />
        <MetricCard
          title="Total Fines"
          value={`R$ ${Number(data.total_fines).toFixed(2)}`}
          icon={<DollarSign size={18} className="text-emerald-600 dark:text-emerald-400" />}
          iconBgColor="bg-emerald-50 dark:bg-emerald-900/20"
        />
      </div>

      {/* Two-column layout: Bar chart + Recent books */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Most Borrowed Books - bar chart */}
        <Card>
          <div className="mb-6">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Most Borrowed Books</h3>
            <p className="text-sm text-slate-500 dark:text-slate-400">Top performers by total loans</p>
          </div>
          {data.most_borrowed_books.length === 0 ? (
            <p className="text-sm text-slate-500 dark:text-slate-400 text-center py-8">No loan data available yet.</p>
          ) : (
            <div className="flex items-end gap-4 h-[260px] px-2">
              {data.most_borrowed_books.map((book) => {
                const barHeight = Math.max(20, (book.loan_count / maxLoanCount) * 200);
                return (
                  <div key={book.book_id} className="flex flex-col items-center w-full group">
                    <span className="text-xs font-semibold text-slate-900 dark:text-white mb-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      {book.loan_count}
                    </span>
                    <div
                      className="w-full rounded-t-lg bg-primary/80 group-hover:bg-primary transition-all"
                      style={{ height: `${barHeight}px` }}
                    />
                    <div className="text-center mt-2">
                      <span className="text-xs font-medium text-slate-600 dark:text-slate-400 block truncate max-w-[80px]">
                        {book.title}
                      </span>
                      <span className="text-[10px] text-slate-400 dark:text-slate-500 block truncate max-w-[80px]">
                        {book.author}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>

        {/* Recently Added Books table */}
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
