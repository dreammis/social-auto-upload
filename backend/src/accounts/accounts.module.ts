import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { AccountsService } from './accounts.service';
import { AccountsController } from './accounts.controller';
import { Account } from './entities/account.entity';
import { CryptoService } from '../common/crypto/crypto.service';

@Module({
  imports: [TypeOrmModule.forFeature([Account])],
  providers: [AccountsService, CryptoService],
  controllers: [AccountsController],
  exports: [AccountsService],
})
export class AccountsModule {}
