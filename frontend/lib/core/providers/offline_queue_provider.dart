import 'package:aico_frontend/networking/services/offline_queue.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Provider for the offline queue service
final offlineQueueProvider = Provider<OfflineQueue>((ref) {
  final queue = OfflineQueue(ref);
  
  // Initialize the queue when first accessed
  queue.initialize();
  
  // Dispose when provider is disposed
  ref.onDispose(() {
    queue.dispose();
  });
  
  return queue;
});

/// Provider for offline queue stream
final offlineQueueStreamProvider = StreamProvider<List<QueuedOperation>>((ref) {
  final queue = ref.watch(offlineQueueProvider);
  return queue.queueStream;
});

/// Provider for offline queue length
final offlineQueueLengthProvider = Provider<int>((ref) {
  final queue = ref.watch(offlineQueueProvider);
  return queue.length;
});
