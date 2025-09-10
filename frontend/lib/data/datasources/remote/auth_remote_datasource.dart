import 'package:aico_frontend/data/models/auth_model.dart';
import 'package:aico_frontend/data/models/user_model.dart';
import 'package:aico_frontend/networking/clients/unified_api_client.dart';

abstract class AuthRemoteDataSource {
  Future<AuthModel> authenticate(String userUuid, String pin);
  Future<bool> refreshToken(String token);
  Future<UserModel> getCurrentUser(String token);
}

class AuthRemoteDataSourceImpl implements AuthRemoteDataSource {
  final UnifiedApiClient _apiClient;

  AuthRemoteDataSourceImpl(this._apiClient);

  @override
  Future<AuthModel> authenticate(String userUuid, String pin) async {
    try {
      final responseData = await _apiClient.post<Map<String, dynamic>>(
        '/users/authenticate',
        data: {
          'user_uuid': userUuid,
          'pin': pin,
        },
        fromJson: (json) => json,
      );

      if (responseData != null) {
        return AuthModel.fromJson(responseData);
      } else {
        throw Exception('Authentication failed: No response data');
      }
    } catch (e) {
      throw Exception('Network error during authentication: ${e.toString()}');
    }
  }

  @override
  Future<bool> refreshToken(String token) async {
    try {
      final responseData = await _apiClient.post<Map<String, dynamic>>(
        '/auth/refresh',
        fromJson: (json) => json,
      );

      return responseData != null;
    } catch (e) {
      throw Exception('Token refresh failed: ${e.toString()}');
    }
  }

  @override
  Future<UserModel> getCurrentUser(String token) async {
    try {
      final responseData = await _apiClient.get<Map<String, dynamic>>(
        '/auth/user',
        fromJson: (json) => json,
      );

      if (responseData != null) {
        return UserModel.fromJson(responseData);
      } else {
        throw Exception('Failed to get user: No response data');
      }
    } catch (e) {
      throw Exception('Network error getting user: ${e.toString()}');
    }
  }
}
