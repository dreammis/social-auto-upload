import { IsEnum, IsInt, IsOptional, IsDateString, Min } from 'class-validator';
import { LicenseTier } from '../../common/enums/license-tier.enum';

export class CreateLicenseDto {
  @IsEnum(LicenseTier)
  tier: LicenseTier;

  @IsInt()
  @Min(1)
  maxDevices: number;

  @IsInt()
  @Min(1)
  maxActivations: number;

  @IsOptional()
  @IsDateString()
  expiresAt?: string;
}
