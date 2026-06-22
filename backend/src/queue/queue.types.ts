/**
 * Queue job types and interfaces for video factory processing
 */

export interface VideoProcessingJobData {
  videoId: string;
  accountId: string;
  filePath: string;
  title: string;
  description?: string;
  tags?: string[];
  scheduledTime?: Date;
  platforms: string[]; // ['douyin', 'tiktok', 'bilibili', ...]
  userId: string;
  createdAt: Date;
}

export interface VideoProcessingJobResult {
  videoId: string;
  jobId: string;
  platform: string;
  status: 'success' | 'failed' | 'pending';
  uploadUrl?: string;
  uploadId?: string;
  error?: string;
  timestamp: Date;
}

export interface QueueConfig {
  host: string;
  port: number;
  password?: string;
  db?: number;
  retryStrategy?: (times: number) => number | null;
}

export enum VideoJobStatus {
  QUEUED = 'queued',
  PROCESSING = 'processing',
  SUCCESS = 'success',
  FAILED = 'failed',
  RETRYING = 'retrying',
}

export enum VideoQueue {
  VIDEO_PROCESSING = 'video-processing',
  VIDEO_UPLOAD = 'video-upload',
  VIDEO_OPTIMIZATION = 'video-optimization',
}
