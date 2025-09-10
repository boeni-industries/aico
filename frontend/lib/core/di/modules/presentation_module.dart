import 'package:aico_frontend/core/di/modules/di_module.dart';
import 'package:aico_frontend/core/theme/aico_theme_manager.dart';
import 'package:aico_frontend/core/theme/theme_manager.dart';
import 'package:aico_frontend/networking/services/token_manager.dart';
import 'package:aico_frontend/networking/services/user_service.dart';
import 'package:aico_frontend/presentation/blocs/auth/auth_bloc.dart';
import 'package:aico_frontend/presentation/blocs/connection/connection_bloc.dart';
import 'package:aico_frontend/presentation/blocs/settings/settings_bloc.dart';
import 'package:get_it/get_it.dart';

/// Presentation module for BLoCs and UI-related services
class PresentationModule implements DIModule {
  @override
  String get name => 'PresentationModule';

  @override
  Future<void> register(GetIt getIt) async {
    // Auth BLoC
    getIt.registerFactory<AuthBloc>(
      () => AuthBloc(
        apiUserService: getIt<ApiUserService>(),
        tokenManager: getIt<TokenManager>(),
      ),
    );

    // Connection BLoC
    getIt.registerFactory<ConnectionBloc>(
      () => ConnectionBloc(),
    );

    // Settings BLoC
    getIt.registerFactory<SettingsBloc>(
      () => SettingsBloc(),
    );

    // Theme Manager
    getIt.registerSingleton<ThemeManager>(
      AicoThemeManager.fromServiceLocator(),
    );
  }

  @override
  Future<void> dispose(GetIt getIt) async {
    // BLoCs are factories, so they don't need disposal here
    // Individual instances are disposed by their consumers
    
    // Dispose ThemeManager singleton
    if (getIt.isRegistered<ThemeManager>()) {
      final themeManager = getIt<ThemeManager>();
      if (themeManager is AicoThemeManager) {
        themeManager.dispose();
      }
    }
  }
}
