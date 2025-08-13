from aico.core.config import ConfigurationManager
from aico.core.logging import AICOLoggerFactory

config = ConfigurationManager()
logger = AICOLoggerFactory(config).create_logger('backend.test','test_module')
log_entry = logger.info('TEST LOG PERSISTENCE TOPIC DEBUG')
print(f"[TEST] Emitted log to topic: logs.backend.test.test_module")
