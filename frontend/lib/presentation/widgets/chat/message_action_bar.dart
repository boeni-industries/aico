import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'package:aico_frontend/presentation/theme/glassmorphism.dart';

/// Glassmorphic action toolbar that appears on message bubble hover/long-press
/// Implements progressive disclosure with award-winning visual fidelity
/// 
/// Design Principles:
/// - Hidden by default (clean conversation)
/// - Appears on hover (desktop) or long-press (mobile)
/// - Heavy glassmorphism with proper borders and shadows
/// - Context-sensitive actions (user vs AICO messages)
/// - Consistent icon styling with rest of app
/// - Clear inactive states for unimplemented features
class MessageActionBar extends StatefulWidget {
  /// Message content for actions (e.g., copy text)
  final String messageContent;
  
  /// Whether this is an AICO message (affects available actions)
  final bool isFromAico;
  
  /// Accent color for visual consistency
  final Color accentColor;
  
  /// Callback when action bar should be dismissed
  final VoidCallback? onDismiss;

  const MessageActionBar({
    super.key,
    required this.messageContent,
    required this.isFromAico,
    required this.accentColor,
    this.onDismiss,
  });

  @override
  State<MessageActionBar> createState() => _MessageActionBarState();
}

class _MessageActionBarState extends State<MessageActionBar>
    with SingleTickerProviderStateMixin {
  late AnimationController _fadeController;
  late Animation<double> _fadeAnimation;
  late Animation<double> _scaleAnimation;

  // Track which action was just executed for visual feedback
  String? _executedAction;

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
          padding: const EdgeInsets.symmetric(horizontal: 2, vertical: 2),
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
                    margin: const EdgeInsets.symmetric(horizontal: 6),
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
                    icon: Icons.auto_awesome_rounded,
                    tooltip: 'Remember this',
                    onTap: () {}, // TODO: Implement
                    isEnabled: false,
                  ),
                  
                  // AICO-specific actions
                  if (widget.isFromAico) ...[
                    // Divider
                    Container(
                      width: 1,
                      height: 24,
                      margin: const EdgeInsets.symmetric(horizontal: 6),
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
                    
                    // This Helped
                    _buildActionButton(
                      icon: Icons.favorite_rounded,
                      tooltip: 'This helped',
                      onTap: () {}, // TODO: Implement
                      isEnabled: false,
                    ),
                    
                    // Divider
                    Container(
                      width: 1,
                      height: 24,
                      margin: const EdgeInsets.symmetric(horizontal: 6),
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
                    
                    // Not Quite
                    _buildActionButton(
                      icon: Icons.lightbulb_outline_rounded,
                      tooltip: 'Not quite',
                      onTap: () {}, // TODO: Implement
                      isEnabled: false,
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
  }) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    
    // Clear, prominent color scheme
    final Color iconColor;
    if (!isEnabled) {
      iconColor = theme.colorScheme.onSurface.withValues(alpha: 0.3);
    } else if (isExecuted) {
      // More prominent success color
      iconColor = widget.accentColor;
    } else {
      iconColor = theme.colorScheme.onSurface.withValues(alpha: 0.7);
    }

    return Tooltip(
      message: tooltip,
      waitDuration: const Duration(milliseconds: 500),
      child: Material(
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
            // More visible background
            decoration: BoxDecoration(
              color: isExecuted
                  ? widget.accentColor.withValues(alpha: 0.25) // More visible
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
                size: 16,
                color: iconColor,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
