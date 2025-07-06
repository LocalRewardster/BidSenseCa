// API Response Types
export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

// Tender Types
export interface Tender {
  id: string;
  title: string;
  reference?: string;
  organization?: string;
  closing_date?: string;
  contract_value?: string;
  description?: string;
  contact_name?: string;
  contact_email?: string;
  contact_phone?: string;
  source_url?: string;
  source_name: string;
  external_id?: string;
  created_at: string;
  updated_at: string;
  summary_raw?: string;
  documents_urls?: string[];
  original_url?: string;
}

export interface TenderList {
  tenders: Tender[];
  total: number;
  limit: number;
  offset: number;
}

export interface TenderFilters {
  province?: string;
  naics?: string;
  keyword?: string;
  status?: string;
  limit?: number;
  offset?: number;
}

// Scraper Types
export interface ScraperStatus {
  scraper_name: string;
  is_enabled: boolean;
  last_run?: string;
  last_error?: string;
  total_tenders: number;
  avg_duration?: number;
}

export interface ScraperJob {
  id: string;
  scraper_name: string;
  limit?: number;
  parameters?: Record<string, any>;
  status: JobStatus;
  started_at?: string;
  completed_at?: string;
  tenders_scraped: number;
  tenders_saved: number;
  error_message?: string;
  logs?: string;
  created_at: string;
}

export enum JobStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

export interface ScraperJobList {
  jobs: ScraperJob[];
  total: number;
  limit: number;
  offset: number;
}

// Statistics Types
export interface TenderStatistics {
  total_tenders: number;
  source_counts: Record<string, number>;
  recent_tenders: number;
  last_updated: string;
}

export interface ScraperStatistics {
  total_scrapers: number;
  active_scrapers: number;
  total_jobs: number;
  successful_jobs: number;
  failed_jobs: number;
}

// Dashboard Types
export interface DashboardStats {
  total_tenders: number;
  recent_tenders: number;
  active_scrapers: number;
  total_value: string;
}

export interface ChartData {
  name: string;
  value: number;
  color?: string;
}

// Navigation Types
export interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  current?: boolean;
}

// Form Types
export interface SearchFormData {
  keyword: string;
  province: string;
  dateRange: string;
  sortBy: string;
}

// UI Types
export interface LoadingState {
  isLoading: boolean;
  error?: string;
}

export interface PaginationState {
  currentPage: number;
  totalPages: number;
  pageSize: number;
  totalItems: number;
}

// Theme Types
export interface Theme {
  name: string;
  primary: string;
  secondary: string;
  accent: string;
  background: string;
  text: string;
}

// Notification Types
export interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
}

// User Types
export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'user';
  created_at: string;
  last_login?: string;
}

// Settings Types
export interface UserSettings {
  theme: 'light' | 'dark' | 'auto';
  notifications: boolean;
  email_alerts: boolean;
  dashboard_layout: string;
}

// API Error Types
export interface ApiError {
  message: string;
  status: number;
  code?: string;
  details?: Record<string, any>;
} 