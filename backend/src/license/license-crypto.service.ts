import { Injectable } from '@nestjs/common';
import * as argon2 from 'argon2';
import { ARGON2_OPTIONS } from '../auth/constants';

@Injectable()
export class LicenseCryptoService {
  /**
   * Hash license key with argon2 for secure storage
   */
  async hashKey(key: string): Promise<string> {
    return argon2.hash(key, ARGON2_OPTIONS);
  }

  /**
   * Verify provided key against stored hash
   */
  async verifyKey(key: string, hash: string): Promise<boolean> {
    try {
      return await argon2.verify(hash, key);
    } catch {
      return false;
    }
  }

  /**
   * Generate display key (first 4 + last 4 chars for admin lookup)
   * Format: XXXX-...-XXXX
   */
  generateDisplayKey(key: string): string {
    const cleaned = key.replace(/[^A-Z0-9]/gi, '').toUpperCase();
    if (cleaned.length >= 8) {
      return `${cleaned.slice(0, 4)}-${cleaned.slice(-4)}`;
    }
    return cleaned;
  }
}
