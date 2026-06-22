import { IsEnum } from 'class-validator';
import { AccountStatus } from '../enums/account-status.enum';

export class UpdateAccountStatusDto {
  @IsEnum(AccountStatus, { message: 'status must be one of: active, dead, checking' })
  status: AccountStatus;
}
