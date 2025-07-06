const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface Tender {
  id: string;
  title: string;
  organization: string;
  description?: string;
  contract_value?: string;
  closing_date?: string;
  source_name: string;
  location?: string;
  url?: string;
  created_at?: string;
  updated_at?: string;
  category?: string;
  reference?: string;
  contact_name?: string;
  contact_email?: string;
  contact_phone?: string;
  external_id?: string;
  summary_raw?: string;
  documents_urls?: string[];
  original_url?: string;
  notice_type?: string;
  languages?: string;
  delivery_regions?: string;
  opportunity_region?: string;
  contract_duration?: string;
  procurement_method?: string;
  selection_criteria?: string;
  commodity_unspsc?: string;
  // Advanced search fields
  rank?: number;
  highlight?: string;
}

export interface TenderStatistics {
  total_tenders: number;
  recent_tenders: number;
  source_counts: Record<string, number>;
  last_updated?: string;
  total_value?: string;
  provinces: string[];
  categories: Record<string, number>;
}

export interface TendersResponse {
  tenders: Tender[];
  total: number;
  offset: number;
  limit: number;
  has_more: boolean;
  filters_applied: Record<string, any>;
  query_info?: {
    original_query: string;
    parsed_query: string;
    filters: Record<string, any>;
    field_filters: Record<string, any>;
    wildcards: string[];
    has_errors: boolean;
    error_message?: string;
  };
}

export interface TendersParams {
  limit?: number;
  offset?: number;
  search?: string;
  source?: string;
  province?: string;
  category?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  use_advanced_search?: boolean;
  use_ai_search?: boolean;
}

export interface TenderFilters {
  sources: string[];
  provinces: string[];
  categories: string[];
  date_range?: {
    earliest: string;
    latest: string;
  };
}

export interface SearchSuggestion {
  text: string;
  type: string;
  frequency?: number;
}

export interface SearchStatistics {
  total_tenders: number;
  tenders_with_summary: number;
  tenders_with_documents: number;
  tenders_with_contacts: number;
  avg_search_vector_length: number;
}

export interface SearchExample {
  query: string;
  description: string;
}

export interface RelatedTender {
  id: string;
  title: string;
  organization: string;
  source_name: string;
  closing_date?: string;
  created_at?: string;
  url?: string;
}

class ApiService {
  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    
    try {
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
        ...options,
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API request failed: ${response.status} ${response.statusText} - ${errorText}`);
      }

      return response.json();
    } catch (error) {
      console.error('API request error:', error);
      throw error;
    }
  }

  async getTenderStatistics(): Promise<TenderStatistics> {
    return this.request<TenderStatistics>('/api/v1/tenders/statistics');
  }

  async getTenders(params: TendersParams = {}): Promise<TendersResponse> {
    const searchParams = new URLSearchParams();
    
    if (params.limit) searchParams.append('limit', params.limit.toString());
    if (params.offset) searchParams.append('offset', params.offset.toString());
    if (params.search) searchParams.append('search', params.search);
    if (params.source) searchParams.append('source', params.source);
    if (params.province) searchParams.append('province', params.province);
    if (params.category) searchParams.append('category', params.category);
    if (params.sort_by) searchParams.append('sort_by', params.sort_by);
    if (params.sort_order) searchParams.append('sort_order', params.sort_order);
    if (params.use_advanced_search !== undefined) {
      searchParams.append('use_advanced_search', params.use_advanced_search.toString());
    }
    if (params.use_ai_search !== undefined) {
      searchParams.append('use_ai_search', params.use_ai_search.toString());
    }

    const queryString = searchParams.toString();
    const endpoint = `/api/v1/tenders/${queryString ? `?${queryString}` : ''}`;
    
    return this.request<TendersResponse>(endpoint);
  }

  async getTender(id: string): Promise<Tender> {
    return this.request<Tender>(`/api/v1/tenders/${id}`);
  }

  async getTenderFilters(): Promise<TenderFilters> {
    return this.request<TenderFilters>('/api/v1/tenders/filters');
  }

  async getSearchSuggestions(query: string, limit: number = 10): Promise<{ success: boolean; data: SearchSuggestion[]; error?: string }> {
    return this.request<{ success: boolean; data: SearchSuggestion[]; error?: string }>(`/api/v1/tenders/search-suggestions?q=${encodeURIComponent(query)}&limit=${limit}`);
  }

  async getSearchStatistics(): Promise<{ success: boolean; data: SearchStatistics; error?: string }> {
    return this.request<{ success: boolean; data: SearchStatistics; error?: string }>('/api/v1/tenders/search-statistics');
  }

  async getSearchExamples(): Promise<{ success: boolean; data: SearchExample[]; error?: string }> {
    return this.request<{ success: boolean; data: SearchExample[]; error?: string }>('/api/v1/tenders/search-examples');
  }

  async getRelatedTenders(tenderId: string, limit: number = 5): Promise<{ success: boolean; data: RelatedTender[]; error?: string }> {
    return this.request<{ success: boolean; data: RelatedTender[]; error?: string }>(`/api/v1/tenders/${tenderId}/related?limit=${limit}`);
  }

  // Scraper management endpoints
  async getScraperStatus(): Promise<any> {
    return this.request<any>('/api/v1/scrapers/status');
  }

  async triggerScraper(scraperName: string): Promise<any> {
    return this.request<any>(`/api/v1/scrapers/${scraperName}/trigger`, {
      method: 'POST',
    });
  }

  async triggerAllScrapers(): Promise<any> {
    return this.request<any>('/api/v1/scrapers/trigger-all', {
      method: 'POST',
    });
  }

  async getScraperJobs(): Promise<any> {
    return this.request<any>('/api/v1/scrapers/jobs');
  }

  async getScraperLogs(scraperName?: string): Promise<any> {
    const endpoint = scraperName 
      ? `/api/v1/scrapers/${scraperName}/logs`
      : '/api/v1/scrapers/logs';
    return this.request<any>(endpoint);
  }

  async getScraperConfigs(): Promise<any> {
    return this.request<any>('/api/v1/scrapers/configs');
  }

  async updateScraperConfig(scraperName: string, config: any): Promise<any> {
    return this.request<any>(`/api/v1/scrapers/configs/${scraperName}`, {
      method: 'PUT',
      body: JSON.stringify(config),
    });
  }

  async getSchedulerStatus(): Promise<any> {
    return this.request<any>('/api/v1/scrapers/scheduler/status');
  }

  // AI Search method
  async searchWithAI(query: string, params: Omit<TendersParams, 'search'> = {}): Promise<TendersResponse> {
    const searchParams = new URLSearchParams();
    
    // Add AI search parameters
    searchParams.append('search', query);
    searchParams.append('use_ai_search', 'true');
    
    if (params.limit) searchParams.append('limit', params.limit.toString());
    if (params.offset) searchParams.append('offset', params.offset.toString());
    if (params.source) searchParams.append('source', params.source);
    if (params.province) searchParams.append('province', params.province);
    if (params.category) searchParams.append('category', params.category);
    if (params.sort_by) searchParams.append('sort_by', params.sort_by);
    if (params.sort_order) searchParams.append('sort_order', params.sort_order);

    const queryString = searchParams.toString();
    const endpoint = `/api/v1/tenders/?${queryString}`;
    
    return this.request<TendersResponse>(endpoint);
  }
}

export const apiService = new ApiService(); 