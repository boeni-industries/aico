"""
Multi-Pass Extraction

Implements multi-pass extraction pipeline with gleanings for high completeness.
Uses GLiNER for entity extraction and LLM for relation extraction.
"""

from typing import List, Dict, Any, Optional
import asyncio
import json
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

# Cache for label embeddings (computed once)
_label_embeddings_cache = {}


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
            logger.debug(f"Semantic correction: '{entity_text}' {label} → {best_label} (similarity: {best_similarity:.3f})")
            return best_label
        
        logger.debug(f"Semantic correction: '{entity_text}' keeping {label} (best: {best_label} @ {best_similarity:.3f})")
        return label
        
    except Exception as e:
        logger.warning(f"Semantic correction failed for '{entity_text}': {e}")
        return label


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
                    threshold=0.1  # Low threshold for high recall (default is 0.5)
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
            
            # Process deduplicated entities
            for entity in deduplicated:
                # Normalize label to canonical form
                canonical_label = normalize_entity_label(entity["type"])
                
                # STAGE 2: Apply semantic classification
                # For universal labels (entity, mention, thing, etc.), always classify
                # For specific labels (person, organization), only reclassify if ambiguous
                if entity["type"].lower() in ["entity", "mention", "thing", "name", "concept", "event"]:
                    # Universal label - must classify semantically
                    corrected_label = await correct_entity_label_semantic(
                        "ENTITY",  # Treat as unknown
                        entity["text"],
                        self.modelservice
                    )
                else:
                    # Specific label - keep it but allow correction for ambiguous cases
                    corrected_label = await correct_entity_label_semantic(
                        canonical_label, 
                        entity["text"],
                        self.modelservice
                    )
                
                node = Node.create(
                    user_id=user_id,
                    label=corrected_label,
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
            
            # Show sample of extracted entities
            print(f"\n📊 [FINAL] Sample entities (top 5 by confidence):")
            sorted_nodes = sorted(graph.nodes, key=lambda n: n.confidence, reverse=True)[:5]
            for node in sorted_nodes:
                print(f"  - '{node.properties.get('name')}' ({node.label}, confidence: {node.confidence:.3f})")
            
            logger.info(f"GLiNER extracted {len(graph.nodes)} entities")
            logger.debug(f"GLiNER extracted {len(graph.nodes)} entities")
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
        try:
            # Build prompt with existing entities if available
            existing_entities = context.get("entities", [])
            entity_context = ""
            if existing_entities:
                entity_list = [f"- {e['label']}: {e['name']}" for e in existing_entities]
                entity_context = f"\n\nKnown entities:\n" + "\n".join(entity_list)
            
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

Return a JSON object with:
- "relationships": array of {{source, relation_type, target, properties}} where source ≠ target
- "new_entities": array of any entities not in the known list (include label and name)

Text: {text}{entity_context}

Return valid JSON only, no explanation."""
            
            logger.debug(f"Sending LLM prompt ({len(prompt)} chars) for relation extraction")
            
            # Call LLM (Eve - reasoning model)
            response = await asyncio.wait_for(
                self.modelservice.generate_completion(
                    prompt=prompt,
                    model="eve",  # Uses default conversation model (qwen3-abliterated)
                    temperature=0.3,  # Lower temp for structured output
                    max_tokens=1024
                ),
                timeout=self.llm_timeout
            )
            
            # Parse LLM response
            response_text = response.get("text", "")
            logger.debug(f"Received LLM response ({len(response_text)} chars)")
            result = self._parse_llm_response(response_text)
            
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
            logger.error(f"LLM extraction timed out after {self.llm_timeout}s")
            return PropertyGraph()
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return PropertyGraph()
    
    def _parse_llm_response(self, text: str) -> Dict[str, Any]:
        """Parse LLM JSON response, handling common issues."""
        try:
            # Try to extract JSON from response
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            return json.loads(text.strip())
        except Exception as e:
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
            if node.properties.get("name", "").lower() == entity_name.lower():
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
        logger.info(f"Starting multi-pass extraction (max_passes={self.max_gleanings + 1})")
        
        # Pass 1: Initial extraction
        graph = await self._initial_extraction(text, user_id)
        initial_count = len(graph)
        
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
        logger.debug("Starting entity extraction phase")
        entity_graph = await self.gliner_extractor.extract(text, user_id, {})
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
                    "name": node.properties.get("name", "")
                }
                for node in entity_graph.nodes
            ]
        }
        
        # Step 3: Extract relations WITH entity context (only one LLM call needed)
        logger.debug(f"Starting relation extraction with {len(entity_context['entities'])} known entities")
        relation_graph = await self.llm_extractor.extract(text, user_id, entity_context)
        logger.info(f"Relation extraction complete: {len(relation_graph.edges)} relationships")
        graph.merge(relation_graph)
        
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
                        "name": node.properties.get("name", "")
                    }
                    for node in existing_graph.nodes
                ],
                "existing_relationships": [
                    {
                        "source": existing_graph.get_node_by_id(edge.source_id).properties.get("name", ""),
                        "relation": edge.relation_type,
                        "target": existing_graph.get_node_by_id(edge.target_id).properties.get("name", "")
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
