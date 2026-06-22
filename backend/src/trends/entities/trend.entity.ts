import { Entity, PrimaryGeneratedColumn, Column, Index } from 'typeorm';

/**
 * Trend Entity — maps to the `trends` table populated by the AI Worker (Python).
 * Read-only from NestJS perspective; writes are handled by the worker.
 */
@Entity('trends')
@Index('idx_trends_platform_extracted', ['platform', 'extracted_at'])
export class Trend {
  @PrimaryGeneratedColumn()
  id: number;

  @Column({ type: 'varchar', length: 20 })
  platform: string;

  @Column({ type: 'varchar', length: 200 })
  keyword: string;

  @Column({ type: 'float', nullable: true })
  volume: number;

  @Column({ type: 'timestamp' })
  extracted_at: Date;
}
