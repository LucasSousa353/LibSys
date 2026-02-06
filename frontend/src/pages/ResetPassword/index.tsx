import { useState } from 'react';
import type { FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Lock } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { usersApi } from '../../services/api';

export default function ResetPasswordPage() {
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const { role, refreshUser } = useAuth();
    const navigate = useNavigate();

    const handleSubmit = async (event: FormEvent) => {
        event.preventDefault();
        setError('');

        if (password.length < 6) {
            setError('Password must be at least 6 characters.');
            return;
        }

        if (password !== confirmPassword) {
            setError('Passwords do not match.');
            return;
        }

        try {
            setLoading(true);
            await usersApi.resetMyPassword(password);
            await refreshUser();
            const target = role === 'admin' ? '/dashboard' : '/books';
            navigate(target, { replace: true });
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Unable to reset password.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-background-light dark:bg-background-dark flex items-center justify-center px-4">
            <div className="w-full max-w-md rounded-2xl border border-slate-200 dark:border-border-dark bg-white dark:bg-surface-dark p-8 shadow-xl">
                <div className="flex items-center gap-3 mb-6">
                    <div className="h-11 w-11 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
                        <Lock size={20} />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Reset your password</h1>
                        <p className="text-sm text-slate-500 dark:text-slate-400">
                            You must set a new password to continue.
                        </p>
                    </div>
                </div>

                {error && (
                    <div className="mb-5 rounded-lg border border-red-200 dark:border-red-900/30 bg-red-50 dark:bg-red-900/20 px-4 py-3 text-sm text-red-700 dark:text-red-400">
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-5">
                    <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
                            New password
                        </label>
                        <input
                            type="password"
                            value={password}
                            onChange={(event) => setPassword(event.target.value)}
                            className="w-full rounded-lg border border-slate-200 dark:border-border-dark bg-white dark:bg-slate-900 px-4 py-2.5 text-sm text-slate-900 dark:text-white"
                            placeholder="Minimum 6 characters"
                            required
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
                            Confirm password
                        </label>
                        <input
                            type="password"
                            value={confirmPassword}
                            onChange={(event) => setConfirmPassword(event.target.value)}
                            className="w-full rounded-lg border border-slate-200 dark:border-border-dark bg-white dark:bg-slate-900 px-4 py-2.5 text-sm text-slate-900 dark:text-white"
                            placeholder="Repeat your new password"
                            required
                        />
                    </div>
                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-60"
                    >
                        {loading ? 'Updating...' : 'Update password'}
                    </button>
                </form>
            </div>
        </div>
    );
}
