import { Injectable, Logger } from '@nestjs/common';
import { InjectQueue } from '@nestjs/bull';
import { Queue, Job } from 'bull';
import { VideoProcessingJobData, VideoProcessingJobResult, VideoQueue } from './queue.types';

@Injectable()
export class QueueService {
  private logger = new Logger(QueueService.name);

  constructor(
    @InjectQueue(VideoQueue.VIDEO_PROCESSING)
    private videoProcessingQueue: Queue<VideoProcessingJobData>,
  ) {}

  async addVideoProcessingJob(
    jobData: VideoProcessingJobData,
  ): Promise<Job<VideoProcessingJobData>> {
    this.logger.log(`Adding video processing job for video ${jobData.videoId}`);

    const job = await this.videoProcessingQueue.add(jobData, {
      jobId: `video-${jobData.videoId}-${Date.now()}`,
      priority: jobData.scheduledTime ? 5 : 10, // Scheduled jobs lower priority
      delay: jobData.scheduledTime
        ? Math.max(0, jobData.scheduledTime.getTime() - Date.now())
        : 0,
    });

    this.logger.debug(`Job ${job.id} created for video ${jobData.videoId}`);
    return job;
  }

  async getJobStatus(jobId: string): Promise<any> {
    const job = await this.videoProcessingQueue.getJob(jobId);

    if (!job) {
      return null;
    }

    const state = await job.getState();
    const progress = job.progress();
    const failedReason = job.failedReason;

    return {
      id: job.id,
      state,
      progress,
      data: job.data,
      failedReason,
      attemptsMade: job.attemptsMade,
      processedOn: job.processedOn,
      finishedOn: job.finishedOn,
    };
  }

  async cancelJob(jobId: string): Promise<boolean> {
    const job = await this.videoProcessingQueue.getJob(jobId);

    if (!job) {
      return false;
    }

    await job.remove();
    this.logger.log(`Job ${jobId} cancelled`);
    return true;
  }

  async getQueueStats() {
    const [waiting, active, completed, failed, delayed] = await Promise.all([
      this.videoProcessingQueue.getWaitingCount(),
      this.videoProcessingQueue.getActiveCount(),
      this.videoProcessingQueue.getCompletedCount(),
      this.videoProcessingQueue.getFailedCount(),
      this.videoProcessingQueue.getDelayedCount(),
    ]);

    return {
      waiting,
      active,
      completed,
      failed,
      delayed,
      total: waiting + active + completed + failed + delayed,
    };
  }

  async cleanOldJobs(gracePeriodMs: number = 86400000): Promise<void> {
    // Clean completed jobs older than grace period (default 24h)
    await this.videoProcessingQueue.clean(gracePeriodMs, 'completed');

    // Clean failed jobs older than grace period
    await this.videoProcessingQueue.clean(gracePeriodMs, 'failed');

    this.logger.log('Old jobs cleaned');
  }
}
