import 'dart:async';

import 'package:aico_frontend/core/providers/networking_providers.dart';
import 'package:aico_frontend/networking/services/token_manager.dart';
import 'package:aico_frontend/presentation/providers/auth_provider.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Simple re-authentication listener that delegates to existing AuthProvider
/// Follows KISS principle and reuses existing authentication logic
class ReAuthListener extends ConsumerStatefulWidget {
  final Widget child;
  
  const ReAuthListener({super.key, required this.child});

  @override
  ConsumerState<ReAuthListener> createState() => _ReAuthListenerState();
}

class _ReAuthListenerState extends ConsumerState<ReAuthListener> {
  StreamSubscription<ReAuthenticationRequired>? _subscription;

  @override
  void initState() {
    super.initState();
    final tokenManager = ref.read(tokenManagerProvider);
    
    // Simple listener - delegate to existing AuthProvider logic
    _subscription = tokenManager.reAuthenticationStream.listen((_) {
      final authNotifier = ref.read(authProvider.notifier);
      authNotifier.attemptAutoLogin(); // Reuse existing logic
    });
  }

  @override
  void dispose() {
    _subscription?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => widget.child;
}
