import 'package:aico_frontend/domain/entities/user.dart';
import 'package:aico_frontend/presentation/providers/auth_provider.dart';
import 'package:aico_frontend/presentation/screens/settings/settings_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Logs screen for system diagnostics and debugging.
/// Requires admin role - redirects non-admin users to settings.
class LogsScreen extends ConsumerStatefulWidget {
  const LogsScreen({super.key});

  @override
  ConsumerState<LogsScreen> createState() => _LogsScreenState();
}

class _LogsScreenState extends ConsumerState<LogsScreen> {
  @override
  void initState() {
    super.initState();
    
    // Check admin access on init
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _checkAdminAccess();
    });
  }
  
  void _checkAdminAccess() {
    final authState = ref.read(authProvider);
    
    // Redirect if not authenticated or not admin
    if (!authState.isAuthenticated || authState.user?.role.isAdmin != true) {
      if (mounted) {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(builder: (_) => const SettingsScreen()),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('System Logs'),
      ),
      body: const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.description, size: 64, color: Colors.grey),
            SizedBox(height: 16),
            Text('System Logs', 
                 style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
            Text('Log viewing coming soon'),
          ],
        ),
      ),
    );
  }
}
