import 'package:aico_frontend/domain/entities/user.dart';
import 'package:aico_frontend/domain/repositories/user_repository.dart';
import 'package:aico_frontend/networking/repositories/user_repository.dart';
import 'package:aico_frontend/networking/models/user_models.dart' as NetworkingModels;

/// Clean architecture implementation of UserRepository using networking services
class UserDataRepository implements UserRepository {
  final ApiUserService _apiUserService;

  const UserDataRepository(this._apiUserService);

  @override
  Future<User?> getCurrentUser() async {
    // For now, return null - this would need to be implemented based on authentication state
    // The networking layer doesn't have a direct getCurrentUser method
    return null;
  }

  @override
  Future<User?> getUserById(String id) async {
    try {
      final networkingUser = await _apiUserService.getUser(id);
      return _convertNetworkingUserToDomainUser(networkingUser);
    } catch (e) {
      return null;
    }
  }

  @override
  Future<User> updateUser(User user) async {
    // This would need proper implementation with request/response conversion
    throw UnimplementedError('updateUser needs proper request/response conversion');
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
    // This would need to be implemented in the API service
    throw UnimplementedError('isUsernameAvailable not implemented in API service');
  }

  @override
  Future<bool> isEmailAvailable(String email) async {
    // This would need to be implemented in the API service
    throw UnimplementedError('isEmailAvailable not implemented in API service');
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
}
