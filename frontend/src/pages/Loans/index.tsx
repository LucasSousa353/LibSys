import { useState } from 'react';
import { Plus, Filter, MoreVertical, QrCode, AlertTriangle, Check, User } from 'lucide-react';
import { Button, Input, Card, Badge, Avatar, Modal } from '../../components/ui';
import type { Loan, Book, User as UserType } from '../../types';

const sampleLoans: (Loan & { book: Book; user: UserType })[] = [
  {
    id: 1,
    user_id: 1,
    book_id: 1,
    loan_date: '2023-10-23',
    due_date: '2023-10-24',
    status: 'overdue',
    fine_amount: 2.00,
    book: { id: 1, title: 'The Great Gatsby', author: 'F. Scott Fitzgerald', isbn: '978-0743273565', total_copies: 12 },
    user: { id: 1, name: 'Alice Martin', email: 'alice@example.com' },
  },
  {
    id: 2,
    user_id: 2,
    book_id: 2,
    loan_date: '2023-10-20',
    due_date: '2023-10-22',
    status: 'overdue',
    fine_amount: 6.00,
    book: { id: 2, title: 'Sapiens', author: 'Yuval Noah Harari', isbn: '978-0062316097', total_copies: 5 },
    user: { id: 2, name: 'Diana Prince', email: 'diana@mail.com' },
  },
  {
    id: 3,
    user_id: 3,
    book_id: 3,
    loan_date: '2023-10-20',
    due_date: '2023-10-26',
    status: 'active',
    book: { id: 3, title: '1984', author: 'George Orwell', isbn: '978-0451524935', total_copies: 8 },
    user: { id: 3, name: 'Bob Smith', email: 'bob@libsys.net' },
  },
  {
    id: 4,
    user_id: 4,
    book_id: 4,
    loan_date: '2023-10-18',
    due_date: '2023-10-30',
    status: 'active',
    book: { id: 4, title: 'Clean Code', author: 'Robert C. Martin', isbn: '978-0132350884', total_copies: 3 },
    user: { id: 4, name: 'Charlie Davis', email: 'charlie@test.com' },
  },
];

const availableUsers = [
  { id: 1, name: 'Alice Martin', email: 'alice@example.com' },
  { id: 2, name: 'Bob Smith', email: 'bob@libsys.net' },
  { id: 3, name: 'Charlie Davis', email: 'charlie@test.com' },
];

const availableBooks = [
  { id: 1, title: 'The Great Gatsby', author: 'F. Scott Fitzgerald' },
  { id: 2, title: 'Sapiens', author: 'Yuval Noah Harari' },
  { id: 3, title: '1984', author: 'George Orwell' },
];

export default function LoansPage() {
  const [loans, setLoans] = useState(sampleLoans);
  const [activeFilter, setActiveFilter] = useState<'all' | 'due_soon' | 'overdue' | 'returned'>('all');
  const [showNewLoanModal, setShowNewLoanModal] = useState(false);
  const [showReturnModal, setShowReturnModal] = useState(false);
  const [selectedLoan, setSelectedLoan] = useState<typeof sampleLoans[0] | null>(null);
  const [bookIdSearch, setBookIdSearch] = useState('');
  const [newLoanData, setNewLoanData] = useState({ user_id: 0, book_id: 0 });

  const overdueCount = loans.filter(l => l.status === 'overdue').length;
  const dueSoonCount = loans.filter(l => l.status === 'active').length;

  const filteredLoans = loans.filter(loan => {
    if (activeFilter === 'overdue') return loan.status === 'overdue';
    if (activeFilter === 'due_soon') return loan.status === 'active';
    if (activeFilter === 'returned') return loan.status === 'returned';
    return true;
  });

  const handleReturn = () => {
    if (selectedLoan) {
      setLoans(loans.map(loan =>
        loan.id === selectedLoan.id
          ? { ...loan, status: 'returned' as const, return_date: new Date().toISOString() }
          : loan
      ));
      setShowReturnModal(false);
      setSelectedLoan(null);
    }
  };

  const handleNewLoan = (e: React.FormEvent) => {
    e.preventDefault();
    setShowNewLoanModal(false);
    setNewLoanData({ user_id: 0, book_id: 0 });
  };

  const getDueDateDisplay = (loan: typeof sampleLoans[0]) => {
    const dueDate = new Date(loan.due_date);
    const today = new Date();
    const diffDays = Math.ceil((dueDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));

    if (diffDays < 0) {
      return {
        text: Math.abs(diffDays) === 1 ? 'Yesterday' : `${Math.abs(diffDays)} days ago`,
        color: 'text-red-600 dark:text-red-400',
      };
    } else if (diffDays === 0) {
      return { text: 'Today', color: 'text-amber-600 dark:text-amber-400' };
    } else if (diffDays === 1) {
      return { text: 'Tomorrow', color: 'text-slate-600 dark:text-slate-300' };
    } else {
      return { text: `In ${diffDays} days`, color: 'text-slate-600 dark:text-slate-300' };
    }
  };

  return (
    <div className="flex h-full gap-6">
      <div className="flex-1 flex flex-col min-w-0">
        <div className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Active Loans</h1>
              <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">Monitor due dates and overdue items.</p>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" icon={<Filter size={18} />}>
                Filter
              </Button>
              <Button icon={<Plus size={18} />} onClick={() => setShowNewLoanModal(true)}>
                New Loan
              </Button>
            </div>
          </div>

          <div className="flex items-center gap-4 overflow-x-auto pb-2">
            <button
              onClick={() => setActiveFilter('all')}
              className={`px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${activeFilter === 'all'
                  ? 'bg-white dark:bg-surface-dark border border-slate-200 dark:border-border-dark text-slate-900 dark:text-white shadow-sm'
                  : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                }`}
            >
              All Loans
            </button>
            <button
              onClick={() => setActiveFilter('due_soon')}
              className={`px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${activeFilter === 'due_soon'
                  ? 'bg-white dark:bg-surface-dark border border-slate-200 dark:border-border-dark text-slate-900 dark:text-white shadow-sm'
                  : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                }`}
            >
              Due Soon ({dueSoonCount})
            </button>
            <button
              onClick={() => setActiveFilter('overdue')}
              className={`px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap flex items-center gap-1 transition-colors ${activeFilter === 'overdue'
                  ? 'bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400'
                  : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                }`}
            >
              <span className="w-2 h-2 rounded-full bg-red-500"></span>
              Overdue ({overdueCount})
            </button>
          </div>
        </div>

        <Card padding="none" className="flex-1 overflow-hidden">
          <div className="overflow-x-auto">
            <div className="grid grid-cols-12 gap-4 px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider border-b border-slate-200 dark:border-border-dark">
              <div className="col-span-4">Book Details</div>
              <div className="col-span-3">Member</div>
              <div className="col-span-2">Due Date</div>
              <div className="col-span-2">Status</div>
              <div className="col-span-1 text-right">Action</div>
            </div>

            <div className="divide-y divide-slate-200 dark:divide-border-dark">
              {filteredLoans.map((loan) => {
                const dueDisplay = getDueDateDisplay(loan);
                return (
                  <div
                    key={loan.id}
                    className="group grid grid-cols-12 gap-4 items-center px-4 py-4 hover:bg-slate-50 dark:hover:bg-surface-dark transition-colors cursor-pointer"
                    onClick={() => {
                      setSelectedLoan(loan);
                      if (loan.status !== 'returned') setShowReturnModal(true);
                    }}
                  >
                    <div className="col-span-4 flex items-center gap-3">
                      <div className="w-10 h-14 bg-slate-200 dark:bg-slate-700 rounded shadow-sm flex items-center justify-center shrink-0">
                        <span className="text-xs">📖</span>
                      </div>
                      <div>
                        <h4 className="text-sm font-semibold text-slate-900 dark:text-white">{loan.book.title}</h4>
                        <p className="text-xs text-slate-500 dark:text-slate-400">ID: #BK-{loan.book_id.toString().padStart(4, '0')}</p>
                      </div>
                    </div>
                    <div className="col-span-3">
                      <div className="flex items-center gap-2">
                        <Avatar name={loan.user.name} size="sm" />
                        <span className="text-sm font-medium text-slate-900 dark:text-white">
                          {loan.user.name.split(' ')[0]} {loan.user.name.split(' ')[1]?.[0]}.
                        </span>
                      </div>
                    </div>
                    <div className="col-span-2">
                      <span className={`text-sm font-medium ${dueDisplay.color}`}>{dueDisplay.text}</span>
                      <div className="text-xs text-slate-500 dark:text-slate-400">
                        {new Date(loan.due_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                      </div>
                    </div>
                    <div className="col-span-2">
                      <Badge variant={loan.status === 'overdue' ? 'danger' : loan.status === 'returned' ? 'default' : 'success'}>
                        {loan.status.charAt(0).toUpperCase() + loan.status.slice(1)}
                      </Badge>
                      {loan.fine_amount && loan.fine_amount > 0 && (
                        <div className="text-xs text-red-600 dark:text-red-400 font-semibold mt-1">
                          Fine: R$ {loan.fine_amount.toFixed(2)}
                        </div>
                      )}
                    </div>
                    <div className="col-span-1 flex justify-end">
                      <button className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-primary transition-colors">
                        <MoreVertical size={18} />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </Card>
      </div>

      <aside className="w-[380px] shrink-0 hidden xl:flex flex-col">
        <Card className="flex-1 flex flex-col">
          <div className="border-b border-slate-200 dark:border-border-dark pb-4 mb-4">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <QrCode size={20} className="text-primary" />
              Process Return
            </h3>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Scan a book or enter ID to begin return.</p>
          </div>

          <div className="space-y-4 mb-6">
            <label className="block text-sm font-medium text-slate-900 dark:text-white">Book ID / Barcode</label>
            <div className="flex gap-2">
              <Input
                icon={<QrCode size={18} />}
                placeholder="Scan or type ID..."
                value={bookIdSearch}
                onChange={(e) => setBookIdSearch(e.target.value)}
              />
              <Button>Find</Button>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-200 dark:border-border-dark">
            <h4 className="text-base font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
              <User size={18} className="text-slate-400" />
              Member Quick Check
            </h4>
            <Input
              showSearchIcon
              placeholder="Enter Member ID or Name..."
              className="mb-4"
            />

            <div className="bg-slate-50 dark:bg-background-dark rounded-xl p-4 border border-slate-200 dark:border-border-dark">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <Avatar name="John Smith" />
                  <div>
                    <div className="text-sm font-bold text-slate-900 dark:text-white">John Smith</div>
                    <div className="text-xs text-slate-500 dark:text-slate-400">ID: MEM-0042</div>
                  </div>
                </div>
                <Badge variant="success" size="sm">Good Standing</Badge>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500 dark:text-slate-400">Active Loans</span>
                  <span className="font-medium text-slate-900 dark:text-white">2 / 3</span>
                </div>
                <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
                  <div className="bg-primary h-2 rounded-full" style={{ width: '66%' }}></div>
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400 pt-1">
                  Can borrow <strong className="text-slate-900 dark:text-white">1</strong> more item.
                </p>
              </div>
            </div>
          </div>
        </Card>
      </aside>

      <Modal
        isOpen={showNewLoanModal}
        onClose={() => setShowNewLoanModal(false)}
        title="Create New Loan"
        size="md"
      >
        <form onSubmit={handleNewLoan} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">Select User</label>
            <select
              value={newLoanData.user_id}
              onChange={(e) => setNewLoanData({ ...newLoanData, user_id: parseInt(e.target.value) })}
              className="w-full h-11 px-4 rounded-lg bg-slate-50 dark:bg-[#192633] border border-slate-300 dark:border-[#324d67] text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary"
              required
            >
              <option value="">Select a user...</option>
              {availableUsers.map(user => (
                <option key={user.id} value={user.id}>{user.name} ({user.email})</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">Select Book</label>
            <select
              value={newLoanData.book_id}
              onChange={(e) => setNewLoanData({ ...newLoanData, book_id: parseInt(e.target.value) })}
              className="w-full h-11 px-4 rounded-lg bg-slate-50 dark:bg-[#192633] border border-slate-300 dark:border-[#324d67] text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary"
              required
            >
              <option value="">Select a book...</option>
              {availableBooks.map(book => (
                <option key={book.id} value={book.id}>{book.title} - {book.author}</option>
              ))}
            </select>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-200 dark:border-border-dark">
            <Button type="button" variant="outline" onClick={() => setShowNewLoanModal(false)}>
              Cancel
            </Button>
            <Button type="submit">
              Create Loan
            </Button>
          </div>
        </form>
      </Modal>

      <Modal
        isOpen={showReturnModal}
        onClose={() => setShowReturnModal(false)}
        title="Process Return"
        size="md"
      >
        {selectedLoan && (
          <div className="space-y-6">
            <div className={`rounded-xl border p-4 ${selectedLoan.status === 'overdue' ? 'border-red-500/30 bg-red-500/5' : 'border-slate-200 dark:border-border-dark'}`}>
              {selectedLoan.status === 'overdue' && (
                <div className="flex items-center gap-2 text-red-600 dark:text-red-400 mb-3">
                  <AlertTriangle size={18} />
                  <span className="font-medium">This book is overdue</span>
                </div>
              )}
              <div className="flex gap-3 mb-4">
                <div className="w-16 h-24 bg-slate-200 dark:bg-slate-700 rounded-md shrink-0 flex items-center justify-center">
                  <span>📖</span>
                </div>
                <div>
                  <h4 className="text-base font-bold text-slate-900 dark:text-white">{selectedLoan.book.title}</h4>
                  <p className="text-sm text-slate-500 dark:text-slate-400 mb-1">#{selectedLoan.book.isbn}</p>
                  <p className="text-sm text-slate-500 dark:text-slate-400">Borrowed by: {selectedLoan.user.name}</p>
                </div>
              </div>

              {selectedLoan.fine_amount && selectedLoan.fine_amount > 0 && (
                <div className="bg-white dark:bg-surface-dark rounded-lg p-3 border border-slate-200 dark:border-border-dark mb-4">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-xs font-medium text-slate-500">Daily Fine Rate</span>
                    <span className="text-xs font-medium text-slate-900 dark:text-white">R$ 2,00</span>
                  </div>
                  <div className="flex justify-between items-center pt-2 border-t border-slate-200 dark:border-border-dark">
                    <span className="text-sm font-bold text-slate-900 dark:text-white">Total Fine</span>
                    <span className="text-lg font-bold text-red-600 dark:text-red-400">R$ {selectedLoan.fine_amount.toFixed(2)}</span>
                  </div>
                </div>
              )}
            </div>

            <div className="flex gap-2">
              <Button variant="outline" className="flex-1" onClick={() => setShowReturnModal(false)}>
                Cancel
              </Button>
              <Button className="flex-1" onClick={handleReturn} icon={<Check size={18} />}>
                Confirm Return
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
