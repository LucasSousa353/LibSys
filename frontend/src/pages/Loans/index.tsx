import { useCallback, useEffect, useMemo, useState } from 'react';
import { Plus, Filter, MoreVertical, ChevronsLeft, ChevronsRight, ChevronLeft, ChevronRight } from 'lucide-react';
import { Button, Input, Card, Badge, Avatar, Modal } from '../../components/ui';
import type { Loan, Book, User as UserType } from '../../types';
import { booksApi, loansApi, usersApi } from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';

type LoanWithDetails = Loan & { book?: Book; user?: UserType };

type LoanFilter = 'all' | 'active' | 'overdue' | 'returned';

type SelectableUser = UserType & { selectable: boolean };

const PAGE_WINDOW = 4;
const SEARCH_DEBOUNCE_MS = 350;

const getTokenEmail = () => {
    const token = localStorage.getItem('access_token');
    if (!token) return null;
    try {
        const payload = token.split('.')[1];
        const decoded = JSON.parse(atob(payload));
        return typeof decoded?.sub === 'string' ? decoded.sub : null;
    } catch {
        return null;
    }
};

const getDueDateDisplay = (expectedReturnDate: string) => {
    const dueDate = new Date(expectedReturnDate);
    const today = new Date();
    const diffDays = Math.ceil((dueDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));

    if (diffDays < 0) {
        return {
            text: Math.abs(diffDays) === 1 ? 'Yesterday' : `${Math.abs(diffDays)} days ago`,
            color: 'text-red-600 dark:text-red-400',
        };
    }
    if (diffDays === 0) {
        return { text: 'Today', color: 'text-amber-600 dark:text-amber-400' };
    }
    if (diffDays === 1) {
        return { text: 'Tomorrow', color: 'text-slate-600 dark:text-slate-300' };
    }
    return { text: `In ${diffDays} days`, color: 'text-slate-600 dark:text-slate-300' };
};

export default function LoansPage() {
    const { role, user } = useAuth();
    const canManageLoans = role === 'admin' || role === 'librarian';
    const canCreateLoan = role === 'admin' || role === 'librarian';
    const canExportLoans = role === 'admin' || role === 'librarian';
    const [loans, setLoans] = useState<LoanWithDetails[]>([]);
    const [activeFilter, setActiveFilter] = useState<LoanFilter>('all');
    const [searchQuery, setSearchQuery] = useState('');
    const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('');
    const [isLoadingList, setIsLoadingList] = useState(true);
    const [listError, setListError] = useState<string | null>(null);
    const [page, setPage] = useState(0);
    const [pageSize, setPageSize] = useState(10);
    const [lastPage, setLastPage] = useState<number | null>(null);
    const [statusCounts, setStatusCounts] = useState({ active: 0, overdue: 0, returned: 0 });

    const [showNewLoanModal, setShowNewLoanModal] = useState(false);
    const [newLoanLoading, setNewLoanLoading] = useState(false);
    const [newLoanError, setNewLoanError] = useState<string | null>(null);
    const [openActionId, setOpenActionId] = useState<number | null>(null);
    const [returningLoanId, setReturningLoanId] = useState<number | null>(null);
    const [returnError, setReturnError] = useState<string | null>(null);
    const [confirmReturnLoan, setConfirmReturnLoan] = useState<LoanWithDetails | null>(null);
    const [returnSuccess, setReturnSuccess] = useState<string | null>(null);
    const [confirmExtendLoan, setConfirmExtendLoan] = useState<LoanWithDetails | null>(null);
    const [extendingLoanId, setExtendingLoanId] = useState<number | null>(null);
    const [extendError, setExtendError] = useState<string | null>(null);
    const [extendSuccess, setExtendSuccess] = useState<string | null>(null);

    const [availableUsers, setAvailableUsers] = useState<UserType[]>([]);
    const [availableBooks, setAvailableBooks] = useState<Book[]>([]);
    const [userSearch, setUserSearch] = useState('');
    const [debouncedUserSearch, setDebouncedUserSearch] = useState('');
    const [bookSearch, setBookSearch] = useState('');
    const [debouncedBookSearch, setDebouncedBookSearch] = useState('');
    const [selectedUser, setSelectedUser] = useState<UserType | null>(null);
    const [selectedBook, setSelectedBook] = useState<Book | null>(null);
    const [usersLoading, setUsersLoading] = useState(false);
    const [booksLoading, setBooksLoading] = useState(false);

    const tokenEmail = useMemo(() => getTokenEmail(), []);

    const fetchLoans = useCallback(async (targetPage: number = page) => {
        try {
            setIsLoadingList(true);
            setListError(null);
            const statusParam = activeFilter === 'all' ? undefined : activeFilter;
            const data = await loansApi.list({
                status: statusParam,
                skip: targetPage * pageSize,
                limit: pageSize,
            });
            const list = Array.isArray(data) ? data : [];

            if (list.length < pageSize) {
                setLastPage(targetPage);
            }

            const bookIds = Array.from(new Set(list.map((loan: Loan) => loan.book_id)));
            const userIds = Array.from(new Set(list.map((loan: Loan) => loan.user_id)));

            const bookResults = await Promise.all(
                bookIds.map((id) => booksApi.getById(id).catch(() => null))
            );

            let userResults: UserType[] = [];
            if (role === 'admin' || role === 'librarian') {
                userResults = await usersApi.lookupByIds(userIds);
            } else if (user && userIds.includes(user.id)) {
                userResults = [user];
            }

            const bookMap = new Map<number, Book>();
            bookResults.filter(Boolean).forEach((book: Book) => {
                bookMap.set(book.id, book);
            });

            const userMap = new Map<number, UserType>();
            (Array.isArray(userResults) ? userResults : []).forEach((user: UserType) => {
                userMap.set(user.id, user);
            });

            const enriched = list.map((loan: Loan) => ({
                ...loan,
                book: bookMap.get(loan.book_id),
                user: userMap.get(loan.user_id),
            }));

            setLoans(enriched);

            if (!statusParam) {
                const active = list.filter((loan: Loan) => loan.status === 'active').length;
                const overdue = list.filter((loan: Loan) => loan.status === 'overdue').length;
                const returned = list.filter((loan: Loan) => loan.status === 'returned').length;
                setStatusCounts({ active, overdue, returned });
            }
        } catch (error) {
            console.error('Error loading loans:', error);
            setListError('Unable to load loans. Please try again.');
        } finally {
            setIsLoadingList(false);
        }
    }, [activeFilter, page, pageSize]);

    useEffect(() => {
        fetchLoans();
    }, [fetchLoans]);

    useEffect(() => {
        const handle = window.setTimeout(() => {
            setDebouncedSearchQuery(searchQuery);
        }, SEARCH_DEBOUNCE_MS);
        return () => window.clearTimeout(handle);
    }, [searchQuery]);

    useEffect(() => {
        const handle = window.setTimeout(() => {
            setDebouncedUserSearch(userSearch);
        }, SEARCH_DEBOUNCE_MS);
        return () => window.clearTimeout(handle);
    }, [userSearch]);

    useEffect(() => {
        const handle = window.setTimeout(() => {
            setDebouncedBookSearch(bookSearch);
        }, SEARCH_DEBOUNCE_MS);
        return () => window.clearTimeout(handle);
    }, [bookSearch]);

    useEffect(() => {
        setLastPage(null);
    }, [activeFilter, pageSize]);

    useEffect(() => {
        const handleClick = (event: MouseEvent) => {
            const target = event.target as HTMLElement | null;
            if (!target?.closest('[data-loan-actions="menu"]')) {
                setOpenActionId(null);
            }
        };
        document.addEventListener('click', handleClick);
        return () => document.removeEventListener('click', handleClick);
    }, []);

    const filteredLoans = useMemo(() => {
        const query = debouncedSearchQuery.trim().toLowerCase();
        if (!query) return loans;

        return loans.filter((loan) => {
            const book = loan.book;
            const user = loan.user;
            return (
                book?.title?.toLowerCase().includes(query) ||
                book?.author?.toLowerCase().includes(query) ||
                book?.isbn?.toLowerCase().includes(query) ||
                user?.name?.toLowerCase().includes(query) ||
                user?.email?.toLowerCase().includes(query) ||
                `#bk-${loan.book_id}`.includes(query) ||
                `id-${loan.user_id}`.includes(query)
            );
        });
    }, [debouncedSearchQuery, loans]);

    const overdueCount = statusCounts.overdue;
    const activeCount = statusCounts.active;
    const returnedCount = statusCounts.returned;

    const canGoBack = page > 0;
    const canGoNext = lastPage !== null ? page < lastPage : loans.length === pageSize;
    const startItem = filteredLoans.length ? page * pageSize + 1 : 0;
    const endItem = page * pageSize + filteredLoans.length;

    const pageNumbers = useMemo(() => {
        if (lastPage === null) {
            return [page];
        }

        let start = Math.max(0, page - 1);
        let end = start + PAGE_WINDOW - 1;

        end = Math.min(end, lastPage);
        start = Math.max(0, end - PAGE_WINDOW + 1);

        return Array.from({ length: end - start + 1 }, (_, index) => start + index);
    }, [lastPage, page]);

    const loadUsers = useCallback(async () => {
        try {
            setUsersLoading(true);
            const trimmed = debouncedUserSearch.trim();
            if (!trimmed) {
                setAvailableUsers([]);
                return;
            }
            const data = await usersApi.lookup(trimmed, 0, 50);
            const list = Array.isArray(data) ? data : [];
            setAvailableUsers(list);
        } catch (error) {
            console.error('Error loading users:', error);
        } finally {
            setUsersLoading(false);
        }
    }, [debouncedUserSearch]);

    const loadBooks = useCallback(async () => {
        try {
            setBooksLoading(true);
            const trimmed = debouncedBookSearch.trim();
            if (!trimmed) {
                setAvailableBooks([]);
                return;
            }
            const [titleMatches, authorMatches] = await Promise.all([
                booksApi.list({
                    title: trimmed || undefined,
                    skip: 0,
                    limit: 20,
                }),
                booksApi.list({
                    author: trimmed || undefined,
                    skip: 0,
                    limit: 20,
                }),
            ]);
            const combined = [
                ...(Array.isArray(titleMatches) ? titleMatches : []),
                ...(Array.isArray(authorMatches) ? authorMatches : []),
            ];
            const merged = Array.from(new Map(combined.map((book: Book) => [book.id, book])).values());
            setAvailableBooks(merged.filter((book: Book) => (book.available_copies ?? book.total_copies) > 0));
        } catch (error) {
            console.error('Error loading books:', error);
        } finally {
            setBooksLoading(false);
        }
    }, [debouncedBookSearch]);

    useEffect(() => {
        if (!showNewLoanModal) return;
        loadUsers();
        loadBooks();
    }, [loadBooks, loadUsers, showNewLoanModal]);

    useEffect(() => {
        if (!showNewLoanModal) return;
        loadUsers();
    }, [debouncedUserSearch, loadUsers, showNewLoanModal]);

    useEffect(() => {
        if (!showNewLoanModal) return;
        loadBooks();
    }, [debouncedBookSearch, loadBooks, showNewLoanModal]);

    const selectableUsers = useMemo<SelectableUser[]>(() => {
        const query = debouncedUserSearch.trim().toLowerCase();
        if (!query) {
            return [];
        }

        const list = availableUsers.filter((user) => user.name.toLowerCase().includes(query) || user.email.toLowerCase().includes(query));

        return list.map((user) => ({
            ...user,
            selectable: role === 'user' ? user.email === tokenEmail : true,
        }));
    }, [availableUsers, debouncedUserSearch, role, tokenEmail]);

    const handleNewLoan = async (e: React.FormEvent) => {
        e.preventDefault();
        setNewLoanError(null);

        if (!selectedUser || !selectedBook) {
            setNewLoanError('Please select a member and a book.');
            return;
        }

        if (role === 'user' && tokenEmail && selectedUser.email !== tokenEmail) {
            setNewLoanError('You can only create loans for your own account.');
            return;
        }

        try {
            setNewLoanLoading(true);
            await loansApi.create({ user_id: selectedUser.id, book_id: selectedBook.id });
            setShowNewLoanModal(false);
            setSelectedBook(null);
            setSelectedUser(null);
            setUserSearch('');
            setDebouncedUserSearch('');
            setBookSearch('');
            setDebouncedBookSearch('');
            setPage(0);
            await fetchLoans(0);
        } catch (error) {
            console.error('Error creating loan:', error);
            const detail = error?.response?.data?.detail;
            if (typeof detail === 'string' && detail.trim()) {
                setNewLoanError(detail);
            } else {
                setNewLoanError('Unable to create loan. Please try again.');
            }
        } finally {
            setNewLoanLoading(false);
        }
    };

    const handleExportCsv = async () => {
        const today = new Date().toISOString().split('T')[0];
        const statusParam = activeFilter === 'all' ? undefined : activeFilter;
        try {
            const blob = await loansApi.exportCsv({ status: statusParam });
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `loans_${activeFilter}_${today}.csv`);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
        } catch (error) {
            console.error('Error exporting loans:', error);
        }
    };

    const handleExportPdf = async () => {
        const today = new Date().toISOString().split('T')[0];
        try {
            const blob = await loansApi.exportPdf();
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `loans_${activeFilter}_${today}.pdf`);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
        } catch (error) {
            console.error('Error exporting loans:', error);
        }
    };

    const handleReturnLoan = async (loanId: number) => {
        try {
            setReturnError(null);
            setReturningLoanId(loanId);
            await loansApi.return(loanId);
            setOpenActionId(null);
            setConfirmReturnLoan(null);
            setReturnSuccess('Loan returned successfully.');
            await fetchLoans(0);
        } catch (error) {
            console.error('Error returning loan:', error);
            setReturnError('Unable to return loan. Please try again.');
        } finally {
            setReturningLoanId(null);
        }
    };

    const handleExtendLoan = async (loanId: number) => {
        try {
            setExtendError(null);
            setExtendingLoanId(loanId);
            await loansApi.extend(loanId);
            setOpenActionId(null);
            setConfirmExtendLoan(null);
            setExtendSuccess('Loan renewed successfully.');
            await fetchLoans(0);
        } catch (error) {
            console.error('Error extending loan:', error);
            setExtendError('Unable to renew loan. Please try again.');
        } finally {
            setExtendingLoanId(null);
        }
    };

    useEffect(() => {
        if (!returnSuccess) return;
        const timeout = window.setTimeout(() => {
            setReturnSuccess(null);
        }, 3000);
        return () => window.clearTimeout(timeout);
    }, [returnSuccess]);

    useEffect(() => {
        if (!extendSuccess) return;
        const timeout = window.setTimeout(() => {
            setExtendSuccess(null);
        }, 3000);
        return () => window.clearTimeout(timeout);
    }, [extendSuccess]);

    return (
        <div className="flex h-full min-h-0 gap-6">
            {returnSuccess && (
                <div className="fixed right-6 top-6 z-50 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700 shadow-lg">
                    {returnSuccess}
                </div>
            )}
            {extendSuccess && (
                <div className="fixed right-6 top-20 z-50 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700 shadow-lg">
                    {extendSuccess}
                </div>
            )}
            <div className="flex-1 flex flex-col min-w-0 min-h-0">
                <div className="mb-6">
                    <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-4">
                        <div>
                            <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Active Loans</h1>
                            <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">Monitor due dates and overdue items.</p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                            {canExportLoans && (
                                <>
                                    <Button variant="outline" onClick={handleExportCsv}>
                                        Export CSV
                                    </Button>
                                    <Button variant="outline" onClick={handleExportPdf}>
                                        Export PDF
                                    </Button>
                                </>
                            )}
                            <Button variant="outline" icon={<Filter size={18} />} disabled>
                                Filter
                            </Button>
                            {canCreateLoan && (
                                <Button icon={<Plus size={18} />} onClick={() => setShowNewLoanModal(true)}>
                                    New Loan
                                </Button>
                            )}
                        </div>
                    </div>

                    {returnError && (
                        <div className="mt-3 rounded-lg border border-red-200 dark:border-red-900/30 bg-red-50 dark:bg-red-900/20 px-4 py-3 text-sm text-red-700 dark:text-red-400">
                            {returnError}
                        </div>
                    )}
                    {extendError && (
                        <div className="mt-3 rounded-lg border border-red-200 dark:border-red-900/30 bg-red-50 dark:bg-red-900/20 px-4 py-3 text-sm text-red-700 dark:text-red-400">
                            {extendError}
                        </div>
                    )}

                    <div className="flex flex-wrap items-center gap-3 overflow-x-auto pb-2">
                        <button
                            onClick={() => {
                                setPage(0);
                                setActiveFilter('all');
                            }}
                            className={`px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${activeFilter === 'all'
                                ? 'bg-white dark:bg-surface-dark border border-slate-200 dark:border-border-dark text-slate-900 dark:text-white shadow-sm'
                                : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                                }`}
                        >
                            All Loans
                        </button>
                        <button
                            onClick={() => {
                                setPage(0);
                                setActiveFilter('active');
                            }}
                            className={`px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${activeFilter === 'active'
                                ? 'bg-white dark:bg-surface-dark border border-slate-200 dark:border-border-dark text-slate-900 dark:text-white shadow-sm'
                                : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                                }`}
                        >
                            Active ({activeCount})
                        </button>
                        <button
                            onClick={() => {
                                setPage(0);
                                setActiveFilter('overdue');
                            }}
                            className={`px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap flex items-center gap-1 transition-colors ${activeFilter === 'overdue'
                                ? 'bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400'
                                : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                                }`}
                        >
                            <span className="w-2 h-2 rounded-full bg-red-500"></span>
                            Overdue ({overdueCount})
                        </button>
                        <button
                            onClick={() => {
                                setPage(0);
                                setActiveFilter('returned');
                            }}
                            className={`px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${activeFilter === 'returned'
                                ? 'bg-white dark:bg-surface-dark border border-slate-200 dark:border-border-dark text-slate-900 dark:text-white shadow-sm'
                                : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                                }`}
                        >
                            Returned ({returnedCount})
                        </button>
                    </div>

                    <div className="mt-4 flex flex-col lg:flex-row lg:items-center justify-between gap-3">
                        <div className="lg:w-[360px]">
                            <Input
                                showSearchIcon
                                placeholder="Search by member or book..."
                                value={searchQuery}
                                onChange={(e) => {
                                    setPage(0);
                                    setSearchQuery(e.target.value);
                                }}
                            />
                        </div>
                        <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
                            <span>Show</span>
                            <select
                                className="h-10 rounded-lg border border-slate-200 dark:border-border-dark bg-white dark:bg-slate-800 px-3 text-sm text-slate-700 dark:text-slate-200"
                                value={pageSize}
                                onChange={(e) => {
                                    setPage(0);
                                    setPageSize(parseInt(e.target.value, 10));
                                }}
                            >
                                {[5, 10, 15, 20].map((size) => (
                                    <option key={size} value={size}>
                                        {size}
                                    </option>
                                ))}
                            </select>
                        </div>
                    </div>
                </div>

                <Card padding="none" className="flex-1 overflow-hidden flex flex-col min-h-0">
                    <div className="overflow-x-auto">
                        <div className="grid grid-cols-12 gap-4 px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider border-b border-slate-200 dark:border-border-dark">
                            <div className="col-span-4">Book Details</div>
                            <div className="col-span-3">Member</div>
                            <div className="col-span-2">Due Date</div>
                            <div className="col-span-2">Status</div>
                            <div className="col-span-1 text-right">Action</div>
                        </div>
                    </div>

                    <div className="flex-1 min-h-0 overflow-y-auto">
                        <div className="divide-y divide-slate-200 dark:divide-border-dark">
                            {isLoadingList && (
                                <div className="px-4 py-6 text-center text-sm text-slate-500 dark:text-slate-400">Loading loans...</div>
                            )}
                            {!isLoadingList && listError && (
                                <div className="px-4 py-6 text-center text-sm text-rose-500">{listError}</div>
                            )}
                            {!isLoadingList && !listError && filteredLoans.length === 0 && (
                                <div className="px-4 py-6 text-center text-sm text-slate-500 dark:text-slate-400">No loans found.</div>
                            )}
                            {!isLoadingList && !listError && filteredLoans.map((loan) => {
                                const dueDisplay = getDueDateDisplay(loan.expected_return_date);
                                return (
                                    <div
                                        key={loan.id}
                                        className="group grid grid-cols-12 gap-4 items-center px-4 py-4 hover:bg-slate-50 dark:hover:bg-surface-dark transition-colors"
                                    >
                                        <div className="col-span-4 flex items-center gap-3">
                                            <div className="w-10 h-14 bg-slate-200 dark:bg-slate-700 rounded shadow-sm flex items-center justify-center shrink-0">
                                                <span className="text-xs">📖</span>
                                            </div>
                                            <div>
                                                <h4 className="text-sm font-semibold text-slate-900 dark:text-white">
                                                    {loan.book?.title ?? `Book #${loan.book_id}`}
                                                </h4>
                                                <p className="text-xs text-slate-500 dark:text-slate-400">
                                                    ID: #BK-{loan.book_id.toString().padStart(4, '0')}
                                                </p>
                                            </div>
                                        </div>
                                        <div className="col-span-3">
                                            <div className="flex items-center gap-2">
                                                <Avatar name={loan.user?.name ?? 'Member'} size="sm" />
                                                <span className="text-sm font-medium text-slate-900 dark:text-white">
                                                    {loan.user?.name ?? `User #${loan.user_id}`}
                                                </span>
                                            </div>
                                        </div>
                                        <div className="col-span-2">
                                            <span className={`text-sm font-medium ${dueDisplay.color}`}>{dueDisplay.text}</span>
                                            <div className="text-xs text-slate-500 dark:text-slate-400">
                                                {new Date(loan.expected_return_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                                            </div>
                                        </div>
                                        <div className="col-span-2">
                                            <Badge variant={loan.status === 'overdue' ? 'danger' : loan.status === 'returned' ? 'default' : 'success'}>
                                                {loan.status.charAt(0).toUpperCase() + loan.status.slice(1)}
                                            </Badge>
                                            {loan.fine_amount && loan.fine_amount > 0 && (
                                                <div className="text-xs text-red-600 dark:text-red-400 font-semibold mt-1">
                                                    Fine: R$ {Number(loan.fine_amount).toFixed(2)}
                                                </div>
                                            )}
                                        </div>
                                        <div className="col-span-1 flex justify-end" data-loan-actions="menu">
                                            {canManageLoans ? (
                                                <div className="relative">
                                                    <button
                                                        className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-primary transition-colors"
                                                        title="Actions"
                                                        onClick={(event) => {
                                                            event.stopPropagation();
                                                            setOpenActionId((current) => (current === loan.id ? null : loan.id));
                                                        }}
                                                    >
                                                        <MoreVertical size={18} />
                                                    </button>
                                                    {openActionId === loan.id && (
                                                        <div className="absolute right-0 mt-2 w-44 rounded-lg border border-slate-200 dark:border-border-dark bg-white dark:bg-slate-900 shadow-lg z-10">
                                                            <button
                                                                className="w-full px-3 py-2 text-left text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50"
                                                                onClick={() => setConfirmExtendLoan(loan)}
                                                                disabled={loan.status !== 'active' || extendingLoanId === loan.id}
                                                            >
                                                                {extendingLoanId === loan.id ? 'Renewing...' : 'Renew loan'}
                                                            </button>
                                                            <button
                                                                className="w-full px-3 py-2 text-left text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50"
                                                                onClick={() => setConfirmReturnLoan(loan)}
                                                                disabled={loan.status === 'returned' || returningLoanId === loan.id}
                                                            >
                                                                {returningLoanId === loan.id ? 'Returning...' : 'Return loan'}
                                                            </button>
                                                        </div>
                                                    )}
                                                </div>
                                            ) : (
                                                <span className="text-xs text-slate-400">-</span>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 border-t border-slate-200 dark:border-border-dark bg-slate-50 dark:bg-[#192633]">
                        <p className="text-sm text-slate-500 dark:text-slate-400">
                            Showing <span className="font-medium text-slate-900 dark:text-white">{startItem}</span> to{' '}
                            <span className="font-medium text-slate-900 dark:text-white">{endItem}</span>
                        </p>
                        <div className="flex items-center gap-2">
                            <button
                                className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 dark:border-border-dark bg-white dark:bg-slate-800 text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50"
                                onClick={() => setPage(0)}
                                disabled={!canGoBack || isLoadingList}
                                title="First page"
                            >
                                <ChevronsLeft size={20} />
                            </button>
                            <button
                                className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 dark:border-border-dark bg-white dark:bg-slate-800 text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50"
                                onClick={() => setPage((prev) => Math.max(prev - 1, 0))}
                                disabled={!canGoBack || isLoadingList}
                                title="Previous page"
                            >
                                <ChevronLeft size={20} />
                            </button>
                            {pageNumbers.map((pageNumber) => (
                                <button
                                    key={pageNumber}
                                    className={`inline-flex h-8 min-w-[32px] items-center justify-center rounded-lg border px-2 text-sm font-medium ${pageNumber === page
                                        ? 'border-primary bg-primary text-white'
                                        : 'border-slate-200 dark:border-border-dark bg-white dark:bg-slate-800 text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-700'
                                        }`}
                                    onClick={() => setPage(pageNumber)}
                                    disabled={isLoadingList}
                                >
                                    {pageNumber + 1}
                                </button>
                            ))}
                            <button
                                className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 dark:border-border-dark bg-white dark:bg-slate-800 text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50"
                                onClick={() => setPage((prev) => prev + 1)}
                                disabled={!canGoNext || isLoadingList}
                                title="Next page"
                            >
                                <ChevronRight size={20} />
                            </button>
                            <button
                                className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 dark:border-border-dark bg-white dark:bg-slate-800 text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50"
                                onClick={() => lastPage !== null && setPage(lastPage)}
                                disabled={lastPage === null || page === lastPage || isLoadingList}
                                title="Last page"
                            >
                                <ChevronsRight size={20} />
                            </button>
                        </div>
                    </div>
                </Card>
            </div>

            <Modal
                isOpen={Boolean(confirmReturnLoan)}
                onClose={() => setConfirmReturnLoan(null)}
                title="Confirm Return"
                size="sm"
            >
                {confirmReturnLoan && (
                    <div className="space-y-4">
                        <p className="text-sm text-slate-600 dark:text-slate-300">
                            Return <span className="font-semibold text-slate-900 dark:text-white">{confirmReturnLoan.book?.title ?? `Book #${confirmReturnLoan.book_id}`}</span> to close the loan?
                        </p>
                        <div className="flex justify-end gap-3">
                            <Button variant="outline" onClick={() => setConfirmReturnLoan(null)}>
                                Cancel
                            </Button>
                            <Button
                                onClick={() => handleReturnLoan(confirmReturnLoan.id)}
                                loading={returningLoanId === confirmReturnLoan.id}
                                disabled={confirmReturnLoan.status === 'returned'}
                            >
                                Confirm Return
                            </Button>
                        </div>
                    </div>
                )}
            </Modal>

            <Modal
                isOpen={Boolean(confirmExtendLoan)}
                onClose={() => setConfirmExtendLoan(null)}
                title="Confirm Renewal"
                size="sm"
            >
                {confirmExtendLoan && (
                    <div className="space-y-4">
                        <p className="text-sm text-slate-600 dark:text-slate-300">
                            Renew <span className="font-semibold text-slate-900 dark:text-white">{confirmExtendLoan.book?.title ?? `Book #${confirmExtendLoan.book_id}`}</span> for another period?
                        </p>
                        <div className="flex justify-end gap-3">
                            <Button variant="outline" onClick={() => setConfirmExtendLoan(null)}>
                                Cancel
                            </Button>
                            <Button
                                onClick={() => handleExtendLoan(confirmExtendLoan.id)}
                                loading={extendingLoanId === confirmExtendLoan.id}
                                disabled={confirmExtendLoan.status !== 'active'}
                            >
                                Confirm Renewal
                            </Button>
                        </div>
                    </div>
                )}
            </Modal>

            <Modal
                isOpen={showNewLoanModal}
                onClose={() => {
                    setShowNewLoanModal(false);
                    setNewLoanError(null);
                    setSelectedUser(null);
                    setSelectedBook(null);
                    setUserSearch('');
                    setDebouncedUserSearch('');
                    setBookSearch('');
                    setDebouncedBookSearch('');
                }}
                title="Create New Loan"
                size="lg"
            >
                <form onSubmit={handleNewLoan} className="space-y-6">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <div className="space-y-3">
                            <div className="flex items-center justify-between">
                                <label className="text-sm font-medium text-slate-700 dark:text-slate-200">Select Member</label>
                                {role === 'user' && (
                                    <span className="text-xs text-slate-400">Only your account is eligible</span>
                                )}
                            </div>
                            <Input
                                showSearchIcon
                                placeholder="Search member by name or email..."
                                value={userSearch}
                                onChange={(e) => setUserSearch(e.target.value)}
                            />
                            <div className="border border-slate-200 dark:border-border-dark rounded-lg max-h-56 overflow-y-auto">
                                {usersLoading && (
                                    <div className="p-3 text-sm text-slate-500 dark:text-slate-400">Loading members...</div>
                                )}
                                {!usersLoading && debouncedUserSearch.trim().length === 0 && (
                                    <div className="p-3 text-sm text-slate-500 dark:text-slate-400">Search by name or email to see results.</div>
                                )}
                                {!usersLoading && debouncedUserSearch.trim().length > 0 && selectableUsers.length === 0 && (
                                    <div className="p-3 text-sm text-slate-500 dark:text-slate-400">No members found.</div>
                                )}
                                {!usersLoading && selectableUsers.map((user) => (
                                    <button
                                        key={user.id}
                                        type="button"
                                        disabled={!user.selectable}
                                        onClick={() => user.selectable && setSelectedUser(user)}
                                        className={`w-full flex items-center gap-3 p-3 text-left border-b border-slate-200 dark:border-border-dark last:border-b-0 transition-colors ${selectedUser?.id === user.id
                                            ? 'bg-primary/10 text-slate-900 dark:text-white'
                                            : 'hover:bg-slate-50 dark:hover:bg-slate-800/40'
                                            } ${user.selectable ? '' : 'opacity-40 cursor-not-allowed'}`}
                                    >
                                        <Avatar name={user.name} size="sm" />
                                        <div>
                                            <div className="text-sm font-medium">{user.name}</div>
                                            <div className="text-xs text-slate-500 dark:text-slate-400">{user.email}</div>
                                        </div>
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div className="space-y-3">
                            <div className="flex items-center justify-between">

                            <label className="text-sm font-medium text-slate-700 dark:text-slate-200">Select Book</label>
                            </div>
                            <Input
                                showSearchIcon
                                placeholder="Search by title or author..."
                                value={bookSearch}
                                onChange={(e) => setBookSearch(e.target.value)}
                            />
                            <div className="border border-slate-200 dark:border-border-dark rounded-lg max-h-56 overflow-y-auto">
                                {booksLoading && (
                                    <div className="p-3 text-sm text-slate-500 dark:text-slate-400">Loading books...</div>
                                )}
                                {!booksLoading && debouncedBookSearch.trim().length === 0 && (
                                    <div className="p-3 text-sm text-slate-500 dark:text-slate-400">Search by title or author to see results.</div>
                                )}
                                {!booksLoading && debouncedBookSearch.trim().length > 0 && availableBooks.length === 0 && (
                                    <div className="p-3 text-sm text-slate-500 dark:text-slate-400">No available books.</div>
                                )}
                                {!booksLoading && availableBooks.map((book) => (
                                    <button
                                        key={book.id}
                                        type="button"
                                        onClick={() => setSelectedBook(book)}
                                        className={`w-full flex items-center justify-between gap-3 p-3 text-left border-b border-slate-200 dark:border-border-dark last:border-b-0 transition-colors ${selectedBook?.id === book.id
                                            ? 'bg-primary/10 text-slate-900 dark:text-white'
                                            : 'hover:bg-slate-50 dark:hover:bg-slate-800/40'
                                            }`}
                                    >
                                        <div>
                                            <div className="text-sm font-medium">{book.title}</div>
                                            <div className="text-xs text-slate-500 dark:text-slate-400">{book.author}</div>
                                        </div>
                                        <span className="text-xs text-slate-500 dark:text-slate-400">
                                            {book.available_copies ?? book.total_copies} available
                                        </span>
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>

                    {newLoanError && (
                        <div className="text-sm text-rose-500">{newLoanError}</div>
                    )}

                    <div className="flex items-center justify-between gap-4 border-t border-slate-200 dark:border-border-dark pt-4">
                        <div className="text-sm text-slate-500 dark:text-slate-400">
                            {selectedUser && selectedBook
                                ? `Loan for ${selectedUser.name} • ${selectedBook.title}`
                                : 'Select a member and a book to continue.'}
                        </div>
                        <div className="flex gap-3">
                            <Button type="button" variant="outline" onClick={() => setShowNewLoanModal(false)}>
                                Cancel
                            </Button>
                            <Button type="submit" loading={newLoanLoading} disabled={!selectedUser || !selectedBook}>
                                Create Loan
                            </Button>
                        </div>
                    </div>
                </form>
            </Modal>
        </div>
    );
}
