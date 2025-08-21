---
title: Performance Guidelines
---

# Performance Guidelines

## Overview

AICO's frontend performance strategy focuses on maintaining 60fps animations, minimizing memory usage, and ensuring responsive interactions even during complex AI operations. These guidelines ensure optimal user experience across all supported platforms while supporting the offline-first and thin client paradigms.

## Performance Targets

### Response Time Targets
- **UI Interactions**: < 16ms (60fps) for animations and transitions
- **API Responses**: < 200ms for local operations, < 1s for network operations
- **App Launch**: < 3s cold start, < 1s warm start
- **Navigation**: < 100ms between screens
- **Avatar Animations**: Smooth 30-60fps depending on device capability

### Memory Targets
- **Baseline Memory**: < 100MB for core app functionality
- **Peak Memory**: < 300MB during intensive operations
- **Memory Growth**: < 5MB/hour during normal usage
- **Cache Limits**: Configurable with sensible defaults (50MB images, 10MB data)

## Widget Performance Optimization

### Efficient Widget Building

#### Const Constructors
```dart
// Use const constructors wherever possible
class MessageBubble extends StatelessWidget {
  const MessageBubble({
    Key? key,
    required this.message,
    required this.isFromUser,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Container(
      // Widget implementation
    );
  }
}
```

#### Widget Recycling
```dart
// Use ListView.builder for large lists
class ConversationList extends StatelessWidget {
  final List<Message> messages;

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      itemCount: messages.length,
      itemBuilder: (context, index) {
        return MessageBubble(
          key: ValueKey(messages[index].id),
          message: messages[index],
          isFromUser: messages[index].isFromUser,
        );
      },
    );
  }
}
```

#### Selective Rebuilds
```dart
// Use BlocBuilder with buildWhen for selective rebuilds
class ChatInterface extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return BlocBuilder<ChatBloc, ChatState>(
      buildWhen: (previous, current) {
        // Only rebuild when messages actually change
        return previous.messages != current.messages;
      },
      builder: (context, state) {
        return ConversationList(messages: state.messages);
      },
    );
  }
}
```

### RepaintBoundary Usage
```dart
// Isolate expensive repaints
class AvatarDisplay extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return RepaintBoundary(
      child: AnimatedBuilder(
        animation: avatarController,
        builder: (context, child) {
          return CustomPaint(
            painter: AvatarPainter(
              expression: avatarController.currentExpression,
              emotion: avatarController.currentEmotion,
            ),
          );
        },
      ),
    );
  }
}
```

## Memory Management

### Image Optimization

#### Cached Network Images
```dart
class OptimizedImage extends StatelessWidget {
  final String imageUrl;
  final double? width;
  final double? height;

  @override
  Widget build(BuildContext context) {
    return CachedNetworkImage(
      imageUrl: imageUrl,
      width: width,
      height: height,
      memCacheWidth: width?.round(),
      memCacheHeight: height?.round(),
      placeholder: (context, url) => ShimmerPlaceholder(),
      errorWidget: (context, url, error) => ErrorPlaceholder(),
      cacheManager: CustomCacheManager(
        stalePeriod: Duration(days: 7),
        maxNrOfCacheObjects: 100,
      ),
    );
  }
}
```

#### Image Size Management
```dart
class ImageSizeManager {
  static Size calculateOptimalSize(Size originalSize, Size containerSize) {
    final devicePixelRatio = WidgetsBinding.instance.window.devicePixelRatio;
    final maxWidth = containerSize.width * devicePixelRatio;
    final maxHeight = containerSize.height * devicePixelRatio;
    
    final aspectRatio = originalSize.width / originalSize.height;
    
    if (originalSize.width > maxWidth || originalSize.height > maxHeight) {
      if (aspectRatio > 1) {
        return Size(maxWidth, maxWidth / aspectRatio);
      } else {
        return Size(maxHeight * aspectRatio, maxHeight);
      }
    }
    
    return originalSize;
  }
}
```

### Stream and Subscription Management
```dart
// Proper stream disposal in BLoCs
class ChatBloc extends Bloc<ChatEvent, ChatState> {
  StreamSubscription? _messageSubscription;
  StreamSubscription? _connectionSubscription;

  @override
  Future<void> close() {
    _messageSubscription?.cancel();
    _connectionSubscription?.cancel();
    return super.close();
  }
}

// AutomaticKeepAlive for expensive widgets
class ExpensiveWidget extends StatefulWidget {
  @override
  _ExpensiveWidgetState createState() => _ExpensiveWidgetState();
}

class _ExpensiveWidgetState extends State<ExpensiveWidget>
    with AutomaticKeepAliveClientMixin {
  @override
  bool get wantKeepAlive => true;

  @override
  Widget build(BuildContext context) {
    super.build(context); // Required for AutomaticKeepAlive
    return ExpensiveContent();
  }
}
```

## Animation Performance

### Hardware Acceleration
```dart
// Use Transform for hardware-accelerated animations
class SmoothAnimation extends StatelessWidget {
  final Animation<double> animation;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: animation,
      builder: (context, child) {
        return Transform.translate(
          offset: Offset(animation.value * 100, 0),
          child: child,
        );
      },
      child: ExpensiveChild(), // Child built once, not on every frame
    );
  }
}
```

### Animation Optimization
```dart
class OptimizedAnimationController {
  late AnimationController _controller;
  late Animation<double> _animation;

  void initializeAnimations(TickerProvider vsync) {
    _controller = AnimationController(
      duration: Duration(milliseconds: 300),
      vsync: vsync,
    );
    
    // Use curves for natural motion
    _animation = CurvedAnimation(
      parent: _controller,
      curve: Curves.easeOutCubic,
    );
  }

  void dispose() {
    _controller.dispose();
  }
}
```

### Reduced Motion Support
```dart
class AccessibleAnimation extends StatelessWidget {
  final Widget child;
  final Animation<double> animation;

  @override
  Widget build(BuildContext context) {
    final reduceMotion = MediaQuery.of(context).disableAnimations;
    
    if (reduceMotion) {
      return child; // Skip animation for accessibility
    }
    
    return AnimatedBuilder(
      animation: animation,
      builder: (context, _) => Transform.scale(
        scale: animation.value,
        child: child,
      ),
    );
  }
}
```

## State Management Performance

### BLoC Optimization
```dart
// Use Equatable for efficient state comparison
class ChatState extends Equatable {
  final List<Message> messages;
  final bool isLoading;
  final String? error;

  const ChatState({
    required this.messages,
    required this.isLoading,
    this.error,
  });

  @override
  List<Object?> get props => [messages, isLoading, error];

  // Efficient copyWith implementation
  ChatState copyWith({
    List<Message>? messages,
    bool? isLoading,
    String? error,
  }) {
    return ChatState(
      messages: messages ?? this.messages,
      isLoading: isLoading ?? this.isLoading,
      error: error ?? this.error,
    );
  }
}
```

### Efficient State Updates
```dart
// Batch state updates to minimize rebuilds
class ChatBloc extends Bloc<ChatEvent, ChatState> {
  @override
  Stream<ChatState> mapEventToState(ChatEvent event) async* {
    if (event is MessageBatchReceived) {
      // Process multiple messages in single state update
      final updatedMessages = List<Message>.from(state.messages);
      updatedMessages.addAll(event.messages);
      
      yield state.copyWith(
        messages: updatedMessages,
        isLoading: false,
      );
    }
  }
}
```

## Network Performance

### Request Optimization
```dart
class OptimizedApiClient {
  final Dio _dio;
  final Map<String, CancelToken> _activeCancellationTokens = {};

  Future<T> get<T>(String path, {String? requestId}) async {
    // Cancel previous request if duplicate
    if (requestId != null && _activeCancellationTokens.containsKey(requestId)) {
      _activeCancellationTokens[requestId]!.cancel();
    }

    final cancelToken = CancelToken();
    if (requestId != null) {
      _activeCancellationTokens[requestId] = cancelToken;
    }

    try {
      final response = await _dio.get<T>(
        path,
        cancelToken: cancelToken,
        options: Options(
          responseType: ResponseType.json,
          receiveTimeout: 10000, // 10 second timeout
        ),
      );
      return response.data!;
    } finally {
      if (requestId != null) {
        _activeCancellationTokens.remove(requestId);
      }
    }
  }
}
```

### Response Caching
```dart
class SmartCacheManager extends CacheManager {
  static const key = 'aicoCache';

  SmartCacheManager() : super(Config(
    key,
    stalePeriod: Duration(days: 7),
    maxNrOfCacheObjects: 200,
    repo: JsonCacheInfoRepository(databaseName: key),
    fileService: HttpFileService(),
  ));

  // Preload critical resources
  Future<void> preloadCriticalAssets() async {
    final criticalUrls = [
      '/api/user/profile',
      '/api/system/status',
      '/assets/avatar/default.png',
    ];

    await Future.wait(
      criticalUrls.map((url) => downloadFile(url)),
    );
  }
}
```

## Platform-Specific Optimizations

### Mobile Optimizations
```dart
class MobileOptimizations {
  static void configurePlatformOptimizations() {
    if (Platform.isAndroid || Platform.isIOS) {
      // Reduce animation duration on mobile
      timeDilation = 0.8;
      
      // Configure memory pressure handling
      SystemChannels.lifecycle.setMessageHandler((message) async {
        if (message == AppLifecycleState.paused.toString()) {
          await _clearNonEssentialCaches();
        }
        return null;
      });
    }
  }

  static Future<void> _clearNonEssentialCaches() async {
    await PaintingBinding.instance.imageCache.clear();
    await DefaultCacheManager().emptyCache();
  }
}
```

### Desktop Optimizations
```dart
class DesktopOptimizations {
  static void configureDesktopPerformance() {
    if (Platform.isWindows || Platform.isMacOS || Platform.isLinux) {
      // Enable higher frame rates on desktop
      WidgetsBinding.instance.addPostFrameCallback((_) {
        final window = WidgetsBinding.instance.window;
        if (window.devicePixelRatio > 1.0) {
          // Optimize for high-DPI displays
          PaintingBinding.instance.imageCache.maximumSizeBytes = 200 << 20; // 200MB
        }
      });
    }
  }
}
```

## Performance Monitoring

### Performance Metrics Collection
```dart
class PerformanceMonitor {
  static final _instance = PerformanceMonitor._internal();
  factory PerformanceMonitor() => _instance;
  PerformanceMonitor._internal();

  final Map<String, Stopwatch> _timers = {};
  final List<PerformanceMetric> _metrics = [];

  void startTimer(String operation) {
    _timers[operation] = Stopwatch()..start();
  }

  void endTimer(String operation) {
    final timer = _timers.remove(operation);
    if (timer != null) {
      timer.stop();
      _recordMetric(PerformanceMetric(
        operation: operation,
        duration: timer.elapsed,
        timestamp: DateTime.now(),
      ));
    }
  }

  void _recordMetric(PerformanceMetric metric) {
    _metrics.add(metric);
    
    // Log slow operations
    if (metric.duration.inMilliseconds > 100) {
      debugPrint('Slow operation detected: ${metric.operation} took ${metric.duration.inMilliseconds}ms');
    }
    
    // Keep only recent metrics
    if (_metrics.length > 1000) {
      _metrics.removeRange(0, 500);
    }
  }
}
```

### Memory Usage Tracking
```dart
class MemoryMonitor {
  static Timer? _monitoringTimer;

  static void startMonitoring() {
    _monitoringTimer = Timer.periodic(Duration(seconds: 30), (_) {
      _checkMemoryUsage();
    });
  }

  static void _checkMemoryUsage() {
    final info = ProcessInfo.currentRss;
    final memoryMB = info / (1024 * 1024);
    
    debugPrint('Current memory usage: ${memoryMB.toStringAsFixed(1)}MB');
    
    if (memoryMB > 250) {
      debugPrint('High memory usage detected, triggering cleanup');
      _performMemoryCleanup();
    }
  }

  static void _performMemoryCleanup() {
    PaintingBinding.instance.imageCache.clear();
    // Additional cleanup operations
  }
}
```

## Build Optimization

### Code Splitting
```dart
// Lazy load heavy features
class LazyFeatureLoader {
  static Widget loadChatFeature() {
    return FutureBuilder<Widget>(
      future: _loadChatModule(),
      builder: (context, snapshot) {
        if (snapshot.hasData) {
          return snapshot.data!;
        }
        return LoadingPlaceholder();
      },
    );
  }

  static Future<Widget> _loadChatModule() async {
    // Simulate dynamic import
    await Future.delayed(Duration(milliseconds: 100));
    return ChatInterface();
  }
}
```

### Asset Optimization
```yaml
# pubspec.yaml - Optimized asset configuration
flutter:
  assets:
    - assets/images/
    - assets/icons/
  
  # Generate different resolutions
  generate: true
  
  # Optimize images
  uses-material-design: true
```

These performance guidelines ensure AICO's frontend delivers smooth, responsive experiences while efficiently managing system resources across all supported platforms.
