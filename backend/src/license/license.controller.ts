import { Controller, Post, Get, Body, UseGuards, Req, HttpCode, HttpStatus, Param, Delete } from '@nestjs/common';
import { Throttle } from '@nestjs/throttler';
import { LicenseService } from './license.service';
import { CreateLicenseDto } from './dto/create-license.dto';
import { ValidateLicenseDto } from './dto/validate-license.dto';
import { Public } from '../common/decorators/public.decorator';
import { Roles } from '../common/decorators/roles.decorator';
import { JwtAuthGuard } from '../common/guards/jwt-auth.guard';
import { RolesGuard } from '../common/guards/roles.guard';
import { UserRole } from '../common/enums/role.enum';
import { CurrentUser } from '../common/decorators/current-user.decorator';

@Controller('license')
export class LicenseController {
  constructor(private readonly licenseService: LicenseService) {}

  /**
   * POST /license
   * Admin only - create new license key
   */
  @Roles(UserRole.ADMIN)
  @UseGuards(JwtAuthGuard, RolesGuard)
  @Post()
  @HttpCode(HttpStatus.CREATED)
  async create(@Body() createDto: CreateLicenseDto) {
    const result = await this.licenseService.create(createDto);
    return {
      code: 201,
      data: result,
      msg: 'License created successfully',
    };
  }

  /**
   * POST /license/validate
   * Public endpoint - validate license key against device
   * Rate limited to prevent brute force
   */
  @Public()
  @Throttle(3, 60000) // 3 req per minute
  @Post('validate')
  @HttpCode(HttpStatus.OK)
  async validate(@Body() validateDto: ValidateLicenseDto) {
    const result = await this.licenseService.validate(validateDto);
    return {
      code: 200,
      data: result,
      msg: 'License validated',
    };
  }

  /**
   * DELETE /license/:id/deactivate
   * Admin only - deactivate license
   */
  @Roles(UserRole.ADMIN)
  @UseGuards(JwtAuthGuard, RolesGuard)
  @Delete(':id/deactivate')
  @HttpCode(HttpStatus.OK)
  async deactivate(@Param('id') id: string) {
    const result = await this.licenseService.deactivate(parseInt(id));
    return {
      code: 200,
      data: result,
      msg: 'License deactivated',
    };
  }
}
