import { IsEnum, IsOptional, IsString, IsUrl, MaxLength } from 'class-validator';
import { Platform } from '../enums/platform.enum';

export class CreateAccountDto {
  @IsEnum(Platform, { message: 'platform must be one of: tiktok, facebook, youtube, instagram, shopee' })
  platform: Platform;

  @IsString()
  @MaxLength(200)
  account_name: string;

  /**
   * Accept raw session_data as any JSON-serializable object.
   * The service will stringify and encrypt before storing.
   */
  session_data: Record<string, any>;

  @IsOptional()
  @IsString()
  @IsUrl({ require_tld: false, require_protocol: true }, { message: 'proxy_url must be a valid URL with protocol' })
  @MaxLength(500)
  proxy_url?: string;
}
