import 'package:aico_frontend/core/di/modules/di_module.dart';
import 'package:aico_frontend/data/repositories/user_repository_impl.dart';
import 'package:aico_frontend/domain/repositories/user_repository.dart';
import 'package:aico_frontend/networking/services/user_service.dart';
import 'package:get_it/get_it.dart';

/// Data module for repository implementations
class DataModule implements DIModule {
  @override
  String get name => 'DataModule';

  @override
  Future<void> register(GetIt getIt) async {
    // Register domain repository implementations
    getIt.registerLazySingleton<UserRepository>(
      () => UserDataRepository(getIt<ApiUserService>()),
    );
  }

  @override
  Future<void> dispose(GetIt getIt) async {
    // No specific disposal needed for repositories
  }
}
