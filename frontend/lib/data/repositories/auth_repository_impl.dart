import 'package:aico_frontend/data/datasources/local/auth_local_datasource.dart';
import 'package:aico_frontend/data/datasources/remote/auth_remote_datasource.dart';
import 'package:aico_frontend/domain/entities/user.dart';
import 'package:aico_frontend/domain/repositories/auth_repository.dart';
import 'package:flutter/foundation.dart';

/// Clean implementation of AuthRepository using modern data sources
class AuthRepositoryImpl implements AuthRepository {
  final AuthRemoteDataSource _remoteDataSource;
  final AuthLocalDataSource _localDataSource;

  const AuthRepositoryImpl(this._remoteDataSource, this._localDataSource);

  @override
  Future<AuthResult> authenticate(String userUuid, String pin) async {
    // Authenticate with remote API - returns null on failure
    final authModel = await _remoteDataSource.authenticate(userUuid, pin);
    
    if (authModel == null) {
      throw Exception('Authentication failed: Backend unavailable or invalid credentials');
    }
    
    // Convert to domain entity
    final authResult = authModel.toDomain();
    
    return authResult;
  }

  @override
  Future<AuthResult?> attemptAutoLogin() async {
    try {
      // Check if we have stored credentials
      final credentials = await _localDataSource.getStoredCredentials();
      
      if (credentials == null) {
        debugPrint('AuthRepository: No stored credentials found');
        return null;
      }

      // Check if we have a valid token - if so, use it directly
      if (credentials.containsKey('token')) {
        debugPrint('AuthRepository: Valid token found, using direct authentication');
        try {
          // Create auth result from stored token without network call
          final authResult = AuthResult(
            user: User(
              id: credentials['userUuid']!,
              username: credentials['userUuid']!, // Use UUID as username for now
              email: '${credentials['userUuid']!}@aico.local', // Placeholder email
              role: UserRole.user,
              createdAt: DateTime.now(),
            ),
            token: credentials['token']!,
          );
          return authResult;
        } catch (e) {
          debugPrint('AuthRepository: Failed to create auth result from token: $e');
          // Fall through to re-authentication
        }
      }

      // No valid token - need to re-authenticate with stored credentials
      debugPrint('AuthRepository: No valid token, re-authenticating with stored credentials');
      final authModel = await _remoteDataSource.authenticate(
        credentials['userUuid']!,
        credentials['pin']!,
      );
      
      if (authModel == null) {
        // Backend unavailable - don't clear credentials, just return null
        debugPrint('AuthRepository: Re-authentication failed - backend unavailable');
        return null;
      }
      
      final authResult = authModel.toDomain();
      
      // Store the new token from the authentication response
      debugPrint('AuthRepository: Re-authentication successful, storing new token');
      await _localDataSource.storeToken(authResult.token);
      
      return authResult;
    } catch (e) {
      debugPrint('AuthRepository: Auto-login failed with error: $e');
      // Only clear credentials on authentication failure (401), not on network errors
      if (e.toString().contains('401') || e.toString().contains('Unauthorized')) {
        debugPrint('AuthRepository: Clearing invalid credentials due to 401');
        await _localDataSource.clearStoredCredentials();
      }
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
