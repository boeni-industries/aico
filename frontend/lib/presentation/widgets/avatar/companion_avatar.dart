import 'package:aico_frontend/core/providers/networking_providers.dart';
import 'package:aico_frontend/data/models/emotion_model.dart';
import 'package:aico_frontend/networking/services/connection_manager.dart';
import 'package:aico_frontend/presentation/providers/agency_state_provider.dart';
import 'package:aico_frontend/presentation/providers/auth_provider.dart';
import 'package:aico_frontend/presentation/providers/avatar_state_provider.dart';
import 'package:aico_frontend/presentation/providers/emotion_provider.dart';
import 'package:aico_frontend/presentation/widgets/agency/floating_agency_icon.dart';
import 'package:aico_frontend/presentation/widgets/avatar/avatar_viewer.dart';
import 'package:aico_frontend/presentation/widgets/emotion/emotion_color_mapper.dart';
import 'package:aico_frontend/presentation/widgets/emotion/emotion_formatter.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Avatar with subtle pulsating ring status indicator - clean, minimal, following design principles
/// Now uses centralized avatar state provider for rich information display
class CompanionAvatar extends ConsumerStatefulWidget {
  const CompanionAvatar({super.key});

  @override
  ConsumerState<CompanionAvatar> createState() => _CompanionAvatarState();
}

class _CompanionAvatarState extends ConsumerState<CompanionAvatar>
    with TickerProviderStateMixin {
  late AnimationController _pulseController;
  late AnimationController _colorTransitionController;
  late Animation<Color?> _ringColorAnimation;
  
  late InternalConnectionStatus _currentStatus;
  late bool _isAuthenticated;
  late AvatarMode _previousAvatarMode;
  late Color _targetRingColor;

  @override
  void initState() {
    super.initState();
    
    // Initialize from actual current state to prevent flicker on rebuild
    final connectionManager = ref.read(connectionManagerProvider);
    final authState = ref.read(authProvider);
    final avatarState = ref.read(avatarRingStateProvider);
    
    _currentStatus = connectionManager.health.status;
    _isAuthenticated = authState.isAuthenticated;
    _previousAvatarMode = avatarState.mode;
    
    // Initialize target color based on current avatar mode
    _targetRingColor = _getInitialRingColor(avatarState.mode);
    
    // Dynamic pulse animation - adapts to connection state
    _pulseController = AnimationController(
      duration: const Duration(milliseconds: 3000),
      vsync: this,
    );
    
    // Color transition controller for smooth color changes
    _colorTransitionController = AnimationController(
      duration: const Duration(milliseconds: 1200), // Longer transition for smoothness
      vsync: this,
    );
    
    _ringColorAnimation = ColorTween(
      begin: _targetRingColor,
      end: _targetRingColor,
    ).animate(CurvedAnimation(
      parent: _colorTransitionController,
      curve: Curves.easeInOutCubic, // Smoother cubic curve
    ));
    
    _startPulsing();
  }

  void _startPulsing() {
    _pulseController.repeat(reverse: true);
  }

  void _stopPulsing() {
    _pulseController.stop();
    _pulseController.reset();
  }

  bool _shouldPulse(AvatarMode avatarMode) {
    // Enhanced pulsing logic for different states
    if (!_isAuthenticated) return false;
    
    // Pulse for most avatar modes
    switch (avatarMode) {
      case AvatarMode.idle:
        return _currentStatus == InternalConnectionStatus.connected;
      case AvatarMode.thinking:
      case AvatarMode.listening:
      case AvatarMode.speaking:
      case AvatarMode.processing:
      case AvatarMode.success:
        return true;
      case AvatarMode.connecting:
        return true;
      case AvatarMode.attention:
        return true;
      case AvatarMode.error:
        return false; // Static for errors
    }
  }

  void _updateAnimationState(AvatarMode avatarMode, double intensity) {
    if (_shouldPulse(avatarMode)) {
      // Adjust pulse speed based on mode and intensity
      final Duration duration = _getPulseDuration(avatarMode, intensity);
      
      if (_pulseController.duration != duration) {
        // Smoothly transition pulse speed by continuing from current position
        final currentValue = _pulseController.value;
        _pulseController.duration = duration;
        
        // Don't reset - continue from current position for smooth transition
        if (!_pulseController.isAnimating) {
          _pulseController.value = currentValue;
          _startPulsing();
        }
      } else if (!_pulseController.isAnimating) {
        _startPulsing();
      }
    } else {
      _stopPulsing();
    }
  }
  
  Duration _getPulseDuration(AvatarMode mode, double intensity) {
    // Base duration modified by intensity (higher intensity = faster)
    final baseDuration = switch (mode) {
      AvatarMode.thinking => 900, // Faster for more visible thinking
      AvatarMode.processing => 800,
      AvatarMode.listening => 1200, // Faster, more responsive
      AvatarMode.speaking => 1000,
      AvatarMode.success => 1000,
      AvatarMode.attention => 1800,
      AvatarMode.connecting => 1500,
      AvatarMode.error => 3000,
      AvatarMode.idle => 3000,
    };
    
    // Intensity affects speed (higher intensity = faster pulse)
    final adjustedDuration = (baseDuration / (0.5 + intensity * 0.5)).round();
    return Duration(milliseconds: adjustedDuration);
  }

  Color _getInitialRingColor(AvatarMode avatarMode) {
    // Get initial color without theme context (for initState)
    // Use full opacity colors as defaults
    const coral = Color(0xFFED7867);
    const emerald = Color(0xFF10B981);
    const amber = Color(0xFFF59E0B);
    const sapphire = Color(0xFF3B82F6);
    const purple = Color(0xFFB8A1EA);
    const violet = Color(0xFF8B5CF6);
    
    switch (avatarMode) {
      case AvatarMode.thinking:
      case AvatarMode.speaking:
        return purple;
      case AvatarMode.processing:
        return violet;
      case AvatarMode.listening:
        return sapphire;
      case AvatarMode.success:
        return emerald;
      case AvatarMode.error:
        return coral;
      case AvatarMode.attention:
        return amber;
      case AvatarMode.connecting:
        return sapphire;
      case AvatarMode.idle:
        return emerald; // Default to green for idle/connected
    }
  }

  Color _getRingColor(AvatarMode avatarMode) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    
    // Enhanced color system for immersive status representation
    const coral = Color(0xFFED7867); // Error/warning accent
    const emerald = Color(0xFF10B981); // Success/healthy state
    const amber = Color(0xFFF59E0B); // Caution/transitional
    const sapphire = Color(0xFF3B82F6); // Processing/connecting
    const purple = Color(0xFFB8A1EA); // Thinking/processing state
    const violet = Color(0xFF8B5CF6); // Deep processing
    
    // Avatar mode takes priority over connection status
    switch (avatarMode) {
      case AvatarMode.thinking:
        return isDark ? purple.withValues(alpha: 0.95) : purple; // More visible
      case AvatarMode.processing:
        return isDark ? violet.withValues(alpha: 0.95) : violet;
      case AvatarMode.listening:
        return isDark ? sapphire.withValues(alpha: 0.95) : sapphire; // Blue for user typing
      case AvatarMode.speaking:
        return isDark ? purple.withValues(alpha: 0.8) : purple.withValues(alpha: 0.9);
      case AvatarMode.success:
        return isDark ? emerald.withValues(alpha: 1.0) : emerald;
      case AvatarMode.error:
        return isDark ? coral.withValues(alpha: 0.9) : coral;
      case AvatarMode.attention:
        return isDark ? amber.withValues(alpha: 0.8) : amber;
      case AvatarMode.connecting:
        return isDark ? sapphire.withValues(alpha: 0.8) : sapphire;
      case AvatarMode.idle:
        // Fall back to connection status for idle mode
        if (!_isAuthenticated) {
          return isDark ? coral.withValues(alpha: 0.7) : coral.withValues(alpha: 0.8);
        }
        
        switch (_currentStatus) {
          case InternalConnectionStatus.connected:
            return isDark ? emerald.withValues(alpha: 0.9) : emerald;
          case InternalConnectionStatus.connecting:
            return isDark ? sapphire.withValues(alpha: 0.8) : sapphire;
          case InternalConnectionStatus.disconnected:
            return isDark ? amber.withValues(alpha: 0.7) : amber;
          case InternalConnectionStatus.offline:
            return isDark ? coral.withValues(alpha: 0.6) : coral.withValues(alpha: 0.7);
          case InternalConnectionStatus.error:
            return isDark ? coral.withValues(alpha: 0.9) : coral;
        }
    }
  }

  InlineSpan _buildTooltipContent(AvatarMode avatarMode, EmotionModel? emotion, AgencyBadgeState agencyState) {
    // Get base status message
    final String statusMessage = switch (avatarMode) {
      AvatarMode.thinking => 'Thinking...',
      AvatarMode.processing => 'Processing...',
      AvatarMode.listening => 'Listening...',
      AvatarMode.speaking => 'Speaking...',
      AvatarMode.success => 'Done!',
      AvatarMode.error => 'Error occurred',
      AvatarMode.attention => 'Attention needed',
      AvatarMode.connecting => 'Connecting...',
      AvatarMode.idle => !_isAuthenticated
          ? 'Touch to authenticate'
          : switch (_currentStatus) {
              InternalConnectionStatus.connected => 'Ready to chat',
              InternalConnectionStatus.connecting => 'Connecting...',
              InternalConnectionStatus.disconnected => 'Reconnecting in background',
              InternalConnectionStatus.offline => 'Check network connection',
              InternalConnectionStatus.error => 'Connection issue - will retry automatically',
            },
    };

    // Build rich tooltip with clear visual hierarchy and gestalt grouping
    final spans = <InlineSpan>[];

    // === AVATAR STATE SECTION ===
    spans.addAll([
      TextSpan(
        text: 'AVATAR',
        style: TextStyle(
          color: Colors.white.withValues(alpha: 0.5),
          fontSize: 9,
          fontWeight: FontWeight.w700,
          letterSpacing: 1.2,
        ),
      ),
      const TextSpan(text: '\n'),
      TextSpan(
        text: statusMessage,
        style: TextStyle(
          color: Colors.white.withValues(alpha: 0.95),
          fontSize: 13,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.02,
        ),
      ),
    ]);

    // === EMOTION SECTION ===
    if (emotion != null) {
      final emotionColor = EmotionColorMapper.getColor(emotion.primary);
      final label = EmotionFormatter.formatLabel(emotion.primary);
      final description = EmotionFormatter.getDescription(emotion.primary);
      final confidence = (emotion.confidence * 100).round();

      spans.addAll([
        const TextSpan(text: '\n\n'),
        // Section header
        TextSpan(
          text: 'EMOTION',
          style: TextStyle(
            color: Colors.white.withValues(alpha: 0.5),
            fontSize: 9,
            fontWeight: FontWeight.w700,
            letterSpacing: 1.2,
          ),
        ),
        const TextSpan(text: '\n'),
        // Emotion indicator with color dot
        WidgetSpan(
          alignment: PlaceholderAlignment.middle,
          child: Container(
            width: 6,
            height: 6,
            margin: const EdgeInsets.only(right: 6, top: 2),
            decoration: BoxDecoration(
              color: emotionColor,
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: emotionColor.withValues(alpha: 0.5),
                  blurRadius: 6,
                  spreadRadius: 2,
                ),
              ],
            ),
          ),
        ),
        TextSpan(
          text: label,
          style: TextStyle(
            color: emotionColor,
            fontSize: 13,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.03,
          ),
        ),
        TextSpan(
          text: ' $confidence%',
          style: TextStyle(
            color: Colors.white.withValues(alpha: 0.6),
            fontSize: 11,
            fontWeight: FontWeight.w500,
          ),
        ),
        const TextSpan(text: '\n'),
        TextSpan(
          text: description,
          style: TextStyle(
            color: Colors.white.withValues(alpha: 0.7),
            fontSize: 11,
            fontWeight: FontWeight.w400,
            height: 1.4,
          ),
        ),
      ]);
    }

    // === AGENCY SECTION ===
    final agencyInfo = _getComprehensiveAgencyInfo(agencyState);
    
    spans.addAll([
      const TextSpan(text: '\n\n'),
      // Section header
      TextSpan(
        text: 'AGENCY',
        style: TextStyle(
          color: Colors.white.withValues(alpha: 0.5),
          fontSize: 9,
          fontWeight: FontWeight.w700,
          letterSpacing: 1.2,
        ),
      ),
      const TextSpan(text: '\n'),
    ]);

    // Add each agency dimension with refined visual design
    for (var i = 0; i < agencyInfo.length; i++) {
      final item = agencyInfo[i];
      final isLast = i == agencyInfo.length - 1;
      
      spans.addAll([
        // Color dot with refined styling
        WidgetSpan(
          alignment: PlaceholderAlignment.middle,
          child: Container(
            width: 6,
            height: 6,
            margin: const EdgeInsets.only(right: 8, top: 2),
            decoration: BoxDecoration(
              color: item.color,
              shape: BoxShape.circle,
              boxShadow: item.isActive ? [
                BoxShadow(
                  color: item.color.withValues(alpha: 0.5),
                  blurRadius: 4,
                  spreadRadius: 1,
                ),
              ] : null,
            ),
          ),
        ),
        // Label with refined typography
        TextSpan(
          text: item.label,
          style: TextStyle(
            color: item.isActive 
              ? item.color 
              : Colors.white.withValues(alpha: 0.45),
            fontSize: 11,
            fontWeight: item.isActive ? FontWeight.w700 : FontWeight.w500,
            letterSpacing: 0.3,
          ),
        ),
        // Value with improved hierarchy
        if (item.value != null)
          TextSpan(
            text: ' · ${item.value}',
            style: TextStyle(
              color: Colors.white.withValues(alpha: item.isActive ? 0.8 : 0.4),
              fontSize: 11,
              fontWeight: FontWeight.w400,
              letterSpacing: 0.1,
            ),
          ),
        if (!isLast) const TextSpan(text: '\n'),
      ]);
    }

    return TextSpan(children: spans);
  }

  List<_AgencyStatusItem> _getComprehensiveAgencyInfo(AgencyBadgeState state) {
    const purple = Color(0xFFB8A1EA);
    const amber = Color(0xFFF59E0B);
    const emerald = Color(0xFF10B981);
    const gray = Color(0xFF9CA3AF);
    
    final items = <_AgencyStatusItem>[];
    
    // 1. Current Intention
    if (state.mode == AgencyBadgeMode.activeIntention && state.intentionSummary != null) {
      items.add(_AgencyStatusItem(
        label: 'Intention',
        value: state.intentionSummary,
        color: purple,
        isActive: true,
      ));
    } else {
      items.add(_AgencyStatusItem(
        label: 'Intention',
        value: 'None',
        color: gray,
        isActive: false,
      ));
    }
    
    // 2. Active Goals
    if (state.mode == AgencyBadgeMode.goalProgress) {
      final percent = (state.intensity * 100).round();
      final goalName = state.metadata['goalName'] as String?;
      items.add(_AgencyStatusItem(
        label: 'Goal',
        value: goalName != null ? '$goalName ($percent%)' : '$percent% complete',
        color: purple,
        isActive: true,
      ));
    } else if (state.mode == AgencyBadgeMode.goalCompleted) {
      final goalName = state.metadata['goalName'] as String?;
      items.add(_AgencyStatusItem(
        label: 'Goal',
        value: goalName != null ? '✓ $goalName' : 'Completed!',
        color: emerald,
        isActive: true,
      ));
    } else {
      items.add(_AgencyStatusItem(
        label: 'Goals',
        value: 'None active',
        color: gray,
        isActive: false,
      ));
    }
    
    // 3. Pending Lessons
    if (state.mode == AgencyBadgeMode.lessonPending || 
        (state.mode == AgencyBadgeMode.multipleItems && state.pendingCount > 0)) {
      final count = state.pendingCount;
      items.add(_AgencyStatusItem(
        label: 'Lessons',
        value: count > 1 ? '$count ready to review' : '1 ready to review',
        color: amber,
        isActive: true,
      ));
    } else {
      items.add(_AgencyStatusItem(
        label: 'Lessons',
        value: 'None pending',
        color: gray,
        isActive: false,
      ));
    }
    
    // 4. Proactive Messages (placeholder - will be populated when backend provides data)
    items.add(_AgencyStatusItem(
      label: 'Proactive',
      value: 'Quiet',
      color: gray,
      isActive: false,
    ));
    
    // 5. Learning Status (placeholder - will show skill performance when available)
    items.add(_AgencyStatusItem(
      label: 'Learning',
      value: 'Observing',
      color: gray,
      isActive: false,
    ));
    
    return items;
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _colorTransitionController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final connectionManager = ref.watch(connectionManagerProvider);
    final authState = ref.watch(authProvider);
    final avatarState = ref.watch(avatarRingStateProvider);
    
    return StreamBuilder<ConnectionHealth>(
      stream: connectionManager.healthStream,
      initialData: connectionManager.health,
      builder: (context, snapshot) {
        final health = snapshot.data ?? connectionManager.health;
        final newStatus = health.status;
        final newAuthState = authState.isAuthenticated;
        
        // Update state and animations when status or avatar mode changes
        if (newStatus != _currentStatus || newAuthState != _isAuthenticated || avatarState.mode != _previousAvatarMode) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            final newColor = _getRingColor(avatarState.mode);
            
            // Smooth color transition using HSL color space
            if (newColor != _targetRingColor) {
              final currentColor = _colorTransitionController.isAnimating
                  ? (_ringColorAnimation.value ?? _targetRingColor)
                  : _targetRingColor;
              
              // Create custom HSL tween to avoid passing through red
              _ringColorAnimation = _HSLColorTween(
                begin: currentColor,
                end: newColor,
              ).animate(CurvedAnimation(
                parent: _colorTransitionController,
                curve: Curves.easeInOutCubic,
              ));
              
              _targetRingColor = newColor;
              _colorTransitionController.forward(from: 0.0);
            }
            
            setState(() {
              _currentStatus = newStatus;
              _isAuthenticated = newAuthState;
              _previousAvatarMode = avatarState.mode;
            });
            _updateAnimationState(avatarState.mode, avatarState.intensity);
          });
        }
        
        // Watch emotion state to keep provider alive and get updates
        final emotion = ref.watch(emotionStateProvider);
        final agencyState = ref.watch(agencyBadgeStateProvider);
        
        return Tooltip(
          richMessage: _buildTooltipContent(avatarState.mode, emotion, agencyState),
          decoration: BoxDecoration(
            // Glassmorphic tooltip matching AICO design
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                Colors.white.withValues(alpha: 0.22),
                Colors.white.withValues(alpha: 0.18),
              ],
            ),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: Colors.white.withValues(alpha: 0.15),
              width: 1,
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.3),
                blurRadius: 20,
                spreadRadius: 2,
              ),
            ],
          ),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          child: AnimatedBuilder(
            animation: _pulseController,
            builder: (context, child) {
              // Use animated color or target color
              final ringColor = _colorTransitionController.isAnimating 
                  ? (_ringColorAnimation.value ?? _targetRingColor)
                  : _getRingColor(avatarState.mode);
              
              // Full-body avatar with seamless background integration
              // Background aura is rendered as a layer behind the avatar for depth
              return LayoutBuilder(
                builder: (context, constraints) {
                  // Use available space, maintain aspect ratio ~9:16 for portrait
                  final maxHeight = constraints.maxHeight;
                  final maxWidth = constraints.maxWidth;
                  final aspectRatio = 9 / 16;
                  
                  double width, height;
                  
                  // Always try to maximize height first (fills vertical space)
                  height = maxHeight;
                  width = height * aspectRatio;
                  
                  // If width exceeds available space, constrain by width instead
                  if (width > maxWidth) {
                    width = maxWidth;
                    height = width / aspectRatio;
                  }
                  
                  // Determine if we're width-constrained (voice mode) for alignment
                  final bool isWidthConstrained = width >= maxWidth * 0.99;
                  
                  // Allow glow to overflow by using clipBehavior: Clip.none
                  // In voice mode (width constrained), top-align to eliminate gap
                  return Stack(
                    clipBehavior: Clip.none, // Allow glow to extend beyond bounds
                    alignment: isWidthConstrained ? Alignment.topCenter : Alignment.center,
                    children: [
                      // Radial glow behind avatar - pure system state only
                      Positioned(
                        left: -maxWidth * 0.2, // Extend glow beyond left
                        right: -maxWidth * 0.2, // Extend glow beyond right
                        top: -maxHeight * 0.1, // Extend glow beyond top
                        bottom: -maxHeight * 0.1, // Extend glow beyond bottom
                        child: Container(
                          decoration: BoxDecoration(
                            gradient: RadialGradient(
                              center: const Alignment(0, -0.1), // Centered on upper body
                              radius: 0.5, // Tighter radius since we extended the container
                              colors: [
                                ringColor.withValues(alpha: theme.brightness == Brightness.dark ? 0.35 : 0.28), // Stronger center
                                ringColor.withValues(alpha: theme.brightness == Brightness.dark ? 0.22 : 0.16), // Mid fade
                                ringColor.withValues(alpha: theme.brightness == Brightness.dark ? 0.12 : 0.08), // Outer fade
                                Colors.transparent,
                              ],
                              stops: const [0.0, 0.35, 0.65, 1.0],
                            ),
                          ),
                        ),
                      ),
                      // Avatar viewer - responsive size, transparent background
                      // Use RepaintBoundary to isolate repaints
                      RepaintBoundary(
                        child: SizedBox(
                          width: width,
                          height: height,
                          child: AvatarViewer(),
                        ),
                      ),
                      // Floating agency icon - appears above avatar head
                      // Gaming-inspired indicator for state changes
                      Positioned(
                        top: height * 0.04, // Above avatar head
                        left: width / 2 - 12, // Centered horizontally
                        child: const FloatingAgencyIcon(),
                      ),
                    ],
                  );
                },
              );
            },
          ),
        );
      },
    );
  }
}

/// Helper class for agency status item display in tooltip
class _AgencyStatusItem {
  final String label;
  final String? value;
  final Color color;
  final bool isActive;

  _AgencyStatusItem({
    required this.label,
    this.value,
    required this.color,
    required this.isActive,
  });
}

/// Custom color tween that interpolates through HSL color space
/// This prevents colors from passing through unwanted hues (e.g., red between green and purple)
class _HSLColorTween extends Tween<Color?> {
  _HSLColorTween({required super.begin, required super.end});

  @override
  Color? lerp(double t) {
    if (begin == null || end == null) return null;
    
    final beginHSL = HSLColor.fromColor(begin!);
    final endHSL = HSLColor.fromColor(end!);
    
    // Interpolate hue taking the shortest path around the color wheel
    double hue;
    final hueDiff = endHSL.hue - beginHSL.hue;
    if (hueDiff.abs() <= 180) {
      hue = beginHSL.hue + hueDiff * t;
    } else if (hueDiff > 180) {
      hue = beginHSL.hue + (hueDiff - 360) * t;
    } else {
      hue = beginHSL.hue + (hueDiff + 360) * t;
    }
    
    // Normalize hue to 0-360 range
    hue = hue % 360;
    if (hue < 0) hue += 360;
    
    return HSLColor.fromAHSL(
      beginHSL.alpha + (endHSL.alpha - beginHSL.alpha) * t,
      hue,
      beginHSL.saturation + (endHSL.saturation - beginHSL.saturation) * t,
      beginHSL.lightness + (endHSL.lightness - beginHSL.lightness) * t,
    ).toColor();
  }
}
