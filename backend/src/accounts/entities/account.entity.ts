import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  CreateDateColumn,
  UpdateDateColumn,
  Index,
  ManyToOne,
  JoinColumn,
} from 'typeorm';
import { Exclude } from 'class-transformer';
import { User } from '../../auth/entities/user.entity';
import { Platform } from '../enums/platform.enum';
import { AccountStatus } from '../enums/account-status.enum';

@Entity('accounts')
@Index('idx_accounts_user_id', ['user_id'])
@Index('idx_accounts_platform', ['platform'])
@Index('idx_accounts_status', ['status'])
export class Account {
  @PrimaryGeneratedColumn()
  id: number;

  @Column({ type: 'integer' })
  @Index('idx_accounts_user_fk')
  user_id: number;

  @ManyToOne(() => User, { onDelete: 'CASCADE' })
  @JoinColumn({ name: 'user_id' })
  user: User;

  @Column({ type: 'varchar', length: 20 })
  platform: Platform;

  @Column({ type: 'varchar', length: 200 })
  account_name: string;

  /**
   * Raw session data (cookies/tokens) encrypted with AES-256-GCM.
   * NEVER exposed in API responses.
   */
  @Column({ type: 'text' })
  @Exclude()
  session_data: string;

  @Column({ type: 'varchar', length: 500, nullable: true })
  @Exclude()
  proxy_url?: string;

  @Column({ type: 'varchar', length: 20, default: AccountStatus.CHECKING })
  status: AccountStatus;

  @Column({ type: 'timestamp', nullable: true })
  last_health_check: Date;

  @CreateDateColumn()
  created_at: Date;

  @UpdateDateColumn()
  updated_at: Date;
}
