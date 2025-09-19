#!/usr/bin/env python3
"""
Dependency check script for AICO sentiment analysis.

This script verifies that all required dependencies are installed
and accessible for the sentiment analysis functionality.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_dependency(name, import_path=None, version_attr=None):
    """Check if a dependency is available and optionally get its version."""
    try:
        if import_path:
            module = __import__(import_path)
            # Handle nested imports like transformers.pipeline
            for attr in import_path.split('.')[1:]:
                module = getattr(module, attr)
        else:
            module = __import__(name)
        
        version = "unknown"
        if version_attr:
            try:
                version = getattr(module, version_attr)
            except AttributeError:
                pass
        
        print(f"✅ {name}: {version}")
        return True
        
    except ImportError as e:
        print(f"❌ {name}: Not installed ({e})")
        return False
    except Exception as e:
        print(f"⚠️ {name}: Error checking ({e})")
        return False


def check_transformers_models():
    """Check if transformers models can be accessed."""
    print("\n📦 Checking Transformers Models:")
    
    try:
        from transformers import AutoTokenizer
        
        models_to_check = [
            ("sentiment_multilingual", "nlptown/bert-base-multilingual-uncased-sentiment"),
            ("sentiment_english", "cardiffnlp/twitter-roberta-base-sentiment-latest"),
        ]
        
        for name, model_id in models_to_check:
            try:
                # Try to load tokenizer (lightweight check)
                tokenizer = AutoTokenizer.from_pretrained(model_id)
                print(f"✅ {name} ({model_id}): Available")
            except Exception as e:
                print(f"❌ {name} ({model_id}): Not available - {e}")
                
    except ImportError:
        print("❌ Cannot check models - transformers not installed")


def check_aico_modules():
    """Check AICO-specific modules."""
    print("\n🏗️ Checking AICO Modules:")
    
    modules_to_check = [
        ("aico.core.config", "ConfigurationManager"),
        ("aico.core.logging", "get_logger"),
        ("aico.core.topics", "AICOTopics"),
        ("aico.proto.aico_modelservice_pb2", "SentimentRequest"),
        ("modelservice.core.transformers_manager", "TransformersManager"),
        ("backend.services.modelservice_client", "ModelServiceClient"),
    ]
    
    for module_path, class_name in modules_to_check:
        try:
            module = __import__(module_path, fromlist=[class_name])
            cls = getattr(module, class_name)
            print(f"✅ {module_path}.{class_name}: Available")
        except ImportError as e:
            print(f"❌ {module_path}.{class_name}: Import error - {e}")
        except AttributeError as e:
            print(f"❌ {module_path}.{class_name}: Attribute error - {e}")
        except Exception as e:
            print(f"⚠️ {module_path}.{class_name}: Error - {e}")


def main():
    """Main dependency check function."""
    print("🔍 AICO Sentiment Analysis Dependency Check")
    print("=" * 50)
    
    print("🐍 Core Dependencies:")
    dependencies = [
        ("torch", None, "__version__"),
        ("transformers", None, "__version__"),
        ("numpy", None, "__version__"),
        ("httpx", None, "__version__"),
        ("protobuf", "google.protobuf", "__version__"),
        ("pyzmq", "zmq", "zmq_version"),
    ]
    
    all_good = True
    for dep in dependencies:
        if not check_dependency(*dep):
            all_good = False
    
    # Check transformers models
    check_transformers_models()
    
    # Check AICO modules
    check_aico_modules()
    
    print("\n" + "=" * 50)
    if all_good:
        print("🎉 All core dependencies are available!")
        print("\n💡 To test sentiment analysis, run:")
        print("   python scripts/test_sentiment_analysis.py")
    else:
        print("❌ Some dependencies are missing!")
        print("\n💡 To install missing dependencies, run:")
        print("   uv sync --all-extras")
    
    return 0 if all_good else 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️ Check interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Check failed with error: {e}")
        sys.exit(1)
