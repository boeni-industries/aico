import { httpJson } from './http';

export interface UserDto {
  uuid: string;
  full_name: string;
  nickname?: string | null;
  user_type: string;
  is_active: boolean;
  primary_language?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface AuthenticationRequestDto {
  user_uuid: string;
  pin: string;
}

export interface AuthenticationResponseDto {
  success: boolean;
  user?: UserDto;
  jwt_token?: string;
  refresh_token?: string;
  last_login?: string | null;
  error?: string;
}

export async function authenticateUser(
  payload: AuthenticationRequestDto,
): Promise<AuthenticationResponseDto> {
  return httpJson<AuthenticationResponseDto>({
    method: 'POST',
    path: '/users/authenticate',
    body: payload,
  });
}

export async function refreshToken(refreshToken: string): Promise<AuthenticationResponseDto> {
  return httpJson<AuthenticationResponseDto>({
    method: 'POST',
    path: '/users/refresh',
    body: { refresh_token: refreshToken },
  });
}

export async function fetchUserProfile(userUuid: string): Promise<UserDto> {
  return httpJson<UserDto>({
    method: 'GET',
    path: `/users/${userUuid}`,
  });
}
