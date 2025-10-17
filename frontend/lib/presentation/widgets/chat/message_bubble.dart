import 'dart:async';
import 'dart:ui';
import 'package:aico_frontend/presentation/widgets/chat/thinking_bubble.dart';
import 'package:flutter/material.dart';

/// Message bubble widget that displays either a thinking animation or message content
/// Handles smooth transitions between thinking state and text display
class MessageBubble extends StatefulWidget {
  final String content;
  final bool isFromAico;
  final bool isThinking;
  final DateTime timestamp;
  final Color accentColor;

  const MessageBubble({
    super.key,
    required this.content,
    required this.isFromAico,
    required this.isThinking,
    required this.timestamp,
    required this.accentColor,
  });

  @override
  State<MessageBubble> createState() => _MessageBubbleState();
}

class _MessageBubbleState extends State<MessageBubble>
    with SingleTickerProviderStateMixin {
  late AnimationController _fadeController;
  late Animation<double> _bubbleFadeOut;
  bool _wasThinking = false;
  bool _transitionScheduled = false;
  DateTime? _thinkingStartTime;
  Timer? _rebuildTimer;
  static const Duration _minThinkingDuration = Duration(milliseconds: 1500); // Minimum 1.5s display for smooth UX

  @override
  void initState() {
    super.initState();

    _fadeController = AnimationController(
      duration: const Duration(milliseconds: 600),
      vsync: this,
    );

    // Bubble fades out in first half
    _bubbleFadeOut = Tween<double>(begin: 1.0, end: 0.0).animate(
      CurvedAnimation(
        parent: _fadeController,
        curve: const Interval(0.0, 0.5, curve: Curves.easeOut),
      ),
    );

    _wasThinking = widget.isThinking;
    if (widget.isThinking) {
      _thinkingStartTime = DateTime.now();
      // Start timer to force rebuilds every 100ms to check time
      _rebuildTimer = Timer.periodic(const Duration(milliseconds: 100), (timer) {
        if (mounted) {
          setState(() {
            // Just trigger rebuild to check time
          });
        }
      });
    }
    
    // Listen for fade completion
    _fadeController.addStatusListener((status) {
      if (status == AnimationStatus.completed) {
        _rebuildTimer?.cancel();
        _rebuildTimer = null;
        _thinkingStartTime = null;
      }
    });
  }

  @override
  void didUpdateWidget(MessageBubble oldWidget) {
    super.didUpdateWidget(oldWidget);

    // Track when thinking starts
    if (!_wasThinking && widget.isThinking) {
      _wasThinking = true;
      _transitionScheduled = false;
      _thinkingStartTime = DateTime.now();
      _fadeController.reset();
      
      // Start timer to force rebuilds every 100ms to check time
      _rebuildTimer?.cancel();
      _rebuildTimer = Timer.periodic(const Duration(milliseconds: 100), (timer) {
        if (mounted) {
          setState(() {
            // Just trigger rebuild to check time
          });
        }
      });
    }
    
    // Detect when thinking phase fully completes (isThinking becomes false)
    // This happens when both thinking AND response streaming are done
    if (_wasThinking && !widget.isThinking && !_transitionScheduled) {
      _transitionScheduled = true;
      
      // Calculate how long particles have been showing
      final thinkingDuration = _thinkingStartTime != null
          ? DateTime.now().difference(_thinkingStartTime!)
          : Duration.zero;
      
      // ALWAYS delay to ensure minimum display time
      final remainingTime = thinkingDuration < _minThinkingDuration
          ? _minThinkingDuration - thinkingDuration
          : Duration.zero;
      
      Future.delayed(remainingTime, () {
        if (mounted) {
          setState(() {
            _wasThinking = false;
          });
          _fadeController.forward();
        }
      });
    }
  }

  @override
  void dispose() {
    _fadeController.dispose();
    _rebuildTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (widget.isFromAico) ...[
            CircleAvatar(
              radius: 16,
              backgroundColor: widget.accentColor.withOpacity(0.1),
              child: Icon(Icons.face, size: 16, color: widget.accentColor),
            ),
            const SizedBox(width: 12),
          ],
          Expanded(
            child: _buildThinkingOrTransition(theme),
          ),
          if (!widget.isFromAico) const SizedBox(width: 48),
        ],
      ),
    );
  }

  Widget _buildThinkingOrTransition(ThemeData theme) {
    // Show thinking bubble if:
    // 1. Still actively thinking (widget.isThinking = true), OR
    // 2. Within minimum display duration (to prevent flashing)
    final shouldShowThinking = widget.isThinking || 
        (_thinkingStartTime != null &&
         DateTime.now().difference(_thinkingStartTime!) < _minThinkingDuration);
    
    // Stop timer once we're past the minimum duration (fade is triggered elsewhere)
    if (!shouldShowThinking && _rebuildTimer != null && !_fadeController.isAnimating) {
      _rebuildTimer?.cancel();
      _rebuildTimer = null;
    }
    
    // If we should show thinking OR we're in transition
    if (shouldShowThinking || (_fadeController.isAnimating && _bubbleFadeOut.value > 0)) {
      return AnimatedBuilder(
        animation: _fadeController,
        builder: (context, child) {
          return Stack(
            clipBehavior: Clip.none,
            children: [
              // Text bubble (BOTTOM LAYER - always present for proper sizing)
              if (widget.content.isNotEmpty)
                Opacity(
                  opacity: _fadeController.isAnimating 
                      ? (1.0 - _bubbleFadeOut.value).clamp(0.0, 1.0) // Fade in as particles fade out
                      : 0.0, // Stay invisible during thinking phase
                  child: _buildTextBubble(theme),
                )
              else
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Colors.transparent,
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: const SizedBox(
                    width: double.infinity,
                    height: 40, // Minimum height for thinking bubble
                  ),
                ),

              // Thinking bubble ON TOP (TOP LAYER - particles overlay text)
              if (shouldShowThinking || (_fadeController.isAnimating && _bubbleFadeOut.value > 0))
                Positioned.fill(
                  child: IgnorePointer(
                    child: Opacity(
                      opacity: _fadeController.isAnimating ? _bubbleFadeOut.value : 1.0,
                      child: const ThinkingBubble(),
                    ),
                  ),
                ),
            ],
          );
        },
      );
    }

    // After thinking/transition completes, show text bubble only if there's content
    // (prevents showing empty bubble before particles start)
    if (widget.content.isNotEmpty) {
      return _buildTextBubble(theme);
    }
    
    // No content yet - show nothing (particles will appear when shouldShowThinking becomes true)
    return const SizedBox.shrink();
  }

  Widget _buildTextBubble(ThemeData theme) {
    // Trim content to remove leading/trailing whitespace and empty lines
    final trimmedContent = widget.content.trim();
    final isDark = theme.brightness == Brightness.dark;
    
    return ClipRRect(
      borderRadius: BorderRadius.circular(16),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            // Glassmorphism: semi-transparent with backdrop blur
            color: widget.isFromAico
                ? (isDark 
                    ? theme.colorScheme.surfaceContainerHighest.withOpacity(0.7) // Semi-transparent glass
                    : theme.colorScheme.surface.withOpacity(0.9))
                : (isDark
                    ? widget.accentColor.withOpacity(0.2) // Accent tint glass
                    : widget.accentColor.withOpacity(0.15)),
            borderRadius: BorderRadius.circular(16),
            // Subtle glowing border
            border: Border.all(
              color: widget.isFromAico
                  ? (isDark 
                      ? theme.colorScheme.outline.withOpacity(0.2)
                      : theme.dividerColor.withOpacity(0.15))
                  : (isDark
                      ? widget.accentColor.withOpacity(0.3)
                      : widget.accentColor.withOpacity(0.2)),
              width: 1,
            ),
            // Soft glow in dark mode (no shadows)
            boxShadow: isDark ? [
              BoxShadow(
                color: widget.isFromAico
                    ? theme.colorScheme.outline.withOpacity(0.1)
                    : widget.accentColor.withOpacity(0.15),
                blurRadius: 12,
                spreadRadius: 0,
              ),
            ] : [
              BoxShadow(
                color: theme.colorScheme.shadow,
                blurRadius: 4,
                offset: const Offset(0, 2),
              ),
            ],
          ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            trimmedContent,
            style: theme.textTheme.bodyMedium,
          ),
          if (widget.content.isNotEmpty) ...[
            const SizedBox(height: 4),
            Text(
              _formatTimestamp(widget.timestamp),
              style: theme.textTheme.labelSmall?.copyWith(
                color: theme.colorScheme.onSurface.withOpacity(0.6),
              ),
            ),
          ],
        ],
      ),
        ), // Close Container
      ), // Close BackdropFilter
    ); // Close ClipRRect
  }

  String _formatTimestamp(DateTime timestamp) {
    final localTimestamp = timestamp.isUtc ? timestamp.toLocal() : timestamp;
    final now = DateTime.now();
    final diff = now.difference(localTimestamp);

    if (diff.inMinutes < 1) return 'Just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes} minutes ago';
    if (diff.inHours < 24) return '${diff.inHours} hours ago';
    return '${diff.inDays} days ago';
  }
}
