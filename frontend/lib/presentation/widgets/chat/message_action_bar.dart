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

    // Smooth entrance animation
    _fadeController = AnimationController(
      duration: const Duration(milliseconds: 150),
      vsync: this,
    );

    _fadeAnimation = Tween<double>(
      begin: 0.0,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _fadeController,
      curve: Curves.easeOutCubic,
    ));

    _scaleAnimation = Tween<double>(
      begin: 0.9,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _fadeController,
      curve: Curves.easeOutBack, // Subtle bounce for delight
    ));

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

    // Visual feedback - icon changes to checkmark with glow
    setState(() {
      _executedAction = 'copy';
    });

    // Reset visual feedback after delay - quicker for better flow
    Future.delayed(const Duration(milliseconds: 1200), () {
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
        child: ClipRRect(
          borderRadius: BorderRadius.circular(24),
          child: BackdropFilter(
            filter: ImageFilter.blur(
              sigmaX: 30, // Heavy blur for true frosted glass
              sigmaY: 30,
            ),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
              decoration: BoxDecoration(
                // True glassmorphism - semi-transparent with heavy blur
                color: isDark
                    ? Colors.white.withValues(alpha: 0.05)
                    : Colors.white.withValues(alpha: 0.7),
                borderRadius: BorderRadius.circular(24),
                // Subtle luminous border
                border: Border.all(
                  color: Colors.white.withValues(alpha: isDark ? 0.15 : 0.4),
                  width: 1.5,
                ),
                // Floating elevation
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: isDark ? 0.6 : 0.15),
                    blurRadius: 32,
                    offset: const Offset(0, 8),
                    spreadRadius: -4,
                  ),
                ],
              ),
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
                  
                  // Subtle divider
                  Container(
                    width: 1,
                    height: 20,
                    margin: const EdgeInsets.symmetric(horizontal: 4),
                    color: Colors.white.withValues(alpha: isDark ? 0.1 : 0.2),
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
                      height: 20,
                      margin: const EdgeInsets.symmetric(horizontal: 4),
                      color: Colors.white.withValues(alpha: isDark ? 0.1 : 0.2),
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
                      height: 20,
                      margin: const EdgeInsets.symmetric(horizontal: 4),
                      color: Colors.white.withValues(alpha: isDark ? 0.1 : 0.2),
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
        ),
      ),
    );
  }

  /// Build individual action button with proper styling and states
  Widget _buildActionButton({
    required IconData icon,
    required String tooltip,
    required VoidCallback onTap,
    bool isExecuted = false,
    bool isEnabled = true,
  }) {
    final theme = Theme.of(context);
    
    // Consistent color scheme with rest of app
    final Color iconColor;
    if (!isEnabled) {
      // Inactive state - very subtle
      iconColor = theme.colorScheme.onSurface.withValues(alpha: 0.25);
    } else if (isExecuted) {
      // Success state - accent color
      iconColor = widget.accentColor;
    } else {
      // Active state - consistent with navigation
      iconColor = theme.colorScheme.onSurface.withValues(alpha: 0.7);
    }

    return Tooltip(
      message: tooltip,
      waitDuration: const Duration(milliseconds: 400),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: isEnabled ? onTap : null,
          borderRadius: BorderRadius.circular(GlassTheme.radiusSmall),
          child: Container(
            width: 36,
            height: 36,
            alignment: Alignment.center,
            decoration: isExecuted
                ? BoxDecoration(
                    borderRadius: BorderRadius.circular(GlassTheme.radiusSmall),
                    boxShadow: [
                      // Success glow - beautiful and prominent
                      BoxShadow(
                        color: widget.accentColor.withValues(alpha: 0.5),
                        blurRadius: 16,
                        spreadRadius: 0,
                      ),
                      BoxShadow(
                        color: widget.accentColor.withValues(alpha: 0.3),
                        blurRadius: 32,
                        spreadRadius: 4,
                      ),
                    ],
                  )
                : null,
            child: AnimatedSwitcher(
              duration: const Duration(milliseconds: 200),
              switchInCurve: Curves.easeOutCubic,
              switchOutCurve: Curves.easeInCubic,
              transitionBuilder: (child, animation) {
                return ScaleTransition(
                  scale: Tween<double>(begin: 0.7, end: 1.0).animate(
                    CurvedAnimation(
                      parent: animation,
                      curve: Curves.easeOutBack,
                    ),
                  ),
                  child: FadeTransition(
                    opacity: animation,
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
      ),
    );
  }
}
