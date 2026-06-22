import { Entity, PrimaryGeneratedColumn, Column, CreateDateColumn, UpdateDateColumn, Index, ManyToOne, JoinColumn } from 'typeorm';
import { License } from './license.entity';

@Entity('license_activations')
@Index('idx_license_activations_unique_device', ['device_fingerprint', 'hw_id'], { unique: true })
export class LicenseActivation {
  @PrimaryGeneratedColumn()
  id: number;

  @Column({ type: 'integer' })
  @Index('idx_license_activations_license')
  license_id: number;

  @ManyToOne(() => License, { onDelete: 'CASCADE' })
  @JoinColumn({ name: 'license_id' })
  license: License;

  @Column({ type: 'varchar', length: 255 })
  device_fingerprint: string;

  @Column({ type: 'varchar', length: 255 })
  hw_id: string;

  @Column({ type: 'varchar', length: 100, nullable: true })
  device_name: string;

  @CreateDateColumn()
  activated_at: Date;

  @UpdateDateColumn()
  last_seen_at: Date;

  @Column({ type: 'boolean', default: true })
  is_active: boolean;
}
