import 'dart:io';
import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/startup_connection_provider.dart';

class StartupConnectionScreen extends ConsumerStatefulWidget {
  final VoidCallback? onConnected;
  
  const StartupConnectionScreen({
    super.key,
    this.onConnected,
  });

  @override
  ConsumerState<StartupConnectionScreen> createState() => _StartupConnectionScreenState();
}

class _StartupConnectionScreenState extends ConsumerState<StartupConnectionScreen>
    with TickerProviderStateMixin {
  late AnimationController _pulseController;
  late AnimationController _progressController;
  late AnimationController _fadeController;
  late Animation<double> _pulseAnimation;
  late Animation<double> _progressAnimation;
  late Animation<double> _fadeAnimation;

  @override
  void initState() {
    super.initState();
    
    _pulseController = AnimationController(
      duration: const Duration(seconds: 2),
      vsync: this,
    );
    
    _progressController = AnimationController(
      duration: const Duration(milliseconds: 800),
      vsync: this,
    );
    
    _fadeController = AnimationController(
      duration: const Duration(milliseconds: 300),
      vsync: this,
    );

    _pulseAnimation = Tween<double>(
      begin: 0.8,
      end: 1.2,
    ).animate(CurvedAnimation(
      parent: _pulseController,
      curve: Curves.easeInOut,
    ));

    _progressAnimation = Tween<double>(
      begin: 0.0,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _progressController,
      curve: Curves.easeOutCubic,
    ));

    _fadeAnimation = Tween<double>(
      begin: 0.0,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _fadeController,
      curve: Curves.easeOut,
    ));

    _pulseController.repeat(reverse: true);
    _fadeController.forward();
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _progressController.dispose();
    _fadeController.dispose();
    super.dispose();
  }

  void _updateAnimations(StartupConnectionState state) {
    if (state.isInProgress) {
      if (!_pulseController.isAnimating) {
        _pulseController.repeat(reverse: true);
      }
      
      // For initial connection (attempt 0), show smooth progress animation
      if (state.currentAttempt == 0 && state.phase == StartupConnectionPhase.connecting) {
        // Animate from 0 to 1 over 4 seconds for initial attempt
        _progressController.animateTo(1.0, duration: const Duration(seconds: 4));
      } else {
        // For retry attempts, show progress based on attempt number
        final progress = state.currentAttempt / state.maxAttempts;
        _progressController.animateTo(progress, duration: const Duration(milliseconds: 500));
      }
    } else {
      _pulseController.stop();
      if (state.isConnected) {
        _progressController.animateTo(1.0, duration: const Duration(milliseconds: 300));
      } else if (state.isFailed) {
        _progressController.animateTo(0.0, duration: const Duration(milliseconds: 300));
      }
    }
  }

  void _handleRetry() {
    HapticFeedback.lightImpact();
    ref.read(startupConnectionProvider.notifier).retry();
  }

  void _handleClose() {
    HapticFeedback.mediumImpact();
    if (Platform.isAndroid || Platform.isIOS) {
      SystemNavigator.pop();
    } else {
      exit(0);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final state = ref.watch(startupConnectionProvider);
    
    // Listen for state changes to update animations
    ref.listen<StartupConnectionState>(startupConnectionProvider, (previous, next) {
      _updateAnimations(next);
      
      // Handle successful connection
      if (next.isConnected && widget.onConnected != null) {
        Future.delayed(const Duration(milliseconds: 500), () {
          widget.onConnected?.call();
        });
      }
    });

    return Scaffold(
      backgroundColor: const Color(0xFFF5F6FA), // Design principle: soft white-neutral background
      body: SafeArea(
        child: FadeTransition(
          opacity: _fadeAnimation,
          child: Center(
            child: Container(
              constraints: const BoxConstraints(maxWidth: 480), // Constrained width, not full screen
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  // Connection indicator card
                  Container(
                    padding: const EdgeInsets.all(48),
                    decoration: BoxDecoration(
                      color: Colors.white, // Design principle: white surface for cards
                      borderRadius: BorderRadius.circular(24), // Design principle: rounded corners
                      boxShadow: [
                        BoxShadow(
                          color: const Color(0xFF243455).withValues(alpha: 0.09), // Design principle: soft shadow
                          blurRadius: 24,
                          offset: const Offset(0, 8),
                        ),
                      ],
                    ),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        _buildConnectionIndicator(theme, state),
                        const SizedBox(height: 32),
                        _buildStatusContent(theme, state),
                      ],
                    ),
                  ),
                  
                  // Action buttons (only when failed)
                  if (state.isFailed) ...[
                    const SizedBox(height: 24),
                    _buildActionButtons(theme, state),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildConnectionIndicator(ThemeData theme, StartupConnectionState state) {
    return SizedBox(
      width: 96, // Design principle: avatar size 96px
      height: 96,
      child: Stack(
        alignment: Alignment.center,
        children: [
          // Outer pulse ring for connecting states
          if (state.isInProgress)
            AnimatedBuilder(
              animation: _pulseAnimation,
              builder: (context, child) {
                return Container(
                  width: 96 * _pulseAnimation.value,
                  height: 96 * _pulseAnimation.value,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: _getStatusColor(theme, state).withValues(alpha: 0.2),
                      width: 1.5,
                    ),
                  ),
                );
              },
            ),
          
          // Progress ring
          AnimatedBuilder(
            animation: _progressAnimation,
            builder: (context, child) {
              return SizedBox(
                width: 80,
                height: 80,
                child: CircularProgressIndicator(
                  value: state.isFailed ? 0.0 : _progressAnimation.value,
                  strokeWidth: 3,
                  backgroundColor: const Color(0xFF243455).withValues(alpha: 0.08),
                  valueColor: AlwaysStoppedAnimation<Color>(
                    _getStatusColor(theme, state),
                  ),
                ),
              );
            },
          ),
          
          // Center icon
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: _getStatusColor(theme, state).withValues(alpha: 0.08),
            ),
            child: Icon(
              _getStatusIcon(state),
              size: 24,
              color: _getStatusColor(theme, state),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatusContent(ThemeData theme, StartupConnectionState state) {
    return SizedBox(
      height: 120, // Fixed height to prevent layout jumps
      child: Column(
        mainAxisAlignment: MainAxisAlignment.start,
        children: [
          // Main status message - Design principle: Inter font, clear hierarchy
          Text(
            _getMainMessage(state),
            style: const TextStyle(
              fontFamily: 'Inter',
              fontSize: 24, // 1.5rem
              fontWeight: FontWeight.w600,
              color: Color(0xFF1A1A1A),
              letterSpacing: 0.02,
            ),
            textAlign: TextAlign.center,
          ),
          
          const SizedBox(height: 12),
          
          // Secondary message - always reserve space
          SizedBox(
            height: 48, // Fixed height for secondary message area
            child: Center(
              child: state.message != null
                  ? Text(
                      state.message!,
                      style: const TextStyle(
                        fontFamily: 'Inter',
                        fontSize: 16, // 1.0rem body
                        fontWeight: FontWeight.w400,
                        color: Color(0xFF6B7280),
                      ),
                      textAlign: TextAlign.center,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    )
                  : const SizedBox.shrink(),
            ),
          ),
          
          // Retry counter area - always reserve space
          SizedBox(
            height: 32, // Fixed height for retry counter area
            child: Center(
              child: (state.isInProgress && state.currentAttempt > 1)
                  ? Container(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                      decoration: BoxDecoration(
                        color: const Color(0xFFF3F4F6),
                        borderRadius: BorderRadius.circular(16), // Design principle: rounded
                      ),
                      child: Text(
                        'Attempt ${state.currentAttempt} of ${state.maxAttempts}',
                        style: const TextStyle(
                          fontFamily: 'Inter',
                          fontSize: 14, // 0.875rem caption
                          fontWeight: FontWeight.w500,
                          color: Color(0xFF6B7280),
                        ),
                      ),
                    )
                  : const SizedBox.shrink(),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActionButtons(ThemeData theme, StartupConnectionState state) {
    return Row(
      children: [
        // Close button - equal width, aligned with content above
        Expanded(
          child: Container(
            height: 48, // Design principle: proper button height
            child: OutlinedButton.icon(
              onPressed: _handleClose,
              icon: const Icon(Icons.close, size: 16),
              label: const Text(
                'Close',
                style: TextStyle(
                  fontFamily: 'Inter',
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
              style: OutlinedButton.styleFrom(
                backgroundColor: Colors.white,
                foregroundColor: const Color(0xFF6B7280),
                side: const BorderSide(
                  color: Color(0xFFD1D5DB),
                  width: 1,
                ),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16), // Design principle: rounded
                ),
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              ),
            ),
          ),
        ),
        const SizedBox(width: 12),
        // Retry button - equal width, aligned with content above
        Expanded(
          child: Container(
            height: 48,
            child: FilledButton.icon(
              onPressed: state.canRetry ? _handleRetry : null,
              icon: const Icon(Icons.refresh, size: 16),
              label: const Text(
                'Retry',
                style: TextStyle(
                  fontFamily: 'Inter',
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
              style: FilledButton.styleFrom(
                backgroundColor: const Color(0xFFB8A1EA), // Design principle: soft purple accent
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
                elevation: 0,
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Color _getStatusColor(ThemeData theme, StartupConnectionState state) {
    switch (state.phase) {
      case StartupConnectionPhase.initializing:
      case StartupConnectionPhase.connecting:
        return const Color(0xFFB8A1EA); // Design principle: soft purple accent
      case StartupConnectionPhase.retryMode:
        return const Color(0xFFF59E0B); // Amber for retrying
      case StartupConnectionPhase.failed:
        return const Color(0xFFED7867); // Design principle: coral for errors
      case StartupConnectionPhase.connected:
        return const Color(0xFF8DD6B8); // Design principle: mint for success
    }
  }

  IconData _getStatusIcon(StartupConnectionState state) {
    switch (state.phase) {
      case StartupConnectionPhase.initializing:
      case StartupConnectionPhase.connecting:
        return Icons.wifi_find;
      case StartupConnectionPhase.retryMode:
        return Icons.refresh;
      case StartupConnectionPhase.failed:
        return Icons.wifi_off;
      case StartupConnectionPhase.connected:
        return Icons.wifi;
    }
  }

  String _getMainMessage(StartupConnectionState state) {
    switch (state.phase) {
      case StartupConnectionPhase.initializing:
        return 'Starting AICO';
      case StartupConnectionPhase.connecting:
        return 'Connecting to AICO';
      case StartupConnectionPhase.retryMode:
        return 'Retrying Connection';
      case StartupConnectionPhase.failed:
        return 'Backend Offline';
      case StartupConnectionPhase.connected:
        return 'Connected to AICO';
    }
  }
}
