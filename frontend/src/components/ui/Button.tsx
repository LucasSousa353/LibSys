import { forwardRef } from 'react';
import type { ButtonHTMLAttributes } from 'react';
import { Loader2 } from 'lucide-react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  icon?: React.ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({
    children,
    variant = 'primary',
    size = 'md',
    loading = false,
    icon,
    className = '',
    disabled,
    ...props
  }, ref) => {
    const baseStyles = `
      inline-flex items-center justify-center gap-2 
      font-medium rounded-lg transition-all duration-200
      focus:outline-none focus:ring-2 focus:ring-offset-2
      disabled:opacity-50 disabled:cursor-not-allowed
      transform active:scale-[0.98]
    `;

    const variants = {
      primary: `
        bg-primary text-white 
        hover:bg-blue-600 
        focus:ring-primary/50
        shadow-md shadow-primary/20
      `,
      secondary: `
        bg-slate-100 dark:bg-slate-800 
        text-slate-900 dark:text-white 
        hover:bg-slate-200 dark:hover:bg-slate-700
        focus:ring-slate-500/50
      `,
      outline: `
        border border-slate-300 dark:border-slate-600 
        bg-white dark:bg-transparent 
        text-slate-700 dark:text-white 
        hover:bg-slate-50 dark:hover:bg-slate-800
        focus:ring-slate-500/50
      `,
      ghost: `
        text-slate-600 dark:text-slate-400 
        hover:bg-slate-100 dark:hover:bg-slate-800 
        hover:text-slate-900 dark:hover:text-white
        focus:ring-slate-500/50
      `,
      danger: `
        bg-red-500 text-white 
        hover:bg-red-600 
        focus:ring-red-500/50
        shadow-md shadow-red-500/20
      `,
    };

    const sizes = {
      sm: 'h-8 px-3 text-xs',
      md: 'h-10 px-4 text-sm',
      lg: 'h-12 px-6 text-base',
    };

    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
        {...props}
      >
        {loading ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : icon ? (
          icon
        ) : null}
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';

export default Button;
