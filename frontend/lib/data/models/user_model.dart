import 'package:aico_frontend/domain/entities/user.dart';

/// Data model for User entity with JSON serialization
class UserModel extends User {
  const UserModel({
    required super.id,
    required super.username,
    required super.email,
    required super.role,
    required super.createdAt,
    super.lastLoginAt,
    super.isActive,
  });

  factory UserModel.fromJson(Map<String, dynamic> json) {
    // Parse user_type from backend and convert to UserRole
    final userType = json['user_type']?.toString().toLowerCase() ?? 'user';
    final role = _parseUserType(userType);
    
    return UserModel(
      // Backend sends 'uuid', fallback to 'id' for compatibility
      id: json['uuid']?.toString() ?? json['id']?.toString() ?? '',
      // Backend sends 'nickname' or 'full_name', fallback to 'username'
      username: json['nickname']?.toString() ?? 
                json['full_name']?.toString() ?? 
                json['username']?.toString() ?? '',
      // Backend doesn't send email, generate fallback
      email: json['email']?.toString() ?? 
             '${json['uuid'] ?? json['id']}@aico.local',
      role: role,
      createdAt: json['created_at'] != null 
          ? DateTime.parse(json['created_at'] as String)
          : DateTime.now(),
      // Support both 'last_login_at' and 'last_login'
      lastLoginAt: json['last_login_at'] != null
          ? DateTime.parse(json['last_login_at'] as String)
          : json['last_login'] != null
              ? DateTime.parse(json['last_login'] as String)
              : null,
      isActive: json['is_active'] as bool? ?? true,
    );
  }
  
  /// Parse backend user_type string to UserRole enum
  static UserRole _parseUserType(String userType) {
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

  @override
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'username': username,
      'email': email,
      'role': role.name,
      'created_at': createdAt.toIso8601String(),
      'last_login_at': lastLoginAt?.toIso8601String(),
      'is_active': isActive,
    };
  }

  factory UserModel.fromDomain(User user) {
    return UserModel(
      id: user.id,
      username: user.username,
      email: user.email,
      role: user.role,
      createdAt: user.createdAt,
      lastLoginAt: user.lastLoginAt,
      isActive: user.isActive,
    );
  }

  User toDomain() {
    return User(
      id: id,
      username: username,
      email: email,
      role: role,
      createdAt: createdAt,
      lastLoginAt: lastLoginAt,
      isActive: isActive,
    );
  }
}
