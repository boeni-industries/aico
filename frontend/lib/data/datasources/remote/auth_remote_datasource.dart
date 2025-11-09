import 'package:aico_frontend/data/models/auth_model.dart';
import 'package:aico_frontend/networking/services/resilient_api_service.dart';

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
    final responseData = await _resilientApi.executeOperation<dynamic>(
      () => _resilientApi.apiClient.post(
        '/users/authenticate',
        data: {
          'user_uuid': userUuid,
          'pin': pin,
        },
      ),
      operationName: 'User Authentication',
    );

    if (responseData != null) {
      return AuthModel.fromJson(responseData);
    }
    
    // Return null on failure - let UI handle gracefully
    return null;
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
