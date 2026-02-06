import { useCallback, useEffect, useMemo, useState } from 'react';
import { Plus, Filter, MoreVertical, ChevronsLeft, ChevronsRight, ChevronLeft, ChevronRight } from 'lucide-react';
import { Button, Input, Card, Badge, Avatar, Modal } from '../../components/ui';
import type { Loan, Book, User as UserType } from '../../types';
import { booksApi, loansApi, usersApi } from '../../services/api';

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
    const [loans, setLoans] = useState<LoanWithDetails[]>([]);
    const [activeFilter, setActiveFilter] = useState<LoanFilter>('all');
    const [searchQuery, setSearchQuery] = useState('');
    const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('');
    const [isLoadingList, setIsLoadingList] = useState(true);
    const [listError, setListError] = useState<string | null>(null);
    const [page, setPage] = useState(0);
    const [pageSize, setPageSize] = useState(10);
    const [lastPage, setLastPage] = useState<number | null>(null);

    const [showNewLoanModal, setShowNewLoanModal] = useState(false);
    const [newLoanLoading, setNewLoanLoading] = useState(false);
    const [newLoanError, setNewLoanError] = useState<string | null>(null);

    const [availableUsers, setAvailableUsers] = useState<UserType[]>([]);
    const [availableBooks, setAvailableBooks] = useState<Book[]>([]);
    const [userSearch, setUserSearch] = useState('');
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

            const [bookResults, userResults] = await Promise.all([
                Promise.all(bookIds.map((id) => booksApi.getById(id).catch(() => null))),
                Promise.all(userIds.map((id) => usersApi.getById(id).catch(() => null))),
            ]);

            const bookMap = new Map<number, Book>();
            bookResults.filter(Boolean).forEach((book: Book) => {
                bookMap.set(book.id, book);
            });

            const userMap = new Map<number, UserType>();
            userResults.filter(Boolean).forEach((user: UserType) => {
                userMap.set(user.id, user);
            });

            const enriched = list.map((loan: Loan) => ({
                ...loan,
                book: bookMap.get(loan.book_id),
                user: userMap.get(loan.user_id),
            }));

            setLoans(enriched);
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
            setDebouncedBookSearch(bookSearch);
        }, SEARCH_DEBOUNCE_MS);
        return () => window.clearTimeout(handle);
    }, [bookSearch]);

    useEffect(() => {
        setLastPage(null);
    }, [activeFilter, pageSize]);

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

    const overdueCount = loans.filter((loan) => loan.status === 'overdue').length;
    const activeCount = loans.filter((loan) => loan.status === 'active').length;
    const returnedCount = loans.filter((loan) => loan.status === 'returned').length;

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
            const data = await usersApi.list(0, 50);
            const list = Array.isArray(data) ? data : [];
            setAvailableUsers(list);

            if (tokenEmail) {
                const current = list.find((user) => user.email === tokenEmail);
                if (current) {
                    setSelectedUser(current);
                }
            }
        } catch (error) {
            console.error('Error loading users:', error);
        } finally {
            setUsersLoading(false);
        }
    }, [tokenEmail]);

    const loadBooks = useCallback(async () => {
        try {
            setBooksLoading(true);
            const trimmed = debouncedBookSearch.trim();
            const data = await booksApi.list({
                title: trimmed || undefined,
                author: trimmed || undefined,
                skip: 0,
                limit: 20,
            });
            const list = Array.isArray(data) ? data : [];
            setAvailableBooks(list.filter((book: Book) => (book.available_copies ?? book.total_copies) > 0));
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
        loadBooks();
    }, [debouncedBookSearch, loadBooks, showNewLoanModal]);

    const selectableUsers = useMemo<SelectableUser[]>(() => {
        const query = userSearch.trim().toLowerCase();
        const list = query
            ? availableUsers.filter((user) => user.name.toLowerCase().includes(query) || user.email.toLowerCase().includes(query))
            : availableUsers;

        return list.map((user) => ({
            ...user,
            selectable: !tokenEmail || user.email === tokenEmail,
        }));
    }, [availableUsers, tokenEmail, userSearch]);

    const handleNewLoan = async (e: React.FormEvent) => {
        e.preventDefault();
        setNewLoanError(null);

        if (!selectedUser || !selectedBook) {
            setNewLoanError('Please select a member and a book.');
            return;
        }

        if (tokenEmail && selectedUser.email !== tokenEmail) {
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
            setBookSearch('');
            setDebouncedBookSearch('');
            setPage(0);
            await fetchLoans(0);
        } catch (error) {
            console.error('Error creating loan:', error);
            setNewLoanError('Unable to create loan. Please try again.');
        } finally {
            setNewLoanLoading(false);
        }
    };

    return (
        <div className="flex h-full min-h-0 gap-6">
            <div className="flex-1 flex flex-col min-w-0 min-h-0">
                <div className="mb-6">
                    <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-4">
                        <div>
                            <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Active Loans</h1>
                            <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">Monitor due dates and overdue items.</p>
                        </div>
                        <div className="flex gap-2">
                            <Button variant="outline" icon={<Filter size={18} />} disabled>
                                Filter
                            </Button>
                            <Button icon={<Plus size={18} />} onClick={() => setShowNewLoanModal(true)}>
                                New Loan
                            </Button>
                        </div>
                    </div>

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
                                        <div className="col-span-1 flex justify-end">
                                            <button
                                                className="p-1.5 rounded-lg text-slate-300 dark:text-slate-600 bg-transparent"
                                                title="Actions (disabled)"
                                                disabled
                                            >
                                                <MoreVertical size={18} />
                                            </button>
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
                isOpen={showNewLoanModal}
                onClose={() => {
                    setShowNewLoanModal(false);
                    setNewLoanError(null);
                }}
                title="Create New Loan"
                size="lg"
            >
                <form onSubmit={handleNewLoan} className="space-y-6">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <div className="space-y-3">
                            <div className="flex items-center justify-between">
                                <label className="text-sm font-medium text-slate-700 dark:text-slate-200">Select Member</label>
                                <span className="text-xs text-slate-400">Only your account is eligible</span>
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
                                {!usersLoading && selectableUsers.length === 0 && (
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
                            <label className="text-sm font-medium text-slate-700 dark:text-slate-200">Select Book</label>
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
                                {!booksLoading && availableBooks.length === 0 && (
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
