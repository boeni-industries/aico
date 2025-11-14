import 'package:aico_frontend/presentation/providers/memory_album_provider.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Glassmorphic action toolbar that appears on message bubble hover/long-press
/// Implements progressive disclosure with relationship-first design
/// 
/// Design Principles:
/// - Hidden by default (clean conversation)
/// - Appears on hover (desktop) or long-press (mobile)
/// - Sub-500ms interactions, non-blocking
/// - Context-sensitive actions (user vs AICO messages)
/// - Ambient emotional feedback through avatar presence
/// 
/// Actions:
/// - User Messages: [Copy] | [Remember]
/// - AICO Messages: [Copy] | [Remember] [Regenerate]
class MessageActionBar extends ConsumerStatefulWidget {
  /// Message content for actions (e.g., copy text)
  final String messageContent;
  
  /// Whether this is an AICO message (affects available actions)
  final bool isFromAico;
  
  /// Accent color for visual consistency
  final Color accentColor;
  
  /// Callback when action bar should be dismissed
  final VoidCallback? onDismiss;
  
  /// Message ID for remembering
  final String? messageId;
  
  /// Conversation ID for remembering
  final String? conversationId;
  
  /// Callback when feedback is submitted (thumbs up/down)
  final Function(bool isPositive)? onFeedback;

  const MessageActionBar({
    super.key,
    required this.messageContent,
    required this.isFromAico,
    required this.accentColor,
    this.onDismiss,
    this.messageId,
    this.conversationId,
    this.onFeedback,
  });

  @override
  ConsumerState<MessageActionBar> createState() => _MessageActionBarState();
}

class _MessageActionBarState extends ConsumerState<MessageActionBar>
    with SingleTickerProviderStateMixin {
  late AnimationController _fadeController;
  late Animation<double> _fadeAnimation;
  late Animation<double> _scaleAnimation;

  // Track which action was just executed for visual feedback
  String? _executedAction;
  
  // Track feedback state (null = no feedback, true = thumbs up, false = thumbs down)
  bool? _feedbackGiven;

  @override
  void initState() {
    super.initState();

    // Smooth entrance with spring physics
    _fadeController = AnimationController(
      duration: const Duration(milliseconds: 200),
      vsync: this,
    );

    _fadeAnimation = CurvedAnimation(
      parent: _fadeController,
      curve: Curves.easeOut,
    );

    _scaleAnimation = CurvedAnimation(
      parent: _fadeController,
      curve: Curves.easeOutCubic,
    );

    // Start animation
    _fadeController.forward();
  }

  @override
  void dispose() {
    _fadeController.dispose();
    super.dispose();
  }

  /// Copy message text to clipboard
  Future<void> _handleCopyText() async {
    if (widget.messageContent.isEmpty) return;

    // Haptic feedback
    HapticFeedback.lightImpact();

    // Copy to clipboard
    await Clipboard.setData(ClipboardData(text: widget.messageContent));

    // Visual feedback - smooth sine wave animation
    setState(() {
      _executedAction = 'copy';
    });

    // Reset after animation completes
    Future.delayed(const Duration(milliseconds: 700), () {
      if (mounted) {
        setState(() {
          _executedAction = null;
        });
      }
    });
  }
  
  /// Handle feedback (thumbs up/down)
  Future<void> _handleFeedback(bool isPositive) async {
    if (widget.messageId == null) return;

    // Haptic feedback
    HapticFeedback.lightImpact();

    // Update feedback state
    setState(() {
      _feedbackGiven = isPositive;
      _executedAction = isPositive ? 'thumbs_up' : 'thumbs_down';
    });

    // Call callback to open detailed feedback dialog
    widget.onFeedback?.call(isPositive);

    // Reset executed action after animation
    Future.delayed(const Duration(milliseconds: 700), () {
      if (mounted) {
        setState(() {
          _executedAction = null;
        });
      }
    });
  }
  
  /// Remember this message
  Future<void> _handleRememberThis() async {
    if (widget.messageContent.isEmpty) return;
    if (widget.messageId == null || widget.conversationId == null) return;

    // Haptic feedback
    HapticFeedback.lightImpact();

    // Show visual feedback immediately
    setState(() {
      _executedAction = 'remember';
    });

    try {
      // Save to Memory Album
      final memoryId = await ref.read(memoryAlbumProvider.notifier).rememberMessage(
        conversationId: widget.conversationId!,
        messageId: widget.messageId!,
        content: widget.messageContent,
      );

      if (memoryId != null) {
        // Success - keep checkmark visible longer
        await Future.delayed(const Duration(milliseconds: 1000));
      }
    } catch (e) {
      // Error - could show error state
      debugPrint('Failed to save memory: $e');
    }

    // Reset after animation completes
    if (mounted) {
      setState(() {
        _executedAction = null;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return FadeTransition(
      opacity: _fadeAnimation,
      child: ScaleTransition(
        scale: _scaleAnimation,
        child: Container(
          decoration: BoxDecoration(
            // Semi-transparent background - matches bubble better
            color: isDark
                ? const Color(0xFF2F3241).withValues(alpha: 0.92) // Elevated surface
                : const Color(0xFFF5F6FA).withValues(alpha: 0.92), // Background tint
            borderRadius: BorderRadius.circular(12),
            // Minimal border
            border: Border.all(
              color: isDark
                  ? Colors.white.withValues(alpha: 0.1)
                  : Colors.black.withValues(alpha: 0.08),
              width: 1.0,
            ),
            // Subtle shadow
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: isDark ? 0.3 : 0.06),
                blurRadius: 12,
                offset: const Offset(0, 2),
                spreadRadius: 0,
              ),
            ],
          ),
          padding: const EdgeInsets.all(10),
            child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Copy Text (Universal)
                  _buildActionButton(
                    icon: _executedAction == 'copy' ? Icons.check_rounded : Icons.content_copy_rounded,
                    tooltip: 'Copy message',
                    onTap: _handleCopyText,
                    isExecuted: _executedAction == 'copy',
                    isEnabled: true,
                  ),
                  
                  // Divider with gradient for depth
                  Container(
                    width: 1,
                    height: 24,
                    margin: const EdgeInsets.symmetric(horizontal: 8),
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: [
                          Colors.white.withValues(alpha: 0.0),
                          Colors.white.withValues(alpha: isDark ? 0.2 : 0.3),
                          Colors.white.withValues(alpha: 0.0),
                        ],
                      ),
                    ),
                  ),
                  
                  // Remember This (Universal)
                  _buildActionButton(
                    icon: _executedAction == 'remember' ? Icons.check_rounded : Icons.auto_awesome_rounded,
                    tooltip: 'Remember this',
                    onTap: _handleRememberThis,
                    isExecuted: _executedAction == 'remember',
                    isEnabled: widget.messageId != null && widget.conversationId != null,
                  ),
                  
                  // AICO-specific actions
                  if (widget.isFromAico) ...[
                    // Divider
                    Container(
                      width: 1,
                      height: 24,
                      margin: const EdgeInsets.symmetric(horizontal: 8),
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          begin: Alignment.topCenter,
                          end: Alignment.bottomCenter,
                          colors: [
                            Colors.white.withValues(alpha: 0.0),
                            Colors.white.withValues(alpha: isDark ? 0.2 : 0.3),
                            Colors.white.withValues(alpha: 0.0),
                          ],
                        ),
                      ),
                    ),
                    
                    // Thumbs Up
                    _buildActionButton(
                      icon: _executedAction == 'thumbs_up' 
                          ? Icons.check_rounded 
                          : (_feedbackGiven == true ? Icons.thumb_up : Icons.thumb_up_outlined),
                      tooltip: 'Helpful response',
                      onTap: () => _handleFeedback(true),
                      isExecuted: _executedAction == 'thumbs_up',
                      isEnabled: widget.messageId != null && widget.onFeedback != null,
                      isActive: _feedbackGiven == true,
                    ),
                    
                    // Thumbs Down
                    _buildActionButton(
                      icon: _executedAction == 'thumbs_down'
                          ? Icons.check_rounded
                          : (_feedbackGiven == false ? Icons.thumb_down : Icons.thumb_down_outlined),
                      tooltip: 'Needs improvement',
                      onTap: () => _handleFeedback(false),
                      isExecuted: _executedAction == 'thumbs_down',
                      isEnabled: widget.messageId != null && widget.onFeedback != null,
                      isActive: _feedbackGiven == false,
                    ),
                  ],
                ],
              ),
        ),
      ),
    );
  }

  /// Build individual action button with clear hover and active states
  Widget _buildActionButton({
    required IconData icon,
    required String tooltip,
    required VoidCallback onTap,
    bool isExecuted = false,
    bool isEnabled = true,
    bool isActive = false,
  }) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    
    // Consistent color scheme with conversation toolbar
    final Color iconColor;
    if (!isEnabled) {
      iconColor = theme.colorScheme.onSurface.withValues(alpha: 0.3);
    } else if (isExecuted) {
      // Bright success state - accent color
      iconColor = widget.accentColor;
    } else if (isActive) {
      // Active feedback state - full accent color
      iconColor = widget.accentColor;
    } else {
      // Normal state - accent color (consistent with toolbar)
      iconColor = widget.accentColor;
    }

    return Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(8),
        child: InkWell(
          onTap: isEnabled ? onTap : null,
          borderRadius: BorderRadius.circular(8),
          // More visible hover effect
          hoverColor: isDark
              ? Colors.white.withValues(alpha: 0.1)
              : Colors.black.withValues(alpha: 0.05),
          splashColor: widget.accentColor.withValues(alpha: 0.2),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 350),
            curve: Curves.easeOutCubic,
            width: 32,
            height: 32,
            alignment: Alignment.center,
            // Prominent background highlight
            decoration: BoxDecoration(
              color: (isExecuted || isActive)
                  ? widget.accentColor.withValues(alpha: 0.35) // Much more visible
                  : Colors.transparent,
              borderRadius: BorderRadius.circular(8),
            ),
            child: AnimatedSwitcher(
              duration: const Duration(milliseconds: 300),
              switchInCurve: Curves.easeOutCubic,
              switchOutCurve: Curves.easeInCubic,
              transitionBuilder: (child, animation) {
                return FadeTransition(
                  opacity: animation,
                  child: ScaleTransition(
                    scale: Tween<double>(begin: 0.8, end: 1.0).animate(animation),
                    child: child,
                  ),
                );
              },
              child: Icon(
                icon,
                key: ValueKey(icon),
                size: 18,
                color: iconColor,
              ),
            ),
          ),
        ),
      );
  }
}
