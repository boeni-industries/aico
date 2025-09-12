import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';
import '../../providers/startup_connection_provider.dart';
import '../../screens/auth/login_screen.dart';
import '../../screens/home/home_screen.dart';
import '../../screens/startup/startup_connection_screen.dart';
import 'auth_status_overlay.dart';

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
        maxWidth: 380,
        maxHeight: 560,
      ),
      margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      child: Material(
        elevation: 16,
        shadowColor: theme.colorScheme.shadow.withValues(alpha: 0.2),
        borderRadius: BorderRadius.circular(16),
        child: Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            color: theme.colorScheme.surface,
            border: Border.all(
              color: theme.colorScheme.outline.withValues(alpha: 0.08),
              width: 1,
            ),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (message != null) ...[
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: (messageColor ?? theme.colorScheme.primary).withValues(alpha: 0.06),
                    borderRadius: const BorderRadius.only(
                      topLeft: Radius.circular(16),
                      topRight: Radius.circular(16),
                    ),
                    border: Border(
                      bottom: BorderSide(
                        color: theme.colorScheme.outline.withValues(alpha: 0.06),
                        width: 1,
                      ),
                    ),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        messageIcon ?? Icons.info_outline,
                        color: messageColor ?? theme.colorScheme.primary,
                        size: 16,
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          message!,
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: messageColor ?? theme.colorScheme.primary,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
              Padding(
                padding: const EdgeInsets.all(20),
                child: const LoginScreen(),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// AuthGate implements progressive disclosure by showing minimal UI when unauthenticated
/// and full companion interface when authenticated
class AuthGate extends ConsumerStatefulWidget {
  const AuthGate({super.key});

  @override
  ConsumerState<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends ConsumerState<AuthGate> {
  String? _loginMessage;
  IconData? _loginMessageIcon;
  Color? _loginMessageColor;
  bool _startupConnectionCompleted = false;
  
  @override
  void initState() {
    super.initState();
    // No immediate auth check - wait for startup connection to complete
  }
  
  void _onStartupConnectionCompleted() {
    if (mounted) {
      setState(() {
        _startupConnectionCompleted = true;
      });
      // Now perform auth check after connection is established
      WidgetsBinding.instance.addPostFrameCallback((_) {
        ref.read(authProvider.notifier).checkAuthStatus();
      });
    }
  }
  
  void _updateLoginMessage(AuthState state) {
    if (state.error != null) {
      final error = state.error!.toLowerCase();
      
      if (error.contains('network') || error.contains('connection')) {
        _loginMessage = 'Unable to connect to AICO. Please check your network connection and try again.';
        _loginMessageIcon = Icons.wifi_off;
        _loginMessageColor = Colors.orange;
      } else if (error.contains('invalid pin') || error.contains('incorrect pin')) {
        _loginMessage = 'Incorrect PIN. Please check your PIN and try again.';
        _loginMessageIcon = Icons.lock_outline;
        _loginMessageColor = Colors.red;
      } else if (error.contains('user not found') || error.contains('invalid user')) {
        _loginMessage = 'User not found. Please check your credentials or contact support.';
        _loginMessageIcon = Icons.lock_outline;
        _loginMessageColor = Colors.red;
      } else if (error.contains('account locked') || error.contains('too many attempts')) {
        _loginMessage = 'Account temporarily locked due to too many failed attempts. Please try again later.';
        _loginMessageIcon = Icons.lock_outline;
        _loginMessageColor = Colors.red;
      } else if (error.contains('token expired') || error.contains('session expired')) {
        _loginMessage = 'Your session has expired. Please sign in again to continue.';
        _loginMessageIcon = Icons.access_time;
        _loginMessageColor = Colors.amber;
      } else if (error.contains('timeout')) {
        _loginMessage = 'Connection timed out. AICO server may be busy. Please try again.';
        _loginMessageIcon = Icons.error_outline;
        _loginMessageColor = Colors.red;
      } else if (error.contains('maintenance')) {
        _loginMessage = 'AICO is currently under maintenance. Please try again later.';
        _loginMessageIcon = Icons.error_outline;
        _loginMessageColor = Colors.red;
      } else if (error.contains('no stored credentials')) {
        _loginMessage = 'No saved credentials found. Please sign in to continue.';
        _loginMessageIcon = Icons.refresh;
        _loginMessageColor = Colors.blue;
      } else if (error.contains('credentials corrupted')) {
        _loginMessage = 'Saved credentials are corrupted. Please sign in again.';
        _loginMessageIcon = Icons.refresh;
        _loginMessageColor = Colors.blue;
      } else if (error.contains('server error')) {
        _loginMessage = 'AICO server error. Please try again later.';
        _loginMessageIcon = Icons.error_outline;
        _loginMessageColor = Colors.red;
      } else if (error.contains('permission denied')) {
        _loginMessage = 'Access denied. Your account may not have the required permissions.';
        _loginMessageIcon = Icons.block;
        _loginMessageColor = Colors.red;
      } else {
        _loginMessage = 'Sign-in issue: ${state.error}';
        _loginMessageIcon = Icons.info_outline;
        _loginMessageColor = Colors.grey[600];
      }
    } else if (!state.isAuthenticated && !state.isLoading) {
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
    // Listen for startup connection state
    final startupConnectionState = ref.watch(startupConnectionProvider);
    
    ref.listen<AuthState>(authProvider, (previous, next) {
      // Update login message based on state
      setState(() {
        _updateLoginMessage(next);
      });
      
      // Debug logging to trace authentication state changes
      if (next.isAuthenticated) {
        debugPrint('AuthGate: User authenticated, showing HomeScreen');
      } else if (!next.isAuthenticated && !next.isLoading) {
        debugPrint('AuthGate: User unauthenticated, showing LoginScreen');
      } else if (next.error != null) {
        debugPrint('AuthGate: Authentication failed - ${next.error}');
      }
    });

    final authState = ref.watch(authProvider);
    
    // Show startup connection screen if not connected yet
    if (!startupConnectionState.isConnected && !_startupConnectionCompleted) {
      return StartupConnectionScreen(
        onConnected: _onStartupConnectionCompleted,
      );
    }
    
    if (authState.isAuthenticated) {
      return const AuthStatusOverlay(
        child: HomeScreen(),
      );
    } else if (authState.isLoading) {
      return Scaffold(
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const CircularProgressIndicator(),
              const SizedBox(height: 16),
              Text(
                'Authenticating...',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
          ),
        ),
      );
    } else {
      return Stack(
        children: [
          const HomeScreen(),
          Container(
            decoration: BoxDecoration(
              color: Theme.of(context).scaffoldBackgroundColor.withValues(alpha: 0.95),
            ),
            child: BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 20.0, sigmaY: 20.0),
              child: Container(
                decoration: BoxDecoration(
                  color: Theme.of(context).scaffoldBackgroundColor.withValues(alpha: 0.3),
                ),
                child: Center(
                  child: LoginOverlay(
                    message: _loginMessage,
                    messageIcon: _loginMessageIcon,
                    messageColor: _loginMessageColor,
                  ),
                ),
              ),
            ),
          ),
        ],
      );
    }
  }
}
