import 'package:aico_frontend/data/models/user_model.dart';
import 'package:aico_frontend/networking/clients/unified_api_client.dart';

/// Remote data source for user operations via API
class RemoteUserDataSource {
  final UnifiedApiClient _apiClient;

  const RemoteUserDataSource(this._apiClient);

  Future<UserModel?> getCurrentUser() async {
    try {
      final response = await _apiClient.request<Map<String, dynamic>>(
        'GET',
        '/auth/me',
        fromJson: (json) => json,
      );
      
      if (response != null) {
        return UserModel.fromJson(response);
      }
      return null;
    } catch (e) {
      throw Exception('Failed to get current user: $e');
    }
  }

  Future<UserModel?> getUserById(String id) async {
    try {
      final response = await _apiClient.request<Map<String, dynamic>>(
        'GET',
        '/users/$id',
        fromJson: (json) => json,
      );
      
      if (response != null) {
        return UserModel.fromJson(response);
      }
      return null;
    } catch (e) {
      throw Exception('Failed to get user by ID: $e');
    }
  }

  Future<UserModel> updateUser(UserModel user) async {
    try {
      final response = await _apiClient.request<Map<String, dynamic>>(
        'PUT',
        '/users/${user.id}',
        data: user.toJson(),
        fromJson: (json) => json,
      );
      
      if (response != null) {
        return UserModel.fromJson(response);
      }
      throw Exception('Invalid response from server');
    } catch (e) {
      throw Exception('Failed to update user: $e');
    }
  }

  Future<void> deleteUser(String id) async {
    try {
      await _apiClient.request<void>(
        'DELETE',
        '/users/$id',
      );
    } catch (e) {
      throw Exception('Failed to delete user: $e');
    }
  }

  Future<List<UserModel>> getAllUsers({
    int? limit,
    int? offset,
    String? search,
  }) async {
    try {
      final queryParams = <String, dynamic>{};
      if (limit != null) queryParams['limit'] = limit;
      if (offset != null) queryParams['offset'] = offset;
      if (search != null && search.isNotEmpty) queryParams['search'] = search;

      final response = await _apiClient.request<Map<String, dynamic>>(
        'GET',
        '/users',
        data: queryParams,
        fromJson: (json) => json,
      );
      
      if (response != null && response['users'] is List) {
        final usersList = response['users'] as List;
        return usersList
            .map((json) => UserModel.fromJson(json as Map<String, dynamic>))
            .toList();
      }
      return [];
    } catch (e) {
      throw Exception('Failed to get all users: $e');
    }
  }

  Future<bool> isUsernameAvailable(String username) async {
    try {
      final response = await _apiClient.request<Map<String, dynamic>>(
        'GET',
        '/users/check-username',
        data: {'username': username},
        fromJson: (json) => json,
      );
      
      return response?['available'] as bool? ?? false;
    } catch (e) {
      throw Exception('Failed to check username availability: $e');
    }
  }

  Future<bool> isEmailAvailable(String email) async {
    try {
      final response = await _apiClient.request<Map<String, dynamic>>(
        'GET',
        '/users/check-email',
        data: {'email': email},
        fromJson: (json) => json,
      );
      
      return response?['available'] as bool? ?? false;
    } catch (e) {
      throw Exception('Failed to check email availability: $e');
    }
  }
}
