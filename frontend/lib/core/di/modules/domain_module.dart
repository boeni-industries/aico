import 'package:aico_frontend/core/di/modules/di_module.dart';
import 'package:aico_frontend/domain/repositories/user_repository.dart';
import 'package:aico_frontend/domain/usecases/get_user_usecase.dart';
import 'package:get_it/get_it.dart';

/// Domain module for use cases and business logic
class DomainModule implements DIModule {
  @override
  String get name => 'DomainModule';

  @override
  Future<void> register(GetIt getIt) async {
    // User use cases
    getIt.registerLazySingleton<GetUserUseCase>(
      () => GetUserUseCase(getIt<UserRepository>()),
    );
    
    getIt.registerLazySingleton<GetCurrentUserUseCase>(
      () => GetCurrentUserUseCase(getIt<UserRepository>()),
    );

    // Message use cases (when message repository is implemented)
    // getIt.registerLazySingleton<SendMessageUseCase>(
    //   () => SendMessageUseCase(getIt<MessageRepository>()),
    // );
  }

  @override
  Future<void> dispose(GetIt getIt) async {
    // Use cases don't typically need disposal
  }
}
