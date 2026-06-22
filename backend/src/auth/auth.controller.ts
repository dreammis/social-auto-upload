import { Controller, Post, Get, Body, UseGuards, Req, HttpCode, HttpStatus } from '@nestjs/common';
import { Throttle } from '@nestjs/throttler';
import { AuthService } from './auth.service';
import { RegisterDto } from './dto/register.dto';
import { LoginDto } from './dto/login.dto';
import { RefreshTokenDto } from './dto/refresh-token.dto';
import { Public } from '../common/decorators/public.decorator';
import { CurrentUser } from '../common/decorators/current-user.decorator';

@Controller('auth')
export class AuthController {
  constructor(private readonly authService: AuthService) {}

  /**
   * POST /auth/register
   * Public endpoint - no authentication required
   * Rate limited by global throttler (default: 10 req/15s)
   */
  @Public()
  @Post('register')
  @HttpCode(HttpStatus.CREATED)
  async register(@Body() registerDto: RegisterDto) {
    const result = await this.authService.register(registerDto);
    return {
      code: 201,
      data: result,
      msg: 'User registered successfully',
    };
  }

  /**
   * POST /auth/login
   * Public endpoint - no authentication required
   * Rate limited: 5 attempts per 15 minutes
   * Replaces any previous login sessions (single-session per user)
   */
  @Public()
  @Post('login')
  @Throttle(5, 900000) // 5 req per 15 min (900000ms)
  @HttpCode(HttpStatus.CREATED)
  async login(@Body() loginDto: LoginDto) {
    const result = await this.authService.login(loginDto);
    return {
      code: 201,
      data: result,
      msg: 'Login successful',
    };
  }

  /**
   * POST /auth/refresh
   * Public endpoint - uses refresh token instead of access token
   * No rate limit (token rotation provides protection)
   * Implements token rotation: old token marked revoked, new token issued
   * Detects replay attacks: if token already replaced, revokes all user tokens
   */
  @Public()
  @Post('refresh')
  @HttpCode(HttpStatus.CREATED)
  async refresh(@Body() refreshTokenDto: RefreshTokenDto) {
    const result = await this.authService.refresh(refreshTokenDto);
    return {
      code: 201,
      data: result,
      msg: 'Token refreshed successfully',
    };
  }

  /**
   * POST /auth/logout
   * Protected endpoint - requires valid access token
   */
  @Post('logout')
  @HttpCode(HttpStatus.OK)
  async logout(@CurrentUser() user: any) {
    await this.authService.logout(user.sub);
    return {
      code: 200,
      data: null,
      msg: 'Logged out successfully',
    };
  }

  /**
   * GET /auth/me
   * Protected endpoint - requires valid access token
   * Returns current user WITHOUT password_hash (enforced by @Exclude decorator)
   */
  @Get('me')
  @HttpCode(HttpStatus.OK)
  async getMe(@CurrentUser() user: any) {
    const result = await this.authService.getMe(user.sub);
    return {
      code: 200,
      data: result,
      msg: 'User info retrieved',
    };
  }
}
