import { useCallback, useEffect, useMemo, useState } from 'react';
import { Plus, Users as UsersIcon, Ban, MoreVertical, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, KeyRound } from 'lucide-react';
import { Button, Input, Card, Badge, Avatar, Modal } from '../../components/ui';
import type { User, CreateUserData } from '../../types';
import { usersApi } from '../../services/api';

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

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [isLoadingList, setIsLoadingList] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [openActionId, setOpenActionId] = useState<number | null>(null);
  const [confirmStatusUser, setConfirmStatusUser] = useState<User | null>(null);
  const [confirmResetUser, setConfirmResetUser] = useState<User | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [lastPage, setLastPage] = useState<number | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [formData, setFormData] = useState<CreateUserData>({
    name: '',
    email: '',
    password: '',
  });

  const fetchUsers = useCallback(async (targetPage: number = page) => {
    try {
      setIsLoadingList(true);
      setListError(null);
      const data = await usersApi.list(targetPage * pageSize, pageSize);
      const list = Array.isArray(data) ? data : [];
      setUsers(list);
      if (list.length < pageSize) {
        setLastPage(targetPage);
      }
    } catch (error) {
      console.error('Error loading users:', error);
      setListError('Unable to load users. Please try again.');
    } finally {
      setIsLoadingList(false);
    }
  }, [page, pageSize]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setDebouncedSearchQuery(searchQuery);
    }, 350);
    return () => window.clearTimeout(handle);
  }, [searchQuery]);

  useEffect(() => {
    setLastPage(null);
  }, [pageSize]);

  useEffect(() => {
    const handleClick = (event: MouseEvent) => {
      const target = event.target as HTMLElement | null;
      if (!target?.closest('[data-user-actions="menu"]')) {
        setOpenActionId(null);
      }
    };
    document.addEventListener('click', handleClick);
    return () => document.removeEventListener('click', handleClick);
  }, []);

  const filteredUsers = useMemo(() => {
    const query = debouncedSearchQuery.trim().toLowerCase();
    if (!query) {
      return users;
    }
    return users.filter((user) =>
      user.name.toLowerCase().includes(query) ||
      user.email.toLowerCase().includes(query)
    );
  }, [debouncedSearchQuery, users]);

  const activeUsers = users.filter(u => u.is_active).length;
  const blockedUsers = users.filter(u => !u.is_active).length;

  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      setFormError(null);
      await usersApi.create(formData);
      setPage(0);
      setShowAddModal(false);
      setFormData({ name: '', email: '', password: '' });
      await fetchUsers(0);
    } catch (error) {
      const detail = error?.response?.data?.detail;
      if (Array.isArray(detail)) {
        const firstMessage = detail[0]?.msg || 'Invalid input. Please review the form.';
        setFormError(firstMessage);
      } else if (typeof detail === 'string') {
        setFormError(detail);
      } else {
        setFormError('Unable to create user. Please check the form and try again.');
      }
      console.error('Error adding user:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleExportCsv = () => {
    const today = new Date().toISOString().split('T')[0];
    const rows = filteredUsers.map((user) => [
      user.id,
      user.name,
      user.email,
      user.is_active ?? true,
      user.created_at ?? '',
    ]);
    downloadCsv(`users_${today}.csv`, ['id', 'name', 'email', 'is_active', 'created_at'], rows);
  };

  const handleExportPdf = async () => {
    const today = new Date().toISOString().split('T')[0];
    const blob = await usersApi.exportPdf();
    downloadBlob(blob, `users_${today}.pdf`);
  };

  const handleToggleStatus = async (user: User) => {
    try {
      setActionLoading(true);
      setActionError(null);
      await usersApi.updateStatus(user.id, !user.is_active);
      setConfirmStatusUser(null);
      await fetchUsers(page);
    } catch (error) {
      console.error('Error updating user status:', error);
      setActionError('Unable to update user status. Please try again.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleResetPassword = async (user: User) => {
    try {
      setActionLoading(true);
      setActionError(null);
      await usersApi.resetPassword(user.id);
      setConfirmResetUser(null);
      await fetchUsers(page);
    } catch (error) {
      console.error('Error resetting password:', error);
      setActionError('Unable to reset password. Please try again.');
    } finally {
      setActionLoading(false);
    }
  };

  const canGoBack = page > 0;
  const canGoNext = lastPage !== null ? page < lastPage : users.length === pageSize;
  const startItem = filteredUsers.length ? page * pageSize + 1 : 0;
  const endItem = page * pageSize + filteredUsers.length;
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

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
        <div className="flex flex-col gap-2">
          <h1 className="text-3xl sm:text-4xl font-black leading-tight tracking-tight text-slate-900 dark:text-white">
            User Management
          </h1>
          <p className="text-slate-500 dark:text-slate-400 text-base">
            Manage library members, registrations, and account status
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" onClick={handleExportCsv} disabled={filteredUsers.length === 0}>
            Export CSV
          </Button>
          <Button variant="outline" onClick={handleExportPdf} disabled={filteredUsers.length === 0}>
            Export PDF
          </Button>
          <Button icon={<Plus size={20} />} onClick={() => setShowAddModal(true)}>
            Register New User
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Card>
            <div className="flex items-center justify-between">
              <p className="text-slate-500 dark:text-slate-400 text-sm font-semibold uppercase tracking-wider">
                Active Users
              </p>
              <UsersIcon size={20} className="text-green-500" />
            </div>
            <p className="text-slate-900 dark:text-white text-3xl font-bold mt-2">{activeUsers.toLocaleString()}</p>
            <p className="text-green-600 dark:text-green-400 text-xs font-medium flex items-center gap-1 mt-1">
              +12% this month
            </p>
          </Card>
          <Card>
            <div className="flex items-center justify-between">
              <p className="text-slate-500 dark:text-slate-400 text-sm font-semibold uppercase tracking-wider">
                Blocked Users
              </p>
              <Ban size={20} className="text-red-500" />
            </div>
            <p className="text-slate-900 dark:text-white text-3xl font-bold mt-2">{blockedUsers}</p>
            <p className="text-slate-400 text-xs font-medium flex items-center gap-1 mt-1">
              Requires attention
            </p>
          </Card>
        </div>

        <div className="lg:col-span-1 flex items-end">
          <Input
            showSearchIcon
            placeholder="Search by Name or Email..."
            value={searchQuery}
            onChange={(e) => {
              setPage(0);
              setSearchQuery(e.target.value);
            }}
            className="h-14"
          />
        </div>
      </div>

      {actionError && (
        <div className="rounded-lg border border-red-200 dark:border-red-900/30 bg-red-50 dark:bg-red-900/20 px-4 py-3 text-sm text-red-700 dark:text-red-400">
          {actionError}
        </div>
      )}

      <Card padding="none" className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-border-dark">
                <th className="p-4 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 w-1/4">Name</th>
                <th className="p-4 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 w-1/4">Email</th>
                <th className="p-4 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 w-1/6">User ID</th>
                <th className="p-4 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 w-1/6">Status</th>
                <th className="p-4 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 text-right w-1/6">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-border-dark">
              {isLoadingList && (
                <tr>
                  <td className="p-6 text-center text-sm text-slate-500 dark:text-slate-400" colSpan={5}>
                    Loading users...
                  </td>
                </tr>
              )}
              {!isLoadingList && listError && (
                <tr>
                  <td className="p-6 text-center text-sm text-rose-500" colSpan={5}>
                    {listError}
                  </td>
                </tr>
              )}
              {!isLoadingList && !listError && filteredUsers.length === 0 && (
                <tr>
                  <td className="p-6 text-center text-sm text-slate-500 dark:text-slate-400" colSpan={5}>
                    No users found.
                  </td>
                </tr>
              )}
              {!isLoadingList && !listError && filteredUsers.map((user) => (
                <tr key={user.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors group">
                  <td className="p-4">
                    <div className="flex items-center gap-3">
                      <Avatar name={user.name} />
                      <div>
                        <p className="text-sm font-medium text-slate-900 dark:text-white">{user.name}</p>
                        <p className="text-xs text-slate-500 dark:text-slate-400 md:hidden">{user.email}</p>
                      </div>
                    </div>
                  </td>
                  <td className="p-4 text-sm text-slate-600 dark:text-slate-300">{user.email}</td>
                  <td className="p-4 text-sm text-slate-500 dark:text-slate-400 font-mono">ID-{user.id.toString().padStart(4, '0')}</td>
                  <td className="p-4">
                    <Badge variant={user.is_active ? 'success' : 'danger'}>
                      {user.is_active ? 'Active' : 'Blocked'}
                    </Badge>
                  </td>
                  <td className="p-4 text-right" data-user-actions="menu">
                    <div className="relative inline-flex">
                      <button
                        className="inline-flex items-center justify-center p-1.5 rounded-md text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-primary transition-colors"
                        title="Actions"
                        onClick={(event) => {
                          event.stopPropagation();
                          setOpenActionId((current) => (current === user.id ? null : user.id));
                        }}
                      >
                        <MoreVertical size={18} />
                      </button>
                      {openActionId === user.id && (
                        <div className="absolute right-0 mt-2 w-48 rounded-lg border border-slate-200 dark:border-border-dark bg-white dark:bg-slate-900 shadow-lg z-10">
                          <button
                            className="w-full px-3 py-2 text-left text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800"
                            onClick={() => setConfirmStatusUser(user)}
                          >
                            {user.is_active ? 'Deactivate user' : 'Activate user'}
                          </button>
                          <button
                            className="w-full px-3 py-2 text-left text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800"
                            onClick={() => setConfirmResetUser(user)}
                          >
                            Reset password
                          </button>
                        </div>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 px-4 py-3 border-t border-slate-200 dark:border-border-dark bg-slate-50 dark:bg-[#192633]">
          <div className="text-sm text-slate-500 dark:text-slate-400">
            Showing <span className="font-medium">{startItem}</span> to <span className="font-medium">{endItem}</span>
          </div>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
              <span>Show</span>
              <select
                className="h-8 rounded-lg border border-slate-200 dark:border-border-dark bg-white dark:bg-slate-800 px-2 text-xs text-slate-700 dark:text-slate-200"
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
            <div className="flex items-center gap-1">
              <button
                className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 dark:border-border-dark bg-white dark:bg-slate-800 text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50"
                onClick={() => setPage(0)}
                disabled={!canGoBack || isLoadingList}
                title="First page"
              >
                <ChevronsLeft size={18} />
              </button>
              <button
                className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 dark:border-border-dark bg-white dark:bg-slate-800 text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50"
                onClick={() => setPage((prev) => Math.max(prev - 1, 0))}
                disabled={!canGoBack || isLoadingList}
                title="Previous page"
              >
                <ChevronLeft size={18} />
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
                <ChevronRight size={18} />
              </button>
              <button
                className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 dark:border-border-dark bg-white dark:bg-slate-800 text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50"
                onClick={() => lastPage !== null && setPage(lastPage)}
                disabled={lastPage === null || page === lastPage || isLoadingList}
                title="Last page"
              >
                <ChevronsRight size={18} />
              </button>
            </div>
          </div>
        </div>
      </Card>

      <Modal
        isOpen={Boolean(confirmStatusUser)}
        onClose={() => setConfirmStatusUser(null)}
        title={confirmStatusUser?.is_active ? 'Deactivate user' : 'Activate user'}
        size="sm"
      >
        {confirmStatusUser && (
          <div className="space-y-4">
            <p className="text-sm text-slate-600 dark:text-slate-300">
              {confirmStatusUser.is_active
                ? `Deactivate ${confirmStatusUser.name}? They will lose access until reactivated.`
                : `Activate ${confirmStatusUser.name}?`}
            </p>
            <div className="flex justify-end gap-3">
              <Button variant="outline" onClick={() => setConfirmStatusUser(null)}>
                Cancel
              </Button>
              <Button
                onClick={() => handleToggleStatus(confirmStatusUser)}
                loading={actionLoading}
                variant={confirmStatusUser.is_active ? 'outline' : 'primary'}
              >
                {confirmStatusUser.is_active ? 'Deactivate' : 'Activate'}
              </Button>
            </div>
          </div>
        )}
      </Modal>

      <Modal
        isOpen={Boolean(confirmResetUser)}
        onClose={() => setConfirmResetUser(null)}
        title="Reset password"
        size="sm"
      >
        {confirmResetUser && (
          <div className="space-y-4">
            <div className="flex items-start gap-3">
              <div className="mt-0.5 rounded-full bg-amber-100 text-amber-600 p-2">
                <KeyRound size={16} />
              </div>
              <p className="text-sm text-slate-600 dark:text-slate-300">
                Force {confirmResetUser.name} to reset their password on next login?
              </p>
            </div>
            <div className="flex justify-end gap-3">
              <Button variant="outline" onClick={() => setConfirmResetUser(null)}>
                Cancel
              </Button>
              <Button onClick={() => handleResetPassword(confirmResetUser)} loading={actionLoading}>
                Confirm
              </Button>
            </div>
          </div>
        )}
      </Modal>
      <Modal
        isOpen={showAddModal}
        onClose={() => {
          setShowAddModal(false);
          setFormError(null);
        }}
        title="Register New User"
        size="md"
      >
        <form onSubmit={handleAddUser} className="space-y-6">
          {formError && (
            <div className="rounded-lg border border-red-200 dark:border-red-900/30 bg-red-50 dark:bg-red-900/20 px-4 py-3 text-sm text-red-700 dark:text-red-400">
              {formError}
            </div>
          )}
          <Input
            label="Full Name"
            placeholder="Enter full name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            required
          />
          <Input
            label="Email Address"
            type="email"
            placeholder="user@example.com"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            required
          />
          <Input
            label="Password"
            type="password"
            placeholder="Minimum 6 characters"
            value={formData.password}
            minLength={6}
            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
            required
          />

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-200 dark:border-border-dark">
            <Button type="button" variant="outline" onClick={() => setShowAddModal(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={loading}>
              Register User
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
