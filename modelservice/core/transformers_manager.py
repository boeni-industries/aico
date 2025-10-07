"""
TransformersManager - Hugging Face Transformers model management and lifecycle control.

This module handles complete Transformers model lifecycle management including:
- Multi-model support for various NLP tasks (sentiment, classification, etc.)
- Automatic model download and caching at startup
- Memory-efficient model loading and unloading
- Integration with AICO's unified logging system
- Support for multilingual models
"""

import asyncio
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum

from aico.core.logging import get_logger
from aico.core.config import ConfigurationManager
from aico.core.paths import AICOPaths


class ModelTask(Enum):
    """Supported Transformers model tasks."""
    SENTIMENT_ANALYSIS = "sentiment-analysis"
    TEXT_CLASSIFICATION = "text-classification"
    TOKEN_CLASSIFICATION = "token-classification"
    QUESTION_ANSWERING = "question-answering"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    TEXT_GENERATION = "text-generation"
    ENTITY_EXTRACTION = "entity-extraction"  # For GLiNER
    RELATION_EXTRACTION = "relation-extraction"


@dataclass
class TransformerModelConfig:
    """Configuration for a Transformers model."""
    name: str
    model_id: str
    task: ModelTask
    priority: int
    required: bool
    description: str
    multilingual: bool = False
    memory_mb: int = 500  # Estimated memory usage
    config_overrides: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.config_overrides is None:
            self.config_overrides = {}


class TransformersManager:
    """Manages Hugging Face Transformers model installation, updates, and lifecycle."""
    
    # Default model configurations
    DEFAULT_MODELS = {
        "sentiment_multilingual": TransformerModelConfig(
            name="sentiment_multilingual",
            model_id="nlptown/bert-base-multilingual-uncased-sentiment",
            task=ModelTask.SENTIMENT_ANALYSIS,
            priority=1,
            required=True,
            description="Multilingual BERT sentiment analysis",
            multilingual=True,
            memory_mb=500,
            config_overrides={"top_k": 1}
        ),
        "sentiment_english": TransformerModelConfig(
            name="sentiment_english",
            model_id="cardiffnlp/twitter-roberta-base-sentiment-latest",
            task=ModelTask.SENTIMENT_ANALYSIS,
            priority=2,
            required=False,
            description="English Twitter sentiment analysis",
            multilingual=False,
            memory_mb=400
        ),
        "emotion_analysis": TransformerModelConfig(
            name="emotion_analysis",
            model_id="j-hartmann/emotion-english-distilroberta-base",
            task=ModelTask.TEXT_CLASSIFICATION,
            priority=3,
            required=False,
            description="English emotion classification",
            multilingual=False,
            memory_mb=300
        ),
        "text_classification": TransformerModelConfig(
            name="text_classification",
            model_id="microsoft/DialoGPT-medium",
            task=ModelTask.TEXT_CLASSIFICATION,
            priority=4,
            required=False,
            description="General text classification",
            multilingual=False,
            memory_mb=600
        ),
        "entity_extraction": TransformerModelConfig(
            name="entity_extraction",
            model_id="urchade/gliner_medium-v2.1",
            task=ModelTask.ENTITY_EXTRACTION,
            priority=1,
            required=True,
            description="GLiNER generalist entity extraction",
            multilingual=True,
            memory_mb=400
        ),
        "intent_classification": TransformerModelConfig(
            name="intent_classification",
            model_id="xlm-roberta-base",
            task=ModelTask.TEXT_CLASSIFICATION,
            required=True,
            description="Multilingual intent classification using XLM-RoBERTa",
            multilingual=True,
            memory_mb=600
        ),
        "embeddings": TransformerModelConfig(
            name="embeddings",
            model_id="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            task=ModelTask.FEATURE_EXTRACTION,
            priority=1,
            required=True,
            description="Multilingual sentence embeddings for semantic memory",
            multilingual=True,
            memory_mb=500
        )
    }
    
    def __init__(self, config_manager: ConfigurationManager):
        """Initialize TransformersManager with configuration."""
        self.config_manager = config_manager
        self.logger = None  # Lazy initialization
        
        # Get transformers configuration
        self.transformers_config = self.config_manager.get("core.modelservice.transformers", {})
        
        # Loaded models cache
        self.loaded_models: Dict[str, Any] = {}
        self.model_configs: Dict[str, TransformerModelConfig] = {}
        
        # Memory management
        self.max_memory_mb = self.transformers_config.get("max_memory_mb", 2048)
        self.auto_unload = self.transformers_config.get("auto_unload", True)
        self.max_concurrent_models = self.transformers_config.get("max_concurrent_models", 3)
        
        # Initialize model configurations
        self._initialize_model_configs()
    
    def _ensure_logger(self):
        """Ensure logger is initialized (lazy initialization)."""
        if self.logger is None:
            try:
                self.logger = get_logger("modelservice", "core.transformers_manager")
            except RuntimeError:
                # Logging not initialized yet, use basic Python logger as fallback
                import logging
                self.logger = logging.getLogger("transformers_manager")
                self.logger.setLevel(logging.INFO)
    
    def _initialize_model_configs(self):
        """Initialize model configurations from defaults and config."""
        self._ensure_logger()
        
        # Start with default models
        self.model_configs = self.DEFAULT_MODELS.copy()
        
        # Override with configuration
        config_models = self.transformers_config.get("models", {})
        for model_name, config in config_models.items():
            if model_name in self.model_configs:
                # Update existing model config
                existing = self.model_configs[model_name]
                for key, value in config.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
            else:
                # Add new model config
                self.model_configs[model_name] = TransformerModelConfig(**config)
        
        self.logger.info(f"Initialized {len(self.model_configs)} transformer model configurations")
    
    async def initialize_models(self) -> bool:
        """Initialize and download required models at startup."""
        self._ensure_logger()
        
        # Beautiful startup messages like Ollama
        print("🤖 Initializing Transformers Models")
        self.logger.info("Initializing Transformers models...")
        
        try:
            # Check if transformers is available
            try:
                import transformers
                print(f"✅ Transformers library v{transformers.__version__} ready")
                self.logger.info(f"Transformers library version: {transformers.__version__}")
            except ImportError:
                print("❌ Transformers library not available")
                self.logger.error("Transformers library not available. Install with: uv sync --extra modelservice")
                return False
            
            # Download required models
            required_models = [
                config for config in self.model_configs.values() 
                if config.required
            ]
            
            if required_models:
                print(f"📥 Downloading {len(required_models)} required model(s)...")
                self.logger.info(f"Downloading {len(required_models)} required models...")
                
                for model_config in sorted(required_models, key=lambda x: x.priority):
                    print(f"   → {model_config.description} ({model_config.model_id})")
                    success = await self._ensure_model_available(model_config)
                    if success:
                        print(f"   ✅ {model_config.name} ready")
                    else:
                        print(f"   ❌ {model_config.name} failed")
                        if model_config.required:
                            self.logger.error(f"Failed to initialize required model: {model_config.name}")
                            return False
            
            print("✅ All Transformers models initialized successfully")
            self.logger.info("✅ All required Transformers models initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ Transformers initialization failed: {e}")
            self.logger.error(f"Failed to initialize Transformers models: {e}")
            return False
    
    async def ensure_models_loaded(self) -> bool:
        """Ensure all required models are loaded."""
        return await self.initialize_models()
    
    async def _ensure_model_available(self, model_config: TransformerModelConfig) -> bool:
        """Ensure a model is downloaded and available."""
        try:
            # Special handling for GLiNER models
            if model_config.name == "entity_extraction" and "gliner" in model_config.model_id.lower():
                self.logger.info(f"Checking GLiNER model availability: {model_config.model_id}")
                try:
                    from gliner import GLiNER
                    # Try to load GLiNER model (this will download if needed)
                    model = GLiNER.from_pretrained(model_config.model_id)
                    self.logger.info(f"✅ GLiNER model {model_config.name} is available")
                    return True
                except Exception as e:
                    self.logger.error(f"Failed to load GLiNER model {model_config.name}: {e}")
                    return False
            
            # Standard transformers models
            from transformers import pipeline, AutoTokenizer, AutoModel
            
            self.logger.info(f"Checking model availability: {model_config.model_id}")
            
            # Try to load tokenizer first (lightweight check)
            try:
                tokenizer = AutoTokenizer.from_pretrained(model_config.model_id)
                self.logger.info(f"✅ Model {model_config.name} is available")
                return True
            except Exception as e:
                # Model needs to be downloaded
                self.logger.info(f"Downloading model {model_config.name}: {model_config.model_id}")
                
                # Download model and tokenizer (this will show progress bars)
                tokenizer = AutoTokenizer.from_pretrained(model_config.model_id)
                model = AutoModel.from_pretrained(model_config.model_id)
                
                self.logger.info(f"✅ Downloaded model {model_config.name} successfully")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to ensure model {model_config.name} availability: {e}")
            return False
    
    async def get_pipeline(self, model_name: str, **kwargs) -> Optional[Any]:
        """Get or create a pipeline for the specified model."""
        self._ensure_logger()
        
        self.logger.info(f"🔍 [TRANSFORMERS_DEBUG] get_pipeline called for: {model_name}")
        self.logger.info(f"🔍 [TRANSFORMERS_DEBUG] Available configs: {list(self.model_configs.keys())}")
        self.logger.info(f"🔍 [TRANSFORMERS_DEBUG] Loaded models: {list(self.loaded_models.keys())}")
        
        if model_name not in self.model_configs:
            self.logger.error(f"🔍 [TRANSFORMERS_DEBUG] ❌ Unknown model: {model_name}")
            self.logger.error(f"🔍 [TRANSFORMERS_DEBUG] ❌ Available: {list(self.model_configs.keys())}")
            return None
        
        # Check if already loaded
        if model_name in self.loaded_models:
            self.logger.debug(f"Using cached pipeline for {model_name}")
            return self.loaded_models[model_name]
        
        # Check memory constraints
        if len(self.loaded_models) >= self.max_concurrent_models:
            if self.auto_unload:
                await self._unload_least_used_model()
            else:
                self.logger.warning(f"Max concurrent models ({self.max_concurrent_models}) reached")
                return None
        
        try:
            from transformers import pipeline
            
            model_config = self.model_configs[model_name]
            
            self.logger.info(f"🔍 [TRANSFORMERS_DEBUG] Loading pipeline for {model_name}: {model_config.model_id}")
            self.logger.info(f"🔍 [TRANSFORMERS_DEBUG] Task: {model_config.task.value}")
            self.logger.info(f"🔍 [TRANSFORMERS_DEBUG] Config overrides: {model_config.config_overrides}")
            
            # Merge config overrides with kwargs
            pipeline_kwargs = model_config.config_overrides.copy()
            pipeline_kwargs.update(kwargs)
            
            self.logger.info(f"🔍 [TRANSFORMERS_DEBUG] Final pipeline kwargs: {pipeline_kwargs}")
            
            # Create pipeline
            self.logger.info(f"🔍 [TRANSFORMERS_DEBUG] Creating pipeline...")
            pipe = pipeline(
                model_config.task.value,
                model=model_config.model_id,
                tokenizer=model_config.model_id,
                **pipeline_kwargs
            )
            self.logger.info(f"🔍 [TRANSFORMERS_DEBUG] ✅ Pipeline created successfully")
            
            self.loaded_models[model_name] = pipe
            self.logger.info(f"✅ Pipeline loaded for {model_name}")
            
            return pipe
            
        except Exception as e:
            self.logger.error(f"🔍 [TRANSFORMERS_DEBUG] ❌ Failed to load pipeline for {model_name}: {e}")
            import traceback
            self.logger.error(f"🔍 [TRANSFORMERS_DEBUG] ❌ Full traceback: {traceback.format_exc()}")
            return None
    
    async def _unload_least_used_model(self):
        """Unload the least recently used model to free memory."""
        if not self.loaded_models:
            return
        
        # For now, unload the first model (FIFO)
        # TODO: Implement proper LRU tracking
        model_name = next(iter(self.loaded_models))
        await self.unload_model(model_name)
    
    async def unload_model(self, model_name: str):
        """Unload a specific model from memory."""
        if model_name in self.loaded_models:
            del self.loaded_models[model_name]
            self.logger.info(f"Unloaded model: {model_name}")
            
            # Force garbage collection
            import gc
            gc.collect()
    
    async def unload_all_models(self):
        """Unload all models from memory."""
        model_names = list(self.loaded_models.keys())
        for model_name in model_names:
            await self.unload_model(model_name)
        
        self.logger.info("All models unloaded")
    
    def get_model(self, model_name: str) -> Optional[Any]:
        """Get a loaded model instance."""
        self._ensure_logger()
        
        if model_name == "entity_extraction":
            # Load GLiNER model specifically
            try:
                if model_name not in self.loaded_models:
                    try:
                        from gliner import GLiNER
                    except ImportError as e:
                        self.logger.warning(f"GLiNER package not available: {e}")
                        # Return None instead of dummy model - let the caller handle it
                        return None
                        
                    print(f"🔍 Loading GLiNER model for advanced entity extraction...")
                    self.logger.info(f"Loading GLiNER model for entity extraction...")
                    model = GLiNER.from_pretrained("urchade/gliner_medium-v2.1")
                    self.loaded_models[model_name] = model
                    print(f"✅ GLiNER entity extraction ready (replacing legacy spaCy)")
                    self.logger.info(f"✅ GLiNER model loaded successfully")
                
                return self.loaded_models[model_name]
                
            except Exception as e:
                self.logger.error(f"Failed to load GLiNER model: {e}")
                return None
        
        elif model_name == "intent_classification":
            # Load XLM-RoBERTa model for intent classification
            try:
                if model_name not in self.loaded_models:
                    try:
                        from transformers import AutoTokenizer, AutoModel
                    except ImportError as e:
                        self.logger.warning(f"transformers package not available: {e}")
                        # Return None instead of dummy model - let the caller handle it
                        return None
                        
                    from dataclasses import dataclass
                    
                    print(f"🔍 Loading XLM-RoBERTa model for intent classification...")
                    self.logger.info(f"Loading XLM-RoBERTa model for intent classification...")
                    
                    # Load tokenizer and model
                    tokenizer = AutoTokenizer.from_pretrained("xlm-roberta-base")
                    model = AutoModel.from_pretrained("xlm-roberta-base")
                    
                    # Create a model wrapper with both components
                    @dataclass
                    class IntentModelWrapper:
                        tokenizer: Any
                        model: Any
                    
                    wrapper = IntentModelWrapper(tokenizer=tokenizer, model=model)
                    self.loaded_models[model_name] = wrapper
                    
                    print(f"✅ XLM-RoBERTa intent classification ready (multilingual)")
                    self.logger.info(f"✅ XLM-RoBERTa model loaded successfully")
                
                return self.loaded_models[model_name]
                
            except Exception as e:
                self.logger.error(f"Failed to load XLM-RoBERTa model: {e}")
                return None
        
        elif model_name == "paraphrase-multilingual":
            # Load sentence-transformers model for embeddings
            try:
                if model_name not in self.loaded_models:
                    try:
                        from sentence_transformers import SentenceTransformer
                    except ImportError as e:
                        self.logger.error(f"sentence-transformers package not available: {e}")
                        print(f"❌ sentence-transformers package missing - install with: pip install sentence-transformers")
                        return None
                    
                    print(f"🔍 Loading sentence-transformers model for embeddings...")
                    self.logger.info(f"🔍 [EMBEDDING_MODEL_DEBUG] Loading sentence-transformers model...")
                    
                    # Track loading time
                    import time
                    start_time = time.time()
                    
                    # Load model
                    model_id = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
                    self.logger.info(f"🔍 [EMBEDDING_MODEL_DEBUG] Loading model_id: {model_id}")
                    model = SentenceTransformer(model_id)
                    self.loaded_models[model_name] = model
                    
                    load_time = time.time() - start_time
                    print(f"✅ sentence-transformers embedding model ready in {load_time:.2f}s")
                    self.logger.info(f"🔍 [EMBEDDING_MODEL_DEBUG] ✅ Model loaded successfully in {load_time:.2f}s")
                    self.logger.info(f"🔍 [EMBEDDING_MODEL_DEBUG] Model info: {model}")
                else:
                    self.logger.debug(f"🔍 [EMBEDDING_MODEL_DEBUG] Using cached embedding model: {model_name}")
                
                return self.loaded_models[model_name]
                
            except Exception as e:
                self.logger.error(f"Failed to load sentence-transformers model: {e}")
                print(f"❌ sentence-transformers model loading failed: {e}")
                import traceback
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                return None
        
        # REMOVED: coreference model loader (V3 cleanup)
        
        # For other models that were downloaded during initialize_models but don't have specific loaders
        # Check if the model was successfully downloaded and create a basic pipeline
        if model_name in self.model_configs:
            model_config = self.model_configs[model_name]
            try:
                if model_name not in self.loaded_models:
                    try:
                        from transformers import pipeline
                    except ImportError as e:
                        self.logger.warning(f"transformers package not available for {model_name}: {e}")
                        return None
                    
                    self.logger.info(f"Loading pipeline for {model_name}: {model_config.model_id}")
                    
                    # Create pipeline based on task type
                    pipe = pipeline(
                        model_config.task.value,
                        model=model_config.model_id,
                        **model_config.config_overrides
                    )
                    self.loaded_models[model_name] = pipe
                    self.logger.info(f"✅ Pipeline loaded for {model_name}")
                
                return self.loaded_models[model_name]
                
            except Exception as e:
                self.logger.error(f"Failed to load pipeline for {model_name}: {e}")
                return None
        
        # For models not in config, return from loaded_models cache
        return self.loaded_models.get(model_name)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about available and loaded models."""
        return {
            "available_models": {
                name: {
                    "model_id": config.model_id,
                    "task": config.task.value,
                    "description": config.description,
                    "required": config.required,
                    "multilingual": config.multilingual,
                    "memory_mb": config.memory_mb
                }
                for name, config in self.model_configs.items()
            },
            "loaded_models": list(self.loaded_models.keys()),
            "memory_config": {
                "max_memory_mb": self.max_memory_mb,
                "max_concurrent_models": self.max_concurrent_models,
                "auto_unload": self.auto_unload
            }
        }
    
    def add_model_config(self, model_config: TransformerModelConfig):
        """Add a new model configuration."""
        self.model_configs[model_config.name] = model_config
        self.logger.info(f"Added model configuration: {model_config.name}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the transformers system."""
        try:
            import transformers
            
            # Check if required models are available
            required_models = [
                config for config in self.model_configs.values() 
                if config.required
            ]
            
            available_count = 0
            for model_config in required_models:
                try:
                    from transformers import AutoTokenizer
                    AutoTokenizer.from_pretrained(model_config.model_id)
                    available_count += 1
                except:
                    pass
            
            return {
                "status": "healthy" if available_count == len(required_models) else "degraded",
                "transformers_version": transformers.__version__,
                "required_models": len(required_models),
                "available_models": available_count,
                "loaded_models": len(self.loaded_models),
                "memory_usage": f"{len(self.loaded_models)}/{self.max_concurrent_models} models"
            }
            
        except ImportError:
            return {
                "status": "unhealthy",
                "error": "Transformers library not available"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
