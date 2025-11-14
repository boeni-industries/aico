import 'package:aico_frontend/domain/entities/user.dart';

/// Authentication result containing user and token information
class AuthResult {
  final User user;
  final String token;
  final String? refreshToken;
  final DateTime? lastLogin;

  const AuthResult({
    required this.user,
    required this.token,
    this.refreshToken,
    this.lastLogin,
  });
}

/// Abstract repository interface for authentication operations
abstract class AuthRepository {
  /// Authenticate user with UUID and PIN
  Future<AuthResult> authenticate(String userUuid, String pin);
  
  /// Attempt automatic login with stored credentials
  Future<AuthResult?> attemptAutoLogin();
  
  /// Logout and clear stored credentials
  Future<void> logout();
  
  /// Refresh authentication token
  Future<bool> refreshToken();
  
  /// Store credentials for auto-login (remember me)
  Future<void> storeCredentials(String userUuid, String pin, String token);
  
  /// Clear stored credentials
  Future<void> clearStoredCredentials();
  
  /// Check if user has stored credentials for auto-login
  Future<bool> hasStoredCredentials();
}
