import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { QueueConfig } from './queue.types';

@Injectable()
export class QueueConfigService {
  private redisConfig: QueueConfig;

  constructor(private configService: ConfigService) {
    this.redisConfig = this.buildRedisConfig();
  }

  private buildRedisConfig(): QueueConfig {
    return {
      host: this.configService.get<string>('REDIS_HOST') || 'localhost',
      port: parseInt(this.configService.get<string>('REDIS_PORT') || '6379'),
      password: this.configService.get<string>('REDIS_PASSWORD'),
      db: parseInt(this.configService.get<string>('REDIS_DB') || '0'),
      retryStrategy: (times: number) => {
        const delay = Math.min(times * 50, 2000);
        return delay;
      },
    };
  }

  getRedisConfig(): QueueConfig {
    return this.redisConfig;
  }

  getQueueOptions() {
    const config = this.getRedisConfig();
    return {
      redis: {
        host: config.host,
        port: config.port,
        password: config.password,
        db: config.db,
        retryStrategy: config.retryStrategy,
      },
      defaultJobOptions: {
        attempts: 3,
        backoff: {
          type: 'exponential',
          delay: 2000,
        },
        removeOnComplete: true,
        removeOnFail: false,
      },
      settings: {
        maxStalledCount: 2,
        stalledInterval: 5000,
        maxRetriesPerSecond: 5,
      },
    };
  }
}
