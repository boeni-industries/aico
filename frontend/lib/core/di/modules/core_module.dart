import 'package:aico_frontend/core/di/modules/di_module.dart';
import 'package:aico_frontend/core/services/encryption_service.dart';
import 'package:aico_frontend/core/services/settings_service.dart';
import 'package:aico_frontend/core/services/storage_service.dart';
import 'package:get_it/get_it.dart';

/// Core services module for fundamental app services
class CoreModule implements DIModule {
  @override
  String get name => 'CoreModule';

  @override
  Future<void> register(GetIt getIt) async {
    // Storage service
    getIt.registerLazySingleton<StorageService>(
      () => StorageService(),
    );

    // Settings service
    getIt.registerLazySingleton<SettingsService>(
      () => SettingsService(
        storageService: getIt<StorageService>(),
      ),
    );

    // Encryption service
    getIt.registerLazySingleton<EncryptionService>(
      () => EncryptionService(),
    );

    // Initialize async services
    await _initializeAsyncServices(getIt);
  }

  /// Initialize services that require async setup
  Future<void> _initializeAsyncServices(GetIt getIt) async {
    // Initialize storage service
    final storageService = getIt<StorageService>();
    await storageService.initialize();

    // Initialize settings service
    final settingsService = getIt<SettingsService>();
    await settingsService.initialize();

    // Initialize encryption service
    final encryptionService = getIt<EncryptionService>();
    await encryptionService.initialize();
  }

  @override
  Future<void> dispose(GetIt getIt) async {
    // Dispose services in reverse order
    if (getIt.isRegistered<SettingsService>()) {
      await getIt<SettingsService>().dispose();
    }
    
    if (getIt.isRegistered<StorageService>()) {
      await getIt<StorageService>().dispose();
    }
  }
}
