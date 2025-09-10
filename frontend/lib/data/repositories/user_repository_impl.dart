import 'package:aico_frontend/domain/entities/user.dart';
import 'package:aico_frontend/domain/repositories/user_repository.dart';
import 'package:aico_frontend/networking/models/user_models.dart' as NetworkingModels;
import 'package:aico_frontend/networking/services/user_service.dart';

/// Clean architecture implementation of UserRepository using networking services
class UserDataRepository implements UserRepository {
  final ApiUserService _apiUserService;

  const UserDataRepository(this._apiUserService);

  @override
  Future<User?> getCurrentUser() async {
    try {
      final networkingUser = await _apiUserService.getCurrentUserFromToken();
      return networkingUser != null ? _convertNetworkingUserToDomainUser(networkingUser) : null;
    } catch (e) {
      if (e is UnimplementedError) {
        rethrow; // Preserve UnimplementedError for WIP features
      }
      // Network or other errors should return null for graceful degradation
      return null;
    }
  }

  @override
  Future<User?> getUserById(String id) async {
    try {
      final networkingUser = await _apiUserService.getUser(id);
      return _convertNetworkingUserToDomainUser(networkingUser);
    } catch (e) {
      if (e is UnimplementedError) {
        rethrow; // Preserve UnimplementedError for WIP features
      }
      // Network or other errors should return null for graceful degradation
      return null;
    }
  }

  @override
  Future<User> updateUser(User user) async {
    try {
      // Convert domain User to networking UpdateUserRequest
      final updateRequest = NetworkingModels.UpdateUserRequest(
        fullName: user.username, // Using username as fullName for now
        nickname: user.username,
        userType: _convertRoleToUserType(user.role),
      );
      
      final updatedNetworkingUser = await _apiUserService.updateUser(user.id, updateRequest);
      return _convertNetworkingUserToDomainUser(updatedNetworkingUser);
    } catch (e) {
      if (e is UnimplementedError) {
        rethrow; // Preserve UnimplementedError for WIP features
      }
      // Re-throw other exceptions for proper error handling
      rethrow;
    }
  }

  @override
  Future<void> deleteUser(String id) async {
    await _apiUserService.deleteUser(id);
  }

  @override
  Future<List<User>> getAllUsers({
    int? limit,
    int? offset,
    String? search,
  }) async {
    try {
      final networkingUsers = await _apiUserService.getUsers(
        limit: limit ?? 100,
      );
      return networkingUsers.map(_convertNetworkingUserToDomainUser).toList();
    } catch (e) {
      return [];
    }
  }

  @override
  Future<bool> isUsernameAvailable(String username) async {
    try {
      return await _apiUserService.checkUsernameAvailability(username);
    } catch (e) {
      if (e is UnimplementedError) {
        rethrow; // Preserve UnimplementedError for WIP features
      }
      // Network errors should be treated as unavailable for safety
      return false;
    }
  }

  @override
  Future<bool> isEmailAvailable(String email) async {
    try {
      return await _apiUserService.checkEmailAvailability(email);
    } catch (e) {
      if (e is UnimplementedError) {
        rethrow; // Preserve UnimplementedError for WIP features
      }
      // Network errors should be treated as unavailable for safety
      return false;
    }
  }

  /// Converts networking layer User model to domain layer User entity
  User _convertNetworkingUserToDomainUser(NetworkingModels.User networkingUser) {
    return User(
      id: networkingUser.uuid,
      username: networkingUser.nickname, // networking uses nickname as username
      email: '', // networking model doesn't have email field
      role: _convertUserTypeToRole(networkingUser.userType),
      createdAt: networkingUser.createdAt,
      lastLoginAt: null, // not available in networking model
      isActive: networkingUser.isActive ?? true,
    );
  }

  /// Converts networking userType string to domain UserRole enum
  UserRole _convertUserTypeToRole(String userType) {
    switch (userType.toLowerCase()) {
      case 'admin':
        return UserRole.admin;
      case 'superadmin':
      case 'super_admin':
        return UserRole.superAdmin;
      default:
        return UserRole.user;
    }
  }

  /// Converts domain UserRole enum to networking userType string
  String _convertRoleToUserType(UserRole role) {
    switch (role) {
      case UserRole.admin:
        return 'admin';
      case UserRole.superAdmin:
        return 'superadmin';
      case UserRole.user:
        return 'user';
    }
  }
}
