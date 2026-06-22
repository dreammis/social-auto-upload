import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { LicenseService } from './license.service';
import { LicenseController } from './license.controller';
import { License } from './entities/license.entity';
import { LicenseActivation } from './entities/license-activation.entity';
import { LicenseCryptoService } from './license-crypto.service';

@Module({
  imports: [
    TypeOrmModule.forFeature([License, LicenseActivation]),
  ],
  providers: [LicenseService, LicenseCryptoService],
  controllers: [LicenseController],
  exports: [LicenseService],
})
export class LicenseModule {}
