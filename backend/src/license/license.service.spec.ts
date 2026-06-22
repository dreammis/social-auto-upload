import { Test, TestingModule } from '@nestjs/testing';
import { getRepositoryToken } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { BadRequestException, NotFoundException, ForbiddenException } from '@nestjs/common';
import * as argon2 from 'argon2';
import { LicenseService } from './license.service';
import { LicenseCryptoService } from './license-crypto.service';
import { License } from './entities/license.entity';
import { LicenseActivation } from './entities/license-activation.entity';
import { CreateLicenseDto } from './dto/create-license.dto';
import { ValidateLicenseDto } from './dto/validate-license.dto';
import { LicenseTier } from '../common/enums/license-tier.enum';

jest.mock('argon2');

describe('LicenseService', () => {
  let service: LicenseService;
  let licenseRepository: jest.Mocked<Repository<License>>;
  let activationRepository: jest.Mocked<Repository<LicenseActivation>>;
  let cryptoService: jest.Mocked<LicenseCryptoService>;

  const mockLicense: License = {
    id: 1,
    key_hash: 'hashed_license_key',
    key_display: 'ABCD-EFGH-IJKL-MNOP',
    tier: LicenseTier.STANDARD,
    max_devices: 2,
    max_activations: 3,
    expires_at: new Date(Date.now() + 86400000 * 30),
    is_active: true,
    created_at: new Date(),
    updated_at: new Date(),
  } as License;

  const createMockRepository = () => ({
    findOne: jest.fn(),
    findOneBy: jest.fn(),
    create: jest.fn(),
    save: jest.fn(),
    count: jest.fn(),
    countBy: jest.fn(),
    update: jest.fn(),
    delete: jest.fn(),
    find: jest.fn(),
    createQueryBuilder: jest.fn(() => ({
      where: jest.fn().mockReturnThis(),
      andWhere: jest.fn().mockReturnThis(),
      leftJoinAndSelect: jest.fn().mockReturnThis(),
      getOne: jest.fn(),
      getMany: jest.fn(),
    })),
  });

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [
        LicenseService,
        {
          provide: LicenseCryptoService,
          useValue: {
            hashKey: jest.fn(),
            verifyKey: jest.fn(),
            generateDisplayKey: jest.fn().mockReturnValue('ABCD-EFGH-IJKL-MNOP'),
          },
        },
        {
          provide: getRepositoryToken(License),
          useValue: createMockRepository(),
        },
        {
          provide: getRepositoryToken(LicenseActivation),
          useValue: createMockRepository(),
        },
      ],
    }).compile();

    service = module.get<LicenseService>(LicenseService);
    licenseRepository = module.get(getRepositoryToken(License));
    activationRepository = module.get(getRepositoryToken(LicenseActivation));
    cryptoService = module.get(LicenseCryptoService);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('create', () => {
    const createDto: CreateLicenseDto = {
      tier: LicenseTier.STANDARD,
      maxDevices: 2,
      maxActivations: 3,
      expiresAt: new Date(Date.now() + 86400000 * 30).toISOString(),
    };

    it('should create license with hashed key and display key', async () => {
      cryptoService.hashKey.mockResolvedValue('hashed_license_key');
      licenseRepository.create.mockReturnValue(mockLicense);
      licenseRepository.save.mockResolvedValue(mockLicense);
      licenseRepository.findOneBy.mockResolvedValue(null);

      const result = await service.create(createDto);

      expect(cryptoService.hashKey).toHaveBeenCalled();
      expect(licenseRepository.create).toHaveBeenCalledWith(
        expect.objectContaining({
          key_hash: 'hashed_license_key',
          tier: LicenseTier.STANDARD,
          max_devices: 2,
          max_activations: 3,
        }),
      );
      expect(result).toHaveProperty('key_display');
      expect(result.key_display).toMatch(/^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$/);
    });

    it('should reject invalid tier', async () => {
      const invalidDto = { ...createDto, tier: 'invalid' as any };
      await expect(service.create(invalidDto)).rejects.toThrow(BadRequestException);
    });
  });

  describe('validate', () => {
    const validateDto: ValidateLicenseDto = {
      key: 'TEST-KEY-1234-5678',
      deviceFingerprint: 'fp_device_a',
      hwId: 'hw_device_a',
      deviceName: 'Test Device A',
    };

    it('should activate new device for valid license', async () => {
      cryptoService.hashKey.mockResolvedValue('hashed_license_key');
      licenseRepository.findOneBy.mockResolvedValue(mockLicense);
      activationRepository.findOne.mockResolvedValue(null);
      activationRepository.count.mockResolvedValue(0);
      activationRepository.create.mockReturnValue({
        license_id: 1,
        device_fingerprint: validateDto.deviceFingerprint,
        hw_id: validateDto.hwId,
        device_name: validateDto.deviceName,
      } as LicenseActivation);
      activationRepository.save.mockResolvedValue({ id: 1 } as LicenseActivation);
      licenseRepository.update.mockResolvedValue({} as any);

      const result = await service.validate(validateDto);

      expect(cryptoService.hashKey).toHaveBeenCalledWith(validateDto.key);
      expect(activationRepository.create).toHaveBeenCalledWith(
        expect.objectContaining({
          license_id: 1,
          device_fingerprint: validateDto.deviceFingerprint,
          hw_id: validateDto.hwId,
        }),
      );
      expect(result).toHaveProperty('activated', true);
      expect(result).toHaveProperty('tier', LicenseTier.STANDARD);
    });

    it('should allow re-validation from already activated device', async () => {
      cryptoService.hashKey.mockResolvedValue('hashed_license_key');
      licenseRepository.findOneBy.mockResolvedValue(mockLicense);
      activationRepository.findOne.mockResolvedValue({
        id: 1,
        license_id: 1,
        device_fingerprint: validateDto.deviceFingerprint,
        hw_id: validateDto.hwId,
        device_name: validateDto.deviceName,
        is_active: true,
        activated_at: new Date(),
        last_seen_at: new Date(),
      } as LicenseActivation);
      activationRepository.update.mockResolvedValue({} as any);

      const result = await service.validate(validateDto);

      expect(result).toHaveProperty('activated', true);
      expect(activationRepository.update).toHaveBeenCalledWith(
        1,
        expect.objectContaining({ last_seen_at: expect.any(Date) }),
      );
    });

    it('should reject license key not found', async () => {
      cryptoService.hashKey.mockResolvedValue('hashed_license_key');
      licenseRepository.findOneBy.mockResolvedValue(null);

      await expect(service.validate(validateDto)).rejects.toThrow(NotFoundException);
    });

    it('should reject inactive license', async () => {
      cryptoService.hashKey.mockResolvedValue('hashed_license_key');
      licenseRepository.findOneBy.mockResolvedValue({ ...mockLicense, is_active: false });

      await expect(service.validate(validateDto)).rejects.toThrow(ForbiddenException);
    });

    it('should reject expired license', async () => {
      cryptoService.hashKey.mockResolvedValue('hashed_license_key');
      licenseRepository.findOneBy.mockResolvedValue({
        ...mockLicense,
        expires_at: new Date(Date.now() - 1000),
      });

      await expect(service.validate(validateDto)).rejects.toThrow(ForbiddenException);
    });

    it('should reject device fingerprint mismatch when max activations reached', async () => {
      cryptoService.hashKey.mockResolvedValue('hashed_license_key');
      licenseRepository.findOneBy.mockResolvedValue(mockLicense);
      activationRepository.findOne.mockResolvedValue(null);
      activationRepository.count.mockResolvedValue(3); // max_activations reached

      await expect(service.validate(validateDto)).rejects.toThrow(ForbiddenException);
    });

    it('should reject same fingerprint with different hw_id exceeding max_devices', async () => {
      cryptoService.hashKey.mockResolvedValue('hashed_license_key');
      licenseRepository.findOneBy.mockResolvedValue(mockLicense);
      activationRepository.findOne.mockResolvedValue(null);
      activationRepository.count.mockImplementation(async (options: any) => {
        const where = options?.where || {};
        if (where.device_fingerprint === validateDto.deviceFingerprint) return 2;
        return 1;
      });

      await expect(service.validate(validateDto)).rejects.toThrow(ForbiddenException);
    });
  });

  describe('deactivate', () => {
    it('should deactivate license and all activations', async () => {
      licenseRepository.findOneBy.mockResolvedValue(mockLicense);
      licenseRepository.update.mockResolvedValue({} as any);
      activationRepository.update.mockResolvedValue({} as any);

      await service.deactivate(1);

      expect(licenseRepository.update).toHaveBeenCalledWith(
        1,
        { is_active: false, disabled_reason: 'Deactivated by admin' },
      );
      expect(activationRepository.update).toHaveBeenCalledWith(
        { license_id: 1 },
        { is_active: false },
      );
    });

    it('should throw NotFoundException for non-existent license', async () => {
      licenseRepository.findOneBy.mockResolvedValue(null);

      await expect(service.deactivate(999)).rejects.toThrow(NotFoundException);
    });
  });
});
