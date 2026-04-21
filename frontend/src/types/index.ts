/**
 * Type definitions for SyferStack V2 Frontend
 */

// User types
export interface User {
  id: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  roles?: string | null;
  created_at: string;
  updated_at: string;
}

export interface UserCreate {
  email: string;
  full_name: string;
  password: string;
}

export interface UserUpdate {
  email?: string;
  is_active?: boolean;
}

// Authentication types
export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  role?: string | null;
  user: User;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

// API Response types
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  errors?: Record<string, string[]>;
}

export interface ApiError {
  detail: string;
  status_code: number;
  type?: string;
}

// Health check types
export interface ApiHealthResponse {
  status: 'healthy' | 'unhealthy';
  version: string;
  uptime: number;
  timestamp: number;
  database?: {
    status: string;
    response_time_ms?: number;
  };
}

// AI Service types
export interface AIRequest {
  prompt: string;
  model?: string;
  max_tokens?: number;
  temperature?: number;
}

export interface AIResponse {
  id: string;
  response: string;
  model: string;
  tokens_used: number;
  created_at: string;
}

// DriveOps IQ types
export type DriveOpsRequestStatus =
  | 'pending_validation'
  | 'validated'
  | 'claimed'
  | 'enroute'
  | 'onsite'
  | 'complete'
  | 'hold';

export interface DriveOpsRequestCreate {
  ro_number: string;
  vin: string;
  customer: string;
  insurer: string;
  calibration_type: string;
  notes?: string | null;
}

export interface DriveOpsRequest extends DriveOpsRequestCreate {
  id: string;
  status: DriveOpsRequestStatus;
  created_at: string;
  updated_at: string;
}

export interface DriveOpsRequestCreateResponse {
  status: string;
  message: string;
  request: DriveOpsRequest;
}

// Component props types
export interface BaseComponentProps {
  className?: string;
  children?: React.ReactNode;
}

export interface ButtonProps extends BaseComponentProps {
  onClick?: () => void;
  disabled?: boolean;
  variant?: 'primary' | 'secondary' | 'danger';
  size?: 'small' | 'medium' | 'large';
  type?: 'button' | 'submit' | 'reset';
}

export interface InputProps extends BaseComponentProps {
  type?: string;
  value?: string;
  placeholder?: string;
  onChange?: (value: string) => void;
  onBlur?: () => void;
  disabled?: boolean;
  required?: boolean;
  error?: string;
}

// Form types
export interface FormState<T = Record<string, any>> {
  values: T;
  errors: Record<keyof T, string>;
  isSubmitting: boolean;
  isValid: boolean;
}

// Application state types
export interface AppState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  theme: 'light' | 'dark';
}

// Route types
export interface RouteConfig {
  path: string;
  component: React.ComponentType;
  protected?: boolean;
  exact?: boolean;
}

// HTTP types
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';

export interface RequestOptions {
  method?: HttpMethod;
  headers?: Record<string, string>;
  body?: string | FormData;
  signal?: AbortSignal;
}

// Utility types
export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;
export type RequiredFields<T, K extends keyof T> = T & Required<Pick<T, K>>;
export type Nullable<T> = T | null;
export type AsyncResult<T> = Promise<T>;

// Event types
export interface AppEvent<T = any> {
  type: string;
  payload?: T;
  timestamp: number;
}

// Configuration types
export interface AppConfig {
  apiUrl: string;
  environment: 'development' | 'production' | 'test';
  features: {
    aiService: boolean;
    userManagement: boolean;
    analytics: boolean;
  };
  version: string;
}

// Error boundary types
export interface ErrorInfo {
  componentStack: string;
  errorBoundary?: string;
}

export interface ErrorState {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
}
