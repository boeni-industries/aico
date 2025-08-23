import 'package:aico_frontend/presentation/blocs/auth/auth_bloc.dart';
import 'package:aico_frontend/presentation/screens/auth/login_screen.dart';
import 'package:aico_frontend/presentation/screens/home/home_screen.dart' as presentation;
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

/// Login overlay widget that displays as a card on top of the main UI
class LoginOverlay extends StatelessWidget {
  final String? message;
  final IconData? messageIcon;
  final Color? messageColor;
  
  const LoginOverlay({
    super.key,
    this.message,
    this.messageIcon,
    this.messageColor,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return Container(
      constraints: const BoxConstraints(
        maxWidth: 400,
        maxHeight: 650, // Increased to accommodate message
      ),
      margin: const EdgeInsets.all(24),
      child: Card(
        elevation: 8,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (message != null) ...[
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: (messageColor ?? theme.colorScheme.primary).withValues(alpha: 0.1),
                  borderRadius: const BorderRadius.only(
                    topLeft: Radius.circular(12),
                    topRight: Radius.circular(12),
                  ),
                ),
                child: Row(
                  children: [
                    Icon(
                      messageIcon ?? Icons.info_outline,
                      color: messageColor ?? theme.colorScheme.primary,
                      size: 20,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        message!,
                        style: theme.textTheme.bodyMedium?.copyWith(
                          color: messageColor ?? theme.colorScheme.primary,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
            const Flexible(
              child: LoginScreen(),
            ),
          ],
        ),
      ),
    );
  }
}

/// AuthGate implements progressive disclosure by showing minimal UI when unauthenticated
/// and full companion interface when authenticated
class AuthGate extends StatefulWidget {
  const AuthGate({super.key});

  @override
  State<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<AuthGate> {
  String? _loginMessage;
  IconData? _loginMessageIcon;
  Color? _loginMessageColor;
  
  @override
  void initState() {
    super.initState();
    // Trigger automatic login check on app startup
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<AuthBloc>().add(const AuthAutoLoginRequested());
    });
  }
  
  void _updateLoginMessage(AuthState state) {
    if (state is AuthFailure) {
      switch (state.errorCode) {
        case 'NETWORK_ERROR':
          _loginMessage = 'Unable to connect to AICO. Please check your network connection and try again.';
          _loginMessageIcon = Icons.wifi_off;
          _loginMessageColor = Colors.orange;
          break;
        case 'AUTH_FAILED':
          // More specific message based on the actual error details
          if (state.message.toLowerCase().contains('invalid pin') || 
              state.message.toLowerCase().contains('incorrect pin')) {
            _loginMessage = 'Incorrect PIN. Please check your PIN and try again.';
          } else if (state.message.toLowerCase().contains('user not found') || 
                     state.message.toLowerCase().contains('invalid user')) {
            _loginMessage = 'User not found. Please check your credentials or contact support.';
          } else if (state.message.toLowerCase().contains('account locked') || 
                     state.message.toLowerCase().contains('too many attempts')) {
            _loginMessage = 'Account temporarily locked due to too many failed attempts. Please try again later.';
          } else {
            _loginMessage = 'Authentication failed. ${state.message.isNotEmpty ? state.message : "Please check your credentials."}';
          }
          _loginMessageIcon = Icons.lock_outline;
          _loginMessageColor = Colors.red;
          break;
        case 'TOKEN_EXPIRED':
          _loginMessage = 'Your session has expired. Please sign in again to continue.';
          _loginMessageIcon = Icons.access_time;
          _loginMessageColor = Colors.amber;
          break;
        case 'SERVER_ERROR':
          if (state.message.toLowerCase().contains('timeout')) {
            _loginMessage = 'Connection timed out. AICO server may be busy. Please try again.';
          } else if (state.message.toLowerCase().contains('maintenance')) {
            _loginMessage = 'AICO is currently under maintenance. Please try again later.';
          } else {
            _loginMessage = 'AICO server error. ${state.message.isNotEmpty ? state.message : "Please try again later."}';
          }
          _loginMessageIcon = Icons.error_outline;
          _loginMessageColor = Colors.red;
          break;
        case 'AUTO_LOGIN_FAILED':
          if (state.message.toLowerCase().contains('no stored credentials')) {
            _loginMessage = 'No saved credentials found. Please sign in to continue.';
          } else if (state.message.toLowerCase().contains('credentials corrupted')) {
            _loginMessage = 'Saved credentials are corrupted. Please sign in again.';
          } else {
            _loginMessage = 'Automatic sign-in failed. ${state.message.isNotEmpty ? state.message : "Please enter your credentials."}';
          }
          _loginMessageIcon = Icons.refresh;
          _loginMessageColor = Colors.blue;
          break;
        case 'CONNECTION_ERROR':
          _loginMessage = 'Connection error. Please check your internet connection and try again.';
          _loginMessageIcon = Icons.signal_wifi_off;
          _loginMessageColor = Colors.orange;
          break;
        case 'INVALID_RESPONSE':
          _loginMessage = 'Invalid server response. Please try again or contact support if the issue persists.';
          _loginMessageIcon = Icons.warning_outlined;
          _loginMessageColor = Colors.amber;
          break;
        case 'PERMISSION_DENIED':
          _loginMessage = 'Access denied. Your account may not have the required permissions.';
          _loginMessageIcon = Icons.block;
          _loginMessageColor = Colors.red;
          break;
        default:
          // Enhanced fallback with more context
          if (state.message.isNotEmpty) {
            _loginMessage = 'Sign-in issue: ${state.message}';
          } else if (state.errorCode?.isNotEmpty == true) {
            _loginMessage = 'Authentication error (${state.errorCode}). Please try again.';
          } else {
            _loginMessage = 'An unexpected error occurred. Please try signing in again.';
          }
          _loginMessageIcon = Icons.info_outline;
          _loginMessageColor = Colors.grey[600];
      }
    } else if (state is AuthUnauthenticated) {
      // Check if this is the first time or a logout
      _loginMessage = 'Welcome to AICO. Please sign in to get started.';
      _loginMessageIcon = Icons.waving_hand;
      _loginMessageColor = null;
    } else {
      _loginMessage = null;
      _loginMessageIcon = null;
      _loginMessageColor = null;
    }
  }

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<AuthBloc, AuthState>(
      listener: (context, state) {
        // Update login message based on state
        setState(() {
          _updateLoginMessage(state);
        });
        
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
                  child: Center(
                    child: LoginOverlay(
                      message: _loginMessage,
                      messageIcon: _loginMessageIcon,
                      messageColor: _loginMessageColor,
                    ),
                  ),
                ),
              ],
            );
          case AuthLoading _:
            return Scaffold(
              body: Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const CircularProgressIndicator(),
                    const SizedBox(height: 16),
                    Text(
                      'Connecting to AICO...',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
            );
          default:
            return Scaffold(
              body: Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const CircularProgressIndicator(),
                    const SizedBox(height: 16),
                    Text(
                      'Initializing AICO...',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
            );
        }
      },
    );
  }
}
