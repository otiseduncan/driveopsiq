import { httpClient, ApiError } from './httpClient';
import {
  DriveOpsRequest,
  DriveOpsRequestCreate,
  DriveOpsRequestCreateResponse,
} from '@/types';

export class DriveOpsService {
  static async createRequest(
    payload: DriveOpsRequestCreate,
  ): Promise<DriveOpsRequestCreateResponse> {
    try {
      return await httpClient.post<DriveOpsRequestCreateResponse>(
        '/driveops/requests',
        payload,
      );
    } catch (error) {
      if (error instanceof ApiError) {
        throw new Error(error.message || 'Failed to create request');
      }
      throw new Error('Failed to create request');
    }
  }

  static async listRequests(): Promise<DriveOpsRequest[]> {
    try {
      return await httpClient.get<DriveOpsRequest[]>('/driveops/requests');
    } catch (error) {
      if (error instanceof ApiError) {
        throw new Error(error.message || 'Failed to load requests');
      }
      throw new Error('Failed to load requests');
    }
  }
}

export default DriveOpsService;
