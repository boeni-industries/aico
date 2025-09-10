import 'package:equatable/equatable.dart';

/// Domain entity representing a user in the AICO system
class User extends Equatable {
  final String id;
  final String username;
  final String email;
  final UserRole role;
  final DateTime createdAt;
  final DateTime? lastLoginAt;
  final bool isActive;

  const User({
    required this.id,
    required this.username,
    required this.email,
    required this.role,
    required this.createdAt,
    this.lastLoginAt,
    this.isActive = true,
  });

  @override
  List<Object?> get props => [
        id,
        username,
        email,
        role,
        createdAt,
        lastLoginAt,
        isActive,
      ];

  User copyWith({
    String? id,
    String? username,
    String? email,
    UserRole? role,
    DateTime? createdAt,
    DateTime? lastLoginAt,
    bool? isActive,
  }) {
    return User(
      id: id ?? this.id,
      username: username ?? this.username,
      email: email ?? this.email,
      role: role ?? this.role,
      createdAt: createdAt ?? this.createdAt,
      lastLoginAt: lastLoginAt ?? this.lastLoginAt,
      isActive: isActive ?? this.isActive,
    );
  }

  /// Create User from JSON (for hydrated bloc persistence)
  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'] as String,
      username: json['username'] as String,
      email: json['email'] as String,
      role: UserRole.values.firstWhere(
        (e) => e.name == json['role'],
        orElse: () => UserRole.user,
      ),
      createdAt: DateTime.parse(json['createdAt'] as String),
      lastLoginAt: json['lastLoginAt'] != null
          ? DateTime.parse(json['lastLoginAt'] as String)
          : null,
      isActive: json['isActive'] as bool? ?? true,
    );
  }

  /// Convert User to JSON (for hydrated bloc persistence)
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'username': username,
      'email': email,
      'role': role.name,
      'createdAt': createdAt.toIso8601String(),
      'lastLoginAt': lastLoginAt?.toIso8601String(),
      'isActive': isActive,
    };
  }

  @override
  String toString() {
    return 'User(id: $id, username: $username, email: $email, role: $role, isActive: $isActive)';
  }
}

enum UserRole {
  user,
  admin,
  superAdmin,
}

extension UserRoleExtension on UserRole {
  String get displayName {
    switch (this) {
      case UserRole.user:
        return 'User';
      case UserRole.admin:
        return 'Admin';
      case UserRole.superAdmin:
        return 'Super Admin';
    }
  }

  bool get isAdmin => this == UserRole.admin || this == UserRole.superAdmin;
  bool get isSuperAdmin => this == UserRole.superAdmin;
}
