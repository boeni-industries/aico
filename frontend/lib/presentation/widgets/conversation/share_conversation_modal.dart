import 'dart:ui';

import 'package:aico_frontend/presentation/theme/glassmorphism.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Stunning glassmorphic modal for sharing/exporting conversations
/// 
/// Design Philosophy:
/// - Slides up from bottom with spring physics
/// - Heavy glassmorphism with purple accents
/// - Clear format selection with visual previews
/// - Privacy controls with explanations
/// - Beautiful micro-interactions throughout
/// 
/// Phase 1 Features:
/// - Export to text file (markdown format)
/// - Privacy: Remove personal info toggle
/// - Local file save (no cloud upload)
class ShareConversationModal extends StatefulWidget {
  /// Accent color for visual consistency
  final Color accentColor;
  
  /// Callback when export is confirmed
  final Function(ShareConversationConfig)? onExport;

  const ShareConversationModal({
    super.key,
    required this.accentColor,
    this.onExport,
  });

  @override
  State<ShareConversationModal> createState() => _ShareConversationModalState();
}

class _ShareConversationModalState extends State<ShareConversationModal>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _slideAnimation;
  late Animation<double> _fadeAnimation;
  
  // Export configuration
  ExportFormat _selectedFormat = ExportFormat.markdown;
  
  @override
  void initState() {
    super.initState();
    
    // Smooth entrance animation
    _controller = AnimationController(
      duration: const Duration(milliseconds: 400),
      vsync: this,
    );
    
    _slideAnimation = CurvedAnimation(
      parent: _controller,
      curve: Curves.easeOutCubic,
    );
    
    _fadeAnimation = CurvedAnimation(
      parent: _controller,
      curve: Curves.easeOut,
    );
    
    // Start animation
    _controller.forward();
  }
  
  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }
  
  Future<void> _handleClose() async {
    try {
      await _controller.reverse();
      if (mounted && Navigator.canPop(context)) {
        Navigator.of(context).pop();
      }
    } catch (e) {
      // Silently handle navigation errors
      if (mounted && Navigator.canPop(context)) {
        Navigator.of(context).pop();
      }
    }
  }
  
  void _handleExport() {
    HapticFeedback.mediumImpact();
    
    final config = ShareConversationConfig(
      format: _selectedFormat,
    );
    
    widget.onExport?.call(config);
    _handleClose();
  }
  
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final screenHeight = MediaQuery.of(context).size.height;
    
    return GestureDetector(
      onTap: _handleClose,
      child: Container(
        color: Colors.black.withValues(alpha: 0.6),
        child: FadeTransition(
          opacity: _fadeAnimation,
          child: Stack(
            children: [
              // Backdrop blur
              BackdropFilter(
                filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
                child: Container(color: Colors.transparent),
              ),
              
              // Modal content
              Align(
                alignment: Alignment.bottomCenter,
                child: SlideTransition(
                  position: Tween<Offset>(
                    begin: const Offset(0, 1),
                    end: Offset.zero,
                  ).animate(_slideAnimation),
                  child: GestureDetector(
                    onTap: () {}, // Prevent tap-through
                    child: Container(
                      constraints: BoxConstraints(
                        maxHeight: screenHeight * 0.75,
                        maxWidth: 600,
                      ),
                      margin: const EdgeInsets.all(16),
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(GlassTheme.radiusXLarge),
                        child: BackdropFilter(
                          filter: ImageFilter.blur(
                            sigmaX: GlassTheme.blurHeavy,
                            sigmaY: GlassTheme.blurHeavy,
                          ),
                          child: Container(
                            decoration: BoxDecoration(
                              color: isDark
                                  ? Colors.white.withValues(alpha: 0.08)
                                  : Colors.white.withValues(alpha: 0.85),
                              borderRadius: BorderRadius.circular(GlassTheme.radiusXLarge),
                              border: Border.all(
                                color: isDark
                                    ? Colors.white.withValues(alpha: 0.2)
                                    : Colors.white.withValues(alpha: 0.6),
                                width: 1.5,
                              ),
                              boxShadow: [
                                BoxShadow(
                                  color: Colors.black.withValues(alpha: isDark ? 0.5 : 0.15),
                                  blurRadius: 60,
                                  offset: const Offset(0, 20),
                                  spreadRadius: -10,
                                ),
                                BoxShadow(
                                  color: widget.accentColor.withValues(alpha: 0.15),
                                  blurRadius: 80,
                                  spreadRadius: -5,
                                ),
                              ],
                            ),
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                _buildHeader(theme, isDark),
                                Flexible(
                                  child: SingleChildScrollView(
                                    padding: const EdgeInsets.all(24),
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        _buildFormatSelection(theme, isDark),
                                      ],
                                    ),
                                  ),
                                ),
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
            ],
          ),
        ),
      ),
    );
  }
  
  Widget _buildHeader(ThemeData theme, bool isDark) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(
            color: theme.dividerColor.withValues(alpha: 0.1),
            width: 1,
          ),
        ),
      ),
      child: Row(
        children: [
          // Icon with glow
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: widget.accentColor.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(16),
              boxShadow: [
                BoxShadow(
                  color: widget.accentColor.withValues(alpha: 0.3),
                  blurRadius: 20,
                  spreadRadius: 0,
                ),
              ],
            ),
            child: Icon(
              Icons.ios_share_rounded,
              color: widget.accentColor,
              size: 28,
            ),
          ),
          
          const SizedBox(width: 16),
          
          // Title
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Share Conversation',
                  style: theme.textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.w600,
                    letterSpacing: -0.3,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Export to file',
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
                  ),
                ),
              ],
            ),
          ),
          
          // Close button
          IconButton(
            onPressed: _handleClose,
            icon: Icon(
              Icons.close_rounded,
              color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
            ),
            style: IconButton.styleFrom(
              backgroundColor: theme.colorScheme.surface.withValues(alpha: 0.5),
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildFormatSelection(ThemeData theme, bool isDark) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Export Format',
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 12),
        
        // Format options
        _buildFormatOption(
          theme: theme,
          isDark: isDark,
          format: ExportFormat.markdown,
          icon: Icons.description_outlined,
          title: 'Markdown',
          description: 'Formatted text with code blocks',
        ),
        
        const SizedBox(height: 12),
        
        // Future formats (disabled)
        _buildFormatOption(
          theme: theme,
          isDark: isDark,
          format: ExportFormat.pdf,
          icon: Icons.picture_as_pdf_outlined,
          title: 'PDF Document',
          description: 'Professional format for archiving',
          isEnabled: false,
        ),
      ],
    );
  }
  
  Widget _buildFormatOption({
    required ThemeData theme,
    required bool isDark,
    required ExportFormat format,
    required IconData icon,
    required String title,
    required String description,
    bool isEnabled = true,
  }) {
    final isSelected = _selectedFormat == format;
    
    return GestureDetector(
      onTap: isEnabled ? () {
        HapticFeedback.selectionClick();
        setState(() => _selectedFormat = format);
      } : null,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        curve: Curves.easeOutCubic,
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: isSelected
              ? widget.accentColor.withValues(alpha: 0.12)
              : theme.colorScheme.surface.withValues(alpha: 0.3),
          borderRadius: BorderRadius.circular(GlassTheme.radiusMedium),
          border: Border.all(
            color: isSelected
                ? widget.accentColor.withValues(alpha: 0.5)
                : theme.dividerColor.withValues(alpha: 0.2),
            width: isSelected ? 2 : 1,
          ),
        ),
        child: Row(
          children: [
            // Icon
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: isSelected
                    ? widget.accentColor.withValues(alpha: 0.2)
                    : theme.colorScheme.surface.withValues(alpha: 0.5),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(
                icon,
                color: isSelected
                    ? widget.accentColor
                    : theme.colorScheme.onSurface.withValues(
                        alpha: isEnabled ? 0.6 : 0.3,
                      ),
                size: 24,
              ),
            ),
            
            const SizedBox(width: 16),
            
            // Text
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: theme.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w600,
                      color: isEnabled
                          ? null
                          : theme.colorScheme.onSurface.withValues(alpha: 0.4),
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    description,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onSurface.withValues(
                        alpha: isEnabled ? 0.6 : 0.3,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            
            // Selection indicator
            if (isSelected)
              Icon(
                Icons.check_circle_rounded,
                color: widget.accentColor,
                size: 24,
              )
            else if (!isEnabled)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: theme.colorScheme.surface.withValues(alpha: 0.5),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  'Soon',
                  style: theme.textTheme.labelSmall?.copyWith(
                    color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildActions(ThemeData theme, bool isDark) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        border: Border(
          top: BorderSide(
            color: theme.dividerColor.withValues(alpha: 0.1),
            width: 1,
          ),
        ),
      ),
      child: Row(
        children: [
          // Cancel button
          Expanded(
            child: TextButton(
              onPressed: _handleClose,
              style: TextButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
                backgroundColor: theme.colorScheme.surface.withValues(alpha: 0.5),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(GlassTheme.radiusMedium),
                ),
              ),
              child: Text(
                'Cancel',
                style: theme.textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w600,
                  color: theme.colorScheme.onSurface.withValues(alpha: 0.7),
                ),
              ),
            ),
          ),
          
          const SizedBox(width: 12),
          
          // Export button (primary)
          Expanded(
            flex: 2,
            child: ElevatedButton(
              onPressed: _handleExport,
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
                backgroundColor: widget.accentColor,
                foregroundColor: Colors.white,
                elevation: 0,
                shadowColor: widget.accentColor.withValues(alpha: 0.5),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(GlassTheme.radiusMedium),
                ),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.download_rounded, size: 20),
                  const SizedBox(width: 8),
                  Text(
                    'Export',
                    style: theme.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w600,
                      color: Colors.white,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Export format options
enum ExportFormat {
  markdown,
  pdf,
  image,
}

/// Configuration for conversation export
class ShareConversationConfig {
  final ExportFormat format;

  const ShareConversationConfig({
    required this.format,
  });
}
