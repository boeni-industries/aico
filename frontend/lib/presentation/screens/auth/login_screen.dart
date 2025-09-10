import 'package:aico_frontend/core/widgets/atoms/aico_button.dart';
import 'package:aico_frontend/core/widgets/atoms/aico_text_field.dart';
import 'package:aico_frontend/presentation/providers/auth_provider.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
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
      ref.read(authProvider.notifier).login(
        _userUuidController.text.trim(),
        _pinController.text.trim(),
        rememberMe: _rememberMe,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    final authState = ref.watch(authProvider);
    
    return Form(
      key: _formKey,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Logo/Title Group
          Icon(
            Icons.person,
            size: 48,
            color: colorScheme.primary,
          ),
          const SizedBox(height: 8),
          Text(
            'AICO',
            style: theme.textTheme.headlineSmall?.copyWith(
              color: colorScheme.primary,
              fontWeight: FontWeight.bold,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 2),
          Text(
            'Welcome back',
            style: theme.textTheme.bodySmall?.copyWith(
              color: colorScheme.onSurface.withValues(alpha: 0.7),
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 20),

          // Form Fields Group
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
          const SizedBox(height: 12),

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
          const SizedBox(height: 8),

          // Remember Me
          Row(
            children: [
              Checkbox(
                value: _rememberMe,
                onChanged: (value) {
                  setState(() {
                    _rememberMe = value ?? false;
                  });
                },
                activeColor: colorScheme.primary,
              ),
              Text(
                'Remember me',
                style: theme.textTheme.bodySmall,
              ),
            ],
          ),
          const SizedBox(height: 16),

          // Action Button Group
          AicoButton.primary(
            onPressed: _handleLogin,
            isLoading: authState.isLoading,
            child: const Text('Sign In'),
          ),
        ],
      ),
    );
  }
}
