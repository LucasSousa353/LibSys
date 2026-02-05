import { useState } from 'react';
import { Plus, Filter, MoreVertical, ChevronLeft, ChevronRight } from 'lucide-react';
import { Button, Input, Card, Badge, Modal } from '../../components/ui';
import type { Book, CreateBookData } from '../../types';

const sampleBooks: Book[] = [
  { id: 1, title: 'The Great Gatsby', author: 'F. Scott Fitzgerald', isbn: '978-0743273565', total_copies: 12, available_copies: 8 },
  { id: 2, title: '1984', author: 'George Orwell', isbn: '978-0451524935', total_copies: 8, available_copies: 0 },
  { id: 3, title: 'Sapiens: A Brief History', author: 'Yuval Noah Harari', isbn: '978-0062316097', total_copies: 5, available_copies: 3 },
  { id: 4, title: 'Clean Code', author: 'Robert C. Martin', isbn: '978-0132350884', total_copies: 3, available_copies: 2 },
  { id: 5, title: 'Dune', author: 'Frank Herbert', isbn: '978-0441013593', total_copies: 6, available_copies: 0 },
  { id: 6, title: 'Atomic Habits', author: 'James Clear', isbn: '978-0735211292', total_copies: 8, available_copies: 5 },
];

export default function BooksPage() {
  const [books, setBooks] = useState<Book[]>(sampleBooks);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [formData, setFormData] = useState<CreateBookData>({
    title: '',
    author: '',
    isbn: '',
    total_copies: 1,
  });

  const filteredBooks = books.filter(book => 
    book.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    book.author.toLowerCase().includes(searchQuery.toLowerCase()) ||
    book.isbn.includes(searchQuery)
  );

  const handleAddBook = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      const newBook = { ...formData, id: books.length + 1, available_copies: formData.total_copies };
      setBooks([...books, newBook]);
      setShowAddModal(false);
      setFormData({ title: '', author: '', isbn: '', total_copies: 1 });
    } catch (error) {
      console.error('Error adding book:', error);
    } finally {
      setLoading(false);
    }
  };

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
        <Button 
          icon={<Plus size={20} />}
          onClick={() => setShowAddModal(true)}
        >
          Add New Book
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-5">
          <Input
            showSearchIcon
            placeholder="Search by title, author, or ISBN..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <div className="lg:col-span-7 flex flex-wrap items-center gap-3 justify-start lg:justify-end">
          <Button variant="outline" icon={<Filter size={18} />}>
            All Genres
          </Button>
          <Button variant="outline">
            Availability
          </Button>
          <Button variant="outline" icon={<Filter size={18} />}>
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
              {filteredBooks.map((book) => (
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
            Showing <span className="font-medium text-slate-900 dark:text-white">1</span> to{' '}
            <span className="font-medium text-slate-900 dark:text-white">{filteredBooks.length}</span> of{' '}
            <span className="font-medium text-slate-900 dark:text-white">{books.length}</span> results
          </p>
          <div className="flex items-center gap-2">
            <button className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 dark:border-border-dark bg-white dark:bg-slate-800 text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50" disabled>
              <ChevronLeft size={20} />
            </button>
            <button className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-primary bg-primary text-white font-medium text-sm">
              1
            </button>
            <button className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 dark:border-border-dark bg-white dark:bg-slate-800 text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-700 font-medium text-sm">
              2
            </button>
            <button className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 dark:border-border-dark bg-white dark:bg-slate-800 text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700">
              <ChevronRight size={20} />
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
