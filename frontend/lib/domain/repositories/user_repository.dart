import 'package:aico_frontend/domain/entities/user.dart';

/// Abstract repository interface for user operations
abstract class UserRepository {
  /// Get current authenticated user
  Future<User?> getCurrentUser();
  
  /// Get user by ID
  Future<User?> getUserById(String id);
  
  /// Update user profile
  Future<User> updateUser(User user);
  
  /// Delete user account
  Future<void> deleteUser(String id);
  
  /// Get all users (admin only)
  Future<List<User>> getAllUsers({
    int? limit,
    int? offset,
    String? search,
  });
  
  /// Check if username is available
  Future<bool> isUsernameAvailable(String username);
  
  /// Check if email is available
  Future<bool> isEmailAvailable(String email);
}
