"""
Modern async request queue with circuit breaker and rate limiting for semantic memory operations.
Replaces fire-and-forget tasks with controlled, scalable processing.
"""

import asyncio
import time
import uuid
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import threading
from collections import defaultdict
import os
import signal
import atexit
from contextlib import asynccontextmanager
logger = logging.getLogger(__name__)


# Global shutdown tracking - integrates with existing AICO shutdown system
_global_shutdown_requested = False
_shutdown_lock = threading.Lock()

def _set_global_shutdown():
    """Mark global shutdown as requested"""
    global _global_shutdown_requested
    with _shutdown_lock:
        _global_shutdown_requested = True

def _is_global_shutdown_requested() -> bool:
    """Check if global shutdown has been requested"""
    global _global_shutdown_requested
    with _shutdown_lock:
        return _global_shutdown_requested


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class RequestItem:
    """Individual request in the queue"""
    id: str
    operation: str  # 'embedding', 'ner', 'sentiment'
    data: Dict[str, Any]
    priority: int = 0  # Higher = more important
    created_at: float = field(default_factory=time.time)
    retry_count: int = 0
    max_retries: int = 3
    callback: Optional[Callable] = None
    future: Optional[asyncio.Future] = None


class SemanticRequestQueue:
    """
    Modern async request queue with:
    - Circuit breaker pattern
    - Rate limiting with token bucket
    - Batch processing optimization  
    - Graceful degradation
    - Comprehensive monitoring
    """
    
    def __init__(
        self,
        max_concurrent: int = 2,
        rate_limit_per_second: float = 5.0,
        circuit_failure_threshold: int = 5,
        circuit_timeout: float = 30.0,
        batch_size: int = 10,
        batch_timeout: float = 1.0,
        enable_threading: bool = True,
        thread_pool_size: Optional[int] = None
    ):
        # Core queue management
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active_requests: Dict[str, RequestItem] = {}
        
        # Rate limiting (token bucket algorithm)
        self._rate_limit = rate_limit_per_second
        self._tokens = rate_limit_per_second
        self._last_refill = time.time()
        
        # Circuit breaker
        self._circuit_state = CircuitState.CLOSED
        self._failure_count = 0
        self._failure_threshold = circuit_failure_threshold
        self._circuit_timeout = circuit_timeout
        self._last_failure_time: Optional[float] = None
        
        # Batch processing
        self._batch_size = batch_size
        self._batch_timeout = batch_timeout
        self._pending_batches: Dict[str, List[RequestItem]] = {}
        self._batch_timers: Dict[str, asyncio.Task] = {}
        
        # Monitoring
        self._stats = {
            'requests_processed': 0,
            'requests_failed': 0,
            'requests_circuit_broken': 0,
            'requests_rate_limited': 0,
            'average_processing_time': 0.0,
            'batch_efficiency': 0.0
        }
        
        # Worker management
        self._workers: List[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()
        self._running = False
        
        # Multi-threading optimization
        self._enable_threading = enable_threading
        self._thread_pool_size = thread_pool_size or min(32, (os.cpu_count() or 1) + 4)
        self._thread_pool: Optional[ThreadPoolExecutor] = None
        self._cpu_intensive_pool: Optional[ProcessPoolExecutor] = None
        
        logger.info(f"SemanticRequestQueue configured with threading={enable_threading}, "
                   f"thread_pool_size={self._thread_pool_size}, cpu_cores={os.cpu_count()}")
    
    async def start(self, num_workers: int = 3):
        """Start the request queue workers with threading support"""
        if self._running:
            return
            
        # Check if global shutdown is already requested
        if _is_global_shutdown_requested():
            logger.warning("Cannot start queue - global shutdown in progress")
            return
            
        self._running = True
        self._shutdown_event.clear()
        
        # Initialize thread pools for CPU-intensive operations
        if self._enable_threading:
            self._thread_pool = ThreadPoolExecutor(
                max_workers=self._thread_pool_size,
                thread_name_prefix="semantic-worker"
            )
            # For truly CPU-bound operations (like large batch processing)
            self._cpu_intensive_pool = ProcessPoolExecutor(
                max_workers=min(4, os.cpu_count() or 1)
            )
            logger.info(f"Thread pools initialized: {self._thread_pool_size} threads, "
                       f"{self._cpu_intensive_pool._max_workers} processes")
        
        # Start async worker tasks
        for i in range(num_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self._workers.append(worker)
        
        logger.info(f"SemanticRequestQueue started with {num_workers} async workers + threading pools")
    
    async def stop(self, timeout: float = 30.0):
        """Gracefully stop the request queue and thread pools"""
        if not self._running:
            return
            
        logger.warning(f"🔄 QUEUE SHUTDOWN: Stopping queue {id(self)} with {timeout}s timeout")
        
        self._running = False
        self._shutdown_event.set()
        
        start_time = time.time()
        
        try:
            # Cancel batch timers
            for timer in self._batch_timers.values():
                timer.cancel()
            
            # Wait for workers to finish with timeout
            if self._workers:
                remaining_time = max(0, timeout - (time.time() - start_time))
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*self._workers, return_exceptions=True),
                        timeout=remaining_time
                    )
                    logger.info(f"All async workers stopped for queue {id(self)}")
                except asyncio.TimeoutError:
                    logger.warning(f"Some async workers did not stop within timeout for queue {id(self)}")
                    # Cancel remaining workers
                    for worker in self._workers:
                        if not worker.done():
                            worker.cancel()
            
            # Shutdown thread pools with remaining time
            remaining_time = max(0, timeout - (time.time() - start_time))
            
            if self._thread_pool:
                logger.info(f"Shutting down thread pool for queue {id(self)}")
                try:
                    # Use a separate thread to handle shutdown with timeout
                    shutdown_future = asyncio.get_event_loop().run_in_executor(
                        None, 
                        lambda: self._thread_pool.shutdown(wait=True, timeout=min(10.0, remaining_time))
                    )
                    await asyncio.wait_for(shutdown_future, timeout=remaining_time)
                    logger.info(f"Thread pool shutdown completed for queue {id(self)}")
                except (asyncio.TimeoutError, Exception) as e:
                    logger.warning(f"Thread pool shutdown timeout/error for queue {id(self)}: {e}")
            
            remaining_time = max(0, timeout - (time.time() - start_time))
            
            if self._cpu_intensive_pool:
                logger.info(f"Shutting down process pool for queue {id(self)}")
                try:
                    shutdown_future = asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self._cpu_intensive_pool.shutdown(wait=True, timeout=min(15.0, remaining_time))
                    )
                    await asyncio.wait_for(shutdown_future, timeout=remaining_time)
                    logger.info(f"Process pool shutdown completed for queue {id(self)}")
                except (asyncio.TimeoutError, Exception) as e:
                    logger.warning(f"Process pool shutdown timeout/error for queue {id(self)}: {e}")
            
            self._workers.clear()
            
            # Mark as stopped (no need to unregister from global manager)
            pass
            
            total_time = time.time() - start_time
            logger.warning(f"✅ QUEUE SHUTDOWN: Completed for queue {id(self)} in {total_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Error during queue shutdown {id(self)}: {e}")
            raise
    
    async def submit_request(
        self,
        operation: str,
        data: Dict[str, Any],
        priority: int = 0,
        timeout: float = 30.0
    ) -> Any:
        """
        Submit a request to the queue
        Returns: Future that resolves with the result
        """
        logger.info(f"🔍 [QUEUE_DEBUG] submit_request called: operation={operation}, timeout={timeout}")
        
        if not self._running:
            logger.error(f"🔍 [QUEUE_DEBUG] Request queue not started!")
            raise RuntimeError("Request queue not started")
        
        logger.info(f"🔍 [QUEUE_DEBUG] Queue is running, workers: {len(self._workers)}, active: {len([w for w in self._workers if not w.done()])}")
        
        # Check if global shutdown is in progress
        if _is_global_shutdown_requested():
            raise RuntimeError("Global shutdown in progress - rejecting new requests")
        
        # Check if modelservice is available
        if not hasattr(self, '_modelservice') or not self._modelservice:
            logger.error(f"🔍 [QUEUE_DEBUG] Modelservice not available!")
            raise RuntimeError("Modelservice not available - cannot process requests")
        
        logger.info(f"🔍 [QUEUE_DEBUG] Modelservice available: {type(self._modelservice)}")
        
        # Check circuit breaker
        if not self._is_circuit_closed():
            self._stats['requests_circuit_broken'] += 1
            logger.warning(f"🔍 [QUEUE_DEBUG] Circuit breaker is open! State: {self._circuit_state.value}")
            raise RuntimeError("Circuit breaker is open - service unavailable")
        
        logger.info(f"🔍 [QUEUE_DEBUG] Circuit breaker is closed, proceeding")
        
        # Check rate limit
        if not await self._acquire_rate_limit():
            self._stats['requests_rate_limited'] += 1
            raise RuntimeError("Rate limit exceeded")
        
        # Create request item
        request_id = str(uuid.uuid4())
        future = asyncio.Future()
        request = RequestItem(
            id=request_id,
            operation=operation,
            data=data,
            priority=priority,
            future=future,
            created_at=time.time()
        )
        
        logger.info(f"🔍 [QUEUE_DEBUG] Created request {request_id}, adding to queue")
        
        # Track active request
        self._active_requests[request_id] = request
        
        # Add to queue with priority (negative for max-heap behavior)
        await self._queue.put((-priority, time.time(), request))
        self._stats['requests_processed'] += 1
        
        logger.info(f"🔍 [QUEUE_DEBUG] Request {request_id} added to queue, queue size: {self._queue.qsize()}")
        
        try:
            # Wait for result with timeout
            logger.info(f"🔍 [QUEUE_DEBUG] Waiting for result for request {request_id} with timeout {timeout}s")
            result = await asyncio.wait_for(future, timeout=timeout)
            logger.info(f"🔍 [QUEUE_DEBUG] Request {request_id} completed successfully")
            return result
        except asyncio.TimeoutError:
            logger.error(f"🔍 [QUEUE_DEBUG] Request {request_id} timed out after {timeout}s")
            # Cancel the request if still pending
            if request_id in self._active_requests:
                del self._active_requests[request_id]
            raise
    async def _worker(self, worker_name: str):
        """Worker coroutine that processes requests from the queue"""
        logger.info(f"🔍 [WORKER_DEBUG] Worker {worker_name} started")
        
        while not self._shutdown_event.is_set() and not _is_global_shutdown_requested():
            try:
                # Get request from queue with timeout
                try:
                    logger.debug(f"🔍 [WORKER_DEBUG] {worker_name} waiting for request, queue size: {self._queue.qsize()}")
                    _, _, request = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=1.0
                    )
                    logger.info(f"🔍 [WORKER_DEBUG] {worker_name} got request {request.id}, operation: {request.operation}")
                except asyncio.TimeoutError:
                    continue
                
                # Check shutdown again after getting request
                if self._shutdown_event.is_set() or _is_global_shutdown_requested():
                    # Put request back and exit
                    if not request.future.cancelled():
                        request.future.cancel()
                    break
                
                # Skip if request was cancelled
                if request.future.cancelled():
                    logger.warning(f"🔍 [WORKER_DEBUG] {worker_name} skipping cancelled request {request.id}")
                    continue
                
                logger.info(f"🔍 [WORKER_DEBUG] {worker_name} processing request {request.id}")
                
                # Process request with semaphore (concurrency control)
                async with self._semaphore:
                    logger.info(f"🔍 [WORKER_DEBUG] {worker_name} calling _process_request for {request.operation}")
                    await self._process_request(request)
                
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {e}")
        
        logger.debug(f"Worker {worker_name} stopped")
    
    async def _process_request(self, request: RequestItem):
        """Process a single request"""
        logger.info(f"🔍 [PROCESS_DEBUG] _process_request called for {request.id}, operation: {request.operation}")
        start_time = time.time()
        self._active_requests[request.id] = request
        
        try:
            # Determine if this should be batched
            if self._should_batch(request.operation):
                logger.info(f"🔍 [PROCESS_DEBUG] Request {request.id} should be batched")
                result = await self._process_batched_request(request)
            else:
                logger.info(f"🔍 [PROCESS_DEBUG] Request {request.id} will be processed individually")
                result = await self._process_individual_request(request)
            
            # Success - reset circuit breaker
            if self._circuit_state == CircuitState.HALF_OPEN:
                self._circuit_state = CircuitState.CLOSED
                self._failure_count = 0
                logger.warning(f"✅ CIRCUIT BREAKER CLOSED: Service recovered - semantic processing restored")
            elif self._circuit_state == CircuitState.CLOSED and self._failure_count > 0:
                # Reset failure count on success
                self._failure_count = 0
            
            # Update stats
            processing_time = time.time() - start_time
            self._update_processing_stats(processing_time, success=True)
            
            # Return result
            if not request.future.cancelled():
                request.future.set_result(result)
        
        except Exception as e:
            # Handle failure
            await self._handle_request_failure(request, e)
        
        finally:
            # Cleanup
            if request.id in self._active_requests:
                del self._active_requests[request.id]
    
    def _should_batch(self, operation: str) -> bool:
        """Determine if operation should be batched"""
        # RE-ENABLED: Batch embedding operations for efficiency
        if operation == 'embedding':
            return self._queue.qsize() >= self._batch_size or len(self._pending_batches.get(operation, [])) >= self._batch_size
        return False
    
    async def _process_batched_request(self, request: RequestItem) -> Any:
        """Process request as part of a batch"""
        operation = request.operation
        
        # Add to pending batch
        if operation not in self._pending_batches:
            self._pending_batches[operation] = []
        
        self._pending_batches[operation].append(request)
        
        # Check if batch is ready
        batch = self._pending_batches[operation]
        if len(batch) >= self._batch_size:
            # Process full batch immediately
            return await self._execute_batch(operation)
        else:
            # Set timer for batch timeout
            if operation not in self._batch_timers:
                timer = asyncio.create_task(
                    self._batch_timeout_handler(operation)
                )
                self._batch_timers[operation] = timer
            
            # Wait for batch to be processed
            return await request.future
    
    async def _batch_timeout_handler(self, operation: str):
        """Handle batch timeout - process partial batch"""
        await asyncio.sleep(self._batch_timeout)
        
        if operation in self._pending_batches and self._pending_batches[operation]:
            await self._execute_batch(operation)
    
    async def _execute_batch(self, operation: str) -> Any:
        """Execute a batch of requests"""
        if operation not in self._pending_batches:
            return
        
        batch = self._pending_batches[operation]
        if not batch:
            return
        
        # Check for shutdown before processing batch
        if self._shutdown_event.is_set() or _is_global_shutdown_requested():
            # Cancel all requests in batch
            for request in batch:
                if not request.future.cancelled():
                    request.future.cancel()
            return
        
        # Clear batch and timer
        self._pending_batches[operation] = []
        if operation in self._batch_timers:
            self._batch_timers[operation].cancel()
            del self._batch_timers[operation]
        
        try:
            # Process batch based on operation type
            if operation == 'embedding':
                results = await self._process_embedding_batch(batch)
            elif operation == 'ner':
                results = await self._process_ner_batch(batch)
            else:
                raise ValueError(f"Unsupported batch operation: {operation}")
            
            # Set results for all requests in batch
            for i, request in enumerate(batch):
                if not request.future.cancelled() and not request.future.done():
                    try:
                        request.future.set_result(results[i])
                    except asyncio.InvalidStateError:
                        # Future was already resolved, ignore
                        pass
            
            # Update batch efficiency stats
            self._stats['batch_efficiency'] = len(batch) / self._batch_size
            
        except Exception as e:
            # Set exception for all requests in batch (check if future is still valid)
            for request in batch:
                if not request.future.cancelled() and not request.future.done():
                    try:
                        request.future.set_exception(e)
                    except asyncio.InvalidStateError:
                        # Future was already resolved, ignore
                        pass
            raise
    
    async def _process_embedding_batch(self, batch: List[RequestItem]) -> List[Any]:
        """Process a batch of embedding requests using modelservice with threading"""
        if not hasattr(self, '_modelservice') or not self._modelservice:
            raise RuntimeError("Modelservice not available for embedding batch")
        
        # Check for shutdown before processing
        if self._shutdown_event.is_set() or _is_global_shutdown_requested():
            raise RuntimeError("Shutdown in progress - cancelling batch processing")
        
        # Extract texts from batch
        texts = [req.data.get('text', '') for req in batch]
        batch_size = len(texts)
        
        logger.info(f"Processing embedding batch of {batch_size} texts with threading optimization")
        
        try:
            logger.info(f"🔍 [BATCH_DEBUG] Processing batch of {batch_size} embeddings")
            
            # Use modelservice batch embedding (it handles individual requests internally)
            if hasattr(self._modelservice, 'get_embeddings_batch'):
                logger.info(f"🔍 [BATCH_DEBUG] Using modelservice batch processing")
                # ModelServiceClient.get_embeddings_batch(model, prompts) signature
                result = await self._modelservice.get_embeddings_batch(
                    model="paraphrase-multilingual",  # Default embedding model
                    prompts=texts
                )
                logger.info(f"🔍 [BATCH_DEBUG] Batch result: success={result.get('success') if result else 'None'}")
                
                if result and result.get('success'):
                    embeddings = result.get('data', {}).get('embeddings', [])
                    logger.info(f"🔍 [BATCH_DEBUG] Got {len(embeddings)} embeddings from batch")
                    return embeddings
                else:
                    error_msg = result.get('error', 'Unknown error') if result else 'No result returned'
                    raise RuntimeError(f"Batch embedding failed: {error_msg}")
            
            # Fallback to individual async requests if batch not available
            logger.info(f"🔍 [BATCH_DEBUG] Fallback to individual requests for {batch_size} embeddings")
            embeddings = []
            for i, text in enumerate(texts):
                logger.info(f"🔍 [BATCH_DEBUG] Processing individual request {i+1}/{batch_size}")
                result = await self._modelservice.get_embeddings(
                    model="paraphrase-multilingual",
                    prompt=text
                )
                if result and result.get('success'):
                    embedding = result.get('data', {}).get('embedding')
                    embeddings.append(embedding)
                    logger.info(f"🔍 [BATCH_DEBUG] Individual request {i+1} succeeded")
                else:
                    embeddings.append(None)
                    logger.warning(f"🔍 [BATCH_DEBUG] Individual request {i+1} failed")
            return embeddings
                
        except Exception as e:
            logger.error(f"Threaded batch embedding failed: {e}")
            raise
    
    async def _process_ner_batch(self, batch: List[RequestItem]) -> List[Any]:
        """Process a batch of NER requests"""
        # Similar to embedding batch but for NER
        texts = [req.data.get('text', '') for req in batch]
        
        # Process NER batch (would need modelservice client)
        # This is a placeholder - actual implementation would use modelservice
        results = []
        for text in texts:
            # Placeholder NER result
            results.append({'entities': {}})
        
        return results
    
    async def _process_individual_request(self, request: RequestItem) -> Any:
        """Process a single request immediately"""
        logger.info(f"Processing {request.operation} request {request.id}")
        
        if request.operation == 'embedding':
            return await self._process_single_embedding(request.data)
        elif request.operation == 'ner':
            return await self._process_single_ner(request.data)
        elif request.operation == 'sentiment':
            return await self._process_single_sentiment(request.data)
        else:
            raise ValueError(f"Unsupported operation: {request.operation}")
    
    async def _process_single_embedding(self, data: Dict[str, Any]) -> Any:
        """Process single embedding request using modelservice"""
        if not hasattr(self, '_modelservice') or not self._modelservice:
            raise RuntimeError("Modelservice not available for embedding")
        # Check for shutdown before processing
        if self._shutdown_event.is_set() or _is_global_shutdown_requested():
            raise RuntimeError("Shutdown in progress - cancelling embedding request")
        
        text = data.get('text', '')
        if not text:
            raise ValueError("No text provided for embedding")
        
        try:
            logger.info(f"🔍 [EMBEDDING_DEBUG] Calling ModelService.get_embeddings for: '{text[:30]}...'")
            
            # Use correct ModelServiceClient.get_embeddings(model, prompt) signature
            result = await self._modelservice.get_embeddings(
                model="paraphrase-multilingual",
                prompt=text
            )
            
            logger.info(f"🔍 [EMBEDDING_DEBUG] ModelService result: success={result.get('success') if result else 'None'}")
            
            if result and result.get('success'):
                embedding = result.get('data', {}).get('embedding')
                if embedding:
                    logger.info(f"🔍 [EMBEDDING_DEBUG] Got embedding with {len(embedding)} dimensions")
                    return embedding
                else:
                    raise RuntimeError("No embedding data in successful response")
            else:
                error_msg = result.get('error', 'Unknown error') if result else 'No result returned'
                raise RuntimeError(f"Embedding request failed: {error_msg}")
        except Exception as e:
            logger.error(f"🔍 [EMBEDDING_DEBUG] Single embedding failed for text '{text[:50]}...': {e}")
            raise
    
    async def _process_single_ner(self, data: Dict[str, Any]) -> Any:
        """Process single NER request"""
        # Placeholder - would use modelservice client
        return {'entities': {}}
    
    async def _process_single_sentiment(self, data: Dict[str, Any]) -> Any:
        """Process single sentiment request"""
        # Placeholder - would use modelservice client
        return {'sentiment': 'positive', 'confidence': 0.8}
    
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get detailed queue statistics for monitoring"""
        stats = {
            **self.get_stats(),
            'pending_batches': {op: len(batch) for op, batch in self._pending_batches.items()},
            'batch_timers_active': len(self._batch_timers),
            'workers_running': len([w for w in self._workers if not w.done()]),
            'modelservice_available': hasattr(self, '_modelservice') and self._modelservice is not None,
            'threading_enabled': self._enable_threading,
            'thread_pool_size': self._thread_pool_size if self._enable_threading else 0,
            'circuit_breaker_can_reset': True,
        }
        
        # Add thread pool statistics if available
        if self._thread_pool:
            stats['thread_pool_active'] = True
            # ThreadPoolExecutor doesn't expose detailed stats, but we can add custom tracking
        else:
            stats['thread_pool_active'] = False
            
        if self._cpu_intensive_pool:
            stats['process_pool_active'] = True
        else:
            stats['process_pool_active'] = False
            
        return stats
    
    async def _handle_request_failure(self, request: RequestItem, error: Exception):
        """Handle request failure with retry logic and circuit breaker"""
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        # Update circuit breaker state
        if self._failure_count >= self._failure_threshold:
            if self._circuit_state == CircuitState.CLOSED:
                self._circuit_state = CircuitState.OPEN
                logger.warning(f"🚨 CIRCUIT BREAKER OPENED: {self._failure_count} failures detected - semantic requests blocked for {self._circuit_timeout}s")
        
        # Retry logic
        if request.retry_count < request.max_retries:
            request.retry_count += 1
            # Exponential backoff
            delay = min(2 ** request.retry_count, 30)
            await asyncio.sleep(delay)
            
            # Re-queue request
            await self._queue.put((-request.priority, time.time(), request))
            logger.debug(f"Retrying request {request.id} (attempt {request.retry_count})")
        else:
            # Max retries exceeded
            self._stats['requests_failed'] += 1
            if not request.future.cancelled():
                request.future.set_exception(error)
    
    def _is_circuit_closed(self) -> bool:
        """Check if circuit breaker allows requests"""
        if self._circuit_state == CircuitState.CLOSED:
            return True
        elif self._circuit_state == CircuitState.OPEN:
            # Check if timeout has passed
            if (self._last_failure_time and 
                time.time() - self._last_failure_time > self._circuit_timeout):
                self._circuit_state = CircuitState.HALF_OPEN
                logger.warning(f"🔄 CIRCUIT BREAKER HALF-OPEN: Testing recovery after {self._circuit_timeout}s timeout")
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    async def _acquire_rate_limit(self) -> bool:
        """Token bucket rate limiting"""
        now = time.time()
        
        # Refill tokens
        time_passed = now - self._last_refill
        self._tokens = min(
            self._rate_limit,
            self._tokens + time_passed * self._rate_limit
        )
        self._last_refill = now
        
        # Check if token available
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return True
        
        return False
    
    def _update_processing_stats(self, processing_time: float, success: bool):
        """Update processing statistics"""
        if success:
            self._stats['requests_processed'] += 1
            
            # Update average processing time (exponential moving average)
            alpha = 0.1
            current_avg = self._stats['average_processing_time']
            self._stats['average_processing_time'] = (
                alpha * processing_time + (1 - alpha) * current_avg
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get basic queue statistics"""
        return {
            'requests_processed': self._stats['requests_processed'],
            'requests_failed': self._stats['requests_failed'],
            'requests_circuit_broken': self._stats['requests_circuit_broken'],
            'requests_rate_limited': self._stats['requests_rate_limited'],
            'average_processing_time': self._stats['average_processing_time'],
            'batch_efficiency': self._stats['batch_efficiency'],
            'circuit_state': self._circuit_state.value,
            'failure_count': self._failure_count,
            'queue_size': self._queue.qsize(),
            'active_requests': len(self._active_requests),
            'tokens_available': self._tokens
        }
    
    def reset_circuit_breaker(self) -> None:
        """Manually reset the circuit breaker to closed state"""
        self._circuit_state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        logger.warning(f" CIRCUIT BREAKER RESET: Manually reset to CLOSED state")
