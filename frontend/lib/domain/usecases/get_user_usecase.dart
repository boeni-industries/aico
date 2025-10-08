import 'package:aico_frontend/domain/entities/user.dart';
import 'package:aico_frontend/domain/repositories/user_repository.dart';

/// Use case for retrieving user information
class GetUserUseCase {
  final UserRepository _userRepository;

  const GetUserUseCase(this._userRepository);

  Future<User?> call(String userId) async {
    if (userId.trim().isEmpty) {
      throw ArgumentError('User ID cannot be empty');
    }

    return await _userRepository.getUserById(userId);
  }
}

/// Use case for getting current authenticated user
class GetCurrentUserUseCase {
  final UserRepository _userRepository;

  const GetCurrentUserUseCase(this._userRepository);

  Future<User?> call() async {
    return await _userRepository.getCurrentUser();
  }
}
