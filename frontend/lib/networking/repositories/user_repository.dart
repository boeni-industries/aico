import 'package:aico_frontend/networking/clients/api_client.dart';
import 'package:aico_frontend/networking/models/error_models.dart';
import 'package:aico_frontend/networking/models/user_models.dart';
import 'package:aico_frontend/networking/services/offline_queue.dart';

abstract class UserRepository {
  Future<List<User>> getUsers({String? userType, int limit = 100});
  Future<User> createUser(CreateUserRequest request);
  Future<User> getUser(String uuid);
  Future<User> updateUser(String uuid, UpdateUserRequest request);
  Future<void> deleteUser(String uuid);
  Future<AuthenticationResponse> authenticate(AuthenticateRequest request);
}

class ApiUserRepository implements UserRepository {
  final AicoApiClient _apiClient;
  final OfflineQueue _offlineQueue;

  ApiUserRepository(this._apiClient, this._offlineQueue);

  @override
  Future<List<User>> getUsers({String? userType, int limit = 100}) async {
    try {
      final response = await _apiClient.getUsers(
        userType: userType,
        limit: limit,
      );
      return response.users;
    } catch (e) {
      if (e is NetworkException) {
        // For read operations, we could return cached data if available
        // For now, just rethrow the error
        rethrow;
      }
      throw ConnectionException('Failed to get users: $e');
    }
  }

  @override
  Future<User> createUser(CreateUserRequest request) async {
    try {
      return await _apiClient.createUser(request);
    } catch (e) {
      if (e is NetworkException) {
        // Queue for offline execution and return optimistic result
        final operation = CreateUserOperation(
          id: DateTime.now().millisecondsSinceEpoch.toString(),
          data: request.toJson(),
          createdAt: DateTime.now(),
        );
        _offlineQueue.add(operation);
        
        // Return optimistic user object
        return User(
          uuid: 'pending-${operation.id}',
          fullName: request.fullName,
          nickname: request.nickname,
          userType: request.userType,
          pin: request.pin,
          createdAt: DateTime.now(),
          updatedAt: DateTime.now(),
        );
      }
      throw ConnectionException('Failed to create user: $e');
    }
  }

  @override
  Future<User> getUser(String uuid) async {
    try {
      return await _apiClient.getUser(uuid);
    } catch (e) {
      if (e is NetworkException) {
        rethrow;
      }
      throw ConnectionException('Failed to get user: $e');
    }
  }

  @override
  Future<User> updateUser(String uuid, UpdateUserRequest request) async {
    try {
      return await _apiClient.updateUser(uuid, request);
    } catch (e) {
      if (e is NetworkException) {
        // TODO: Implement offline update operation
        rethrow;
      }
      throw ConnectionException('Failed to update user: $e');
    }
  }

  @override
  Future<void> deleteUser(String uuid) async {
    try {
      await _apiClient.deleteUser(uuid);
    } catch (e) {
      if (e is NetworkException) {
        // TODO: Implement offline delete operation
        rethrow;
      }
      throw ConnectionException('Failed to delete user: $e');
    }
  }

  @override
  Future<AuthenticationResponse> authenticate(AuthenticateRequest request) async {
    try {
      return await _apiClient.authenticate(request);
    } catch (e) {
      if (e is NetworkException) {
        // Authentication cannot be done offline
        rethrow;
      }
      throw ConnectionException('Failed to authenticate: $e');
    }
  }
}
