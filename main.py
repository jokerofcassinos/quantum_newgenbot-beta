"""
FOREX QUANTUM BOT - Main Entry Point
CEO: Qwen Code | Created: 2026-04-10
"""

import sys
import asyncio
from loguru import logger
from src.core.orchestrator import Orchestrator
from src.core.config_manager import ConfigManager


def setup_logging():
    """Configure Loguru logging system"""
    logger.remove()  # Remove default handler
    
    # Console logging
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    
    # File logging
    logger.add(
        "logs/bot_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="30 days",
        level="DEBUG",
        encoding="utf-8"
    )


def main():
    """Main entry point"""
    logger.info("="*80)
    logger.info(" FOREX QUANTUM BOT - INICIALIZANDO")
    logger.info("="*80)
    logger.info(" Capital FTMO Demo: $100,000 USD")
    logger.info(" Smbolo: BTCUSD")
    logger.info(" DNA Engine: ATIVO (Zero Hardcoded Params)")
    logger.info("="*80)
    
    # Setup logging
    setup_logging()
    
    # Initialize configuration
    config = ConfigManager()
    
    # Load DNA
    dna = config.load_dna()
    logger.info(f" DNA carregado: {config.dna_file_path}")
    
    # Load absolute limits
    limits = config.load_absolute_limits()
    logger.info(f" Limites absolutos carregados: {config.absolute_limits_path}")
    
    # Initialize orchestrator
    orchestrator = Orchestrator(config=config, dna=dna)
    
    # Run main loop
    try:
        asyncio.run(orchestrator.run())
    except KeyboardInterrupt:
        logger.warning(" Interrupo manual detectada")
        orchestrator.shutdown()
    except Exception as e:
        logger.error(f" Erro fatal: {e}", exc_info=True)
        orchestrator.emergency_shutdown()


if __name__ == "__main__":
    main()




