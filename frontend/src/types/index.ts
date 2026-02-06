export interface User {
  id: number;
  name: string;
  email: string;
  role?: 'admin' | 'librarian' | 'user';
  must_reset_password?: boolean;
  is_active?: boolean;
  created_at?: string;
}

export interface CreateUserData {
  name: string;
  email: string;
  password: string;
}

export interface Book {
  id: number;
  title: string;
  author: string;
  isbn: string;
  total_copies: number;
  available_copies?: number;
  created_at?: string;
}

export interface CreateBookData {
  title: string;
  author: string;
  isbn: string;
  total_copies: number;
}

export interface Loan {
  id: number;
  user_id: number;
  book_id: number;
  loan_date: string;
  expected_return_date: string;
  due_date?: string;
  return_date?: string;
  status: 'active' | 'returned' | 'overdue';
  fine_amount?: number;
  user?: User;
  book?: Book;
}

export interface CreateLoanData {
  user_id: number;
  book_id: number;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  role: 'admin' | 'librarian' | 'user';
  must_reset_password: boolean;
}

export interface AuthState {
  isAuthenticated: boolean;
  token: string | null;
  user: User | null;
  role: 'admin' | 'librarian' | 'user' | null;
  mustResetPassword: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

export interface HealthStatus {
  status: string;
  database?: string;
  cache?: string;
}

export interface MostBorrowedBookItem {
  book_id: number;
  title: string;
  author: string;
  loan_count: number;
}

export interface DashboardSummary {
  total_books: number;
  active_loans: number;
  overdue_loans: number;
  total_fines: number;
  recent_books: Book[];
}

export interface ReportsSummary {
  total_books: number;
  total_users: number;
  active_loans: number;
  overdue_loans: number;
  total_fines: number;
  most_borrowed_books: MostBorrowedBookItem[];
}
