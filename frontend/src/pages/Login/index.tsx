import { useState } from 'react';
import type { FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { Eye, EyeOff, Mail, Library } from 'lucide-react';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(email, password);
      const mustResetPassword = localStorage.getItem('must_reset_password') === 'true';
      if (mustResetPassword) {
        navigate('/reset-password');
        return;
      }
      const role = localStorage.getItem('user_role');
      navigate(role === 'admin' ? '/dashboard' : '/books');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid credentials. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen w-full flex-row bg-background-light dark:bg-background-dark">
      <div className="relative hidden w-0 flex-1 lg:block bg-slate-900">
        <div
          className="absolute inset-0 h-full w-full bg-cover bg-center"
          style={{
            backgroundImage: "url('https://images.unsplash.com/photo-1507842217343-583bb7270b66?ixlib=rb-4.0.3&auto=format&fit=crop&w=2070&q=80')"
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-background-dark/90 via-background-dark/50 to-primary/30 mix-blend-multiply" />

        <div className="relative z-10 flex h-full flex-col justify-between p-16">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/20 backdrop-blur-sm border border-primary/30 text-white">
              <Library size={24} />
            </div>
            <span className="text-xl font-bold tracking-tight text-white">LibSys</span>
          </div>

          <div className="max-w-lg">
            <h1 className="text-4xl font-black leading-tight tracking-tight text-white mb-4">
              Manage Knowledge.<br />Securely.
            </h1>
            <p className="text-lg font-medium text-slate-200/90 leading-relaxed">
              Access the world's most comprehensive digital library management system designed for modern institutions.
            </p>
          </div>
        </div>
      </div>

      <div className="flex flex-1 flex-col justify-center px-4 py-12 sm:px-6 lg:flex-none lg:px-20 xl:px-24 bg-background-light dark:bg-background-dark w-full lg:w-1/2 xl:w-[600px] h-screen overflow-y-auto">
        <div className="mx-auto w-full max-w-sm lg:w-96">
          <div className="flex lg:hidden items-center gap-2 mb-8 justify-center">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-white">
              <Library size={24} />
            </div>
            <span className="text-2xl font-bold text-slate-900 dark:text-white">LibSys</span>
          </div>

          <div className="text-center lg:text-left mb-10">
            <h2 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
              Welcome back
            </h2>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
              Please enter your credentials to access your account.
            </p>
          </div>

          {error && (
            <div className="mb-6 p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-900/30">
              <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="group">
              <label
                htmlFor="email"
                className="block text-sm font-medium leading-6 text-slate-900 dark:text-slate-200 mb-2"
              >
                Email or Library ID
              </label>
              <div className="relative rounded-lg shadow-sm">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                  <Mail size={20} className="text-slate-400 group-focus-within:text-primary transition-colors" />
                </div>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="member@libsys.edu"
                  required
                  className="block w-full rounded-lg border-0 py-3 pl-10 text-slate-900 shadow-sm ring-1 ring-inset ring-slate-300 placeholder:text-slate-400 focus:ring-2 focus:ring-inset focus:ring-primary dark:bg-slate-800 dark:ring-slate-700 dark:text-white dark:placeholder:text-slate-500 sm:text-sm sm:leading-6 transition-all"
                />
              </div>
            </div>

            <div className="group">
              <label
                htmlFor="password"
                className="block text-sm font-medium leading-6 text-slate-900 dark:text-slate-200 mb-2"
              >
                Password
              </label>
              <div className="relative rounded-lg shadow-sm">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="block w-full rounded-lg border-0 py-3 pl-3 pr-10 text-slate-900 shadow-sm ring-1 ring-inset ring-slate-300 placeholder:text-slate-400 focus:ring-2 focus:ring-inset focus:ring-primary dark:bg-slate-800 dark:ring-slate-700 dark:text-white dark:placeholder:text-slate-500 sm:text-sm sm:leading-6 transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 flex items-center pr-3 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-end">
              <a href="#" className="text-sm font-semibold text-primary hover:text-primary/80 transition-colors">
                Forgot Password?
              </a>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="flex w-full justify-center rounded-lg bg-primary px-3 py-3 text-sm font-bold leading-6 text-white shadow-sm hover:bg-primary/90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary transition-all duration-200 transform active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          <div className="mt-10 pt-6 border-t border-slate-200 dark:border-slate-800">
            <div className="flex flex-col items-center justify-center space-y-2">
              <p className="text-xs text-slate-500 dark:text-slate-500 font-medium">
                Version 1.0
              </p>
              <div className="flex items-center gap-2 rounded-full bg-emerald-50 dark:bg-emerald-900/20 px-3 py-1 border border-emerald-100 dark:border-emerald-900/30">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-400">
                  System Health: Online
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
