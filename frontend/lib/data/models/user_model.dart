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
    return UserModel(
      id: json['id'] as String,
      username: json['username'] as String,
      email: json['email'] as String,
      role: UserRole.values.firstWhere(
        (e) => e.name == json['role'],
        orElse: () => UserRole.user,
      ),
      createdAt: DateTime.parse(json['created_at'] as String),
      lastLoginAt: json['last_login_at'] != null
          ? DateTime.parse(json['last_login_at'] as String)
          : null,
      isActive: json['is_active'] as bool? ?? true,
    );
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
