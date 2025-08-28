import 'package:aico_frontend/core/theme/aico_theme.dart';
import 'package:aico_frontend/core/widgets/atoms/aico_button.dart';
import 'package:aico_frontend/core/widgets/atoms/aico_text_field.dart';
import 'package:aico_frontend/presentation/blocs/auth/auth_bloc.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _userUuidController = TextEditingController();
  final _pinController = TextEditingController();
  bool _rememberMe = false;

  @override
  void dispose() {
    _userUuidController.dispose();
    _pinController.dispose();
    super.dispose();
  }

  void _handleLogin() {
    if (_formKey.currentState?.validate() ?? false) {
      context.read<AuthBloc>().add(
        AuthLoginRequested(
          userUuid: _userUuidController.text.trim(),
          pin: _pinController.text.trim(),
          rememberMe: _rememberMe,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final aicoTheme = theme.extension<AicoThemeExtension>()!;

    return BlocBuilder<AuthBloc, AuthState>(
      builder: (context, state) {
        return Padding(
          padding: const EdgeInsets.all(24.0),
          child: Form(
            key: _formKey,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                    // Logo/Title
                    Icon(
                      Icons.person,
                      size: 80,
                      color: aicoTheme.colors.primary,
                    ),
                    const SizedBox(height: 16),
                    Text(
                      'AICO',
                      style: theme.textTheme.headlineLarge?.copyWith(
                        color: aicoTheme.colors.primary,
                        fontWeight: FontWeight.bold,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Welcome back',
                      style: theme.textTheme.bodyLarge?.copyWith(
                        color: aicoTheme.colors.onSurface.withValues(alpha: 0.7),
                      ),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 48),

                    // User UUID Field
                    AicoTextField(
                      controller: _userUuidController,
                      label: 'User ID',
                      hint: 'Enter your user ID',
                      keyboardType: TextInputType.text,
                      validator: (value) {
                        if (value?.trim().isEmpty ?? true) {
                          return 'Please enter your user ID';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),

                    // PIN Field
                    AicoTextField(
                      controller: _pinController,
                      label: 'PIN',
                      hint: 'Enter your PIN',
                      obscureText: true,
                      keyboardType: TextInputType.number,
                      textInputAction: TextInputAction.done,
                      onSubmitted: (_) => _handleLogin(),
                      validator: (value) {
                        if (value?.trim().isEmpty ?? true) {
                          return 'Please enter your PIN';
                        }
                        if (value!.length < 4) {
                          return 'PIN must be at least 4 digits';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),

                    // Remember Me Checkbox
                    Row(
                      children: [
                        Checkbox(
                          value: _rememberMe,
                          onChanged: (value) {
                            setState(() {
                              _rememberMe = value ?? false;
                            });
                          },
                          activeColor: aicoTheme.colors.primary,
                        ),
                        Text(
                          'Remember me',
                          style: theme.textTheme.bodyMedium,
                        ),
                      ],
                    ),
                    const SizedBox(height: 32),

                    // Login Button
                    AicoButton.primary(
                      onPressed: _handleLogin,
                      isLoading: state is AuthLoading,
                      child: const Text('Sign In'),
                    ),
              ],
                ),
              ),
            ),
          );
      },
    );
  }
}
