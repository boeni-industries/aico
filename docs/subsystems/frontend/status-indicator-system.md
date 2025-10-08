# AICO Ultra-Modern Status Indicator System

## Overview

The AICO Status Indicator System provides real-time, contextual awareness of system health, connectivity, authentication, and operational state through elegant, non-intrusive visual elements that enhance user confidence without creating distraction.

## Design Philosophy

### Core Principles
- **Ambient Awareness**: Status information is present but never demanding attention
- **Progressive Disclosure**: Critical states are immediately visible, detailed information available on demand
- **Emotional Intelligence**: Visual language that reduces anxiety and builds trust
- **Zero Cognitive Load**: Users understand system state intuitively without learning

### Visual Language
- **Breathing Animations**: Subtle pulsing indicates active/healthy states
- **Color Semantics**: Soft purple (healthy), amber (transitioning), coral (attention needed)
- **Spatial Hierarchy**: More critical indicators positioned closer to primary interaction zones
- **Micro-Interactions**: Gentle hover/tap feedback with meaningful state transitions

## System Architecture

### Status Categories

#### 1. Connection Health
- **Online**: Soft purple breathing ring around avatar
- **Offline**: Muted gray with subtle "offline" badge
- **Reconnecting**: Amber pulse with connection attempt counter
- **Degraded**: Partial ring with performance indicator

#### 2. Authentication State  
- **Authenticated**: Invisible (default state)
- **Token Refreshing**: Subtle spinner in status bar
- **Re-authentication Required**: Gentle modal with soft purple accent
- **Session Expired**: Contextual prompt with clear action path

#### 3. Encryption Status
- **Secure Session**: Tiny lock icon with soft glow
- **Handshaking**: Animated key exchange icon
- **Insecure**: Amber warning with explanation
- **Encryption Failed**: Clear error state with retry option

#### 4. System Performance
- **Optimal**: No indicator (invisible excellence)
- **Processing**: Subtle activity indicator near relevant UI elements
- **Resource Constrained**: Contextual performance mode notification
- **Error State**: Clear problem description with suggested actions

## Component Specifications

### Primary Status Ring
**Location**: Around avatar (96px diameter)
**States**:
- Healthy: `#B8A1EA` 2px ring, 60% opacity, 2s breathing cycle
- Warning: `#F4A261` 2px ring, 80% opacity, 1.5s pulse
- Error: `#ED7867` 2px ring, 90% opacity, 1s urgent pulse
- Offline: `#9CA3AF` 1px dashed ring, static

### Status Bar Component
**Location**: Top of main content area
**Height**: 32px (collapsible to 0px when all systems healthy)
**Content**: Icon + Status Text + Action Button (if applicable)

```dart
class StatusBar extends StatelessWidget {
  final List<StatusItem> activeStatuses;
  final bool isCollapsed;
  
  Widget build(BuildContext context) {
    if (activeStatuses.isEmpty) return SizedBox.shrink();
    
    return AnimatedContainer(
      height: isCollapsed ? 0 : 32,
      child: Container(
        decoration: BoxDecoration(
          color: _getStatusColor(activeStatuses.first.severity),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Row(
          children: [
            _buildStatusIcon(),
            _buildStatusText(),
            _buildActionButton(),
          ],
        ),
      ),
    );
  }
}
```

### Floating Status Indicators
**Purpose**: Contextual status for specific operations
**Behavior**: Appear near relevant UI elements, auto-dismiss after resolution
**Animation**: Slide-in from relevant direction, fade-out on completion

### Connection Quality Indicator
**Location**: Bottom-right corner of main content
**Size**: 24x24px
**States**:
- Excellent: 4 bars, soft purple
- Good: 3 bars, soft purple  
- Fair: 2 bars, amber
- Poor: 1 bar, coral
- Offline: X icon, gray

## Implementation Architecture

### State Management
```dart
class SystemStatusProvider extends ChangeNotifier {
  ConnectionStatus _connectionStatus = ConnectionStatus.unknown;
  AuthenticationStatus _authStatus = AuthenticationStatus.authenticated;
  EncryptionStatus _encryptionStatus = EncryptionStatus.secure;
  List<SystemAlert> _activeAlerts = [];
  
  // Stream subscriptions to various system components
  StreamSubscription? _connectionSubscription;
  StreamSubscription? _authSubscription;
  StreamSubscription? _encryptionSubscription;
  
  void initialize() {
    _connectionSubscription = connectionManager.statusStream.listen(_updateConnectionStatus);
    _authSubscription = tokenManager.reAuthenticationStream.listen(_handleAuthEvent);
    _encryptionSubscription = encryptionService.statusStream.listen(_updateEncryptionStatus);
  }
}
```

### Integration Points

#### ConnectionManager Integration
```dart
// Listen to connection health and retry attempts
connectionManager.healthStream.listen((health) {
  statusProvider.updateConnectionHealth(health);
});

connectionManager.retryStream.listen((attempt) {
  statusProvider.showRetryIndicator(attempt);
});
```

#### TokenManager Integration  
```dart
// Listen to re-authentication events
tokenManager.reAuthenticationStream.listen((event) {
  statusProvider.showReAuthenticationPrompt(event);
});

// Monitor token refresh operations
tokenManager.refreshStream.listen((status) {
  statusProvider.updateAuthStatus(status);
});
```

#### UnifiedApiClient Integration
```dart
// Show request status for long-running operations
apiClient.requestStream.listen((request) {
  if (request.duration > Duration(seconds: 2)) {
    statusProvider.showRequestIndicator(request);
  }
});
```

## User Experience Flows

### Scenario 1: Network Disconnection
1. **Immediate**: Avatar ring changes to dashed gray
2. **2 seconds**: Status bar appears with "Working offline" message
3. **Background**: ConnectionManager attempts reconnection
4. **Reconnecting**: Status bar updates to "Reconnecting..." with attempt counter
5. **Success**: Status bar shows "Back online" for 3 seconds, then disappears
6. **Avatar ring**: Returns to soft purple breathing

### Scenario 2: Token Expiration
1. **Background**: TokenManager detects expired token
2. **Attempt**: Automatic refresh attempt (invisible to user)
3. **Failure**: Re-authentication required event triggered
4. **UI Response**: Gentle modal appears with soft purple accent
5. **Message**: "Please sign in again to continue" with clear action button
6. **Resolution**: User authenticates, modal disappears smoothly

### Scenario 3: System Performance Degradation
1. **Detection**: System monitoring detects high resource usage
2. **Notification**: Subtle status bar appears: "Performance mode active"
3. **Visual Changes**: Animations reduce to 30fps, non-essential effects disabled
4. **User Control**: Status bar includes "Settings" button for manual control
5. **Recovery**: Auto-dismisses when resources available

## Accessibility Features

### Screen Reader Support
- All status changes announced with appropriate ARIA live regions
- Status indicators have descriptive labels and roles
- Critical alerts interrupt screen reader flow appropriately

### Keyboard Navigation
- Status indicators focusable via Tab navigation
- Keyboard shortcuts for common status actions (Ctrl+Shift+S for status overview)
- Focus indicators use consistent soft purple accent

### Visual Accessibility
- All status colors meet WCAG AA contrast requirements
- Status never relies solely on color (always paired with icons/text)
- Reduced motion preferences respected for all animations

## Technical Implementation

### Status Widget Hierarchy
```
StatusSystem
├── PrimaryStatusRing (around avatar)
├── StatusBar (top of content)
├── FloatingIndicators (contextual)
├── ConnectionQualityIndicator (bottom-right)
└── SystemAlertOverlay (critical states)
```

### Animation Specifications
- **Breathing**: `opacity: 0.6 → 1.0 → 0.6` over 2000ms with `Curves.easeInOut`
- **Pulse**: `scale: 1.0 → 1.1 → 1.0` over 1000ms with `Curves.elasticOut`
- **Slide-in**: `translateY: 32px → 0px` over 300ms with `Curves.easeOutCubic`
- **Fade**: `opacity: 0.0 → 1.0` over 200ms with `Curves.easeOut`

### Performance Considerations
- Status updates batched to prevent excessive rebuilds
- Animations use `AnimatedWidget` for optimal performance
- Status polling limited to 1Hz for non-critical indicators
- Critical status changes trigger immediate updates

## Configuration Options

### User Preferences
```yaml
status_indicators:
  show_connection_quality: true
  show_performance_indicators: true
  animation_intensity: normal  # minimal, normal, enhanced
  auto_hide_duration: 3000     # milliseconds
  critical_alerts_only: false
```

### Developer Options
```yaml
debug_status:
  show_all_indicators: false
  simulate_offline: false
  force_performance_mode: false
  status_update_logging: false
```

## Future Enhancements

### Phase 2: Advanced Indicators
- **Emotion State**: Avatar mood ring reflecting current emotional state
- **Learning Progress**: Subtle indicators for background AI training
- **Relationship Context**: Visual cues for current conversation partner
- **Privacy Mode**: Clear indicators when in private/secure modes

### Phase 3: Predictive Status
- **Proactive Warnings**: "Network quality declining" before disconnection
- **Resource Forecasting**: "High usage detected, switching to performance mode"
- **Maintenance Windows**: Advance notice of system updates/restarts

### Phase 4: Contextual Intelligence
- **Adaptive Sensitivity**: Status prominence adjusts based on user expertise
- **Workflow Awareness**: Status indicators adapt to current task context
- **Emotional Awareness**: Status presentation considers user stress/focus state

## Success Metrics

### User Experience
- **Confidence Score**: User surveys on system reliability perception
- **Interruption Rate**: Frequency of unexpected status changes
- **Recovery Time**: Average time from problem detection to resolution
- **User Actions**: Frequency of manual status checking/intervention

### Technical Performance  
- **Status Accuracy**: Percentage of correct status representations
- **Update Latency**: Time from system state change to UI update
- **Resource Usage**: CPU/memory overhead of status system
- **Animation Performance**: Frame rate maintenance during status updates

## Conclusion

The AICO Status Indicator System creates a foundation of trust and transparency through elegant, intelligent visual communication. By following these specifications, the system will provide users with confident awareness of system state while maintaining the clean, modern aesthetic that defines the AICO experience.

The system scales from basic connectivity indicators to sophisticated contextual awareness, always prioritizing user confidence and task flow over technical complexity.
