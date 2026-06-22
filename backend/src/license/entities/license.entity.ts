import { Entity, PrimaryGeneratedColumn, Column, CreateDateColumn, UpdateDateColumn, Index } from 'typeorm';
import { LicenseTier } from '../../common/enums/license-tier.enum';

@Entity('licenses')
export class License {
  @PrimaryGeneratedColumn()
  id: number;

  @Column({ type: 'varchar', length: 255, unique: true })
  @Index('idx_licenses_key_hash')
  key_hash: string;

  @Column({ type: 'varchar', length: 32, unique: true })
  key_display: string;

  @Column({ type: 'varchar', length: 20 })
  tier: LicenseTier;

  @Column({ type: 'integer', default: 5 })
  max_devices: number;

  @Column({ type: 'integer', default: 5 })
  max_activations: number;

  @Column({ type: 'timestamp', nullable: true })
  expires_at: Date;

  @Column({ type: 'boolean', default: true })
  @Index('idx_licenses_is_active')
  is_active: boolean;

  @Column({ type: 'varchar', length: 255, nullable: true })
  disabled_reason: string;

  @CreateDateColumn()
  created_at: Date;

  @UpdateDateColumn()
  updated_at: Date;
}
