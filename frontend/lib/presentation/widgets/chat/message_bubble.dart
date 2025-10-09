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
    with TickerProviderStateMixin {
  late AnimationController _fadeController;
  late AnimationController _glintController;
  late Animation<double> _bubbleFadeOut;
  late Animation<double> _textFadeIn;
  late Animation<double> _glintPosition;
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

    // Text fades in during second half
    _textFadeIn = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _fadeController,
        curve: const Interval(0.5, 1.0, curve: Curves.easeIn),
      ),
    );

    // Glint animation - sweeps across the bubble edge (slower, more elegant)
    _glintController = AnimationController(
      duration: const Duration(milliseconds: 3500), // Slower sweep
      vsync: this,
    );
    
    _glintPosition = Tween<double>(begin: -0.5, end: 1.5).animate(
      CurvedAnimation(
        parent: _glintController,
        curve: Curves.easeInOut,
      ),
    );

    _wasThinking = widget.isThinking;
    if (widget.isThinking) {
      _thinkingStartTime = DateTime.now();
      _glintController.repeat(); // Start glint animation when thinking begins
      print('🎨 [INIT] Started glint animation');
    }
    
    // Listen for fade completion
    _fadeController.addStatusListener((status) {
      if (status == AnimationStatus.completed) {
        _rebuildTimer?.cancel();
        _rebuildTimer = null;
        _thinkingStartTime = null;
        print('🎨 [Animation] Fade completed, cleaned up');
      }
    });
  }

  @override
  void didUpdateWidget(MessageBubble oldWidget) {
    super.didUpdateWidget(oldWidget);

    // Debug logging
    if (widget.isThinking != oldWidget.isThinking) {
      print('🎨 [MessageBubble] isThinking changed: ${oldWidget.isThinking} → ${widget.isThinking}');
      print('🎨 [MessageBubble] content: "${widget.content}"');
      print('🎨 [MessageBubble] isFromAico: ${widget.isFromAico}');
    }

    // Track when thinking starts
    if (!_wasThinking && widget.isThinking) {
      _wasThinking = true;
      _transitionScheduled = false;
      _thinkingStartTime = DateTime.now();
      _fadeController.reset();
      _glintController.repeat(); // Start glint animation
      print('🎨 [MessageBubble] Started thinking animation');
      
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
      
      print('🎨 [STREAMING_EVENT] Streaming ended, content received');
      
      // Calculate how long particles have been showing
      final thinkingDuration = _thinkingStartTime != null
          ? DateTime.now().difference(_thinkingStartTime!)
          : Duration.zero;
      
      print('🎨 [MessageBubble] Thinking duration: ${thinkingDuration.inMilliseconds}ms');
      
      // ALWAYS delay to ensure minimum display time
      final remainingTime = thinkingDuration < _minThinkingDuration
          ? _minThinkingDuration - thinkingDuration
          : Duration.zero;
      
      print('🎨 [MessageBubble] Will transition after ${remainingTime.inMilliseconds}ms');
      
      Future.delayed(remainingTime, () {
        if (mounted) {
          // Stop glint animation when streaming actually ends
          _glintController.stop();
          print('🎨 [STREAMING_EVENT] Stopped glint animation');
          
          setState(() {
            _wasThinking = false;
          });
          _fadeController.forward();
          print('🎨 [MessageBubble] Starting fade transition now');
        }
      });
    }
  }

  @override
  void dispose() {
    _fadeController.dispose();
    _glintController.dispose();
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
      print('🎨 [BUILD] Stopped rebuild timer');
    }
    
    print('🎨 [BUILD] shouldShowThinking: $shouldShowThinking, isAnimating: ${_fadeController.isAnimating}, fadeValue: ${_bubbleFadeOut.value}');
    
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

  Widget _buildMessageContent(ThemeData theme) {
    return _buildTextBubble(theme);
  }

  Widget _buildTextBubble(ThemeData theme) {
    // Check if we should show glint
    final showGlint = _glintController.isAnimating;
    
    if (showGlint) {
      print('🎨 [GLINT] Rendering glint at position: ${_glintPosition.value}');
    }
    
    return AnimatedBuilder(
      animation: _glintController,
      builder: (context, child) {
        return CustomPaint(
          painter: showGlint ? _GlintBorderPainter(
            glintPosition: _glintPosition.value,
            borderRadius: 16.0,
            accentColor: widget.accentColor,
          ) : null,
          child: Container(
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
                  widget.content,
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
          ),
        );
      },
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

/// Custom painter for the glint effect that sweeps around the border
class _GlintBorderPainter extends CustomPainter {
  final double glintPosition; // -1.0 to 2.0
  final double borderRadius;
  final Color accentColor;

  _GlintBorderPainter({
    required this.glintPosition,
    required this.borderRadius,
    required this.accentColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Rect.fromLTWH(0, 0, size.width, size.height);
    final rrect = RRect.fromRectAndRadius(rect, Radius.circular(borderRadius));
    
    // Calculate the path length around the border
    final perimeter = 2 * (size.width + size.height);
    final glintLength = perimeter * 0.15; // Glint covers 15% of perimeter
    
    // Map glintPosition (-1.0 to 2.0) to actual position on perimeter
    final currentPos = glintPosition * perimeter;
    
    // Create paint for drawing glint points
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.0;
    
    // Draw the glint as individual points along the border
    for (double i = 0; i < perimeter; i += 1.0) {
      final distanceFromGlint = (i - currentPos).abs();
      
      if (distanceFromGlint < glintLength) {
        // Calculate opacity based on distance from glint center
        final normalizedDist = distanceFromGlint / glintLength;
        final opacity = (1.0 - normalizedDist) * 0.6; // Max 60% opacity
        
        paint.color = accentColor.withOpacity(opacity);
        
        // Calculate position on border
        final point = _getPointOnBorder(i, size, borderRadius);
        canvas.drawCircle(point, 1.5, paint);
      }
    }
  }
  
  Offset _getPointOnBorder(double distance, Size size, double radius) {
    final w = size.width;
    final h = size.height;
    final perimeter = 2 * (w + h);
    final normalizedDist = distance % perimeter;
    
    // Top edge
    if (normalizedDist < w) {
      return Offset(normalizedDist, 0);
    }
    // Right edge
    else if (normalizedDist < w + h) {
      return Offset(w, normalizedDist - w);
    }
    // Bottom edge
    else if (normalizedDist < 2 * w + h) {
      return Offset(w - (normalizedDist - w - h), h);
    }
    // Left edge
    else {
      return Offset(0, h - (normalizedDist - 2 * w - h));
    }
  }

  @override
  bool shouldRepaint(_GlintBorderPainter oldDelegate) {
    return oldDelegate.glintPosition != glintPosition;
  }
}
