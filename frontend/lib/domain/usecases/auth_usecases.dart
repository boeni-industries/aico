import 'package:aico_frontend/domain/repositories/auth_repository.dart';
import 'package:flutter/foundation.dart';

/// Use case for user authentication
class LoginUseCase {
  final AuthRepository _authRepository;

  const LoginUseCase(this._authRepository);

  Future<AuthResult> execute(String userUuid, String pin, {bool rememberMe = false}) async {
    debugPrint('LoginUseCase: Authenticating user - userUuid: $userUuid, rememberMe: $rememberMe');
    final result = await _authRepository.authenticate(userUuid, pin);
    
    if (rememberMe) {
      debugPrint('LoginUseCase: Storing credentials - userUuid: $userUuid, token: ${result.token.isNotEmpty ? "PROVIDED" : "EMPTY"}');
      await _authRepository.storeCredentials(userUuid, pin, result.token);
    }
    
    return result;
  }
}

/// Use case for automatic login with stored credentials
class AutoLoginUseCase {
  final AuthRepository _authRepository;

  const AutoLoginUseCase(this._authRepository);

  Future<AuthResult?> execute() async {
    return await _authRepository.attemptAutoLogin();
  }
}

/// Use case for user logout
class LogoutUseCase {
  final AuthRepository _authRepository;

  const LogoutUseCase(this._authRepository);

  Future<void> execute() async {
    await _authRepository.logout();
  }
}

/// Use case for token refresh
class RefreshTokenUseCase {
  final AuthRepository _authRepository;

  const RefreshTokenUseCase(this._authRepository);

  Future<bool> execute() async {
    return await _authRepository.refreshToken();
  }
}

/// Use case for checking if user has stored credentials
class CheckAuthStatusUseCase {
  final AuthRepository _authRepository;

  const CheckAuthStatusUseCase(this._authRepository);

  Future<bool> execute() async {
    return await _authRepository.hasStoredCredentials();
  }
}
