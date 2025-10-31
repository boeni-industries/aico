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

logger = get_logger("shared", "ai.knowledge_graph.extractor")

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
        print(f"[{_ts()}] 🔍 [GLINER] Starting entity extraction for text: {text[:50]}...")
        try:
            # Call modelservice for entity extraction
            # GLiNER is configured in modelservice.transformers.models.entity_extraction
            print(f"[{_ts()}] 🔍 [GLINER] Calling modelservice.extract_entities...")
            try:
                response = await self.modelservice.extract_entities(
                    text=text,
                    labels=[
                        "person", "organization", "location", "event",
                        "date", "time", "product", "skill", "topic",
                        "project", "goal", "task", "interest"
                    ]
                )
                print(f"[{_ts()}] 🔍 [GLINER] extract_entities returned successfully")
            except Exception as e:
                print(f"[{_ts()}] 🔍 [GLINER] ❌ EXCEPTION in extract_entities: {e}")
                import traceback
                traceback.print_exc()
                raise
            
            graph = PropertyGraph()
            
            # Convert GLiNER entities to nodes
            # Response format: {"entities": {"PERSON": [...], "ORGANIZATION": [...]}}
            print(f"[{_ts()}] 🔍 [GLINER] Raw response: {response}")
            entities_by_type = response.get("entities", {})
            print(f"[{_ts()}] 🔍 [GLINER] Entities by type: {entities_by_type}")
            
            for entity_type, entity_list in entities_by_type.items():
                print(f"[{_ts()}] 🔍 [GLINER] Processing {len(entity_list)} entities of type {entity_type}")
                for entity in entity_list:
                    print(f"[{_ts()}] 🔍 [GLINER] Creating node for entity: {entity}")
                    node = Node.create(
                        user_id=user_id,
                        label=entity["label"].upper(),
                        properties={
                            "name": entity["text"],
                            "start": entity.get("start_pos", 0),
                            "end": entity.get("end_pos", 0)
                        },
                        confidence=entity.get("confidence", 0.9),
                        source_text=text
                    )
                    print(f"[{_ts()}] 🔍 [GLINER] Created node: {node.label} - {node.properties}")
                    graph.add_node(node)
            
            print(f"[{_ts()}] 🔍 [GLINER] Total nodes in graph: {len(graph.nodes)}")
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
            
            prompt = f"""Extract relationships from the following text. Return a JSON object with:
- "relationships": array of {{source, relation_type, target, properties}}
- "new_entities": array of any entities not in the known list

Text: {text}{entity_context}

Return valid JSON only, no explanation."""
            
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
            result = self._parse_llm_response(response.get("text", ""))
            
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
                    relation_type=rel["relation_type"].upper(),
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
        # Run GLiNER and LLM extraction in parallel
        print(f"[{_ts()}] 🔍 [EXTRACTOR] Starting parallel GLiNER + LLM extraction...")
        entity_graph, relation_graph = await asyncio.gather(
            self.gliner_extractor.extract(text, user_id, {}),
            self.llm_extractor.extract(text, user_id, {})
        )
        print(f"[{_ts()}] 🔍 [EXTRACTOR] Parallel extraction complete")
        
        # Merge results
        graph = PropertyGraph()
        graph.merge(entity_graph)
        
        # Build entity context for relation extraction
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
        
        # Extract relations with entity context
        relation_graph = await self.llm_extractor.extract(text, user_id, entity_context)
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
            
            response = await self.llm_extractor.modelservice.generate_completion(
                prompt=prompt,
                model="eve",
                temperature=0.3,
                max_tokens=1024
            )
            
            result = self.llm_extractor._parse_llm_response(response.get("text", ""))
            
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
                    relation_type=rel["relation_type"].upper(),
                    properties=rel.get("properties", {}),
                    confidence=0.75,
                    source_text=text
                )
                graph.add_edge(edge)
            
            return graph
            
        except Exception as e:
            logger.error(f"Gleaning pass {pass_num} failed: {e}")
            return PropertyGraph()
