import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Glassmorphic feedback dialog for detailed user feedback
/// 
/// Design Principles:
/// - Fast path: Just thumbs (already submitted)
/// - Detailed path: Quick tags + optional free text
/// - Sub-500ms interactions, non-blocking
/// - Beautiful glassmorphic design matching AICO aesthetic
/// 
/// Flow:
/// 1. User clicks thumbs up/down (immediate feedback sent)
/// 2. Dialog opens with pre-selected sentiment
/// 3. User optionally adds quick tags or free text
/// 4. Submit sends additional context to backend
class FeedbackDialog extends StatefulWidget {
  /// Whether the initial feedback was positive
  final bool isPositive;
  
  /// Message ID for feedback
  final String messageId;
  
  /// Accent color for visual consistency
  final Color accentColor;
  
  /// Callback when feedback is submitted
  final Function(String? reason, String? freeText) onSubmit;

  const FeedbackDialog({
    super.key,
    required this.isPositive,
    required this.messageId,
    required this.accentColor,
    required this.onSubmit,
  });

  @override
  State<FeedbackDialog> createState() => _FeedbackDialogState();
}

class _FeedbackDialogState extends State<FeedbackDialog>
    with SingleTickerProviderStateMixin {
  late AnimationController _slideController;
  late Animation<Offset> _slideAnimation;
  late Animation<double> _fadeAnimation;
  
  // Quick tag selection
  String? _selectedTag;
  
  // Free text input
  final TextEditingController _textController = TextEditingController();
  final FocusNode _textFocusNode = FocusNode();
  
  // Submission state
  bool _isSubmitting = false;

  // Quick tags based on sentiment
  // Quick tag options - only for negative feedback (backend schema)
  // Backend expects: too_verbose, too_brief, wrong_tone, not_helpful, incorrect_info
  List<Map<String, String>> get _quickTags => widget.isPositive
      ? [] // No predefined tags for positive feedback - use free text
      : [
          {'label': 'Too verbose', 'value': 'too_verbose'},
          {'label': 'Too brief', 'value': 'too_brief'},
          {'label': 'Wrong tone', 'value': 'wrong_tone'},
          {'label': 'Not helpful', 'value': 'not_helpful'},
          {'label': 'Incorrect info', 'value': 'incorrect_info'},
        ];

  @override
  void initState() {
    super.initState();

    // Slide up animation with spring physics
    _slideController = AnimationController(
      duration: const Duration(milliseconds: 400),
      vsync: this,
    );

    _slideAnimation = Tween<Offset>(
      begin: const Offset(0, 1),
      end: Offset.zero,
    ).animate(CurvedAnimation(
      parent: _slideController,
      curve: Curves.easeOutCubic,
    ));

    _fadeAnimation = CurvedAnimation(
      parent: _slideController,
      curve: Curves.easeOut,
    );

    // Start animation
    _slideController.forward();
  }

  @override
  void dispose() {
    _slideController.dispose();
    _textController.dispose();
    _textFocusNode.dispose();
    super.dispose();
  }

  /// Handle dialog close
  Future<void> _handleClose() async {
    // Slide down animation
    await _slideController.reverse();
    if (mounted) {
      Navigator.of(context).pop();
    }
  }

  /// Handle feedback submission
  Future<void> _handleSubmit() async {
    if (_isSubmitting) return;

    setState(() {
      _isSubmitting = true;
    });

    // Haptic feedback
    HapticFeedback.lightImpact();

    // Get feedback details
    final reason = _selectedTag;
    final freeText = _textController.text.trim();

    // Call callback
    widget.onSubmit(
      reason,
      freeText.isEmpty ? null : freeText,
    );

    // Close dialog
    await _handleClose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return FadeTransition(
      opacity: _fadeAnimation,
      child: GestureDetector(
        onTap: _handleClose,
        child: Container(
          color: Colors.black.withValues(alpha: 0.5),
          child: GestureDetector(
            onTap: () {}, // Prevent tap through
            child: Align(
              alignment: Alignment.bottomCenter,
              child: SlideTransition(
                position: _slideAnimation,
                child: Container(
                  margin: const EdgeInsets.all(16),
                  constraints: const BoxConstraints(maxWidth: 500),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(28),
                    child: BackdropFilter(
                      filter: ImageFilter.blur(sigmaX: 30, sigmaY: 30),
                      child: Container(
                        decoration: BoxDecoration(
                          color: isDark
                              ? Colors.white.withValues(alpha: 0.06)
                              : Colors.white.withValues(alpha: 0.7),
                          borderRadius: BorderRadius.circular(28),
                          border: Border.all(
                            color: isDark
                                ? Colors.white.withValues(alpha: 0.2)
                                : Colors.white.withValues(alpha: 0.5),
                            width: 1.5,
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withValues(alpha: isDark ? 0.4 : 0.08),
                              blurRadius: 40,
                              offset: const Offset(0, 20),
                              spreadRadius: -10,
                            ),
                          ],
                        ),
                        padding: const EdgeInsets.all(24),
                        child: SingleChildScrollView(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                            // Header
                            _buildHeader(theme, isDark),
                            
                            const SizedBox(height: 24),
                            
                            // Quick tags
                            _buildQuickTags(theme, isDark),
                            
                            const SizedBox(height: 20),
                            
                            // Free text input
                            _buildFreeTextInput(theme, isDark),
                            
                            const SizedBox(height: 24),
                            
                            // Actions
                            _buildActions(theme, isDark),
                          ],
                        ),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  /// Build header with icon and title
  Widget _buildHeader(ThemeData theme, bool isDark) {
    return Row(
      children: [
        // Icon
        Container(
          width: 48,
          height: 48,
          decoration: BoxDecoration(
            color: widget.accentColor.withValues(alpha: 0.15),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Icon(
            widget.isPositive ? Icons.thumb_up_rounded : Icons.thumb_down_rounded,
            color: widget.accentColor,
            size: 24,
          ),
        ),
        
        const SizedBox(width: 16),
        
        // Title
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                widget.isPositive ? 'Great!' : 'Help me improve',
                style: theme.textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.w600,
                  color: theme.colorScheme.onSurface,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                widget.isPositive
                    ? 'Want to share what worked well?'
                    : 'What could I do better?',
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: theme.colorScheme.onSurface.withValues(alpha: 0.7),
                ),
              ),
            ],
          ),
        ),
        
        // Close button
        Material(
          color: Colors.transparent,
          borderRadius: BorderRadius.circular(8),
          child: InkWell(
            onTap: _handleClose,
            borderRadius: BorderRadius.circular(8),
            child: Container(
              width: 32,
              height: 32,
              alignment: Alignment.center,
              child: Icon(
                Icons.close_rounded,
                size: 20,
                color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
              ),
            ),
          ),
        ),
      ],
    );
  }

  /// Build quick tag selection
  Widget _buildQuickTags(ThemeData theme, bool isDark) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Quick feedback (optional)',
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: _quickTags.map((tagMap) {
            final tagValue = tagMap['value']!;
            final tagLabel = tagMap['label']!;
            final isSelected = _selectedTag == tagValue;
            return Material(
              color: Colors.transparent,
              borderRadius: BorderRadius.circular(20),
              child: InkWell(
                onTap: () {
                  HapticFeedback.lightImpact();
                  setState(() {
                    _selectedTag = isSelected ? null : tagValue;
                  });
                },
                borderRadius: BorderRadius.circular(20),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  curve: Curves.easeOut,
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                  decoration: BoxDecoration(
                    color: isSelected
                        ? widget.accentColor.withValues(alpha: 0.2)
                        : (isDark
                            ? Colors.white.withValues(alpha: 0.05)
                            : Colors.black.withValues(alpha: 0.03)),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(
                      color: isSelected
                          ? widget.accentColor.withValues(alpha: 0.5)
                          : (isDark
                              ? Colors.white.withValues(alpha: 0.1)
                              : Colors.black.withValues(alpha: 0.1)),
                      width: 1.5,
                    ),
                  ),
                  child: Text(
                    tagLabel,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: isSelected
                          ? widget.accentColor
                          : theme.colorScheme.onSurface.withValues(alpha: 0.8),
                      fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
                    ),
                  ),
                ),
              ),
            );
          }).toList(),
        ),
      ],
    );
  }

  /// Build free text input
  Widget _buildFreeTextInput(ThemeData theme, bool isDark) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Tell me more (optional)',
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 12),
        Container(
          decoration: BoxDecoration(
            color: isDark
                ? Colors.white.withValues(alpha: 0.05)
                : Colors.black.withValues(alpha: 0.03),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: isDark
                  ? Colors.white.withValues(alpha: 0.1)
                  : Colors.black.withValues(alpha: 0.1),
              width: 1.0,
            ),
          ),
          child: Material(
            color: Colors.transparent,
            child: TextField(
              controller: _textController,
              focusNode: _textFocusNode,
              maxLines: 3,
              maxLength: 500,
              decoration: InputDecoration(
              hintText: 'Any additional thoughts...',
              hintStyle: TextStyle(
                color: theme.colorScheme.onSurface.withValues(alpha: 0.4),
              ),
              border: InputBorder.none,
              contentPadding: const EdgeInsets.all(16),
              counterStyle: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurface.withValues(alpha: 0.4),
              ),
            ),
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurface,
            ),
            ),
          ),
        ),
      ],
    );
  }

  /// Build action buttons
  Widget _buildActions(ThemeData theme, bool isDark) {
    return Row(
      children: [
        // Skip button
        Expanded(
          child: Material(
            color: Colors.transparent,
            borderRadius: BorderRadius.circular(12),
            child: InkWell(
              onTap: _isSubmitting ? null : _handleClose,
              borderRadius: BorderRadius.circular(12),
              child: Container(
                height: 48,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: isDark
                      ? Colors.white.withValues(alpha: 0.05)
                      : Colors.black.withValues(alpha: 0.03),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: isDark
                        ? Colors.white.withValues(alpha: 0.1)
                        : Colors.black.withValues(alpha: 0.1),
                    width: 1.0,
                  ),
                ),
                child: Text(
                  'Skip',
                  style: theme.textTheme.bodyLarge?.copyWith(
                    color: theme.colorScheme.onSurface.withValues(alpha: 0.7),
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ),
          ),
        ),
        
        const SizedBox(width: 12),
        
        // Submit button
        Expanded(
          child: Material(
            color: Colors.transparent,
            borderRadius: BorderRadius.circular(12),
            child: InkWell(
              onTap: _isSubmitting ? null : _handleSubmit,
              borderRadius: BorderRadius.circular(12),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                height: 48,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: widget.accentColor,
                  borderRadius: BorderRadius.circular(12),
                  boxShadow: [
                    BoxShadow(
                      color: widget.accentColor.withValues(alpha: 0.3),
                      blurRadius: 12,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: _isSubmitting
                    ? SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          valueColor: AlwaysStoppedAnimation<Color>(
                            Colors.white.withValues(alpha: 0.9),
                          ),
                        ),
                      )
                    : Text(
                        'Submit',
                        style: theme.textTheme.bodyLarge?.copyWith(
                          color: Colors.white,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}
