---
title: Performance Guidelines
---

# Performance Guidelines

## Overview

AICO's frontend maintains 60fps animations and responsive interactions by offloading heavy operations to background threads, keeping the main UI thread free for rendering. This ensures smooth user experience across all platforms while supporting offline-first and thin client paradigms.

## Core Performance Principles

### Threading Strategy
**Critical Rule**: Heavy operations ALWAYS run on separate threads to keep the main UI thread responsive.

- **Main Thread**: UI rendering, animations, user interactions only
- **Background Threads**: API calls, data processing, file I/O, image processing
- **Isolates**: CPU-intensive tasks like encryption, large data parsing

### Performance Targets
- **UI Interactions**: < 16ms (60fps) for all animations
- **App Launch**: < 3s cold start, < 1s warm start  
- **Navigation**: < 100ms between screens
- **Memory**: < 100MB baseline, < 300MB peak

## Background Threading

### Heavy Operations Strategy
All computationally expensive or I/O operations must run on background threads:

```dart
// API calls on background thread
Future<List<Message>> loadMessages() async {
  return compute(_processMessages, rawData);
}

// Image processing in isolate
Future<Uint8List> processImage(Uint8List imageData) async {
  return compute(_resizeImage, imageData);
}
```

### Widget Optimization
- **Const Constructors**: Use `const` wherever possible to prevent unnecessary rebuilds
- **ListView.builder**: For large lists to recycle widgets efficiently
- **Consumer with select**: Selective rebuilds only when specific state changes using Riverpod's select modifier
- **RepaintBoundary**: Isolate expensive custom painting operations

## Memory Management

### Image Optimization
- **Cached Network Images**: Use `CachedNetworkImage` with size constraints (`memCacheWidth`, `memCacheHeight`)
- **Automatic Sizing**: Calculate optimal image dimensions based on container size and device pixel ratio
- **Cache Management**: Configure stale periods and maximum cache objects to prevent memory bloat

### Resource Cleanup
- **Provider Disposal**: Riverpod automatically handles provider lifecycle and resource cleanup
- **AutomaticKeepAlive**: Use for expensive widgets that should persist across rebuilds
- **Memory Monitoring**: Track memory usage and trigger cleanup when thresholds are exceeded

## Animation Performance

### Hardware Acceleration
- **Transform Widgets**: Use `Transform.translate`, `Transform.scale` for GPU-accelerated animations
- **Child Optimization**: Build expensive child widgets once, not on every animation frame
- **Curves**: Apply easing curves like `Curves.easeOutCubic` for natural motion

### Accessibility Support
- **Reduced Motion**: Respect `MediaQuery.disableAnimations` for users with motion sensitivity
- **Controller Disposal**: Always dispose animation controllers to prevent memory leaks

## State Management

### Riverpod Optimization
- **Immutable State**: Use immutable state objects with proper equality for efficient comparison
- **Selective Watching**: Use `ref.watch` with select to rebuild only when specific state properties change
- **Provider Caching**: Leverage Riverpod's automatic caching and dependency management
- **State Normalization**: Structure state efficiently to minimize unnecessary provider updates

```dart
// Selective state watching for performance
Widget build(BuildContext context, WidgetRef ref) {
  // Only rebuilds when loading state changes
  final isLoading = ref.watch(conversationProvider.select((state) => state.isLoading));
  
  // Only rebuilds when message count changes
  final messageCount = ref.watch(conversationProvider.select((state) => state.messages.length));
  
  return /* Widget tree */;
}
```

## Network Performance

### Request Management
- **Background Threading**: All API calls run on background threads using `compute()` or isolates
- **Request Cancellation**: Cancel duplicate requests to prevent resource waste
- **Timeout Configuration**: Set appropriate timeouts (10s for network requests)
- **Smart Caching**: Cache responses with configurable stale periods and size limits
- **Preloading**: Load critical assets during app initialization

## Platform Optimizations

### Mobile
- **Memory Pressure**: Clear non-essential caches when app is paused
- **Animation Tuning**: Slightly reduce animation duration for better battery life
- **Background Processing**: Minimize work when app is not in foreground

### Desktop
- **High-DPI Support**: Increase image cache size for high-resolution displays
- **Resource Allocation**: Take advantage of more available memory and CPU

## Performance Monitoring

### Metrics Collection
- **Operation Timing**: Track duration of key operations and log slow operations (>100ms)
- **Memory Monitoring**: Periodic memory usage checks with automatic cleanup at thresholds
- **Frame Rate Tracking**: Monitor animation performance and UI responsiveness

## Build Optimization

### Code Splitting
- **Lazy Loading**: Load heavy features on-demand using `FutureBuilder`
- **Asset Optimization**: Use multiple image resolutions and compress assets
- **Tree Shaking**: Remove unused code during build process

These guidelines ensure AICO maintains smooth, responsive performance by keeping the UI thread free while efficiently managing resources across all platforms.
