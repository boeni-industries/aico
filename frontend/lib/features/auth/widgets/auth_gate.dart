import 'package:aico_frontend/features/auth/bloc/auth_bloc.dart';
import 'package:aico_frontend/features/auth/screens/login_screen.dart';
import 'package:aico_frontend/features/home/screens/home_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

/// AuthGate implements progressive disclosure by showing minimal UI when unauthenticated
/// and full companion interface when authenticated
class AuthGate extends StatelessWidget {
  const AuthGate({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<AuthBloc, AuthState>(
      builder: (context, state) {
        switch (state) {
          case AuthInitial _:
          case AuthLoading _:
            return const Center(
              child: CircularProgressIndicator(),
            );
          case AuthAuthenticated _:
            return const HomeScreen();
          case AuthUnauthenticated _:
          case AuthFailure _:
          default:
            return const LoginScreen();
        }
      },
    );
  }
}
