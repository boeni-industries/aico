import 'dart:async';
import 'dart:io';
import 'dart:math' as math;

import 'package:aico_frontend/presentation/providers/startup_connection_provider.dart';
import 'package:aico_frontend/presentation/widgets/common/animated_button.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

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
  late AnimationController _retryRingController;
  late Animation<double> _pulseAnimation;
  late Animation<double> _progressAnimation;
  late Animation<double> _fadeAnimation;
  late Animation<double> _retryRingAnimation;
  
  Timer? _retryRingTimer;
  bool _isRetryRingActive = false;
  int? _animationStartTime;
  bool _isShowingCompletionAnimation = false;

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
    
    _retryRingController = AnimationController(
      duration: const Duration(seconds: 30), // Initial duration, will be updated dynamically
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
    
    _retryRingAnimation = Tween<double>(
      begin: 0.0,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _retryRingController,
      curve: Curves.linear, // Linear for smooth, consistent progress
    ));

    _pulseController.repeat(reverse: true);
    _fadeController.forward();
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _progressController.dispose();
    _fadeController.dispose();
    _retryRingController.dispose();
    _retryRingTimer?.cancel();
    super.dispose();
  }

  void _updateAnimations(StartupConnectionState state) {
    if (state.isInProgress) {
      if (!_pulseController.isAnimating) {
        _pulseController.repeat(reverse: true);
      }
      
      // For initial connection (attempt 0), show smooth progress animation
      if (state.currentAttempt == 0 && state.phase == StartupConnectionPhase.connecting) {
        // Reset to 0 and animate to 1 over 4 seconds for initial attempt
        _progressController.reset();
        _progressController.animateTo(1.0, duration: const Duration(seconds: 4));
        _stopRetryRingAnimation();
      } else if (state.phase == StartupConnectionPhase.retryMode) {
        // Start independent retry ring animation only once when entering retry mode
        _startRetryRingAnimation();
        // Keep progress ring at 0 during retry mode - retry ring shows progress
        _progressController.reset();
      }
    } else {
      _pulseController.stop();
      
      if (state.isConnected) {
        // If we were in retry mode, smoothly transition from retry ring progress to completion
        if (_isRetryRingActive) {
          final currentRetryProgress = _retryRingAnimation.value;
          debugPrint('Connection successful during retry mode at ${(currentRetryProgress * 100).toInt()}% progress');
          _stopRetryRingAnimation();
          // Start progress ring from current retry progress and animate to completion
          _progressController.value = currentRetryProgress;
          _progressController.animateTo(1.0, duration: const Duration(milliseconds: 500));
        } else {
          _progressController.animateTo(1.0, duration: const Duration(milliseconds: 300));
        }
      } else if (state.isFailed) {
        // If retry ring was active, complete it to 100% for proper UX closure
        if (_isRetryRingActive) {
          debugPrint('Connection failed - completing retry ring to 100% for UX closure');
          _isShowingCompletionAnimation = true;
          _retryRingController.animateTo(1.0, duration: const Duration(milliseconds: 800));
          // Stop the retry ring after completion animation
          Timer(const Duration(milliseconds: 1000), () {
            _isShowingCompletionAnimation = false;
            _stopRetryRingAnimation();
            // Trigger UI rebuild to show failed state
            if (mounted) {
              setState(() {});
            }
            // Only animate progress ring to 0 after retry ring completion is visible
            _progressController.animateTo(0.0, duration: const Duration(milliseconds: 300));
          });
        } else {
          _progressController.animateTo(0.0, duration: const Duration(milliseconds: 300));
        }
      }
    }
  }
  
  void _startRetryRingAnimation() {
    if (!_isRetryRingActive) {
      _isRetryRingActive = true;
      _animationStartTime = DateTime.now().millisecondsSinceEpoch;
      _retryRingController.reset();
      
      // Calculate actual retry cycle duration based on exponential backoff
      final actualDuration = _calculateActualRetryDuration();
      
      debugPrint('Starting retry ring animation with duration: ${actualDuration.inSeconds}s');
      
      // Update animation duration to match actual retry timing
      _retryRingController.duration = actualDuration;
      _retryRingController.forward();
      
      // Add listener to debug animation progress
      _retryRingController.addListener(() {
        if (_retryRingController.value % 0.1 < 0.01) { // Log every 10%
          final elapsed = DateTime.now().millisecondsSinceEpoch - _animationStartTime!;
          debugPrint('Retry ring progress: ${(_retryRingController.value * 100).toInt()}% at ${elapsed}ms elapsed');
        }
      });
      
      // Set timer to complete animation after actual duration
      _retryRingTimer = Timer(actualDuration, () {
        debugPrint('Retry ring timer completed, stopping animation');
        _stopRetryRingAnimation();
      });
    }
  }
  
  Duration _calculateActualRetryDuration() {
    // Calculate total retry cycle duration matching StartupConnectionProvider's ACTUAL logic
    // The provider has a bug: it passes (nextAttempt - 2) to _calculateRetryDelay
    const baseDelayMs = 3000; // 3 second base
    const maxDelayMs = 12000; // 12 seconds max
    const connectionTestMs = 2000; // 2 seconds per connection test
    const maxJitterMs = 1000; // Maximum jitter
    
    int totalMs = 0;
    
    // Match the actual buggy parameter passing in StartupConnectionProvider
    // nextAttempt values: 1, 2, 3 → _calculateRetryDelay gets: -1, 0, 1
    final actualAttemptParams = [-1, 0, 1];
    
    for (int i = 0; i < 3; i++) {
      final attemptParam = actualAttemptParams[i];
      final exponentialDelay = (baseDelayMs * math.pow(2, attemptParam)).toInt();
      final clampedDelay = exponentialDelay.clamp(baseDelayMs, maxDelayMs);
      totalMs += clampedDelay + maxJitterMs + connectionTestMs;
      
      debugPrint('Retry ${i+1}: attemptParam=$attemptParam, delay=${clampedDelay}ms, total so far=${totalMs}ms');
    }
    
    final duration = Duration(milliseconds: totalMs);
    debugPrint('Total calculated retry duration: ${duration.inSeconds}s (${totalMs}ms)');
    return duration;
  }
  
  void _stopRetryRingAnimation() {
    debugPrint('Stopping retry ring animation at ${(_retryRingController.value * 100).toInt()}% progress');
    _isRetryRingActive = false;
    _retryRingTimer?.cancel();
    _retryRingTimer = null;
    _retryRingController.reset();
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
    
    // Override state to show retry mode during completion animation
    final displayState = _isShowingCompletionAnimation && state.isFailed
        ? state.copyWith(phase: StartupConnectionPhase.retryMode)
        : state;
    
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
                padding: EdgeInsets.symmetric(
                  horizontal: 24, 
                  vertical: math.max(32, MediaQuery.of(context).padding.top + 16),
                ),
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
                        _buildConnectionIndicator(theme, displayState),
                        const SizedBox(height: 32),
                        _buildStatusContent(theme, displayState),
                      ],
                    ),
                  ),
                  
                  // Action buttons (only when failed and not showing completion animation)
                  if (state.isFailed && !_isShowingCompletionAnimation) ...[
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
          
          // Progress ring - shows initial connection or retry ring animation
          AnimatedBuilder(
            animation: state.phase == StartupConnectionPhase.retryMode 
                ? _retryRingAnimation 
                : _progressAnimation,
            builder: (context, child) {
              double progressValue;
              if (state.isFailed) {
                progressValue = 0.0;
              } else if (state.phase == StartupConnectionPhase.retryMode) {
                progressValue = _retryRingAnimation.value;
              } else {
                progressValue = _progressAnimation.value;
              }
              
              return SizedBox(
                width: 80,
                height: 80,
                child: CircularProgressIndicator(
                  value: progressValue,
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
    return Container(
      constraints: const BoxConstraints(
        minHeight: 80,
        maxHeight: 120,
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
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
            maxLines: 2, // Allow wrapping for very long messages
            overflow: TextOverflow.ellipsis,
          ),
          
          const SizedBox(height: 16),
          
          // Secondary message - flexible height with fixed constraints
          if (state.message != null)
            Flexible(
              child: Container(
                constraints: const BoxConstraints(
                  minHeight: 20,
                  maxHeight: 80,
                ),
                child: Center(
                  child: Text(
                    state.message!,
                    style: const TextStyle(
                      fontFamily: 'Inter',
                      fontSize: 16, // 1.0rem body
                      fontWeight: FontWeight.w400,
                      color: Color(0xFF6B7280),
                    ),
                    textAlign: TextAlign.center,
                    maxLines: 4, // Allow more lines if space permits
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
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
          child: SizedBox(
            height: 48, // Design principle: proper button height
            child: AnimatedButton(
              onPressed: _handleClose,
              icon: Icons.close,
              size: 48,
              borderRadius: 24,
              backgroundColor: Theme.of(context).brightness == Brightness.dark
                  ? Theme.of(context).colorScheme.primary.withOpacity(0.15)
                  : Theme.of(context).colorScheme.primary.withOpacity(0.12),
              foregroundColor: Theme.of(context).colorScheme.primary,
              tooltip: 'Close',
            ),
          ),
        ),
        const SizedBox(width: 12),
        // Retry button - equal width, aligned with content above
        Expanded(
          child: SizedBox(
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
