import { useCallback, useEffect, useMemo, useState } from 'react';
import { Plus, Filter, MoreVertical, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react';
import { Button, Input, Card, Badge, Modal } from '../../components/ui';
import type { Book, CreateBookData } from '../../types';
import { booksApi } from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';

const toCsvValue = (value: string | number | boolean | null | undefined) => {
  const safe = String(value ?? '').replace(/"/g, '""');
  return `"${safe}"`;
};

const downloadCsv = (filename: string, headers: string[], rows: Array<Array<string | number | boolean | null | undefined>>) => {
  const csvRows = [headers.map(toCsvValue).join(',')];
  rows.forEach((row) => {
    csvRows.push(row.map(toCsvValue).join(','));
  });
  const blob = new Blob([csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};

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

export default function BooksPage() {
  const { role } = useAuth();
  const canManageBooks = role === 'admin';
  const [books, setBooks] = useState<Book[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [authorQuery, setAuthorQuery] = useState('');
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('');
  const [debouncedAuthorQuery, setDebouncedAuthorQuery] = useState('');
  const [availabilityFilter, setAvailabilityFilter] = useState<'all' | 'available' | 'borrowed'>('all');
  const [loading, setLoading] = useState(false);
  const [isLoadingList, setIsLoadingList] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [lastPage, setLastPage] = useState<number | null>(null);
  const [formData, setFormData] = useState<CreateBookData>({
    title: '',
    author: '',
    isbn: '',
    total_copies: 1,
  });

  const fetchBooks = useCallback(async (targetPage: number = page) => {
    try {
      setIsLoadingList(true);
      setListError(null);
      const trimmedTitle = debouncedSearchQuery.trim();
      const trimmedAuthor = debouncedAuthorQuery.trim();
      const data = await booksApi.list({
        title: trimmedTitle || undefined,
        author: trimmedAuthor || undefined,
        skip: targetPage * pageSize,
        limit: pageSize,
      });
      const list = Array.isArray(data) ? data : [];
      setBooks(list);
      if (list.length < pageSize) {
        setLastPage(targetPage);
      }
    } catch (error) {
      console.error('Error loading books:', error);
      setListError('Unable to load books. Please try again.');
    } finally {
      setIsLoadingList(false);
    }
  }, [debouncedAuthorQuery, debouncedSearchQuery, page, pageSize]);

  useEffect(() => {
    fetchBooks();
  }, [fetchBooks]);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setDebouncedSearchQuery(searchQuery);
    }, 350);
    return () => window.clearTimeout(handle);
  }, [searchQuery]);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setDebouncedAuthorQuery(authorQuery);
    }, 350);
    return () => window.clearTimeout(handle);
  }, [authorQuery]);

  useEffect(() => {
    setLastPage(null);
  }, [debouncedAuthorQuery, debouncedSearchQuery, pageSize]);

  const filteredBooks = useMemo(() => {
    if (availabilityFilter === 'available') {
      return books.filter((book) => (book.available_copies ?? book.total_copies) > 0);
    }
    if (availabilityFilter === 'borrowed') {
      return books.filter((book) => (book.available_copies ?? book.total_copies) === 0);
    }
    return books;
  }, [availabilityFilter, books]);

  const handleAddBook = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      await booksApi.create(formData);
      setPage(0);
      setShowAddModal(false);
      setFormData({ title: '', author: '', isbn: '', total_copies: 1 });
      await fetchBooks(0);
    } catch (error) {
      console.error('Error adding book:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleExportCsv = () => {
    const today = new Date().toISOString().split('T')[0];
    const rows = filteredBooks.map((book) => [
      book.id,
      book.title,
      book.author,
      book.isbn,
      book.total_copies,
      book.available_copies ?? book.total_copies,
      book.created_at ?? '',
    ]);
    downloadCsv(`books_${today}.csv`, ['id', 'title', 'author', 'isbn', 'total_copies', 'available_copies', 'created_at'], rows);
  };

  const handleExportPdf = async () => {
    const today = new Date().toISOString().split('T')[0];
    const blob = await booksApi.exportPdf();
    downloadBlob(blob, `books_${today}.pdf`);
  };

  const canGoBack = page > 0;
  const canGoNext = lastPage !== null ? page < lastPage : books.length === pageSize;
  const startItem = filteredBooks.length ? page * pageSize + 1 : 0;
  const endItem = page * pageSize + filteredBooks.length;
  const pageWindow = 4;

  const pageNumbers = useMemo(() => {
    if (lastPage === null) {
      return [page];
    }

    let start = Math.max(0, page - 1);
    let end = start + pageWindow - 1;

    end = Math.min(end, lastPage);
    start = Math.max(0, end - pageWindow + 1);

    return Array.from({ length: end - start + 1 }, (_, index) => start + index);
  }, [lastPage, page]);

  const getStatusBadge = (book: Book) => {
    const available = book.available_copies ?? book.total_copies;
    if (available > 0) {
      return <Badge variant="success" dot>Available</Badge>;
    }
    return <Badge variant="warning" dot>Borrowed</Badge>;
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-3xl font-black leading-tight tracking-tight text-slate-900 dark:text-white">
            Book Catalog Management
          </h1>
          <p className="text-slate-500 dark:text-slate-400 text-base">
            Manage and track library inventory across all branches.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {canManageBooks && (
            <>
              <Button variant="outline" onClick={handleExportCsv} disabled={filteredBooks.length === 0}>
                Export CSV
              </Button>
              <Button variant="outline" onClick={handleExportPdf} disabled={filteredBooks.length === 0}>
                Export PDF
              </Button>
              <Button
                icon={<Plus size={20} />}
                onClick={() => setShowAddModal(true)}
              >
                Add New Book
              </Button>
            </>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-5">
          <Input
            showSearchIcon
            placeholder="Search by title..."
            value={searchQuery}
            onChange={(e) => {
              setPage(0);
              setLastPage(null);
              setSearchQuery(e.target.value);
            }}
          />
        </div>
        <div className="lg:col-span-4">
          <Input
            placeholder="Filter by author..."
            value={authorQuery}
            onChange={(e) => {
              setPage(0);
              setLastPage(null);
              setAuthorQuery(e.target.value);
            }}
          />
        </div>
        <div className="lg:col-span-3 flex flex-wrap items-center gap-3 justify-start lg:justify-end">
          <label className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
            <span>Availability</span>
            <select
              className="h-10 rounded-lg border border-slate-200 dark:border-border-dark bg-white dark:bg-slate-900 px-3 text-sm text-slate-700 dark:text-slate-200"
              value={availabilityFilter}
              onChange={(e) => {
                setPage(0);
                setAvailabilityFilter(e.target.value as 'all' | 'available' | 'borrowed');
              }}
            >
              <option value="all">All</option>
              <option value="available">Available</option>
              <option value="borrowed">Borrowed</option>
            </select>
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
            <span>Show</span>
            <select
              className="h-10 rounded-lg border border-slate-200 dark:border-border-dark bg-white dark:bg-slate-900 px-3 text-sm text-slate-700 dark:text-slate-200"
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
          </label>
          <Button variant="outline" icon={<Filter size={18} />} disabled>
            All Genres
          </Button>
          <Button variant="outline" icon={<Filter size={18} />} disabled>
            More Filters
          </Button>
        </div>
      </div>

      <Card padding="none" className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 dark:bg-[#192633] border-b border-slate-200 dark:border-border-dark">
                <th className="p-4 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 min-w-[200px]">Title</th>
                <th className="p-4 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 min-w-[150px]">Author</th>
                <th className="p-4 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 hidden sm:table-cell">ISBN</th>
                <th className="p-4 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Status</th>
                <th className="p-4 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 text-center w-[80px]">Stock</th>
                <th className="p-4 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 text-right w-[80px]">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-border-dark">
              {isLoadingList && (
                <tr>
                  <td className="p-6 text-center text-sm text-slate-500 dark:text-slate-400" colSpan={6}>
                    Loading books...
                  </td>
                </tr>
              )}
              {!isLoadingList && listError && (
                <tr>
                  <td className="p-6 text-center text-sm text-rose-500" colSpan={6}>
                    {listError}
                  </td>
                </tr>
              )}
              {!isLoadingList && !listError && filteredBooks.length === 0 && (
                <tr>
                  <td className="p-6 text-center text-sm text-slate-500 dark:text-slate-400" colSpan={6}>
                    No books found.
                  </td>
                </tr>
              )}
              {!isLoadingList && !listError && filteredBooks.map((book) => (
                <tr key={book.id} className="group hover:bg-slate-50 dark:hover:bg-[#1e2a36] transition-colors">
                  <td className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-8 bg-slate-200 dark:bg-slate-700 rounded shadow-sm flex items-center justify-center">
                        <span className="text-xs text-slate-400">📖</span>
                      </div>
                      <div>
                        <div className="font-medium text-slate-900 dark:text-white">{book.title}</div>
                      </div>
                    </div>
                  </td>
                  <td className="p-4 text-sm text-slate-500 dark:text-slate-400">{book.author}</td>
                  <td className="p-4 text-sm text-slate-500 dark:text-slate-400 font-mono hidden sm:table-cell">{book.isbn}</td>
                  <td className="p-4">{getStatusBadge(book)}</td>
                  <td className="p-4 text-sm text-slate-900 dark:text-white font-medium text-center">
                    {book.available_copies ?? book.total_copies}
                  </td>
                  <td className="p-4 text-right">
                    <button className="text-slate-400 hover:text-primary transition-colors p-1 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800">
                      <MoreVertical size={20} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
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

      <Modal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        title="Add New Book"
        size="lg"
      >
        <form onSubmit={handleAddBook} className="space-y-6">
          <Input
            label="Book Title"
            placeholder="e.g. The Great Gatsby"
            value={formData.title}
            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            required
          />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Input
              label="ISBN"
              placeholder="978-3-16-148410-0"
              value={formData.isbn}
              onChange={(e) => setFormData({ ...formData, isbn: e.target.value })}
              required
            />
            <Input
              label="Author"
              placeholder="Author name"
              value={formData.author}
              onChange={(e) => setFormData({ ...formData, author: e.target.value })}
              required
            />
          </div>

          <Input
            label="Total Copies"
            type="number"
            min="1"
            value={formData.total_copies}
            onChange={(e) => setFormData({ ...formData, total_copies: parseInt(e.target.value) })}
            required
          />

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-200 dark:border-border-dark">
            <Button type="button" variant="outline" onClick={() => setShowAddModal(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={loading}>
              Save Book
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
