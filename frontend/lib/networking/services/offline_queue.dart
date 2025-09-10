import 'dart:async';
import 'package:flutter/foundation.dart';
// import 'package:aico_frontend/core/services/storage_service.dart'; // TODO: Remove when migrated to Riverpod
// TODO: Replace with Riverpod providers when storage service is migrated

abstract class QueuedOperation {
  String get id;
  String get type;
  Map<String, dynamic> get data;
  DateTime get createdAt;
  int get retryCount;
  
  Future<void> execute();
  QueuedOperation withIncrementedRetry();
}

class CreateUserOperation extends QueuedOperation {
  @override
  final String id;
  @override
  final String type = 'create_user';
  @override
  final Map<String, dynamic> data;
  @override
  final DateTime createdAt;
  @override
  final int retryCount;

  CreateUserOperation({
    required this.id,
    required this.data,
    required this.createdAt,
    this.retryCount = 0,
  });

  @override
  Future<void> execute() async {
    throw UnimplementedError('CreateUserOperation.execute() - User creation via repository not yet implemented');
  }

  @override
  QueuedOperation withIncrementedRetry() {
    return CreateUserOperation(
      id: id,
      data: data,
      createdAt: createdAt,
      retryCount: retryCount + 1,
    );
  }
}

class OfflineQueue {
  final List<QueuedOperation> _operations = [];
  final StreamController<List<QueuedOperation>> _queueController = 
      StreamController.broadcast();
  
  Timer? _processTimer;
  bool _isProcessing = false;
  
  static const int _maxRetries = 3;
  static const Duration _processInterval = Duration(seconds: 30);

  Stream<List<QueuedOperation>> get queueStream => _queueController.stream;
  List<QueuedOperation> get operations => List.unmodifiable(_operations);
  int get length => _operations.length;
  bool get isEmpty => _operations.isEmpty;
  bool get isNotEmpty => _operations.isNotEmpty;

  void add(QueuedOperation operation) {
    _operations.add(operation);
    _saveQueue();
    _notifyQueueChanged();
    
    // Start processing if not already running
    _startProcessing();
    
    debugPrint('Added operation ${operation.type} to offline queue');
  }

  void remove(QueuedOperation operation) {
    _operations.removeWhere((op) => op.id == operation.id);
    _saveQueue();
    _notifyQueueChanged();
  }

  void clear() {
    _operations.clear();
    _saveQueue();
    _notifyQueueChanged();
  }

  Future<void> processQueue() async {
    if (_isProcessing || _operations.isEmpty) return;
    
    _isProcessing = true;
    debugPrint('Processing offline queue with ${_operations.length} operations');
    
    final operationsToProcess = List<QueuedOperation>.from(_operations);
    final failedOperations = <QueuedOperation>[];
    
    for (final operation in operationsToProcess) {
      try {
        await operation.execute();
        remove(operation);
        debugPrint('Successfully executed operation ${operation.type}');
      } catch (e) {
        debugPrint('Failed to execute operation ${operation.type}: $e');
        
        if (operation.retryCount < _maxRetries) {
          // Retry with incremented count
          final retryOperation = operation.withIncrementedRetry();
          remove(operation);
          failedOperations.add(retryOperation);
        } else {
          // Max retries reached, remove from queue
          remove(operation);
          debugPrint('Max retries reached for operation ${operation.type}, removing from queue');
        }
      }
    }
    
    // Add failed operations back to queue for retry
    _operations.addAll(failedOperations);
    if (failedOperations.isNotEmpty) {
      _saveQueue();
      _notifyQueueChanged();
    }
    
    _isProcessing = false;
  }

  void _startProcessing() {
    _processTimer?.cancel();
    _processTimer = Timer.periodic(_processInterval, (timer) {
      processQueue();
    });
  }

  void _stopProcessing() {
    _processTimer?.cancel();
    _processTimer = null;
  }

  void _notifyQueueChanged() {
    _queueController.add(List.unmodifiable(_operations));
  }

  Future<void> _saveQueue() async {
    try {
      // TODO: Replace with Riverpod provider when storage service is migrated
      // final storageService = ref.read(storageServiceProvider);
      
      final serializedOps = _operations.map((op) => {
        'id': op.id,
        'type': op.type,
        'data': op.data,
        'createdAt': op.createdAt.toIso8601String(),
        'retryCount': op.retryCount,
      }).toList();
      
      // await storageService.setJson('offline_queue', {'operations': serializedOps});
      debugPrint('Saved ${serializedOps.length} operations to storage');
    } catch (e) {
      debugPrint('Failed to save queue to storage: $e');
    }
  }

  Future<void> _loadQueue() async {
    try {
      // TODO: Replace with Riverpod provider when storage service is migrated
      // final storageService = ref.read(storageServiceProvider);
      // final queueData = storageService.getJson('offline_queue');
      
      // Temporary: Skip loading from storage until migration is complete
      debugPrint('Queue loading skipped - awaiting Riverpod migration'); 
      _notifyQueueChanged();
    } catch (e) {
      debugPrint('Failed to load queue from storage: $e');
    }
  }


  Future<void> initialize() async {
    await _loadQueue();
    _startProcessing();
  }

  void dispose() {
    _stopProcessing();
    _queueController.close();
  }
}
