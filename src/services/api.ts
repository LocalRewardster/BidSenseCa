import axios, { AxiosInstance, AxiosResponse } from 'axios';
import { 
  Tender, 
  TenderList, 
  TenderFilters, 
  ScraperStatus, 
  ScraperJob, 
  ScraperJobList,
  TenderStatistics,
  ApiResponse,
  ApiError
} from '../types';

class ApiService {
  private api: AxiosInstance;

  constructor() {
    this.api = axios.create({
      baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.api.interceptors.request.use(
      (config) => {
        // Add auth token if available
        const token = localStorage.getItem('auth_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.api.interceptors.response.use(
      (response: AxiosResponse) => response,
      (error) => {
        const apiError: ApiError = {
          message: error.response?.data?.detail || error.message,
          status: error.response?.status || 500,
          code: error.response?.data?.code,
          details: error.response?.data,
        };
        return Promise.reject(apiError);
      }
    );
  }

  // Tender endpoints
  async getTenders(filters: TenderFilters = {}): Promise<TenderList> {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        params.append(key, value.toString());
      }
    });

    const response = await this.api.get<TenderList>(`/tenders/?${params.toString()}`);
    return response.data;
  }

  async getTender(id: string): Promise<Tender> {
    const response = await this.api.get<Tender>(`/tenders/${id}`);
    return response.data;
  }

  async updateTender(id: string, data: Partial<Tender>): Promise<Tender> {
    const response = await this.api.put<Tender>(`/tenders/${id}`, data);
    return response.data;
  }

  async deleteTender(id: string): Promise<void> {
    await this.api.delete(`/tenders/${id}`);
  }

  async getTenderStatistics(): Promise<TenderStatistics> {
    const response = await this.api.get<TenderStatistics>('/tenders/statistics/summary');
    return response.data;
  }

  async getAvailableSources(): Promise<{ sources: ScraperStatus[]; total_sources: number }> {
    const response = await this.api.get('/tenders/sources/list');
    return response.data;
  }

  // Scraper endpoints
  async getScraperStatus(): Promise<ScraperStatus[]> {
    const response = await this.api.get<ScraperStatus[]>('/scrapers/status');
    return response.data;
  }

  async getScraperStatusByName(name: string): Promise<ScraperStatus> {
    const response = await this.api.get<ScraperStatus>(`/scrapers/status/${name}`);
    return response.data;
  }

  async runScraper(name: string, limit?: number): Promise<{ message: string; job_id: string; status: string }> {
    const params = limit ? { limit } : {};
    const response = await this.api.post(`/scrapers/run/${name}`, null, { params });
    return response.data;
  }

  async runAllScrapers(limit?: number): Promise<{ message: string; job_id: string; status: string }> {
    const params = limit ? { limit } : {};
    const response = await this.api.post('/scrapers/run-all', null, { params });
    return response.data;
  }

  async getScraperJobs(limit = 50, offset = 0, status?: string): Promise<ScraperJobList> {
    const params = new URLSearchParams();
    params.append('limit', limit.toString());
    params.append('offset', offset.toString());
    if (status) {
      params.append('status', status);
    }

    const response = await this.api.get<ScraperJobList>(`/scrapers/jobs?${params.toString()}`);
    return response.data;
  }

  async getScraperJob(id: string): Promise<ScraperJob> {
    const response = await this.api.get<ScraperJob>(`/scrapers/jobs/${id}`);
    return response.data;
  }

  async startScraperJob(id: string): Promise<{ message: string }> {
    const response = await this.api.post(`/scrapers/jobs/${id}/start`);
    return response.data;
  }

  async cancelScraperJob(id: string): Promise<{ message: string }> {
    const response = await this.api.post(`/scrapers/jobs/${id}/cancel`);
    return response.data;
  }

  // Scheduler endpoints
  async getSchedulerStatus(): Promise<{ running: boolean; tasks: string[]; schedule: Record<string, string> }> {
    const response = await this.api.get('/scrapers/scheduler/status');
    return response.data;
  }

  async startScheduler(): Promise<{ message: string }> {
    const response = await this.api.post('/scrapers/scheduler/start');
    return response.data;
  }

  async stopScheduler(): Promise<{ message: string }> {
    const response = await this.api.post('/scrapers/scheduler/stop');
    return response.data;
  }

  async updateSchedulerSchedule(schedule: Record<string, string>): Promise<{ message: string }> {
    const response = await this.api.put('/scrapers/scheduler/schedule', schedule);
    return response.data;
  }

  async runSchedulerNow(scraperName = 'all'): Promise<{ message: string; job_id: string }> {
    const response = await this.api.post('/scrapers/scheduler/run-now', null, {
      params: { scraper_name: scraperName }
    });
    return response.data;
  }

  // Health check
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    const response = await this.api.get('/health');
    return response.data;
  }

  // Error handling
  handleError(error: any): ApiError {
    if (error.response) {
      return {
        message: error.response.data?.detail || 'An error occurred',
        status: error.response.status,
        code: error.response.data?.code,
        details: error.response.data,
      };
    }
    return {
      message: error.message || 'Network error',
      status: 0,
    };
  }
}

// Export singleton instance
export const apiService = new ApiService();
export default apiService; 