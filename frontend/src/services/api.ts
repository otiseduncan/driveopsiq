/**
 * API Service Layer for SyferStack V2
 * Provides type-safe API methods with comprehensive error handling
 */

import { httpClient, ApiError } from './httpClient';
import {
  User,
  UserCreate,
  UserUpdate,
  LoginRequest,
  LoginResponse,
  ApiHealthResponse,
  AIRequest,
  AIResponse,
} from '../types';

export class AuthService {
  /**
   * Authenticate user with email and password
   */
  static async login(credentials: LoginRequest): Promise<LoginResponse> {
    try {
      const response = await httpClient.post<LoginResponse>('/auth/login', credentials);
      
      // Set auth token for subsequent requests
      if (response.access_token) {
        httpClient.setAuthToken(response.access_token);
        this.storeAccessToken(response.access_token);
      }

      this.emitAuthChange();

      if (response.refresh_token) {
        this.storeRefreshToken(response.refresh_token);
      }
      
      return response;
    } catch (error) {
      if (error instanceof ApiError) {
        throw new Error(`Login failed: ${error.message}`);
      }
      throw new Error('Login failed: Network error');
    }
  }

  /**
   * Logout current user
   */
  static async logout(): Promise<void> {
    try {
      await httpClient.post('/auth/logout');
    } catch (error) {
      console.warn('Logout request failed:', error);
      // Continue with local logout even if server request fails
    } finally {
      httpClient.setAuthToken('');
      this.removeAccessToken();
      this.removeRefreshToken();
      this.emitAuthChange();
    }
  }

  /**
   * Register new user
   */
  static async register(userData: UserCreate): Promise<User> {
    try {
      return await httpClient.post<User>('/auth/register', userData);
    } catch (error) {
      if (error instanceof ApiError) {
        throw new Error(`Registration failed: ${error.message}`);
      }
      throw new Error('Registration failed: Network error');
    }
  }

  /**
   * Get current user profile
   */
  static async getCurrentUser(): Promise<User> {
    try {
      return await httpClient.get<User>('/auth/me');
    } catch (error) {
      if (error instanceof ApiError && error.statusCode === 401) {
        this.removeAccessToken();
        this.removeRefreshToken();
        httpClient.setAuthToken('');
        this.emitAuthChange();
        throw new Error('Session expired. Please login again.');
      }
      throw new Error('Failed to get user profile');
    }
  }

  /**
   * Store authentication token
   */
  private static storeAccessToken(token: string): void {
    try {
      localStorage.setItem('auth_token', token);
    } catch (error) {
      console.warn('Failed to store auth token:', error);
    }
    this.emitAuthChange();
  }

  private static storeRefreshToken(token: string): void {
    try {
      localStorage.setItem('refresh_token', token);
    } catch (error) {
      console.warn('Failed to store refresh token:', error);
    }
  }

  /**
   * Remove authentication token
   */
  private static removeAccessToken(): void {
    try {
      localStorage.removeItem('auth_token');
    } catch (error) {
      console.warn('Failed to remove auth token:', error);
    }
    this.emitAuthChange();
  }

  private static removeRefreshToken(): void {
    try {
      localStorage.removeItem('refresh_token');
    } catch (error) {
      console.warn('Failed to remove refresh token:', error);
    }
  }

  /**
   * Get stored authentication token
   */
  static getStoredToken(): string | null {
    try {
      return localStorage.getItem('auth_token');
    } catch (error) {
      console.warn('Failed to get stored token:', error);
      return null;
    }
  }

  static getStoredRefreshToken(): string | null {
    try {
      return localStorage.getItem('refresh_token');
    } catch (error) {
      console.warn('Failed to get stored refresh token:', error);
      return null;
    }
  }

  /**
   * Initialize authentication from stored token
   */
  static initializeAuth(): void {
    const token = this.getStoredToken();
    if (token) {
      httpClient.setAuthToken(token);
    }
  }

  private static emitAuthChange(): void {
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new Event('authchange'));
    }
  }
}

export class UserService {
  /**
   * Get all users (admin only)
   */
  static async getUsers(): Promise<User[]> {
    try {
      return await httpClient.get<User[]>('/users');
    } catch (error) {
      if (error instanceof ApiError) {
        throw new Error(`Failed to get users: ${error.message}`);
      }
      throw new Error('Failed to get users: Network error');
    }
  }

  /**
   * Get user by ID
   */
  static async getUserById(userId: string): Promise<User> {
    try {
      return await httpClient.get<User>(`/users/${userId}`);
    } catch (error) {
      if (error instanceof ApiError) {
        throw new Error(`Failed to get user: ${error.message}`);
      }
      throw new Error('Failed to get user: Network error');
    }
  }

  /**
   * Update user
   */
  static async updateUser(userId: string, updates: UserUpdate): Promise<User> {
    try {
      return await httpClient.put<User>(`/users/${userId}`, updates);
    } catch (error) {
      if (error instanceof ApiError) {
        throw new Error(`Failed to update user: ${error.message}`);
      }
      throw new Error('Failed to update user: Network error');
    }
  }

  /**
   * Delete user
   */
  static async deleteUser(userId: string): Promise<void> {
    try {
      await httpClient.delete(`/users/${userId}`);
    } catch (error) {
      if (error instanceof ApiError) {
        throw new Error(`Failed to delete user: ${error.message}`);
      }
      throw new Error('Failed to delete user: Network error');
    }
  }
}

export class HealthService {
  /**
   * Check API health status
   */
  static async checkHealth(): Promise<ApiHealthResponse> {
    try {
      return await httpClient.get<ApiHealthResponse>('/health');
    } catch (error) {
      if (error instanceof ApiError) {
        throw new Error(`Health check failed: ${error.message}`);
      }
      throw new Error('Health check failed: Network error');
    }
  }

  /**
   * Get detailed system status
   */
  static async getSystemStatus(): Promise<any> {
    try {
      return await httpClient.get('/health/detailed');
    } catch (error) {
      if (error instanceof ApiError) {
        throw new Error(`System status check failed: ${error.message}`);
      }
      throw new Error('System status check failed: Network error');
    }
  }
}

export class AIService {
  /**
   * Send AI request
   */
  static async sendRequest(request: AIRequest): Promise<AIResponse> {
    try {
      return await httpClient.post<AIResponse>('/ai/chat', request);
    } catch (error) {
      if (error instanceof ApiError) {
        throw new Error(`AI request failed: ${error.message}`);
      }
      throw new Error('AI request failed: Network error');
    }
  }

  /**
   * Get AI request history
   */
  static async getHistory(limit: number = 10): Promise<AIResponse[]> {
    try {
      return await httpClient.get<AIResponse[]>(`/ai/history?limit=${limit}`);
    } catch (error) {
      if (error instanceof ApiError) {
        throw new Error(`Failed to get AI history: ${error.message}`);
      }
      throw new Error('Failed to get AI history: Network error');
    }
  }

  /**
   * Get available AI models
   */
  static async getModels(): Promise<string[]> {
    try {
      return await httpClient.get<string[]>('/ai/models');
    } catch (error) {
      if (error instanceof ApiError) {
        throw new Error(`Failed to get AI models: ${error.message}`);
      }
      throw new Error('Failed to get AI models: Network error');
    }
  }
}

// Utility function to handle API errors consistently
export const handleApiError = (error: unknown): string => {
  if (error instanceof ApiError) {
    switch (error.statusCode) {
      case 400:
        return 'Invalid request. Please check your input.';
      case 401:
        return 'Authentication required. Please login.';
      case 403:
        return 'Permission denied. You do not have access to this resource.';
      case 404:
        return 'Resource not found.';
      case 429:
        return 'Too many requests. Please try again later.';
      case 500:
        return 'Internal server error. Please try again later.';
      case 503:
        return 'Service temporarily unavailable. Please try again later.';
      default:
        return error.message || 'An unexpected error occurred.';
    }
  }

  if (error instanceof Error) {
    return error.message;
  }

  return 'An unexpected error occurred.';
};

// Initialize authentication on module load
AuthService.initializeAuth();
