import 'package:aico_frontend/presentation/widgets/chat/message_action_bar.dart';
import 'package:aico_frontend/presentation/widgets/chat/message_bubble.dart';
import 'package:flutter/material.dart';

/// Interactive wrapper for MessageBubble that adds hover detection and action bar
/// 
/// Design Principles:
/// - Progressive disclosure: Actions hidden by default
/// - Hover reveals action bar (desktop) with 300ms delay
/// - Long-press reveals action bar (mobile) with haptic feedback
/// - Clean conversation view when not interacting
/// 
/// Implementation follows:
/// - AICO Design Principles: Minimalism, Progressive Disclosure
/// - Information Design: Sub-500ms interactions, Flow State Preservation
/// - Guidelines: Simplicity First, Explicit is Better Than Implicit
class InteractiveMessageBubble extends StatefulWidget {
  final String content;
  final bool isFromAico;
  final bool isThinking;
  final DateTime timestamp;
  final Color accentColor;

  const InteractiveMessageBubble({
    super.key,
    required this.content,
    required this.isFromAico,
    required this.isThinking,
    required this.timestamp,
    required this.accentColor,
  });

  @override
  State<InteractiveMessageBubble> createState() => _InteractiveMessageBubbleState();
}

class _InteractiveMessageBubbleState extends State<InteractiveMessageBubble> {
  bool _isHovered = false;
  bool _showActionBar = false;
  bool _isToolbarHovered = false; // Track if mouse is over the toolbar itself

  /// Handle mouse enter (desktop hover)
  void _onHoverEnter() {
    // Don't show action bar during thinking state or for empty messages
    if (widget.isThinking || widget.content.isEmpty) return;

    setState(() {
      _isHovered = true;
    });

    // Delay action bar appearance for smooth UX (300ms as per design spec)
    Future.delayed(const Duration(milliseconds: 300), () {
      if (mounted && _isHovered) {
        setState(() {
          _showActionBar = true;
        });
      }
    });
  }

  /// Handle mouse exit (desktop hover)
  void _onHoverExit() {
    setState(() {
      _isHovered = false;
    });
    
    // Only hide toolbar if mouse is not over the toolbar itself
    // This allows user to scroll long messages and still access the toolbar
    Future.delayed(const Duration(milliseconds: 100), () {
      if (mounted && !_isHovered && !_isToolbarHovered) {
        setState(() {
          _showActionBar = false;
        });
      }
    });
  }

  /// Handle toolbar hover (keeps toolbar visible even when scrolling)
  void _onToolbarHoverEnter() {
    setState(() {
      _isToolbarHovered = true;
    });
  }

  /// Handle toolbar hover exit
  void _onToolbarHoverExit() {
    setState(() {
      _isToolbarHovered = false;
    });
    
    // Hide toolbar if bubble is also not hovered
    Future.delayed(const Duration(milliseconds: 100), () {
      if (mounted && !_isHovered && !_isToolbarHovered) {
        setState(() {
          _showActionBar = false;
        });
      }
    });
  }

  /// Handle long-press (mobile)
  void _onLongPress() {
    // Don't show action bar during thinking state or for empty messages
    if (widget.isThinking || widget.content.isEmpty) return;

    // Haptic feedback for mobile
    // HapticFeedback.mediumImpact(); // Uncomment when testing on device

    setState(() {
      _showActionBar = !_showActionBar;
    });
  }

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => _onHoverEnter(),
      onExit: (_) => _onHoverExit(),
      child: GestureDetector(
        onLongPress: _onLongPress,
        child: Stack(
          clipBehavior: Clip.none,
          children: [
            // Main message bubble
            MessageBubble(
              content: widget.content,
              isFromAico: widget.isFromAico,
              isThinking: widget.isThinking,
              timestamp: widget.timestamp,
              accentColor: widget.accentColor,
            ),

            // Action bar - positioned to align with bubble's internal content
            // Position from right side only to avoid expansion
            // AICO: bubble padding (20px) from right
            // USER: bubble padding (20px) + right spacing (60px) = 80px
            if (_showActionBar && !widget.isThinking && widget.content.isNotEmpty)
              Positioned(
                top: 16, // Matches bubble's vertical padding
                right: widget.isFromAico ? 20 : 80,
                child: MouseRegion(
                  onEnter: (_) => _onToolbarHoverEnter(),
                  onExit: (_) => _onToolbarHoverExit(),
                  child: MessageActionBar(
                    messageContent: widget.content,
                    isFromAico: widget.isFromAico,
                    accentColor: widget.accentColor,
                    onDismiss: () {
                      setState(() {
                        _showActionBar = false;
                      });
                    },
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
