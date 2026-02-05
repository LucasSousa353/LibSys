import {
  Download,
  FileText
} from 'lucide-react';
import { Card, Button, Badge } from '../../components/ui';

const stats = [
  { title: 'Revenue from Fines', value: '$4,285.50', change: '+5.2%', positive: true },
  { title: 'Active Loans', value: '1,240', change: '+12.0%', positive: true },
  { title: 'Overdue Books', value: '85', change: '-2.5%', positive: false },
  { title: 'New Members', value: '142', change: '+8.4%', positive: true },
];

const transactions = [
  { id: 'TRX-93821', member: 'Alice Martin', memberId: '88293', date: 'Oct 24, 2023', time: '14:30', type: 'Late Fee', status: 'Paid', amount: 4.50, initials: 'AM', color: 'orange' },
  { id: 'TRX-93822', member: 'John Smith', memberId: '11029', date: 'Oct 24, 2023', time: '11:15', type: 'Lost Book Replacement', status: 'Pending', amount: 24.99, initials: 'JS', color: 'blue' },
  { id: 'TRX-93823', member: 'Elena K.', memberId: '55432', date: 'Oct 23, 2023', time: '09:45', type: 'Late Fee', status: 'Paid', amount: 1.25, initials: 'EK', color: 'purple' },
  { id: 'TRX-93824', member: 'Mike Ross', memberId: '77211', date: 'Oct 22, 2023', time: '16:20', type: 'Membership Renewal', status: 'Paid', amount: 50.00, initials: 'MR', color: 'pink' },
  { id: 'TRX-93825', member: 'Sarah Lee', memberId: '99123', date: 'Oct 21, 2023', time: '13:10', type: 'Late Fee', status: 'Failed', amount: 3.00, initials: 'SL', color: 'teal' },
];

const topBooks = [
  { title: 'Atomic', count: 240, height: '95%' },
  { title: '1984', count: 185, height: '75%' },
  { title: 'Dune', count: 156, height: '65%' },
  { title: 'Gatsby', count: 120, height: '50%' },
  { title: 'Sapiens', count: 94, height: '40%' },
];

const getStatusBadge = (status: string) => {
  const variants: Record<string, 'success' | 'warning' | 'danger'> = {
    Paid: 'success',
    Pending: 'warning',
    Failed: 'danger',
  };
  return <Badge variant={variants[status]} dot>{status}</Badge>;
};

const getAvatarColor = (color: string) => {
  const colors: Record<string, string> = {
    orange: 'bg-orange-100 text-orange-600 dark:bg-orange-900/30 dark:text-orange-400',
    blue: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400',
    purple: 'bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400',
    pink: 'bg-pink-100 text-pink-600 dark:bg-pink-900/30 dark:text-pink-400',
    teal: 'bg-teal-100 text-teal-600 dark:bg-teal-900/30 dark:text-teal-400',
  };
  return colors[color] || colors.blue;
};

export default function ReportsPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white">Analytics Overview</h1>
          <p className="text-slate-500 dark:text-slate-400">Track library performance, loan metrics, and financial health.</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" icon={<Download size={18} />}>
            Export CSV
          </Button>
          <Button icon={<FileText size={18} />}>
            Export PDF
          </Button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat, index) => (
          <Card key={index}>
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{stat.title}</p>
              <span className={`
                flex items-center text-xs font-medium px-2 py-0.5 rounded-full
                ${stat.positive
                  ? 'text-emerald-600 bg-emerald-100 dark:bg-emerald-900/30 dark:text-emerald-400'
                  : 'text-rose-600 bg-rose-100 dark:bg-rose-900/30 dark:text-rose-400'
                }
              `}>
                {stat.change}
              </span>
            </div>
            <p className="mt-2 text-3xl font-bold text-slate-900 dark:text-white">{stat.value}</p>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Compared to last month</p>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Most Borrowed Books</h3>
              <p className="text-sm text-slate-500 dark:text-slate-400">Top performers this month</p>
            </div>
          </div>
          <div className="flex items-end justify-between gap-4 h-[240px] px-2 pb-2">
            {topBooks.map((book, index) => (
              <div key={index} className="flex flex-col items-center gap-2 group w-full">
                <div
                  className="relative w-full rounded-t-lg bg-primary/20 dark:bg-primary/20 group-hover:bg-primary/30 transition-all flex items-end justify-center pb-2"
                  style={{ height: book.height }}
                >
                  <div className="w-full bg-primary mx-3 rounded-t-md h-[90%] relative">
                    <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-slate-800 text-white text-xs py-1 px-2 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                      {book.count}
                    </div>
                  </div>
                </div>
                <span className="text-xs font-medium text-slate-600 dark:text-slate-400">{book.title}</span>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Loan Trends</h3>
              <p className="text-sm text-slate-500 dark:text-slate-400">Daily loans over last 30 days</p>
            </div>
            <div className="flex gap-4">
              <span className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
                <span className="size-2 rounded-full bg-primary"></span> Current
              </span>
              <span className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
                <span className="size-2 rounded-full bg-slate-300 dark:bg-slate-600"></span> Previous
              </span>
            </div>
          </div>
          <div className="h-[240px] relative">
            <svg className="w-full h-full text-primary" preserveAspectRatio="none" viewBox="0 0 400 150">
              <defs>
                <linearGradient id="chartGradient" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor="currentColor" stopOpacity="0.2"></stop>
                  <stop offset="100%" stopColor="currentColor" stopOpacity="0"></stop>
                </linearGradient>
              </defs>
              <line className="dark:stroke-slate-700" stroke="#e2e8f0" strokeDasharray="4 4" strokeWidth="1" x1="0" x2="400" y1="120" y2="120"></line>
              <line className="dark:stroke-slate-700" stroke="#e2e8f0" strokeDasharray="4 4" strokeWidth="1" x1="0" x2="400" y1="80" y2="80"></line>
              <line className="dark:stroke-slate-700" stroke="#e2e8f0" strokeDasharray="4 4" strokeWidth="1" x1="0" x2="400" y1="40" y2="40"></line>
              <path d="M0,120 Q40,100 80,110 T160,80 T240,60 T320,90 T400,50 V150 H0 Z" fill="url(#chartGradient)"></path>
              <path d="M0,120 Q40,100 80,110 T160,80 T240,60 T320,90 T400,50" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="3"></path>
            </svg>
            <div className="flex justify-between w-full mt-2 text-xs text-slate-400 font-medium">
              <span>Week 1</span>
              <span>Week 2</span>
              <span>Week 3</span>
              <span>Week 4</span>
            </div>
          </div>
        </Card>
      </div>

      <Card padding="none" className="overflow-hidden">
        <div className="border-b border-slate-200 dark:border-border-dark px-6 py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Recent Transactions</h3>
            <p className="text-sm text-slate-500 dark:text-slate-400">Financial log of fines and fees collected</p>
          </div>
          <select className="h-10 px-4 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-border-dark text-sm text-slate-700 dark:text-white">
            <option>All Transactions</option>
            <option>Paid Fines</option>
            <option>Pending</option>
            <option>Refunded</option>
          </select>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-500 dark:text-slate-400">
            <thead className="bg-slate-50 dark:bg-slate-800/50 text-xs uppercase text-slate-700 dark:text-slate-300">
              <tr>
                <th className="px-6 py-4 font-semibold">Transaction ID</th>
                <th className="px-6 py-4 font-semibold">Member</th>
                <th className="px-6 py-4 font-semibold">Date</th>
                <th className="px-6 py-4 font-semibold">Type</th>
                <th className="px-6 py-4 font-semibold">Status</th>
                <th className="px-6 py-4 font-semibold text-right">Amount</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-border-dark">
              {transactions.map((tx) => (
                <tr key={tx.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                  <td className="whitespace-nowrap px-6 py-4 font-medium text-slate-900 dark:text-white">{tx.id}</td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className={`h-8 w-8 rounded-full flex items-center justify-center font-bold text-xs ${getAvatarColor(tx.color)}`}>
                        {tx.initials}
                      </div>
                      <div>
                        <div className="font-medium text-slate-900 dark:text-white">{tx.member}</div>
                        <div className="text-xs">ID: {tx.memberId}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">{tx.date} <span className="text-xs text-slate-400 ml-1">{tx.time}</span></td>
                  <td className="px-6 py-4">{tx.type}</td>
                  <td className="px-6 py-4">{getStatusBadge(tx.status)}</td>
                  <td className="whitespace-nowrap px-6 py-4 text-right font-medium text-slate-900 dark:text-white">${tx.amount.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
