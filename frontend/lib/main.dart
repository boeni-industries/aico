import 'package:aico_frontend/core/di/service_locator.dart';
import 'package:aico_frontend/core/theme/aico_theme.dart';
import 'package:aico_frontend/features/auth/bloc/auth_bloc.dart';
import 'package:aico_frontend/features/auth/widgets/auth_gate.dart';
import 'package:aico_frontend/features/connection/bloc/connection_bloc.dart';
import 'package:aico_frontend/features/settings/bloc/settings_bloc.dart';
import 'package:aico_frontend/features/settings/models/settings_event.dart';
import 'package:aico_frontend/networking/repositories/user_repository.dart';
import 'package:aico_frontend/networking/services/token_manager.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Initialize dependency injection
  await ServiceLocator.initialize();
  
  runApp(const AicoApp());
}

class AicoApp extends StatelessWidget {
  const AicoApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiBlocProvider(
      providers: [
        BlocProvider<SettingsBloc>(
          create: (context) => ServiceLocator.get<SettingsBloc>()..add(const SettingsLoad()),
        ),
        BlocProvider<ConnectionBloc>(
          create: (context) => ServiceLocator.get<ConnectionBloc>(),
        ),
        BlocProvider<AuthBloc>(
          create: (context) => AuthBloc(
            userRepository: ServiceLocator.get<UserRepository>(),
            tokenManager: ServiceLocator.get<TokenManager>(),
          )..add(const AuthStatusChecked()),
        ),
      ],
      child: MaterialApp(
        title: 'AICO',
        debugShowCheckedModeBanner: false,
        theme: AicoTheme.light(),
        darkTheme: AicoTheme.dark(),
        themeMode: ThemeMode.system,
        home: const AuthGate(),
      ),
    );
  }
}

