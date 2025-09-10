import 'package:aico_frontend/data/models/user_model.dart';
import 'package:aico_frontend/domain/repositories/auth_repository.dart';

class AuthModel {
  final UserModel user;
  final String token;
  final DateTime? lastLogin;

  const AuthModel({
    required this.user,
    required this.token,
    this.lastLogin,
  });

  factory AuthModel.fromJson(Map<String, dynamic> json) {
    return AuthModel(
      user: UserModel.fromJson(json['user'] ?? {}),
      token: json['token'] as String,
      lastLogin: json['last_login'] != null 
          ? DateTime.parse(json['last_login'] as String)
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'user': user.toJson(),
      'token': token,
      'last_login': lastLogin?.toIso8601String(),
    };
  }

  // Convert to domain entity
  AuthResult toDomain() {
    return AuthResult(
      user: user.toDomain(),
      token: token,
      lastLogin: lastLogin,
    );
  }

  // Create from domain entity
  factory AuthModel.fromDomain(AuthResult authResult) {
    return AuthModel(
      user: UserModel.fromDomain(authResult.user),
      token: authResult.token,
      lastLogin: authResult.lastLogin,
    );
  }
}
