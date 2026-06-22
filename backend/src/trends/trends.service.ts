import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Trend } from './entities/trend.entity';

export interface GroupedTrends {
  platform: string;
  trends: Array<{
    id: number;
    keyword: string;
    volume: number;
    extracted_at: Date;
  }>;
}

@Injectable()
export class TrendsService {
  constructor(
    @InjectRepository(Trend)
    private readonly trendRepository: Repository<Trend>,
  ) {}

  /**
   * Get the latest trends grouped by platform.
   * For each platform, returns the top 10 keywords by volume
   * from the most recent crawl batch.
   */
  async getLatest(): Promise<GroupedTrends[]> {
    // Find the single most recent extracted_at timestamp
    const latestRun = await this.trendRepository.findOne({
      where: {},
      order: { extracted_at: 'DESC' },
    });

    if (!latestRun) {
      return [];
    }

    // Get all trends from the latest extraction window (±1 second tolerance)
    const latestTime = latestRun.extracted_at;
    const windowStart = new Date(latestTime.getTime() - 1000);
    const windowEnd = new Date(latestTime.getTime() + 1000);

    const allLatest = await this.trendRepository.find({
      where: {},
      order: { volume: 'DESC' },
    });

    // Filter to only the latest batch
    const latestBatch = allLatest.filter(
      (t) => t.extracted_at >= windowStart && t.extracted_at <= windowEnd,
    );

    // Group by platform, take top 10 per platform
    const platformMap = new Map<string, Trend[]>();

    for (const trend of latestBatch) {
      const existing = platformMap.get(trend.platform) || [];
      if (existing.length < 10) {
        existing.push(trend);
        platformMap.set(trend.platform, existing);
      }
    }

    // Build response
    const result: GroupedTrends[] = [];
    for (const [platform, trends] of platformMap) {
      result.push({
        platform,
        trends: trends.map((t) => ({
          id: t.id,
          keyword: t.keyword,
          volume: t.volume,
          extracted_at: t.extracted_at,
        })),
      });
    }

    return result;
  }
}
