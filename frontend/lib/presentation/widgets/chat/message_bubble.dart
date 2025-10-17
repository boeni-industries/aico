import 'dart:async';
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
  static const Duration _minThinkingDuration = Duration(milliseconds: 3000); // Minimum 3s display

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
    
    // Detect when streaming ends (thinking state changes from true to false)
    if (_wasThinking && !widget.isThinking && widget.content.isNotEmpty && !_transitionScheduled) {
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
    // Check if we should still show thinking bubble based on time
    final shouldShowThinking = _thinkingStartTime != null &&
        DateTime.now().difference(_thinkingStartTime!) < _minThinkingDuration;
    
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
              // Text bubble (BOTTOM LAYER - gives Stack a size)
              widget.content.isNotEmpty
                  ? _buildTextBubble(theme)
                  : Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: theme.colorScheme.surface,
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(color: theme.dividerColor.withOpacity(0.1)),
                      ),
                      child: const SizedBox(
                        width: double.infinity,
                        height: 40, // Minimum height for thinking bubble
                      ),
                    ),

              // Thinking bubble ON TOP (TOP LAYER - no background, just particles)
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

    // Just show text bubble
    return _buildTextBubble(theme);
  }

  Widget _buildTextBubble(ThemeData theme) {
    // Trim content to remove leading/trailing whitespace and empty lines
    final trimmedContent = widget.content.trim();
    
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: widget.isFromAico
            ? theme.colorScheme.surface
            : widget.accentColor.withOpacity(0.1),
        borderRadius: BorderRadius.circular(16),
        border: widget.isFromAico
            ? Border.all(color: theme.dividerColor.withOpacity(0.1))
            : null,
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
    );
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
