import 'package:aico_frontend/data/models/auth_model.dart';
import 'package:aico_frontend/networking/services/resilient_api_service.dart';
import 'package:flutter/foundation.dart';

abstract class AuthRemoteDataSource {
  Future<AuthModel?> authenticate(String userUuid, String pin);
  Future<AuthModel?> refreshToken(String refreshToken);
  Future<Map<String, dynamic>?> getCurrentUser(String token);
}

class AuthRemoteDataSourceImpl implements AuthRemoteDataSource {
  final ResilientApiService _resilientApi;

  AuthRemoteDataSourceImpl(this._resilientApi);

  @override
  Future<AuthModel?> authenticate(String userUuid, String pin) async {
    try {
      debugPrint('🔐 [AuthRemoteDataSource] Starting authentication for user: $userUuid');
      debugPrint('🔐 [AuthRemoteDataSource] Calling executeOperation...');
      
      final responseData = await _resilientApi.executeOperation<dynamic>(
        () {
          debugPrint('🔐 [AuthRemoteDataSource] Inside operation callback, calling apiClient.request with skipTokenEntirely...');
          // Use request() with skipTokenEntirely=true to bypass ALL token operations
          return _resilientApi.apiClient.request(
            'POST',
            '/users/authenticate',
            data: {
              'user_uuid': userUuid,
              'pin': pin,
            },
            skipTokenEntirely: true, // CRITICAL: Skip ALL token operations during authentication!
          );
        },
        operationName: 'User Authentication',
      ).timeout(
        const Duration(seconds: 10),
        onTimeout: () {
          debugPrint('❌ [AuthRemoteDataSource] Authentication request timed out after 10s');
          return null;
        },
      );

      debugPrint('🔐 [AuthRemoteDataSource] executeOperation completed, responseData: ${responseData != null ? "received" : "null"}');

      if (responseData != null) {
        debugPrint('✅ [AuthRemoteDataSource] Authentication successful, parsing response...');
        return AuthModel.fromJson(responseData);
      }
      
      debugPrint('⚠️ [AuthRemoteDataSource] Authentication failed - null response');
      // Return null on failure - let UI handle gracefully
      return null;
    } catch (e) {
      debugPrint('❌ [AuthRemoteDataSource] Authentication failed with error: $e');
      debugPrint('❌ [AuthRemoteDataSource] Error type: ${e.runtimeType}');
      return null;
    }
  }

  @override
  Future<AuthModel?> refreshToken(String refreshToken) async {
    // Temporarily store refresh token for this request
    // The API client will use it in the Authorization header
    final responseData = await _resilientApi.executeOperation<dynamic>(
      () => _resilientApi.apiClient.request(
        'POST',
        '/users/refresh',
        data: {'refresh_token': refreshToken},
      ),
      operationName: 'Token Refresh',
    );

    if (responseData != null && responseData['success'] == true) {
      return AuthModel.fromJson(responseData);
    }
    
    return null;
  }

  @override
  Future<Map<String, dynamic>?> getCurrentUser(String token) async {
    final responseData = await _resilientApi.executeOperation<dynamic>(
      () => _resilientApi.apiClient.get('/users/me'),
      operationName: 'Get Current User',
    );

    return responseData as Map<String, dynamic>?;
  }
}
