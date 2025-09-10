import 'package:aico_frontend/core/services/api_service.dart';
import 'package:aico_frontend/networking/models/user_models.dart';
import 'package:aico_frontend/networking/services/secure_credential_manager.dart';
import 'package:aico_frontend/networking/services/token_manager.dart';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

/// API service for user operations - NOT a repository interface
class ApiUserService {
  final ApiService _apiService;
  final TokenManager _tokenManager;
  final SecureCredentialManager _credentialManager;

  ApiUserService({
    required ApiService apiService,
    required TokenManager tokenManager,
  })  : _apiService = apiService,
        _tokenManager = tokenManager,
        _credentialManager = SecureCredentialManager();

  Future<List<User>> getUsers({String? userType, int limit = 100}) async {
    try {
      final response = await _apiService.getUsers(userType: userType, limit: limit);
      return response.users;
    } catch (e) {
      if (e is DioException) {
        throw Exception('Network error: ${e.message}');
      }
      throw Exception('Failed to fetch users: $e');
    }
  }

  Future<User> createUser(CreateUserRequest request) async {
    try {
      return await _apiService.createUser(request);
    } catch (e) {
      if (e is DioException) {
        throw Exception('Network error: ${e.message}');
      }
      throw Exception('Failed to create user: $e');
    }
  }

  Future<User> getUser(String uuid) async {
    try {
      return await _apiService.getUser(uuid);
    } catch (e) {
      if (e is DioException) {
        throw Exception('Network error: ${e.message}');
      }
      throw Exception('Failed to fetch user: $e');
    }
  }

  Future<User> updateUser(String uuid, UpdateUserRequest request) async {
    try {
      return await _apiService.updateUser(uuid, request);
    } catch (e) {
      if (e is DioException) {
        throw Exception('Network error: ${e.message}');
      }
      throw Exception('Failed to update user: $e');
    }
  }

  Future<void> deleteUser(String uuid) async {
    try {
      await _apiService.deleteUser(uuid);
    } catch (e) {
      if (e is DioException) {
        throw Exception('Network error: ${e.message}');
      }
      throw Exception('Failed to delete user: $e');
    }
  }

  /// Attempts auto-login using stored credentials
  Future<AuthenticationResponse?> attemptAutoLogin() async {
    try {
      // First, check if we have a valid token
      final validToken = await _tokenManager.getValidToken();
      if (validToken != null) {
        debugPrint('UserRepository: Found valid token, attempting token-based auto-login');
        // TODO: Get user info from token or make a lightweight API call
        // For now, we need credentials for full user data
      }
      
      // Try to re-authenticate with stored credentials
      final credentials = await _credentialManager.getStoredCredentials();
      if (credentials != null) {
        final userUuid = credentials['userUuid'];
        final pin = credentials['pin'];
        
        if (userUuid != null && pin != null) {
          debugPrint('UserRepository: Auto-login using stored credentials for user: $userUuid');
          
          final request = AuthenticateRequest(
            uuid: userUuid,
            pin: pin,
          );
          
          final response = await authenticate(request);
          
          // Store the new token with proper expiry
          if (response.token != null) {
            final expiryTime = DateTime.now().add(const Duration(minutes: 15));
            await _tokenManager.storeTokens(
              accessToken: response.token!,
              expiresAt: expiryTime,
            );
          }
          
          return response;
        }
      }

      return null; // No stored credentials available
    } catch (e) {
      debugPrint('UserRepository: Auto-login failed: $e');
      // Clear invalid credentials on authentication failure
      await clearStoredCredentials();
      return null;
    }
  }

  /// Stores credentials securely after successful authentication
  Future<void> storeCredentials(String userUuid, String pin, String token) async {
    await _credentialManager.storeCredentials(userUuid, pin);
    final expiryTime = DateTime.now().add(const Duration(minutes: 15));
    await _tokenManager.storeTokens(
      accessToken: token,
      expiresAt: expiryTime,
    );
  }

  /// Clears stored credentials and tokens
  Future<void> clearStoredCredentials() async {
    await _credentialManager.clearCredentials();
    await _tokenManager.clearTokens();
  }

  /// Refreshes the current token using stored credentials
  Future<String?> refreshToken() async {
    try {
      final credentials = await _credentialManager.getStoredCredentials();
      if (credentials == null) return null;

      final userUuid = credentials['userUuid'];
      final pin = credentials['pin'];
      
      if (userUuid != null && pin != null) {
        final request = AuthenticateRequest(
          uuid: userUuid,
          pin: pin,
        );
        
        final response = await authenticate(request);
        if (response.token != null) {
          final expiryTime = DateTime.now().add(const Duration(minutes: 15));
          await _tokenManager.storeTokens(
            accessToken: response.token!,
            expiresAt: expiryTime,
          );
          return response.token;
        }
      }
      
      return null;
    } catch (e) {
      await clearStoredCredentials();
      return null;
    }
  }

  Future<void> initializeEncryption() async {
    await _apiService.initialize();
  }

  Future<AuthenticationResponse> authenticate(AuthenticateRequest request) async {
    debugPrint('UserRepository: Starting authentication for user UUID: ${request.uuid}');
    debugPrint('UserRepository: Authentication request - PIN provided: ${request.pin.isNotEmpty}');
    
    try {
      debugPrint('UserRepository: Calling API client authenticate method');
      final response = await _apiService.authenticate(request);
      
      debugPrint('UserRepository: Authentication API call successful');
      debugPrint('UserRepository: Response success: ${response.success}');
      debugPrint('UserRepository: Response error: ${response.error ?? "none"}');
      debugPrint('UserRepository: JWT token provided: ${response.token?.isNotEmpty ?? false}');
      debugPrint('UserRepository: User data provided: ${response.user != null}');
      debugPrint('UserRepository: Last login: ${response.lastLogin?.toString() ?? "not provided"}');
      
      if (response.user != null) {
        debugPrint('UserRepository: Authenticated user - UUID: ${response.user!.uuid}, Name: ${response.user!.fullName}');
      }
      
      return response;
    } catch (e) {
      debugPrint('UserRepository: Authentication failed with exception: $e');
      debugPrint('UserRepository: Exception type: ${e.runtimeType}');
      
      if (e is DioException) {
        // Handle specific HTTP status codes
        if (e.response?.statusCode == 401) {
          throw Exception('Invalid credentials');
        } else if (e.response?.statusCode == 403) {
          throw Exception('Access denied');
        } else if (e.response?.statusCode == 429) {
          throw Exception('Too many attempts');
        } else if (e.response?.statusCode == 500) {
          throw Exception('Server error');
        } else {
          throw Exception('Network error: ${e.message}');
        }
      }
      throw Exception('Authentication failed: $e');
    }
  }
}
