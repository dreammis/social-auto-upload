import { Injectable, InternalServerErrorException } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import * as crypto from 'crypto';

/**
 * CryptoService — AES-256-GCM encryption for session_data.
 *
 * Every account stores cookies/tokens as encrypted blobs.
 * No plain-text leakage. Ever.
 */
@Injectable()
export class CryptoService {
  private readonly algorithm = 'aes-256-gcm';
  private readonly keyLength = 32; // 256 bits
  private readonly ivLength = 16;  // 128 bits (GCM recommended)
  private readonly authTagLength = 16; // 128 bits
  private readonly encryptionKey: Buffer;

  constructor(private readonly configService: ConfigService) {
    const envKey = this.configService.get<string>('ENCRYPTION_KEY');
    if (!envKey) {
      throw new InternalServerErrorException(
        'ENCRYPTION_KEY is not set in environment variables',
      );
    }

    // Accept hex-encoded key or raw string (hash to key)
    if (envKey.length >= this.keyLength * 2) {
      this.encryptionKey = Buffer.from(envKey.slice(0, this.keyLength * 2), 'hex');
    } else {
      // Derive 32-byte key from shorter string via SHA-256
      this.encryptionKey = crypto.createHash('sha256').update(envKey).digest();
    }
  }

  /**
   * Encrypt plaintext → base64-encoded ciphertext
   * Format: IV(16) + AuthTag(16) + Ciphertext
   */
  encrypt(plaintext: string): string {
    const iv = crypto.randomBytes(this.ivLength);
    const cipher = crypto.createCipheriv(this.algorithm, this.encryptionKey, iv, {
      authTagLength: this.authTagLength,
    });

    let encrypted = cipher.update(plaintext, 'utf8', 'base64');
    encrypted += cipher.final('base64');
    const authTag = cipher.getAuthTag();

    // Pack: IV + AuthTag + Ciphertext, all base64
    return Buffer.concat([
      iv,
      authTag,
      Buffer.from(encrypted, 'base64'),
    ]).toString('base64');
  }

  /**
   * Decrypt base64-encoded blob → original plaintext
   */
  decrypt(payload: string): string {
    const buffer = Buffer.from(payload, 'base64');

    const iv = buffer.subarray(0, this.ivLength);
    const authTag = buffer.subarray(
      this.ivLength,
      this.ivLength + this.authTagLength,
    );
    const ciphertext = buffer.subarray(this.ivLength + this.authTagLength);

    const decipher = crypto.createDecipheriv(this.algorithm, this.encryptionKey, iv, {
      authTagLength: this.authTagLength,
    });
    decipher.setAuthTag(authTag);

    let decrypted = decipher.update(ciphertext, undefined, 'utf8');
    decrypted += decipher.final('utf8');
    return decrypted;
  }
}
