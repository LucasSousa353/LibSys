import { forwardRef } from 'react';
import type { InputHTMLAttributes } from 'react';
import { Search } from 'lucide-react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  icon?: React.ReactNode;
  showSearchIcon?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, icon, showSearchIcon, className = '', ...props }, ref) => {
    return (
      <div className="space-y-2">
        {label && (
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200">
            {label}
          </label>
        )}
        <div className="relative">
          {(icon || showSearchIcon) && (
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400 dark:text-slate-500">
              {icon || <Search size={18} />}
            </div>
          )}
          <input
            ref={ref}
            className={`
              w-full h-11 px-4 rounded-lg 
              bg-slate-50 dark:bg-[#192633] 
              border border-slate-300 dark:border-[#324d67] 
              text-slate-900 dark:text-white 
              placeholder-slate-400 dark:placeholder-slate-500 
              focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary 
              transition-all text-sm
              ${(icon || showSearchIcon) ? 'pl-10' : ''}
              ${error ? 'border-red-500 focus:ring-red-500/50' : ''}
              ${className}
            `}
            {...props}
          />
        </div>
        {error && (
          <p className="text-sm text-red-500">{error}</p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

export default Input;
