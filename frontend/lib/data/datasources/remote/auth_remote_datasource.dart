import 'package:aico_frontend/data/models/auth_model.dart';
import 'package:aico_frontend/data/models/user_model.dart';
import 'package:dio/dio.dart';

abstract class AuthRemoteDataSource {
  Future<AuthModel> authenticate(String userUuid, String pin);
  Future<bool> refreshToken(String token);
  Future<UserModel> getCurrentUser(String token);
}

class AuthRemoteDataSourceImpl implements AuthRemoteDataSource {
  final Dio _dio;

  AuthRemoteDataSourceImpl(this._dio);

  @override
  Future<AuthModel> authenticate(String userUuid, String pin) async {
    try {
      final response = await _dio.post('/auth/login', data: {
        'user_uuid': userUuid,
        'pin': pin,
      });

      if (response.statusCode == 200) {
        return AuthModel.fromJson(response.data);
      } else {
        throw Exception('Authentication failed: ${response.statusMessage}');
      }
    } on DioException catch (e) {
      throw Exception('Network error during authentication: ${e.message}');
    }
  }

  @override
  Future<bool> refreshToken(String token) async {
    try {
      final response = await _dio.post(
        '/auth/refresh',
        options: Options(headers: {'Authorization': 'Bearer $token'}),
      );

      return response.statusCode == 200;
    } on DioException catch (e) {
      throw Exception('Token refresh failed: ${e.message}');
    }
  }

  @override
  Future<UserModel> getCurrentUser(String token) async {
    try {
      final response = await _dio.get(
        '/auth/user',
        options: Options(headers: {'Authorization': 'Bearer $token'}),
      );

      if (response.statusCode == 200) {
        return UserModel.fromJson(response.data);
      } else {
        throw Exception('Failed to get user: ${response.statusMessage}');
      }
    } on DioException catch (e) {
      throw Exception('Network error getting user: ${e.message}');
    }
  }
}
