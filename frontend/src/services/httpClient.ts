/**
 * HTTP Client Service with enhanced security and error handling
 */

import { RequestOptions } from '../types';

export class ApiError extends Error {
  public readonly statusCode: number;
  public readonly response?: Response;
  
  constructor(message: string, statusCode: number, response?: Response) {
    super(message);
    this.name = 'ApiError';
    this.statusCode = statusCode;
    this.response = response;
  }
}

export class HttpClient {
  private readonly baseUrl: string;
  private readonly defaultHeaders: Record<string, string>;
  private readonly timeout: number;

  constructor(baseUrl: string = '/api/v1', timeout: number = 30000) {
    this.baseUrl = baseUrl.replace(/\/$/, ''); // Remove trailing slash
    this.timeout = timeout;
    this.defaultHeaders = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
  }

  /**
   * Set authentication token for subsequent requests
   */
  setAuthToken(token: string): void {
    if (token) {
      this.defaultHeaders['Authorization'] = `Bearer ${token}`;
    } else {
      delete this.defaultHeaders['Authorization'];
    }
  }

  /**
   * Make HTTP request with comprehensive error handling
   */
  private async request<T = any>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<T> {
    const url = this.buildUrl(endpoint);
    const controller = new AbortController();
    
    // Set timeout
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const requestOptions: RequestInit = {
        method: options.method || 'GET',
        headers: {
          ...this.defaultHeaders,
          ...options.headers,
        },
        body: options.body,
        signal: options.signal || controller.signal,
        credentials: 'same-origin', // Security: only send cookies to same origin
      };

      // Security: Remove undefined/null values from headers
      Object.keys(requestOptions.headers!).forEach(key => {
        if (!requestOptions.headers![key as keyof HeadersInit]) {
          delete requestOptions.headers![key as keyof HeadersInit];
        }
      });

      const response = await fetch(url, requestOptions);
      
      clearTimeout(timeoutId);

      // Handle non-JSON responses
      const contentType = response.headers.get('content-type') || '';
      const isJson = contentType.includes('application/json');

      if (!response.ok) {
        let errorMessage = `Request failed: ${response.status} ${response.statusText}`;
        
        if (isJson) {
          try {
            const errorData = await response.json();
            errorMessage = errorData.detail || errorData.message || errorMessage;
          } catch {
            // Ignore JSON parse errors for error responses
          }
        }
        
        throw new ApiError(errorMessage, response.status, response);
      }

      // Return appropriate response format
      if (response.status === 204) {
        return undefined as T; // No content
      }

      if (isJson) {
        return await response.json() as T;
      }

      return await response.text() as T;

    } catch (error) {
      clearTimeout(timeoutId);
      
      if (error instanceof ApiError) {
        throw error;
      }
      
      if (error instanceof DOMException && error.name === 'AbortError') {
        throw new ApiError('Request timeout', 408);
      }
      
      if (error instanceof TypeError) {
        throw new ApiError('Network error - please check your connection', 0);
      }
      
      throw new ApiError(
        error instanceof Error ? error.message : 'Unknown error occurred',
        0
      );
    }
  }

  /**
   * Build full URL from endpoint
   */
  private buildUrl(endpoint: string): string {
    // Security: Validate endpoint format
    if (endpoint.includes('://') || endpoint.startsWith('//')) {
      throw new Error('Invalid endpoint: absolute URLs not allowed');
    }
    
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    return `${this.baseUrl}${cleanEndpoint}`;
  }

  /**
   * GET request
   */
  async get<T = any>(endpoint: string, headers?: Record<string, string>): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET', headers });
  }

  /**
   * POST request
   */
  async post<T = any>(
    endpoint: string, 
    data?: any, 
    headers?: Record<string, string>
  ): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
      headers,
    });
  }

  /**
   * PUT request
   */
  async put<T = any>(
    endpoint: string, 
    data?: any, 
    headers?: Record<string, string>
  ): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
      headers,
    });
  }

  /**
   * DELETE request
   */
  async delete<T = any>(endpoint: string, headers?: Record<string, string>): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE', headers });
  }

  /**
   * PATCH request
   */
  async patch<T = any>(
    endpoint: string, 
    data?: any, 
    headers?: Record<string, string>
  ): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
      headers,
    });
  }

  /**
   * Upload file with progress tracking
   */
  async uploadFile<T = any>(
    endpoint: string,
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<T> {
    return new Promise((resolve, reject) => {
      const formData = new FormData();
      formData.append('file', file);
      
      const xhr = new XMLHttpRequest();
      
      // Progress tracking
      if (onProgress) {
        xhr.upload.addEventListener('progress', (event) => {
          if (event.lengthComputable) {
            const progress = (event.loaded / event.total) * 100;
            onProgress(progress);
          }
        });
      }
      
      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const result = JSON.parse(xhr.responseText);
            resolve(result);
          } catch {
            resolve(xhr.responseText as T);
          }
        } else {
          reject(new ApiError(`Upload failed: ${xhr.status}`, xhr.status));
        }
      });
      
      xhr.addEventListener('error', () => {
        reject(new ApiError('Upload failed: Network error', 0));
      });
      
      xhr.addEventListener('timeout', () => {
        reject(new ApiError('Upload failed: Timeout', 408));
      });
      
      // Set auth header if available
      const authHeader = this.defaultHeaders['Authorization'];
      if (authHeader) {
        xhr.setRequestHeader('Authorization', authHeader);
      }
      
      xhr.timeout = this.timeout;
      xhr.open('POST', this.buildUrl(endpoint));
      xhr.send(formData);
    });
  }
}

const apiBaseUrl =
  (import.meta.env?.VITE_API_BASE_URL as string | undefined) ||
  (import.meta.env?.VITE_API_URL as string | undefined) ||
  '/api/v1';

// Default HTTP client instance
export const httpClient = new HttpClient(apiBaseUrl);
