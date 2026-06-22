import { Module } from '@nestjs/common';
import { BullModule } from '@nestjs/bull';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { QueueService } from './queue.service';
import { QueueConfigService } from './queue.config';
import { VideoProcessingProcessor } from './processors/video-processing.processor';
import { VideoQueue } from './queue.types';

@Module({
  imports: [
    BullModule.forRootAsync({
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: async (configService: ConfigService) => {
        const queueConfigService = new QueueConfigService(configService);
        return queueConfigService.getQueueOptions();
      },
    }),
    BullModule.registerQueue({
      name: VideoQueue.VIDEO_PROCESSING,
    }),
  ],
  providers: [QueueService, QueueConfigService, VideoProcessingProcessor],
  exports: [QueueService],
})
export class QueueModule {}
