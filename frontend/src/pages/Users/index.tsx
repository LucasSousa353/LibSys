import { useState } from 'react';
import { Plus, Eye, Edit, Trash2, Users as UsersIcon, Ban } from 'lucide-react';
import { Button, Input, Card, Badge, Avatar, Modal } from '../../components/ui';
import type { User, CreateUserData } from '../../types';

const sampleUsers: User[] = [
  { id: 1, name: 'Alice Johnson', email: 'alice@example.com', is_active: true },
  { id: 2, name: 'Bob Smith', email: 'bob@libsys.net', is_active: true },
  { id: 3, name: 'Charlie Brown', email: 'charlie@test.com', is_active: false },
  { id: 4, name: 'Diana Prince', email: 'diana@mail.com', is_active: true },
  { id: 5, name: 'Evan Wright', email: 'evan@school.edu', is_active: true },
];

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>(sampleUsers);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [formData, setFormData] = useState<CreateUserData>({
    name: '',
    email: '',
    password: '',
  });

  const filteredUsers = users.filter(user =>
    user.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    user.email.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const activeUsers = users.filter(u => u.is_active).length;
  const blockedUsers = users.filter(u => !u.is_active).length;

  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      const newUser: User = {
        id: users.length + 1,
        name: formData.name,
        email: formData.email,
        is_active: true,
      };
      setUsers([...users, newUser]);
      setShowAddModal(false);
      setFormData({ name: '', email: '', password: '' });
    } catch (error) {
      console.error('Error adding user:', error);
    } finally {
      setLoading(false);
    }
  };

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
        <Button icon={<Plus size={20} />} onClick={() => setShowAddModal(true)}>
          Register New User
        </Button>
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
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-14"
          />
        </div>
      </div>

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
              {filteredUsers.map((user) => (
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
                  <td className="p-4 text-right">
                    <div className="flex items-center justify-end gap-2 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity">
                      <button className="p-1.5 rounded-md text-slate-400 hover:text-primary hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors" title="View Profile">
                        <Eye size={18} />
                      </button>
                      <button className="p-1.5 rounded-md text-slate-400 hover:text-primary hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors" title="Edit User">
                        <Edit size={18} />
                      </button>
                      <button className="p-1.5 rounded-md text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors" title="Delete User">
                        <Trash2 size={18} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between px-4 py-3 border-t border-slate-200 dark:border-border-dark bg-slate-50 dark:bg-slate-800/30">
          <div className="text-xs text-slate-500 dark:text-slate-400">
            Showing <span className="font-medium">1</span> to <span className="font-medium">{filteredUsers.length}</span> of <span className="font-medium">{users.length}</span> results
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled>Previous</Button>
            <Button variant="outline" size="sm">Next</Button>
          </div>
        </div>
      </Card>

      <Modal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        title="Register New User"
        size="md"
      >
        <form onSubmit={handleAddUser} className="space-y-6">
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
