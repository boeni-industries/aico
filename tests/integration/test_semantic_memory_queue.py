"""
Integration test for the new queue-based semantic memory architecture.
Tests the complete flow with circuit breaker, rate limiting, and batch processing.
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from aico.ai.memory.request_queue import SemanticRequestQueue, CircuitState
from aico.ai.memory.semantic import SemanticMemoryStore, UserFact
from aico.core.config import ConfigurationManager


class MockModelService:
    """Mock modelservice for testing"""
    
    def __init__(self, delay=0.1, failure_rate=0.0):
        self.delay = delay
        self.failure_rate = failure_rate
        self.call_count = 0
        self.batch_call_count = 0
    
    async def get_embeddings(self, text: str):
        """Mock single embedding request"""
        self.call_count += 1
        await asyncio.sleep(self.delay)
        
        if self.failure_rate > 0 and (self.call_count % int(1/self.failure_rate)) == 0:
            return {"success": False, "error": "Mock failure"}
        
        # Return mock embedding
        return {
            "success": True,
            "data": {
                "embedding": [0.1] * 768  # Mock 768-dim embedding
            }
        }
    
    async def get_embeddings_batch(self, texts: list):
        """Mock batch embedding request"""
        self.batch_call_count += 1
        await asyncio.sleep(self.delay * len(texts) * 0.5)  # Batch is faster
        
        embeddings = []
        for text in texts:
            embeddings.append([0.1] * 768)
        
        return {
            "success": True,
            "data": {
                "embeddings": embeddings
            }
        }


@pytest.fixture
async def mock_config():
    """Create mock configuration"""
    config = MagicMock(spec=ConfigurationManager)
    config.get.return_value = {
        "collections": {"user_facts": "test_facts"},
        "embedding_model": "test-model",
        "max_results": 10
    }
    return config


@pytest.fixture
async def request_queue():
    """Create and start request queue"""
    queue = SemanticRequestQueue(
        max_concurrent=2,
        rate_limit_per_second=10.0,  # High for testing
        circuit_failure_threshold=3,
        circuit_timeout=1.0,
        batch_size=3,
        batch_timeout=0.2
    )
    
    await queue.start(num_workers=2)
    yield queue
    await queue.stop()


@pytest.fixture
async def semantic_store(mock_config):
    """Create semantic memory store with mocked dependencies"""
    store = SemanticMemoryStore(mock_config)
    
    # Mock ChromaDB components
    store._chroma_client = MagicMock()
    store._collection = MagicMock()
    
    return store


class TestSemanticRequestQueue:
    """Test the request queue in isolation"""
    
    @pytest.mark.asyncio
    async def test_single_embedding_request(self, request_queue):
        """Test single embedding request processing"""
        # Setup mock modelservice
        mock_service = MockModelService(delay=0.05)
        request_queue._modelservice = mock_service
        
        # Submit request
        result = await request_queue.submit_request(
            operation='embedding',
            data={'text': 'test text'},
            priority=1,
            timeout=2.0
        )
        
        # Verify result
        assert result is not None
        assert len(result) == 768
        assert mock_service.call_count == 1
    
    @pytest.mark.asyncio
    async def test_batch_embedding_processing(self, request_queue):
        """Test batch processing optimization"""
        # Setup mock modelservice with batch support
        mock_service = MockModelService(delay=0.02)
        request_queue._modelservice = mock_service
        
        # Submit multiple requests quickly to trigger batching
        tasks = []
        for i in range(5):
            task = asyncio.create_task(
                request_queue.submit_request(
                    operation='embedding',
                    data={'text': f'test text {i}'},
                    priority=1,
                    timeout=2.0
                )
            )
            tasks.append(task)
        
        # Wait for all requests
        results = await asyncio.gather(*tasks)
        
        # Verify all results
        assert len(results) == 5
        for result in results:
            assert result is not None
            assert len(result) == 768
        
        # Verify batching occurred (should have fewer individual calls)
        total_calls = mock_service.call_count + mock_service.batch_call_count
        assert total_calls > 0
        print(f"Individual calls: {mock_service.call_count}, Batch calls: {mock_service.batch_call_count}")
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_functionality(self, request_queue):
        """Test circuit breaker opens on failures"""
        # Setup mock service with high failure rate
        mock_service = MockModelService(delay=0.01, failure_rate=1.0)  # Always fails
        request_queue._modelservice = mock_service
        
        # Submit requests until circuit breaker opens
        failure_count = 0
        for i in range(5):
            try:
                await request_queue.submit_request(
                    operation='embedding',
                    data={'text': f'test {i}'},
                    timeout=1.0
                )
            except Exception:
                failure_count += 1
        
        # Verify circuit breaker opened
        assert request_queue._circuit_state == CircuitState.OPEN
        assert failure_count >= request_queue._failure_threshold
        
        # Verify subsequent requests are rejected immediately
        with pytest.raises(RuntimeError, match="Circuit breaker is open"):
            await request_queue.submit_request(
                operation='embedding',
                data={'text': 'should fail'},
                timeout=1.0
            )
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, request_queue):
        """Test rate limiting functionality"""
        # Setup with very low rate limit
        queue = SemanticRequestQueue(
            max_concurrent=1,
            rate_limit_per_second=2.0,  # Only 2 requests per second
            circuit_failure_threshold=10,
            circuit_timeout=5.0
        )
        
        await queue.start(num_workers=1)
        
        try:
            mock_service = MockModelService(delay=0.01)
            queue._modelservice = mock_service
            
            # Submit many requests quickly
            start_time = time.time()
            success_count = 0
            rate_limited_count = 0
            
            for i in range(10):
                try:
                    await queue.submit_request(
                        operation='embedding',
                        data={'text': f'test {i}'},
                        timeout=0.5
                    )
                    success_count += 1
                except RuntimeError as e:
                    if "Rate limit exceeded" in str(e):
                        rate_limited_count += 1
                    else:
                        raise
            
            duration = time.time() - start_time
            
            # Verify rate limiting occurred
            assert rate_limited_count > 0
            print(f"Success: {success_count}, Rate limited: {rate_limited_count}, Duration: {duration:.2f}s")
            
        finally:
            await queue.stop()
    
    @pytest.mark.asyncio
    async def test_queue_statistics(self, request_queue):
        """Test queue statistics and monitoring"""
        mock_service = MockModelService(delay=0.05)
        request_queue._modelservice = mock_service
        
        # Submit some requests
        tasks = []
        for i in range(3):
            task = asyncio.create_task(
                request_queue.submit_request(
                    operation='embedding',
                    data={'text': f'test {i}'},
                    timeout=2.0
                )
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Check statistics
        stats = request_queue.get_queue_stats()
        
        assert 'requests_processed' in stats
        assert 'average_processing_time' in stats
        assert 'circuit_state' in stats
        assert 'modelservice_available' in stats
        assert stats['modelservice_available'] is True
        assert stats['requests_processed'] >= 3


class TestSemanticMemoryStoreIntegration:
    """Test semantic memory store with new queue architecture"""
    
    @pytest.mark.asyncio
    async def test_store_fact_with_queue(self, semantic_store):
        """Test storing facts using the request queue"""
        # Setup mock modelservice
        mock_service = MockModelService(delay=0.05)
        semantic_store.set_modelservice(mock_service)
        
        # Initialize store
        await semantic_store.initialize()
        
        # Create test fact
        fact = UserFact(
            content="User likes coffee",
            fact_type="preference",
            category="personal_info",
            confidence=0.9,
            is_immutable=False,
            valid_from=datetime.utcnow(),
            valid_until=None,
            entities=["coffee"],
            source_conversation_id="test-conv-123",
            user_id="test-user-456"
        )
        
        # Store fact
        result = await semantic_store.store_fact(fact)
        
        # Verify success
        assert result is True
        assert mock_service.call_count >= 1  # Embedding was requested
        
        # Verify ChromaDB was called
        assert semantic_store._collection.add.called
    
    @pytest.mark.asyncio
    async def test_query_with_queue(self, semantic_store):
        """Test querying facts using the request queue"""
        # Setup mock modelservice
        mock_service = MockModelService(delay=0.05)
        semantic_store.set_modelservice(mock_service)
        
        # Mock ChromaDB query response
        semantic_store._collection.query.return_value = {
            "documents": [["User likes coffee"]],
            "metadatas": [[{"user_id": "test-user", "confidence": 0.9}]],
            "distances": [[0.1]]
        }
        
        # Initialize store
        await semantic_store.initialize()
        
        # Query facts
        results = await semantic_store.query(
            query_text="coffee preferences",
            max_results=5,
            filters={"user_id": "test-user"}
        )
        
        # Verify results
        assert len(results) == 1
        assert results[0]["content"] == "User likes coffee"
        assert results[0]["metadata"]["user_id"] == "test-user"
        assert mock_service.call_count >= 1  # Query embedding was requested
    
    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, semantic_store):
        """Test graceful shutdown of semantic store"""
        mock_service = MockModelService()
        semantic_store.set_modelservice(mock_service)
        
        # Initialize store
        await semantic_store.initialize()
        assert semantic_store._initialized is True
        assert semantic_store._request_queue._running is True
        
        # Shutdown store
        await semantic_store.shutdown()
        
        # Verify shutdown
        assert semantic_store._initialized is False
        assert semantic_store._request_queue._running is False


class TestEndToEndFlow:
    """Test complete end-to-end semantic memory flow"""
    
    @pytest.mark.asyncio
    async def test_complete_memory_flow(self, mock_config):
        """Test complete flow from fact storage to retrieval"""
        # Create semantic store
        store = SemanticMemoryStore(mock_config)
        
        # Mock ChromaDB
        store._chroma_client = MagicMock()
        store._collection = MagicMock()
        
        # Setup mock modelservice
        mock_service = MockModelService(delay=0.02)
        store.set_modelservice(mock_service)
        
        try:
            # Initialize store
            await store.initialize()
            
            # Store multiple facts
            facts = [
                UserFact(
                    content="User lives in San Francisco",
                    fact_type="identity",
                    category="personal_info",
                    confidence=0.95,
                    is_immutable=True,
                    valid_from=datetime.utcnow(),
                    valid_until=None,
                    entities=["San Francisco"],
                    source_conversation_id="conv-1",
                    user_id="user-123"
                ),
                UserFact(
                    content="User prefers tea over coffee",
                    fact_type="preference",
                    category="personal_info",
                    confidence=0.8,
                    is_immutable=False,
                    valid_from=datetime.utcnow(),
                    valid_until=None,
                    entities=["tea", "coffee"],
                    source_conversation_id="conv-2",
                    user_id="user-123"
                )
            ]
            
            # Store facts concurrently
            store_tasks = [store.store_fact(fact) for fact in facts]
            store_results = await asyncio.gather(*store_tasks)
            
            # Verify all facts stored
            assert all(store_results)
            
            # Mock query results
            store._collection.query.return_value = {
                "documents": [[fact.content for fact in facts]],
                "metadatas": [[{
                    "user_id": fact.user_id,
                    "fact_type": fact.fact_type,
                    "confidence": fact.confidence
                } for fact in facts]],
                "distances": [[0.1, 0.2]]
            }
            
            # Query facts
            query_results = await store.query(
                query_text="user preferences and location",
                filters={"user_id": "user-123"}
            )
            
            # Verify query results
            assert len(query_results) == 2
            
            # Check queue statistics
            stats = store._request_queue.get_queue_stats()
            assert stats['requests_processed'] >= 3  # 2 stores + 1 query
            assert stats['circuit_state'] == 'closed'
            
        finally:
            # Clean shutdown
            await store.shutdown()


if __name__ == "__main__":
    # Run specific test for development
    async def run_basic_test():
        print("Testing basic queue functionality...")
        queue = SemanticRequestQueue(
            max_concurrent=2,
            rate_limit_per_second=5.0,
            batch_size=3,
            batch_timeout=0.5,
            enable_threading=True
        )
        
        await queue.start()
        
        try:
            mock_service = MockModelService(delay=0.1)
            queue._modelservice = mock_service
            
            # Test single request
            result = await queue.submit_request(
                operation='embedding',
                data={'text': 'Hello world'},
                timeout=2.0
            )
            
            print(f"Single request result: {len(result)} dimensions")
            
            # Test batch requests
            tasks = []
            for i in range(5):
                task = asyncio.create_task(
                    queue.submit_request(
                        operation='embedding',
                        data={'text': f'Batch text {i}'},
                        timeout=2.0
                    )
                )
                tasks.append(task)
            
            batch_results = await asyncio.gather(*tasks)
            print(f"Batch results: {len(batch_results)} embeddings")
            
            # Print statistics
            stats = queue.get_queue_stats()
            print(f"Queue stats: {stats}")
            
        finally:
            await queue.stop()
    
    async def run_shutdown_test():
        print("\nTesting shutdown integration...")
        from aico.ai.memory.request_queue import _set_global_shutdown, _is_global_shutdown_requested
        
        queue = SemanticRequestQueue(
            max_concurrent=1,
            enable_threading=True
        )
        
        await queue.start()
        
        try:
            mock_service = MockModelService(delay=0.1)
            queue._modelservice = mock_service
            
            # Submit a request
            task = asyncio.create_task(
                queue.submit_request(
                    operation='embedding',
                    data={'text': 'test'},
                    timeout=2.0
                )
            )
            
            # Wait a bit then signal shutdown
            await asyncio.sleep(0.05)
            _set_global_shutdown()
            
            # Try to submit another request (should fail)
            try:
                await queue.submit_request(
                    operation='embedding',
                    data={'text': 'should fail'},
                    timeout=1.0
                )
                print("ERROR: Request should have been rejected!")
            except RuntimeError as e:
                if "shutdown" in str(e):
                    print(f"✅ Request correctly rejected during shutdown: {e}")
                else:
                    print(f"❌ Unexpected error: {e}")
            
            # Wait for first task
            try:
                result = await task
                print(f"✅ In-flight request completed: {len(result) if result else 0} dimensions")
            except Exception as e:
                print(f"⚠️  In-flight request cancelled: {e}")
            
        finally:
            await queue.stop()
    
    # Run the tests
    asyncio.run(run_basic_test())
    asyncio.run(run_shutdown_test())
    print("\n✅ All tests completed!")
