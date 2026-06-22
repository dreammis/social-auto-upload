import { Controller, Get, UseGuards, HttpCode, HttpStatus } from '@nestjs/common';
import { TrendsService } from './trends.service';
import { JwtAuthGuard } from '../common/guards/jwt-auth.guard';

@Controller('trends')
@UseGuards(JwtAuthGuard)
export class TrendsController {
  constructor(private readonly trendsService: TrendsService) {}

  /**
   * GET /trends/latest
   * Returns trends grouped by platform — top 10 per platform
   * from the most recent crawl batch.
   */
  @Get('latest')
  @HttpCode(HttpStatus.OK)
  async getLatest() {
    const data = await this.trendsService.getLatest();
    return {
      code: 200,
      data,
      msg: 'Latest trends retrieved',
    };
  }
}
