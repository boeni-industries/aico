import 'package:aico_frontend/presentation/providers/auth_provider.dart';
import 'package:aico_frontend/presentation/providers/startup_connection_provider.dart';
import 'package:aico_frontend/presentation/screens/auth/login_screen.dart';
import 'package:aico_frontend/presentation/screens/home/home_screen.dart';
import 'package:aico_frontend/presentation/screens/startup/startup_connection_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Login overlay widget that displays as a card on top of the main UI
class LoginOverlay extends StatelessWidget {
  const LoginOverlay({super.key});

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
  bool _startupConnectionCompleted = false;
  bool _hasCredentials = false;
  
  @override
  void initState() {
    super.initState();
    // Start auth check immediately in parallel with connection check for faster startup
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _performFastCredentialCheck();
    });
  }
  
  /// Perform fast local credential check while connection is establishing
  void _performFastCredentialCheck() async {
    try {
      final authNotifier = ref.read(authProvider.notifier);
      final hasCredentials = await authNotifier.checkAuthStatus();
      
      if (mounted) {
        setState(() {
          _hasCredentials = hasCredentials;
        });
      }
    } catch (e) {
      debugPrint('AuthGate: Fast credential check failed: $e');
      // Continue with normal flow
    }
  }
  
  void _onStartupConnectionCompleted() {
    if (mounted) {
      setState(() {
        _startupConnectionCompleted = true;
      });
      
      // If we have credentials, attempt auto-login with delay to prevent UI blocking
      if (_hasCredentials) {
        Future.delayed(const Duration(milliseconds: 100), () {
          if (mounted) {
            ref.read(authProvider.notifier).attemptAutoLogin();
          }
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final startupConnectionState = ref.watch(startupConnectionProvider);
    
    ref.listen<AuthState>(authProvider, (previous, next) {
      // Authentication state changes are handled by UI rebuilds
    });

    final authState = ref.watch(authProvider);
    
    // Show startup connection screen if not connected yet
    if (!startupConnectionState.isConnected && !_startupConnectionCompleted) {
      return StartupConnectionScreen(
        onConnected: _onStartupConnectionCompleted,
      );
    }
    
    // If authenticated, show home screen
    if (authState.isAuthenticated) {
      return const HomeScreen();
    }
    
    // If we have credentials and are loading (auto-login in progress), show minimal loading
    if (_hasCredentials && authState.isLoading) {
      return Scaffold(
        backgroundColor: Theme.of(context).colorScheme.surface,
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              CircularProgressIndicator(
                color: Theme.of(context).colorScheme.primary,
              ),
              const SizedBox(height: 16),
              Text(
                'Signing you in...',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.7),
                ),
              ),
            ],
          ),
        ),
      );
    }

    // Show login screen only when no credentials or authentication failed
    return Scaffold(
      backgroundColor: Theme.of(context).colorScheme.surface,
      body: Stack(
        children: [
          // Background with blur effect
          Container(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  Theme.of(context).colorScheme.primary.withValues(alpha: 0.1),
                  Theme.of(context).colorScheme.secondary.withValues(alpha: 0.05),
                ],
              ),
            ),
          ),
          
          // Centered login overlay
          Center(
            child: LoginOverlay(),
          ),
        ],
      ),
    );
  }
}
