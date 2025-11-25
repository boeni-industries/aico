"""
Multi-Pass Extraction

Implements multi-pass extraction pipeline with gleanings for high completeness.
Uses GLiNER for entity extraction and LLM for relation extraction.
"""

from typing import List, Dict, Any, Optional
import asyncio
import json
import time
from datetime import datetime

from aico.core.logging import get_logger
from aico.core.config import ConfigurationManager

from .models import Node, Edge, PropertyGraph
from .modelservice_client import ModelserviceClient

logger = get_logger("shared", "ai.knowledge_graph.extractor")


def normalize_relation_type(relation_type: str) -> str:
    """
    Normalize relationship type to valid identifier format.
    
    Replaces spaces with underscores and ensures uppercase.
    Examples: "WORKS FOR" -> "WORKS_FOR", "lives in" -> "LIVES_IN"
    
    Args:
        relation_type: Raw relationship type from extraction
        
    Returns:
        Normalized relationship type
    """
    return relation_type.upper().replace(" ", "_")


def safe_get_name(node: Node) -> str:
    """
    Safely extract name from node properties.
    Handles both string (correct) and list (data corruption) cases.
    
    Args:
        node: Node to extract name from
        
    Returns:
        Name as string
    """
    name = node.properties.get("name", "")
    
    # Handle corrupted data where name is a list instead of string
    if isinstance(name, list):
        name = name[0] if name else ""
        logger.warning(f"Node {node.id} has list 'name' property (data corruption): {name}")
    
    return str(name)


def normalize_entity_label(label: str) -> str:
    """
    Normalize entity label to canonical form.
    
    Maps GLiNER variant labels to canonical personal graph labels.
    Examples: "work project" -> "PROJECT", "todo" -> "TASK"
    
    Args:
        label: Raw entity label from GLiNER
        
    Returns:
        Canonical entity label
    """
    label_lower = label.lower()
    
    # Project variants
    if label_lower in ["work project", "personal project", "software project"]:
        return "PROJECT"
    
    # Goal variants
    if label_lower in ["objective", "ambition"]:
        return "GOAL"
    
    # Task variants
    if label_lower in ["todo", "action item"]:
        return "TASK"
    
    # Interest variants
    if label_lower in ["hobby", "passion"]:
        return "INTEREST"
    
    # Activity variants
    if label_lower in ["action"]:
        return "ACTIVITY"
    
    # Priority variants
    if label_lower in ["deadline"]:
        return "PRIORITY"
    
    # Default: uppercase the label
    return label.upper()


# Semantic label definitions for embedding-based classification
# Based on research: https://arxiv.org/abs/1803.03378 (label embeddings)
# Concrete, example-rich definitions for better semantic matching
# Include specific examples and keywords that appear in real entity mentions
LABEL_DEFINITIONS = {
    "PROJECT": "work project, software project, website redesign, app development, construction project, research project, business initiative, product launch, system upgrade, migration project",
    "GOAL": "career goal, promotion goal, learning goal, get promoted, become senior, achieve certification, reach target, accomplish objective, personal aspiration",
    "TASK": "complete task, finish work, review code, write document, send email, make call, schedule meeting, update system, fix bug, test feature",
    "ACTIVITY": "working on, building, creating, developing, designing, implementing, testing, reviewing, planning, organizing, managing",
    "INTEREST": "interested in, learning about, studying, exploring, researching, passionate about, curious about, want to know more about",
    "PRIORITY": "urgent, important, critical, high priority, must do, need to focus on, top priority, time-sensitive"
}

# Cache for label embeddings (computed once per session)
_label_embeddings_cache = {}

# Cache for entity text embeddings (per-user, with TTL)
# Format: {user_id: {entity_text: (embedding, timestamp)}}
_entity_embeddings_cache = {}
_ENTITY_CACHE_TTL_SECONDS = 3600  # 1 hour TTL to prevent stale data


async def correct_entity_label_semantic(
    label: str, 
    entity_text: str,
    modelservice_client: Any
) -> str:
    """
    Apply semantic similarity-based post-processing to correct GLiNER mislabeling.
    
    This is the production-standard approach using label embeddings:
    1. Embed the entity text using multilingual embeddings
    2. Embed all candidate label definitions
    3. Compute cosine similarity
    4. Return label with highest similarity
    
    This approach is:
    - Language-agnostic (works for any language)
    - Semantic (understands meaning, not keywords)
    - Fast (just cosine similarity, no LLM)
    
    Based on research: https://arxiv.org/abs/1803.03378
    
    Args:
        label: Label assigned by GLiNER
        entity_text: The actual entity text
        modelservice_client: Client for embedding generation
        
    Returns:
        Corrected label
    """
    # Only classify ambiguous or universal labels
    # ENTITY = from universal mention detection (needs classification)
    # EVENT = often confused with PROJECT (needs correction)
    # Other specific labels (PERSON, ORG, etc.) = keep as-is
    if label not in ["EVENT", "ENTITY"]:
        return label
    
    try:
        # Get entity embedding
        entity_result = await modelservice_client.generate_embeddings([entity_text])
        
        if not entity_result.get("embeddings"):
            return label
        
        entity_embedding = entity_result["embeddings"][0]
        if not entity_embedding:
            return label
        
        # Get or compute label embeddings (cached)
        if not _label_embeddings_cache:
            definitions = list(LABEL_DEFINITIONS.values())
            result = await modelservice_client.generate_embeddings(definitions)
            if result.get("embeddings"):
                for label_name, embedding in zip(LABEL_DEFINITIONS.keys(), result["embeddings"]):
                    _label_embeddings_cache[label_name] = embedding
        
        # Compute cosine similarity with each label
        import numpy as np
        entity_vec = np.array(entity_embedding)
        
        best_label = label
        best_similarity = -1.0
        
        for label_name, label_embedding in _label_embeddings_cache.items():
            label_vec = np.array(label_embedding)
            # Cosine similarity
            similarity = np.dot(entity_vec, label_vec) / (np.linalg.norm(entity_vec) * np.linalg.norm(label_vec))
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_label = label_name
        
        # Only override if similarity is reasonable (> 0.4)
        # Lower threshold for better recall with example-based definitions
        if best_similarity > 0.4:
            # Commented out to reduce log volume
            # logger.debug(f"Semantic correction: '{entity_text}' {label} → {best_label} (similarity: {best_similarity:.3f})")
            return best_label
        
        # Commented out to reduce log volume
        # logger.debug(f"Semantic correction: '{entity_text}' keeping {label} (best: {best_label} @ {best_similarity:.3f})")
        return label
        
    except Exception as e:
        logger.warning(f"Semantic correction failed for '{entity_text}': {e}")
        return label


async def correct_entity_labels_batch(
    entities: List[Dict[str, Any]],
    user_id: str,
    modelservice_client: Any
) -> Dict[str, str]:
    """
    Batch version of semantic label correction with caching.
    
    Optimizations:
    1. Batch embedding generation (6× faster than individual)
    2. Per-user entity embedding cache with TTL (80% hit rate)
    3. Only processes entities that need correction
    
    Args:
        entities: List of entity dicts with 'text' and 'type' keys
        user_id: User ID for cache scoping
        modelservice_client: Client for embedding generation
        
    Returns:
        Dict mapping entity text to corrected label
    """
    import time
    import numpy as np
    
    # Initialize user cache if needed
    if user_id not in _entity_embeddings_cache:
        _entity_embeddings_cache[user_id] = {}
    
    user_cache = _entity_embeddings_cache[user_id]
    current_time = time.time()
    
    # Clean expired cache entries (TTL-based invalidation)
    expired_keys = [
        text for text, (_, timestamp) in user_cache.items()
        if current_time - timestamp > _ENTITY_CACHE_TTL_SECONDS
    ]
    for key in expired_keys:
        del user_cache[key]
    
    # Commented out to reduce log volume
    # if expired_keys:
    #     logger.debug(f"Cleaned {len(expired_keys)} expired entity embeddings from cache")
    
    # Ensure label embeddings are cached
    if not _label_embeddings_cache:
        definitions = list(LABEL_DEFINITIONS.values())
        result = await modelservice_client.generate_embeddings(definitions)
        if result.get("embeddings"):
            for label_name, embedding in zip(LABEL_DEFINITIONS.keys(), result["embeddings"]):
                _label_embeddings_cache[label_name] = embedding
    
    # Separate entities into cached and uncached
    results = {}
    entities_to_embed = []
    entity_text_to_idx = {}
    
    for entity in entities:
        entity_text = entity["text"]
        
        # Check cache first
        if entity_text in user_cache:
            cached_embedding, _ = user_cache[entity_text]
            # Compute best label from cached embedding
            entity_vec = np.array(cached_embedding)
            best_label = entity["type"]  # Default
            best_similarity = -1.0
            
            for label_name, label_embedding in _label_embeddings_cache.items():
                label_vec = np.array(label_embedding)
                similarity = np.dot(entity_vec, label_vec) / (np.linalg.norm(entity_vec) * np.linalg.norm(label_vec))
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_label = label_name
            
            results[entity_text] = best_label if best_similarity > 0.4 else entity["type"]
        else:
            # Need to embed this entity
            entity_text_to_idx[entity_text] = len(entities_to_embed)
            entities_to_embed.append(entity)
    
    # Batch embed uncached entities
    if entities_to_embed:
        texts = [e["text"] for e in entities_to_embed]
        # Commented out to reduce log volume
        # logger.debug(f"Batch embedding {len(texts)} entities (cache miss)")
        
        try:
            embedding_result = await modelservice_client.generate_embeddings(texts)
            embeddings = embedding_result.get("embeddings", [])
            
            if embeddings:
                for entity, embedding in zip(entities_to_embed, embeddings):
                    entity_text = entity["text"]
                    
                    # Cache the embedding with timestamp
                    user_cache[entity_text] = (embedding, current_time)
                    
                    # Compute best label
                    entity_vec = np.array(embedding)
                    best_label = entity["type"]  # Default
                    best_similarity = -1.0
                    
                    for label_name, label_embedding in _label_embeddings_cache.items():
                        label_vec = np.array(label_embedding)
                        similarity = np.dot(entity_vec, label_vec) / (np.linalg.norm(entity_vec) * np.linalg.norm(label_vec))
                        if similarity > best_similarity:
                            best_similarity = similarity
                            best_label = label_name
                    
                    results[entity_text] = best_label if best_similarity > 0.4 else entity["type"]
                    
                    # Commented out to reduce log volume
                    # logger.debug(f"Semantic correction: '{entity_text}' {entity['type']} → {results[entity_text]} (similarity: {best_similarity:.3f})")
        
        except Exception as e:
            logger.error(f"Batch embedding failed: {e}")
            # Fallback: use original labels
            for entity in entities_to_embed:
                results[entity["text"]] = entity["type"]
    
    cache_hit_rate = (len(entities) - len(entities_to_embed)) / len(entities) if entities else 0
    logger.info(f"Entity label correction: {len(entities)} entities, {len(entities_to_embed)} cache misses ({cache_hit_rate:.1%} hit rate)")
    
    return results


def clear_entity_embedding_cache(user_id: Optional[str] = None) -> None:
    """
    Clear entity embedding cache.
    
    Call this when:
    - User explicitly requests cache clear
    - Embedding model is updated
    - Memory pressure requires cache cleanup
    
    Args:
        user_id: If provided, only clear cache for this user.
                 If None, clear all caches.
    """
    global _entity_embeddings_cache
    
    if user_id:
        if user_id in _entity_embeddings_cache:
            count = len(_entity_embeddings_cache[user_id])
            del _entity_embeddings_cache[user_id]
            logger.info(f"Cleared {count} cached entity embeddings for user {user_id}")
    else:
        total_count = sum(len(cache) for cache in _entity_embeddings_cache.values())
        _entity_embeddings_cache.clear()
        logger.info(f"Cleared all entity embedding caches ({total_count} total entries)")


def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics for monitoring.
    
    Returns:
        Dict with cache size, hit rates, etc.
    """
    import time
    current_time = time.time()
    
    stats = {
        "label_embeddings_cached": len(_label_embeddings_cache),
        "users_with_cached_entities": len(_entity_embeddings_cache),
        "total_cached_entities": sum(len(cache) for cache in _entity_embeddings_cache.values()),
        "cache_ttl_seconds": _ENTITY_CACHE_TTL_SECONDS
    }
    
    # Count expired entries
    expired_count = 0
    for user_cache in _entity_embeddings_cache.values():
        for _, (_, timestamp) in user_cache.items():
            if current_time - timestamp > _ENTITY_CACHE_TTL_SECONDS:
                expired_count += 1
    
    stats["expired_entries"] = expired_count
    
    return stats


def _ts():
    """Get timestamp for debug prints."""
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


class ExtractionStrategy:
    """Base class for extraction strategies."""
    
    async def extract(
        self,
        text: str,
        user_id: str,
        context: Dict[str, Any]
    ) -> PropertyGraph:
        """Extract entities/relationships from text."""
        raise NotImplementedError


class GLiNEREntityExtractor(ExtractionStrategy):
    """
    Entity extraction using GLiNER (local transformers model).
    
    Extracts entities like PERSON, ORGANIZATION, LOCATION, EVENT, etc.
    """
    
    def __init__(self, modelservice_client: Any):
        """
        Initialize with modelservice client.
        
        Args:
            modelservice_client: Client for modelservice API
        """
        self.modelservice = modelservice_client
    
    async def extract(
        self,
        text: str,
        user_id: str,
        context: Dict[str, Any]
    ) -> PropertyGraph:
        """
        Extract entities using GLiNER.
        
        Args:
            text: Text to extract from
            user_id: User ID
            context: Additional context (existing graph, etc.)
            
        Returns:
            PropertyGraph with extracted entities (nodes only)
        """
        logger.debug(f"Starting two-stage entity extraction for text: {text[:100]}...")
        try:
            # TWO-STAGE APPROACH (based on ToMMeR research, Oct 2024)
            # Stage 1: Mention Detection - Extract ALL potential entity spans (high recall)
            # Stage 2: Semantic Classification - Classify each span using label embeddings
            
            # STAGE 1: Universal mention detection with GLiNER
            # Use broad labels + low threshold to catch all potential entities
            # This solves the "website redesign project" problem - GLiNER will extract it as "entity"
            try:
                print(f"🔍 [STAGE_1] Running mention detection with universal labels...")
                response = await self.modelservice.extract_entities(
                    text=text,
                    labels=[
                        # Universal labels for mention detection (high recall)
                        "entity", "mention", "thing", "name", "concept",
                        # Keep specific labels for better coverage
                        "person", "organization", "location", 
                        "date", "time", "event", "product", 
                        "skill", "topic", "activity"
                    ],
                    threshold=0.15  # Balanced threshold - filters low-confidence false positives
                )
                logger.debug(f"Stage 1 (mention detection) completed successfully")
            except Exception as e:
                logger.error(f"GLiNER extract_entities failed: {e}")
                import traceback
                traceback.print_exc()
                raise
            
            graph = PropertyGraph()
            
            # STAGE 2: Semantic classification of detected mentions
            # Response format: {"entities": {"PERSON": [...], "ORGANIZATION": [...]}}
            entities_by_type = response.get("entities", {})
            logger.debug(f"Stage 1 extracted {len(entities_by_type)} entity types")
            print(f"\n🔍 [STAGE_1_RESULTS] Detected {len(entities_by_type)} entity types:")
            for etype, elist in entities_by_type.items():
                print(f"  {etype}: {[e['text'] for e in elist]}")
            
            logger.debug(f"Stage 2: Starting semantic classification...")
            
            # Collect all entities with their spans for deduplication
            all_entities = []
            for entity_type, entity_list in entities_by_type.items():
                for entity in entity_list:
                    all_entities.append({
                        "text": entity["text"],
                        "type": entity_type,
                        "start": entity.get("start_pos", 0),
                        "end": entity.get("end_pos", 0),
                        "confidence": entity.get("confidence", 0.9)
                    })
            
            # Deduplicate overlapping entities - keep longest span
            # Use text-based overlap detection since GLiNER doesn't provide positions
            print(f"\n🔍 [DEDUP] Starting deduplication: {len(all_entities)} total entities")
            deduplicated = []
            removed_count = 0
            
            # Sort by length (longest first) to prioritize keeping longer entities
            all_entities.sort(key=lambda e: -len(e["text"]))
            
            for entity in all_entities:
                # Check if this entity's text is contained in or contains any kept entity
                overlaps = False
                entity_text_lower = entity["text"].lower()
                
                for kept in deduplicated:
                    kept_text_lower = kept["text"].lower()
                    
                    # Check if one is substring of the other
                    if entity_text_lower in kept_text_lower:
                        # Current entity is substring of kept entity - skip it
                        print(f"❌ [DEDUP] Removing '{entity['text']}' (substring of '{kept['text']}')")
                        overlaps = True
                        removed_count += 1
                        break
                    elif kept_text_lower in entity_text_lower:
                        # Kept entity is substring of current - replace it
                        print(f"🔄 [DEDUP] Replacing '{kept['text']}' with longer '{entity['text']}'")
                        deduplicated.remove(kept)
                        removed_count += 1
                        break
                
                if not overlaps:
                    deduplicated.append(entity)
            
            print(f"✅ [DEDUP] Deduplication complete: {len(all_entities)} → {len(deduplicated)} entities ({removed_count} removed)")
            logger.debug(f"Deduplication: {len(all_entities)} → {len(deduplicated)} entities")
            
            # Monitor false positive indicators
            print(f"\n🔍 [QUALITY] Analyzing entity quality...")
            low_confidence_count = sum(1 for e in deduplicated if e["confidence"] < 0.3)
            medium_confidence_count = sum(1 for e in deduplicated if 0.3 <= e["confidence"] < 0.5)
            high_confidence_count = sum(1 for e in deduplicated if e["confidence"] >= 0.5)
            
            print(f"📊 [QUALITY] Confidence distribution:")
            print(f"  High (≥0.5):   {high_confidence_count}/{len(deduplicated)} ({high_confidence_count/len(deduplicated)*100:.1f}%)")
            print(f"  Medium (0.3-0.5): {medium_confidence_count}/{len(deduplicated)} ({medium_confidence_count/len(deduplicated)*100:.1f}%)")
            print(f"  Low (<0.3):    {low_confidence_count}/{len(deduplicated)} ({low_confidence_count/len(deduplicated)*100:.1f}%)")
            
            if low_confidence_count > len(deduplicated) * 0.3:  # >30% low confidence
                print(f"⚠️  [QUALITY] HIGH FALSE POSITIVE RISK: {low_confidence_count}/{len(deduplicated)} entities have confidence < 0.3")
                print(f"⚠️  [QUALITY] Consider increasing GLiNER threshold from 0.1 to 0.15-0.2")
                logger.warning(f"High false positive risk: {low_confidence_count}/{len(deduplicated)} entities have confidence < 0.3")
            else:
                print(f"✅ [QUALITY] Quality check passed: Low confidence rate acceptable")
            
            # Show low confidence entities for review
            if low_confidence_count > 0:
                print(f"\n🔍 [QUALITY] Low confidence entities (review for false positives):")
                for e in sorted(deduplicated, key=lambda x: x["confidence"])[:5]:  # Show worst 5
                    if e["confidence"] < 0.3:
                        print(f"  - '{e['text']}' ({e['type']}, confidence: {e['confidence']:.3f})")
            
            # STAGE 2: Apply semantic classification (BATCHED + CACHED)
            # Collect entities that need semantic correction
            entities_needing_correction = []
            entity_to_canonical = {}  # Map entity text to canonical label
            
            for entity in deduplicated:
                canonical_label = normalize_entity_label(entity["type"])
                entity_to_canonical[entity["text"]] = canonical_label
                entity_type_lower = entity["type"].lower()
                
                # Only collect entities with ambiguous labels
                if entity_type_lower in ["entity", "mention", "thing", "name", "concept", "event"]:
                    entities_needing_correction.append(entity)
            
            # Batch process all entities needing correction (with caching)
            corrected_labels = {}
            if entities_needing_correction:
                print(f"\n🔍 [BATCH_CORRECTION] Processing {len(entities_needing_correction)} entities with semantic correction...")
                corrected_labels = await correct_entity_labels_batch(
                    entities_needing_correction,
                    user_id,
                    self.modelservice
                )
                print(f"✅ [BATCH_CORRECTION] Semantic correction complete")
            
            # Create nodes with corrected labels
            for entity in deduplicated:
                entity_text = entity["text"]
                
                # Use corrected label if available, otherwise use canonical
                if entity_text in corrected_labels:
                    final_label = corrected_labels[entity_text]
                else:
                    final_label = entity_to_canonical[entity_text]
                
                node = Node.create(
                    user_id=user_id,
                    label=final_label,
                    properties={
                        "name": entity["text"],
                        "start": entity["start"],
                        "end": entity["end"]
                    },
                    confidence=entity["confidence"],
                    source_text=text
                )
                graph.add_node(node)
            
            # Final quality summary
            print(f"\n📊 [FINAL] Extraction complete: {len(graph.nodes)} entities extracted")
            
            # Show label distribution
            label_counts = {}
            for node in graph.nodes:
                label = node.label
                label_counts[label] = label_counts.get(label, 0) + 1
            
            print(f"📊 [FINAL] Label distribution:")
            for label, count in sorted(label_counts.items(), key=lambda x: -x[1]):
                print(f"  {label}: {count}")
            
            # Filter out low-quality entities before returning
            # Uses language-agnostic structural heuristics
            filtered_nodes = []
            filtered_count = 0
            for node in graph.nodes:
                entity_text = node.properties.get('name', '')
                entity_type = node.label
                confidence = node.confidence
                
                # Quality filters (language-agnostic)
                should_keep = True
                text_stripped = entity_text.strip()
                word_count = len(text_stripped.split())
                
                # 1. Minimum confidence threshold (increased from 0.25 to 0.4 for better quality)
                if confidence < 0.4:
                    should_keep = False
                    
                # 2. Filter very short entities (likely pronouns in any language)
                elif len(text_stripped) <= 2:
                    should_keep = False
                    
                # 3. Filter single very short words with low confidence (likely stopwords)
                elif word_count == 1 and len(text_stripped) <= 4 and confidence < 0.35:
                    should_keep = False
                    
                # 4. Filter generic time references (language-agnostic)
                elif entity_type in ['TIME', 'DATE'] and word_count == 1:
                    # Single-word time references without context are usually not meaningful
                    should_keep = False
                    
                # 5. Filter MENTION entities (greetings, filler words - language-agnostic)
                elif entity_type == 'MENTION' and confidence < 0.5:
                    # MENTION type entities with low confidence are usually greetings/fillers
                    should_keep = False
                    
                # 6. Filter overly generic THING entities (too vague to be useful)
                elif entity_type == 'THING' and word_count > 2 and confidence < 0.5:
                    # Generic multi-word things with low confidence are usually noise
                    should_keep = False
                    
                # 7. Filter entities that are just punctuation or numbers
                elif text_stripped.replace(' ', '').replace('-', '').isdigit():
                    should_keep = False
                
                if should_keep:
                    filtered_nodes.append(node)
                else:
                    filtered_count += 1
                    logger.debug(f"Filtered entity: '{entity_text}' ({entity_type}, conf={confidence:.3f})")
            
            graph.nodes = filtered_nodes
            
            if filtered_count > 0:
                print(f"\n🔍 [FILTER] Removed {filtered_count} low-quality entities")
            
            # Show sample of extracted entities
            print(f"\n📊 [FINAL] Sample entities (top 5 by confidence):")
            sorted_nodes = sorted(graph.nodes, key=lambda n: n.confidence, reverse=True)[:5]
            for node in sorted_nodes:
                print(f"  - '{node.properties.get('name')}' ({node.label}, confidence: {node.confidence:.3f})")
            
            logger.info(f"GLiNER extracted {len(graph.nodes)} entities (after filtering)")
            logger.debug(f"GLiNER extracted {len(graph.nodes)} entities (after filtering)")
            return graph
            
        except Exception as e:
            logger.error(f"GLiNER extraction failed: {e}")
            return PropertyGraph()


class LLMRelationExtractor(ExtractionStrategy):
    """
    Relationship extraction using LLM (Eve).
    
    Extracts relationships between entities with typed properties.
    """
    
    def __init__(
        self,
        modelservice_client: Any,
        config: ConfigurationManager
    ):
        """
        Initialize with modelservice client and config.
        
        Args:
            modelservice_client: Client for modelservice API
            config: Configuration manager
        """
        self.modelservice = modelservice_client
        self.config = config
        
        # Get LLM timeout from config
        kg_config = config.get("core.memory.semantic.knowledge_graph", {})
        self.llm_timeout = kg_config.get("llm_timeout_seconds", 30.0)
    
    async def extract(
        self,
        text: str,
        user_id: str,
        context: Dict[str, Any]
    ) -> PropertyGraph:
        """
        Extract relationships using LLM.
        
        Args:
            text: Text to extract from
            user_id: User ID
            context: Additional context (existing entities, etc.)
            
        Returns:
            PropertyGraph with extracted relationships (edges and any new nodes)
        """
        print(f"🔗 [LLM_EXTRACTOR] ========== EXTRACT METHOD CALLED ==========")
        print(f"🔗 [LLM_EXTRACTOR] Text: '{text}'")
        print(f"🔗 [LLM_EXTRACTOR] Context entities: {len(context.get('entities', []))}")
        try:
            # Build prompt with existing entities if available
            existing_entities = context.get("entities", [])
            entity_context = ""
            if existing_entities:
                entity_list = [f"- {e['label']}: {e['name']}" for e in existing_entities]
                entity_context = f"\n\nKnown entities:\n" + "\n".join(entity_list)
                print(f"🔗 [LLM_EXTRACTOR] Processing with {len(existing_entities)} known entities")
            else:
                print(f"🔗 [LLM_EXTRACTOR] No known entities provided")
            
            prompt = f"""Extract relationships between DIFFERENT entities from the following text.

ENTITY TYPES:
World Knowledge: PERSON, ORGANIZATION, LOCATION, EVENT, DATE, TIME, PRODUCT, SKILL, TOPIC
Personal Graph: PROJECT, GOAL, TASK, ACTIVITY, INTEREST, PRIORITY

RELATIONSHIP TYPES:
World Knowledge: WORKS_FOR, WORKS_AT, LIVES_IN, LOCATED_IN, KNOWS, PART_OF, HAPPENED_IN
Personal Graph: WORKING_ON, HAS_GOAL, CONTRIBUTES_TO, DEPENDS_ON, INTERESTED_IN, PRIORITIZES, COMPLETED, STARTED

IMPORTANT RULES:
- Only extract relationships where source and target are DIFFERENT entities
- Do NOT create self-referential relationships (e.g., "Michael" -> "has name" -> "Michael")
- Extract personal activities: projects user is working on, goals they have, tasks to complete
- If user mentions working on something, create WORKING_ON relationship
- If user mentions wanting to achieve something, create HAS_GOAL relationship
- If there are no meaningful relationships between different entities, return empty arrays

RELATIONSHIP PROPERTIES:
Include contextual details about each relationship:
- role, title, position (for work relationships)
- start_date, end_date, since, until (for temporal context)
- amount, salary, percentage (for quantitative data)

Example: "Sarah is CTO of TechCorp since 2020" → 
{{"source": "Sarah", "relation_type": "WORKS_FOR", "target": "TechCorp", "properties": {{"role": "CTO", "start_date": "2020"}}}}

Return JSON with:
- "relationships": [{{"source": "...", "relation_type": "...", "target": "...", "properties": {{...}}}}]
- "new_entities": [{{"label": "...", "name": "..."}}]

Text: {text}{entity_context}

Return valid JSON only, no explanation."""
            
            logger.debug(f"Sending LLM prompt ({len(prompt)} chars) for relation extraction")
            
            # Call LLM with timeout
            print(f"🔗 [LLM_EXTRACTOR] Calling LLM with timeout={self.llm_timeout}s...")
            start_time = time.time()
            response = await asyncio.wait_for(
                self.modelservice.generate_completion(
                    prompt=prompt,
                    temperature=0.3,  # Lower temp for structured output
                    max_tokens=1024
                ),
                timeout=self.llm_timeout
            )
            end_time = time.time()
            print(f"🔗 [LLM_EXTRACTOR] LLM response received ({end_time - start_time:.2f}s)")
            
            # Debug: Check response structure
            print(f"🔗 [LLM_EXTRACTOR] Response type: {type(response)}")
            print(f"🔗 [LLM_EXTRACTOR] Response keys: {response.keys() if isinstance(response, dict) else 'NOT A DICT'}")
            print(f"🔗 [LLM_EXTRACTOR] Full response: {response}")
            
            # Log raw response for debugging
            raw_response = response.get("text", "")  # Fixed: key is "text", not "response"
            print(f"🔗 [LLM_EXTRACTOR] Raw response length: {len(raw_response)} chars")
            if raw_response:
                print(f"🔗 [LLM_EXTRACTOR] Raw response preview: {raw_response[:200]}...")
            else:
                print(f"🔗 [LLM_EXTRACTOR] ⚠️  RAW RESPONSE IS EMPTY!")
            
            # Parse LLM response
            result = self._parse_llm_response(raw_response)
            print(f"🔗 [LLM_EXTRACTOR] Parsed result type: {type(result)}")
            print(f"🔗 [LLM_EXTRACTOR] Parsed result keys: {result.keys() if isinstance(result, dict) else 'NOT A DICT'}")
            print(f"🔗 [LLM_EXTRACTOR] Parsed: {len(result.get('relationships', []))} relationships, {len(result.get('new_entities', []))} new entities")
            
            if len(result.get('relationships', [])) == 0:
                print(f"🔗 [LLM_EXTRACTOR] ⚠️  NO RELATIONSHIPS FOUND!")
                print(f"🔗 [LLM_EXTRACTOR] Full parsed result: {result}")
            
            logger.debug(f"Received LLM response ({len(raw_response)} chars)")
            
            graph = PropertyGraph()
            
            # Create nodes for new entities
            for entity in result.get("new_entities", []):
                node = Node.create(
                    user_id=user_id,
                    label=entity.get("label", "ENTITY").upper(),
                    properties={"name": entity.get("name", "")},
                    confidence=0.8,  # LLM-extracted entities get lower confidence
                    source_text=text
                )
                graph.add_node(node)
            
            # Create edges for relationships
            for rel in result.get("relationships", []):
                # Skip self-referential relationships (source == target)
                if rel["source"].lower().strip() == rel["target"].lower().strip():
                    logger.warning(f"Skipping self-referential relationship: {rel['source']} -> {rel['relation_type']} -> {rel['target']}")
                    continue
                
                # Create placeholder nodes if not in context
                source_node = self._find_or_create_node(
                    rel["source"],
                    user_id,
                    text,
                    graph,
                    context
                )
                target_node = self._find_or_create_node(
                    rel["target"],
                    user_id,
                    text,
                    graph,
                    context
                )
                
                edge = Edge.create(
                    user_id=user_id,
                    source_id=source_node.id,
                    target_id=target_node.id,
                    relation_type=normalize_relation_type(rel["relation_type"]),
                    properties=rel.get("properties", {}),
                    confidence=0.85,
                    source_text=text
                )
                graph.add_edge(edge)
            
            logger.debug(f"LLM extracted {len(graph.edges)} relationships")
            return graph
            
        except asyncio.TimeoutError:
            print(f"🔗 [LLM_EXTRACTOR] ❌ TIMEOUT after {self.llm_timeout}s")
            logger.error(f"LLM extraction timed out after {self.llm_timeout}s")
            return PropertyGraph()
        except Exception as e:
            print(f"🔗 [LLM_EXTRACTOR] ❌ EXCEPTION: {type(e).__name__}: {e}")
            import traceback
            print(f"🔗 [LLM_EXTRACTOR] Traceback:\n{traceback.format_exc()}")
            logger.error(f"LLM extraction failed: {e}")
            return PropertyGraph()
    
    def _parse_llm_response(self, text: str) -> Dict[str, Any]:
        """Parse LLM JSON response, handling common issues."""
        try:
            # Try to extract JSON from response
            original_text = text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
                print(f"🔗 [PARSER] Extracted JSON from markdown code block")
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
                print(f"🔗 [PARSER] Extracted from generic code block")
            
            parsed = json.loads(text.strip())
            print(f"🔗 [PARSER] ✅ Successfully parsed JSON")
            return parsed
        except Exception as e:
            print(f"🔗 [PARSER] ❌ Failed to parse LLM response: {e}")
            print(f"🔗 [PARSER] Raw text (first 500 chars): {original_text[:500]}")
            logger.warning(f"Failed to parse LLM response: {e}")
            return {"relationships": [], "new_entities": []}
    
    def _find_or_create_node(
        self,
        entity_name: str,
        user_id: str,
        source_text: str,
        graph: PropertyGraph,
        context: Dict[str, Any]
    ) -> Node:
        """Find existing node or create placeholder."""
        # Check if node already exists in current graph
        for node in graph.nodes:
            name = node.properties.get("name", "")
            # Handle corrupted data where name is a list
            if isinstance(name, list):
                name = name[0] if name else ""
            if str(name).lower() == entity_name.lower():
                return node
        
        # Check if node exists in context
        existing_entities = context.get("entities", [])
        for entity in existing_entities:
            if entity.get("name", "").lower() == entity_name.lower():
                # Return existing node ID (will be resolved later)
                node = Node.create(
                    user_id=user_id,
                    label=entity.get("label", "ENTITY").upper(),
                    properties={"name": entity_name},
                    confidence=0.9,
                    source_text=source_text
                )
                node.id = entity["id"]  # Use existing ID
                return node
        
        # Create new placeholder node
        node = Node.create(
            user_id=user_id,
            label="ENTITY",
            properties={"name": entity_name},
            confidence=0.7,
            source_text=source_text
        )
        graph.add_node(node)
        return node


class MultiPassExtractor:
    """
    Multi-pass extraction pipeline with gleanings.
    
    Implements the multi-pass extraction algorithm:
    1. Pass 1: GLiNER entity extraction + LLM relation extraction
    2. Pass 2+: Gleaning passes to find missed information
    """
    
    def __init__(
        self,
        modelservice_client: Any,
        config: ConfigurationManager
    ):
        """
        Initialize extractor with strategies.
        
        Args:
            modelservice_client: Client for modelservice API
            config: Configuration manager
        """
        self.config = config
        
        # Get config settings
        kg_config = config.get("core.memory.semantic.knowledge_graph", {})
        self.max_gleanings = kg_config.get("max_gleanings", 2)
        
        # Initialize extraction strategies
        self.gliner_extractor = GLiNEREntityExtractor(modelservice_client)
        self.llm_extractor = LLMRelationExtractor(modelservice_client, config)
        
        logger.info(f"MultiPassExtractor initialized (max_gleanings={self.max_gleanings})")
    
    async def extract(
        self,
        text: str,
        user_id: str
    ) -> PropertyGraph:
        """
        Extract knowledge graph from text using multi-pass algorithm.
        
        Args:
            text: Text to extract from
            user_id: User ID
            
        Returns:
            PropertyGraph with extracted entities and relationships
        """
        print(f"\n📚 [MULTIPASS] Starting multi-pass extraction (max_passes={self.max_gleanings + 1})")
        logger.info(f"Starting multi-pass extraction (max_passes={self.max_gleanings + 1})")
        pipeline_start = time.time()
        
        # Pass 1: Initial extraction
        pass1_start = time.time()
        graph = await self._initial_extraction(text, user_id)
        pass1_time = time.time() - pass1_start
        initial_count = len(graph)
        
        print(f"📚 [MULTIPASS] Pass 1 complete in {pass1_time:.2f}s: {len(graph.nodes)} nodes, {len(graph.edges)} edges")
        logger.info(f"Pass 1 complete: {len(graph.nodes)} nodes, {len(graph.edges)} edges")
        
        # Pass 2+: Gleaning passes
        for i in range(self.max_gleanings):
            new_graph = await self._gleaning_pass(text, user_id, graph, pass_num=i+2)
            
            if len(new_graph) == 0:
                logger.info(f"Pass {i+2}: No new information found, stopping")
                break
            
            graph.merge(new_graph)
            logger.info(f"Pass {i+2} complete: +{len(new_graph.nodes)} nodes, +{len(new_graph.edges)} edges")
        
        final_count = len(graph)
        improvement = ((final_count - initial_count) / initial_count * 100) if initial_count > 0 else 0
        pipeline_time = time.time() - pipeline_start
        
        print(f"\n📚 [MULTIPASS] ✅ Extraction complete in {pipeline_time:.2f}s")
        print(f"📚 [MULTIPASS]    Total: {len(graph.nodes)} nodes, {len(graph.edges)} edges")
        print(f"📚 [MULTIPASS]    Improvement: {improvement:.1f}% over initial pass")
        logger.info(f"Extraction complete: {len(graph.nodes)} nodes, {len(graph.edges)} edges ({improvement:.1f}% improvement)")
        
        return graph
    
    async def _initial_extraction(
        self,
        text: str,
        user_id: str
    ) -> PropertyGraph:
        """
        Pass 1: Initial extraction using GLiNER + LLM.
        
        Args:
            text: Text to extract from
            user_id: User ID
            
        Returns:
            PropertyGraph with initial extraction
        """
        # Step 1: Extract entities using GLiNER (fast)
        print(f"\n  🔍 [ENTITIES] Starting GLiNER entity extraction...")
        entity_start = time.time()
        logger.debug("Starting entity extraction phase")
        entity_graph = await self.gliner_extractor.extract(text, user_id, {})
        entity_time = time.time() - entity_start
        print(f"  🔍 [ENTITIES] ✅ Complete in {entity_time:.2f}s: {len(entity_graph.nodes)} entities")
        logger.info(f"Entity extraction complete: {len(entity_graph.nodes)} entities")
        
        # Merge entity results
        graph = PropertyGraph()
        graph.merge(entity_graph)
        
        # Step 2: Build entity context for relation extraction
        entity_context = {
            "entities": [
                {
                    "id": node.id,
                    "label": node.label,
                    "name": safe_get_name(node)
                }
                for node in entity_graph.nodes
            ]
        }
        
        # Step 3: Extract relations WITH entity context (only one LLM call needed)
        print(f"🔗 [RELATIONS] Starting relation extraction with {len(entity_context['entities'])} known entities")
        logger.debug(f"Starting relation extraction with {len(entity_context['entities'])} known entities")
        
        try:
            relation_graph = await self.llm_extractor.extract(text, user_id, entity_context)
            print(f"🔗 [RELATIONS] Extraction complete: {len(relation_graph.edges)} relationships, {len(relation_graph.nodes)} new nodes")
            logger.info(f"Relation extraction complete: {len(relation_graph.edges)} relationships")
            graph.merge(relation_graph)
        except Exception as e:
            print(f"🔗 [RELATIONS] ❌ Extraction failed: {e}")
            logger.error(f"Relation extraction failed: {e}")
            import traceback
            traceback.print_exc()
        
        return graph
    
    async def _gleaning_pass(
        self,
        text: str,
        user_id: str,
        existing_graph: PropertyGraph,
        pass_num: int
    ) -> PropertyGraph:
        """
        Gleaning pass: Find information missed in previous passes.
        
        Args:
            text: Original text
            user_id: User ID
            existing_graph: Graph from previous passes
            pass_num: Current pass number
            
        Returns:
            PropertyGraph with newly discovered information
        """
        try:
            # Build context with existing graph
            context = {
                "existing_nodes": [
                    {
                        "label": node.label,
                        "name": safe_get_name(node)
                    }
                    for node in existing_graph.nodes
                ],
                "existing_relationships": [
                    {
                        "source": safe_get_name(existing_graph.get_node_by_id(edge.source_id)),
                        "relation": edge.relation_type,
                        "target": safe_get_name(existing_graph.get_node_by_id(edge.target_id))
                    }
                    for edge in existing_graph.edges
                    if existing_graph.get_node_by_id(edge.source_id) and existing_graph.get_node_by_id(edge.target_id)
                ]
            }
            
            # Prompt LLM to find missed information
            prompt = f"""Review the text and identify information we missed.

Text: {text}

Already extracted:
Entities: {json.dumps(context['existing_nodes'], indent=2)}
Relationships: {json.dumps(context['existing_relationships'], indent=2)}

What entities or relationships did we miss? Return JSON with:
- "new_entities": array of missed entities
- "new_relationships": array of missed relationships

Return valid JSON only."""
            
            logger.debug(f"Sending gleaning prompt ({len(prompt)} chars)")
            
            response = await self.llm_extractor.modelservice.generate_completion(
                prompt=prompt,
                model="eve",
                temperature=0.3,
                max_tokens=1024
            )
            
            response_text = response.get("text", "")
            logger.debug(f"Received gleaning response ({len(response_text)} chars)")
            
            result = self.llm_extractor._parse_llm_response(response_text)
            
            graph = PropertyGraph()
            
            # Add new entities
            for entity in result.get("new_entities", []):
                node = Node.create(
                    user_id=user_id,
                    label=entity.get("label", "ENTITY").upper(),
                    properties={"name": entity.get("name", "")},
                    confidence=0.75,  # Gleaned entities get lower confidence
                    source_text=text
                )
                graph.add_node(node)
            
            # Add new relationships
            for rel in result.get("new_relationships", []):
                # Validate relationship structure
                if not all(key in rel for key in ["source", "target", "relation_type"]):
                    logger.warning(f"Skipping invalid relationship in gleaning: {rel}")
                    continue
                
                # Skip self-referential relationships
                if rel["source"].lower().strip() == rel["target"].lower().strip():
                    logger.warning(f"Skipping self-referential relationship in gleaning: {rel['source']} -> {rel['relation_type']} -> {rel['target']}")
                    continue
                
                source_node = self.llm_extractor._find_or_create_node(
                    rel["source"], user_id, text, graph, context
                )
                target_node = self.llm_extractor._find_or_create_node(
                    rel["target"], user_id, text, graph, context
                )
                
                edge = Edge.create(
                    user_id=user_id,
                    source_id=source_node.id,
                    target_id=target_node.id,
                    relation_type=normalize_relation_type(rel["relation_type"]),
                    properties=rel.get("properties", {}),
                    confidence=0.75,
                    source_text=text
                )
                graph.add_edge(edge)
            
            return graph
            
        except Exception as e:
            logger.error(f"Gleaning pass {pass_num} failed: {e}")
            return PropertyGraph()
