import 'package:aico_frontend/presentation/blocs/auth/auth_bloc.dart';
import 'package:aico_frontend/presentation/screens/auth/login_screen.dart';
import 'package:aico_frontend/presentation/screens/home/home_screen.dart' as presentation;
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

/// Login overlay widget that displays as a card on top of the main UI
class LoginOverlay extends StatelessWidget {
  const LoginOverlay({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(
        maxWidth: 400,
        maxHeight: 600,
      ),
      margin: const EdgeInsets.all(24),
      child: Card(
        elevation: 8,
        child: const LoginScreen(),
      ),
    );
  }
}

/// AuthGate implements progressive disclosure by showing minimal UI when unauthenticated
/// and full companion interface when authenticated
class AuthGate extends StatelessWidget {
  const AuthGate({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<AuthBloc, AuthState>(
      listener: (context, state) {
        // Debug logging to trace authentication state changes
        if (state is AuthAuthenticated) {
          debugPrint('AuthGate: User authenticated, showing HomeScreen');
        } else if (state is AuthUnauthenticated) {
          debugPrint('AuthGate: User unauthenticated, showing LoginScreen');
        } else if (state is AuthFailure) {
          debugPrint('AuthGate: Authentication failed - ${state.message}');
        }
      },
      builder: (context, state) {
        switch (state) {
          case AuthAuthenticated _:
            return const presentation.HomeScreen();
          case AuthUnauthenticated _:
          case AuthFailure _:
            return Stack(
              children: [
                const presentation.HomeScreen(),
                Container(
                  color: Colors.black.withValues(alpha: 0.9),
                  child: const Center(
                    child: LoginOverlay(),
                  ),
                ),
              ],
            );
          case AuthLoading _:
            return const Scaffold(
              body: Center(
                child: CircularProgressIndicator(),
              ),
            );
          default:
            return const Scaffold(
              body: Center(
                child: CircularProgressIndicator(),
              ),
            );
        }
      },
    );
  }
}
