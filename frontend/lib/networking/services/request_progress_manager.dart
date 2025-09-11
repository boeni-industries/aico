import 'dart:async';

/// Manages progressive timeout handling with intermediate status updates
class RequestProgressManager {
  static final Map<String, RequestProgress> _activeRequests = {};
  static final StreamController<RequestProgressEvent> _progressController = 
      StreamController<RequestProgressEvent>.broadcast();
  
  static Stream<RequestProgressEvent> get progressStream => _progressController.stream;
  
  /// Start tracking a request with progressive timeout stages
  static String startRequest(String endpoint, String method) {
    final requestId = '${method}_${endpoint}_${DateTime.now().millisecondsSinceEpoch}';
    final progress = RequestProgress(
      id: requestId,
      endpoint: endpoint,
      method: method,
      startTime: DateTime.now(),
    );
    
    _activeRequests[requestId] = progress;
    
    // Schedule intermediate status updates
    _scheduleProgressUpdates(requestId);
    
    return requestId;
  }
  
  /// Complete a request successfully
  static void completeRequest(String requestId, {dynamic result}) {
    final progress = _activeRequests[requestId];
    if (progress != null) {
      progress.status = RequestStatus.completed;
      progress.result = result;
      _emitProgress(progress);
      _activeRequests.remove(requestId);
    }
  }
  
  /// Fail a request with error
  static void failRequest(String requestId, String error, {bool canRetry = true}) {
    final progress = _activeRequests[requestId];
    if (progress != null) {
      progress.status = RequestStatus.failed;
      progress.error = error;
      progress.canRetry = canRetry;
      _emitProgress(progress);
      _activeRequests.remove(requestId);
    }
  }
  
  /// Cancel a request
  static void cancelRequest(String requestId) {
    final progress = _activeRequests[requestId];
    if (progress != null) {
      progress.status = RequestStatus.cancelled;
      _emitProgress(progress);
      _activeRequests.remove(requestId);
    }
  }
  
  static void _scheduleProgressUpdates(String requestId) {
    // 10 seconds: "Processing your request..."
    Timer(const Duration(seconds: 10), () {
      final progress = _activeRequests[requestId];
      if (progress != null && progress.status == RequestStatus.processing) {
        progress.status = RequestStatus.working;
        progress.message = "Processing your request...";
        _emitProgress(progress);
      }
    });
    
    // 30 seconds: "Still working on it..."
    Timer(const Duration(seconds: 30), () {
      final progress = _activeRequests[requestId];
      if (progress != null && progress.status == RequestStatus.working) {
        progress.status = RequestStatus.stillWorking;
        progress.message = "Still working on it, this might take a moment...";
        _emitProgress(progress);
      }
    });
    
    // 60 seconds: "Taking longer than expected..."
    Timer(const Duration(seconds: 60), () {
      final progress = _activeRequests[requestId];
      if (progress != null && progress.status == RequestStatus.stillWorking) {
        progress.status = RequestStatus.takingLong;
        progress.message = "Taking longer than expected, but still processing...";
        _emitProgress(progress);
      }
    });
    
    // 90 seconds: "Almost there..."
    Timer(const Duration(seconds: 90), () {
      final progress = _activeRequests[requestId];
      if (progress != null && progress.status == RequestStatus.takingLong) {
        progress.status = RequestStatus.almostDone;
        progress.message = "Almost there, just a bit longer...";
        _emitProgress(progress);
      }
    });
  }
  
  static void _emitProgress(RequestProgress progress) {
    _progressController.add(RequestProgressEvent(progress));
  }
}

enum RequestStatus {
  processing,
  working,
  stillWorking,
  takingLong,
  almostDone,
  completed,
  failed,
  cancelled,
}

class RequestProgress {
  final String id;
  final String endpoint;
  final String method;
  final DateTime startTime;
  
  RequestStatus status = RequestStatus.processing;
  String? message;
  String? error;
  dynamic result;
  bool canRetry = false;
  
  RequestProgress({
    required this.id,
    required this.endpoint,
    required this.method,
    required this.startTime,
  });
  
  Duration get duration => DateTime.now().difference(startTime);
}

class RequestProgressEvent {
  final RequestProgress progress;
  
  const RequestProgressEvent(this.progress);
}
