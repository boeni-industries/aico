import 'package:flutter/material.dart';

/// Responsive dialog that adapts its presentation based on screen size
/// - Desktop: Constrained dialog respecting content space
/// - Mobile: Full-screen presentation
/// - Tablet: Hybrid approach with larger dialogs
class AdaptiveDialog extends StatelessWidget {
  final Widget child;
  final String? title;
  final EdgeInsets? padding;
  final bool barrierDismissible;
  final Color? barrierColor;

  const AdaptiveDialog({
    super.key,
    required this.child,
    this.title,
    this.padding,
    this.barrierDismissible = true,
    this.barrierColor,
  });

  /// Show an adaptive dialog based on screen size
  static Future<T?> show<T>({
    required BuildContext context,
    required Widget child,
    String? title,
    EdgeInsets? padding,
    bool barrierDismissible = true,
    Color? barrierColor,
  }) {
    return showDialog<T>(
      context: context,
      barrierDismissible: barrierDismissible,
      barrierColor: barrierColor,
      builder: (context) => AdaptiveDialog(
        title: title,
        padding: padding,
        barrierDismissible: barrierDismissible,
        barrierColor: barrierColor,
        child: child,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final screenHeight = MediaQuery.of(context).size.height;
    final theme = Theme.of(context);

    // Determine layout based on screen size
    final isTablet = screenWidth >= 768 && screenWidth < 1024;
    final isMobile = screenWidth < 768;

    if (isMobile) {
      // Mobile: Full-screen modal with slide-up animation
      return Dialog.fullscreen(
        child: Scaffold(
          appBar: title != null
              ? AppBar(
                  title: Text(title!),
                  backgroundColor: theme.colorScheme.surface,
                  foregroundColor: theme.colorScheme.onSurface,
                )
              : null,
          body: Padding(
            padding: padding ?? const EdgeInsets.all(16),
            child: child,
          ),
        ),
      );
    } else if (isTablet) {
      // Tablet: Large dialog but not full-screen
      return Dialog(
        child: Container(
          constraints: BoxConstraints(
            maxWidth: screenWidth * 0.8,
            maxHeight: screenHeight * 0.8,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (title != null) ...[
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.surfaceContainerHighest,
                    borderRadius: const BorderRadius.only(
                      topLeft: Radius.circular(28),
                      topRight: Radius.circular(28),
                    ),
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: Text(
                          title!,
                          style: theme.textTheme.headlineSmall,
                        ),
                      ),
                      IconButton(
                        onPressed: () => Navigator.of(context).pop(),
                        icon: const Icon(Icons.close),
                      ),
                    ],
                  ),
                ),
              ],
              Flexible(
                child: Padding(
                  padding: padding ?? const EdgeInsets.all(24),
                  child: child,
                ),
              ),
            ],
          ),
        ),
      );
    } else {
      // Desktop: Constrained dialog respecting content space
      return Dialog(
        child: Container(
          constraints: const BoxConstraints(
            maxWidth: 600,
            maxHeight: 700,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (title != null) ...[
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.surfaceContainerHighest,
                    borderRadius: const BorderRadius.only(
                      topLeft: Radius.circular(28),
                      topRight: Radius.circular(28),
                    ),
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: Text(
                          title!,
                          style: theme.textTheme.headlineSmall,
                        ),
                      ),
                      IconButton(
                        onPressed: () => Navigator.of(context).pop(),
                        icon: const Icon(Icons.close),
                        iconSize: 20,
                      ),
                    ],
                  ),
                ),
              ],
              Flexible(
                child: Padding(
                  padding: padding ?? const EdgeInsets.all(24),
                  child: child,
                ),
              ),
            ],
          ),
        ),
      );
    }
  }
}

/// Extension to easily show adaptive dialogs
extension AdaptiveDialogExtension on BuildContext {
  Future<T?> showAdaptiveDialog<T>({
    required Widget child,
    String? title,
    EdgeInsets? padding,
    bool barrierDismissible = true,
    Color? barrierColor,
  }) {
    return AdaptiveDialog.show<T>(
      context: this,
      child: child,
      title: title,
      padding: padding,
      barrierDismissible: barrierDismissible,
      barrierColor: barrierColor,
    );
  }
}
