import 'package:aico_frontend/data/models/auth_model.dart';
import 'package:aico_frontend/networking/services/resilient_api_service.dart';

abstract class AuthRemoteDataSource {
  Future<AuthModel?> authenticate(String userUuid, String pin);
  Future<bool> refreshToken(String token);
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
  Future<bool> refreshToken(String token) async {
    final responseData = await _resilientApi.executeOperation<dynamic>(
      () => _resilientApi.apiClient.post('/users/refresh'),
      operationName: 'Token Refresh',
    );

    return responseData != null && responseData['success'] == true;
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
