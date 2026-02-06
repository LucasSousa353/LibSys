import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './contexts/AuthContext';
import DashboardLayout from './components/layout/DashboardLayout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Books from './pages/Books';
import Users from './pages/Users';
import Loans from './pages/Loans';
import ResetPassword from './pages/ResetPassword';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading, mustResetPassword } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-background-light dark:bg-background-dark">
        <div className="flex flex-col items-center gap-4">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
          <p className="text-slate-500 dark:text-slate-400">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (mustResetPassword && location.pathname !== '/reset-password') {
    return <Navigate to="/reset-password" replace />;
  }

  return <>{children}</>;
}

function RoleRoute({
  children,
  allowedRoles,
  redirectTo,
}: {
  children: React.ReactNode;
  allowedRoles: Array<'admin' | 'librarian' | 'user'>;
  redirectTo: string;
}) {
  const { role, loading } = useAuth();

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-background-light dark:bg-background-dark">
        <div className="flex flex-col items-center gap-4">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
          <p className="text-slate-500 dark:text-slate-400">Loading...</p>
        </div>
      </div>
    );
  }

  if (role && !allowedRoles.includes(role)) {
    return <Navigate to={redirectTo} replace />;
  }

  return <>{children}</>;
}

function App() {
  const { role, mustResetPassword } = useAuth();
  const defaultRoute = role === 'admin' ? '/dashboard' : '/books';

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/reset-password"
        element={
          <ProtectedRoute>
            {mustResetPassword ? <ResetPassword /> : <Navigate to={defaultRoute} replace />}
          </ProtectedRoute>
        }
      />

      <Route
        path="/"
        element={
          <ProtectedRoute>
            <DashboardLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to={defaultRoute} replace />} />
        <Route
          path="dashboard"
          element={
            <RoleRoute allowedRoles={['admin']} redirectTo="/books">
              <Dashboard />
            </RoleRoute>
          }
        />
        <Route
          path="books"
          element={
            <RoleRoute allowedRoles={['admin', 'librarian', 'user']} redirectTo="/books">
              <Books />
            </RoleRoute>
          }
        />
        <Route
          path="users"
          element={
            <RoleRoute allowedRoles={['admin']} redirectTo="/books">
              <Users />
            </RoleRoute>
          }
        />
        <Route
          path="loans"
          element={
            <RoleRoute allowedRoles={['admin', 'librarian', 'user']} redirectTo="/books">
              <Loans />
            </RoleRoute>
          }
        />
      </Route>

      <Route path="*" element={<Navigate to={defaultRoute} replace />} />
    </Routes>
  );
}

export default App;
