import 'package:aico_frontend/data/datasources/local/auth_local_datasource.dart';
import 'package:aico_frontend/data/datasources/remote/auth_remote_datasource.dart';
import 'package:aico_frontend/domain/repositories/auth_repository.dart';

/// Clean implementation of AuthRepository using modern data sources
class AuthRepositoryImpl implements AuthRepository {
  final AuthRemoteDataSource _remoteDataSource;
  final AuthLocalDataSource _localDataSource;

  const AuthRepositoryImpl(this._remoteDataSource, this._localDataSource);

  @override
  Future<AuthResult> authenticate(String userUuid, String pin) async {
    try {
      // Authenticate with remote API
      final authModel = await _remoteDataSource.authenticate(userUuid, pin);
      
      // Convert to domain entity
      final authResult = authModel.toDomain();
      
      return authResult;
    } catch (e) {
      throw Exception('Authentication failed: $e');
    }
  }

  @override
  Future<AuthResult?> attemptAutoLogin() async {
    try {
      // Check if we have stored credentials
      final credentials = await _localDataSource.getStoredCredentials();
      if (credentials == null) return null;

      // Try to authenticate with stored credentials
      final authModel = await _remoteDataSource.authenticate(
        credentials['userUuid']!,
        credentials['pin']!,
      );
      
      return authModel.toDomain();
    } catch (e) {
      // Clear invalid credentials
      await _localDataSource.clearStoredCredentials();
      return null;
    }
  }

  @override
  Future<void> logout() async {
    await Future.wait([
      _localDataSource.clearStoredCredentials(),
      _localDataSource.clearToken(),
    ]);
  }

  @override
  Future<bool> refreshToken() async {
    try {
      final token = await _localDataSource.getToken();
      if (token == null) return false;

      final success = await _remoteDataSource.refreshToken(token);
      return success;
    } catch (e) {
      return false;
    }
  }

  @override
  Future<void> storeCredentials(String userUuid, String pin, String token) async {
    await _localDataSource.storeCredentials(userUuid, pin, token);
  }

  @override
  Future<void> clearStoredCredentials() async {
    await _localDataSource.clearStoredCredentials();
  }

  @override
  Future<bool> hasStoredCredentials() async {
    return await _localDataSource.hasStoredCredentials();
  }
}
