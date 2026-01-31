import asyncio
import logging
from src.core.engine import engine
from src.config.settings import settings

logger = logging.getLogger("uvicorn")

async def simulation_loop():
    logger.info("Starting Background Simulation Loop")
    while True:
        try:
            engine.update_simulation()
        except Exception as e:
            logger.error(f"Error in simulation loop: {e}")
        
        await asyncio.sleep(settings.simulation.update_interval_sec)

async def start_simulation_service():
    asyncio.create_task(simulation_loop())
