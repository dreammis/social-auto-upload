import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { TrendsService } from './trends.service';
import { TrendsController } from './trends.controller';
import { Trend } from './entities/trend.entity';

@Module({
  imports: [TypeOrmModule.forFeature([Trend])],
  providers: [TrendsService],
  controllers: [TrendsController],
  exports: [TrendsService],
})
export class TrendsModule {}
