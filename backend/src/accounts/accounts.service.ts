import {
  Injectable,
  NotFoundException,
  ForbiddenException,
  BadRequestException,
} from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Account } from './entities/account.entity';
import { Platform } from './enums/platform.enum';
import { AccountStatus } from './enums/account-status.enum';
import { CreateAccountDto } from './dto/create-account.dto';
import { UpdateAccountStatusDto } from './dto/update-account-status.dto';
import { CryptoService } from '../common/crypto/crypto.service';

@Injectable()
export class AccountsService {
  constructor(
    @InjectRepository(Account)
    private readonly accountRepository: Repository<Account>,
    private readonly cryptoService: CryptoService,
  ) {}

  /**
   * Create a new social media account for the current user.
   * session_data is encrypted with AES-256-GCM before storage.
   */
  async create(userId: number, createDto: CreateAccountDto) {
    // 1. Encrypt session_data
    const plaintext = JSON.stringify(createDto.session_data);
    const encryptedSession = this.cryptoService.encrypt(plaintext);

    // 2. Build account
    const account = this.accountRepository.create({
      user_id: userId,
      platform: createDto.platform,
      account_name: createDto.account_name,
      session_data: encryptedSession,
      proxy_url: createDto.proxy_url,
      status: AccountStatus.CHECKING,
    });

    const saved = await this.accountRepository.save(account);

    // 3. Return safe response — NEVER include session_data
    return this.toResponse(saved, false);
  }

  /**
   * Get all accounts for the current user.
   * session_data is NEVER included in response.
   */
  async findAll(userId: number) {
    const accounts = await this.accountRepository.find({
      where: { user_id: userId },
      order: { created_at: 'DESC' },
    });

    return accounts.map((acc) => this.toResponse(acc, false));
  }

  /**
   * Get a single account. Verifies ownership.
   * session_data is NEVER included.
   */
  async findOne(userId: number, accountId: number) {
    const account = await this.accountRepository.findOneBy({ id: accountId });
    if (!account) {
      throw new NotFoundException('Account not found');
    }
    if (account.user_id !== userId) {
      throw new ForbiddenException('You do not own this account');
    }
    return this.toResponse(account, false);
  }

  /**
   * Update account name or platform.
   * session_data is NEVER returned.
   */
  async update(userId: number, accountId: number, updateDto: Partial<CreateAccountDto>) {
    const account = await this.accountRepository.findOneBy({ id: accountId });
    if (!account) {
      throw new NotFoundException('Account not found');
    }
    if (account.user_id !== userId) {
      throw new ForbiddenException('You do not own this account');
    }

    await this.accountRepository.update(accountId, {
      account_name: updateDto.account_name ?? account.account_name,
      platform: updateDto.platform ?? account.platform,
      proxy_url: updateDto.proxy_url ?? account.proxy_url,
    });

    const updated = await this.accountRepository.findOneBy({ id: accountId });
    return this.toResponse(updated, false);
  }

  /**
   * Update account status (internal / health check)
   * Can optionally return decrypted session for health check workers.
   */
  async updateStatus(accountId: number, status: AccountStatus, includeDecrypted = false) {
    const account = await this.accountRepository.findOneBy({ id: accountId });
    if (!account) {
      throw new NotFoundException('Account not found');
    }

    await this.accountRepository.update(accountId, {
      status,
      last_health_check: new Date(),
    });

    const updated = await this.accountRepository.findOneBy({ id: accountId });
    return this.toResponse(updated, includeDecrypted);
  }

  /**
   * Delete an account.
   */
  async remove(userId: number, accountId: number) {
    const account = await this.accountRepository.findOneBy({ id: accountId });
    if (!account) {
      throw new NotFoundException('Account not found');
    }
    if (account.user_id !== userId) {
      throw new ForbiddenException('You do not own this account');
    }

    await this.accountRepository.delete(accountId);
    return { code: 200, data: { id: accountId }, msg: 'Account deleted' };
  }

  /**
   * Internal: Get decrypted session for a health check worker.
   * NOT exposed via the public CRUD API.
   */
  async getDecryptedSession(accountId: number): Promise<Record<string, any>> {
    const account = await this.accountRepository.findOneBy({ id: accountId });
    if (!account) {
      throw new NotFoundException('Account not found');
    }
    const plaintext = this.cryptoService.decrypt(account.session_data);
    return JSON.parse(plaintext);
  }

  /**
   * Strip sensitive fields for API responses.
   * @param includeDecrypted — only true for internal health check workers
   */
  private toResponse(account: Account, includeDecrypted: boolean) {
    const response: any = {
      id: account.id,
      platform: account.platform,
      account_name: account.account_name,
      status: account.status,
      last_health_check: account.last_health_check,
      created_at: account.created_at,
      updated_at: account.updated_at,
      // user_id included only for ownership verification, safe to expose
      user_id: account.user_id,
    };

    // utils.check: NEVER include session_data in normal API responses
    if (includeDecrypted) {
      response.session_data = JSON.parse(this.cryptoService.decrypt(account.session_data));
    }

    return response;
  }
}
