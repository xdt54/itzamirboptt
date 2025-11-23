import time
import asyncio

from database.models import get_mining_users, add_resources, update_mining_times
from config.settings import (
    IRON_MINING_INTERVAL,
    SILVER_MINING_INTERVAL,
    MINING_LOOP_INTERVAL
)
from utils.logger import logger


class MiningLoop:
    
    def __init__(self):
        self.is_running = False
        self.task = None
    
    async def start(self):
        if self.is_running:
            logger.warning("Mining loop already running. Skipping duplicate start.")
            return
        
        self.is_running = True
        logger.info("Mining loop started.")
        
        try:
            while self.is_running:
                await self._process_mining()
                await asyncio.sleep(MINING_LOOP_INTERVAL)
        except asyncio.CancelledError:
            logger.info("Mining loop cancelled.")
        except Exception as e:
            logger.exception(f"Mining loop crashed: {e}")
        finally:
            self.is_running = False
            logger.info("Mining loop stopped.")
    
    async def _process_mining(self):
        try:
            users = get_mining_users()
            now = time.time()
            
            for user_id, last_iron, last_silver in users:
                try:
                    last_iron = last_iron or now
                    last_silver = last_silver or now
                    
                    iron_add = 0
                    silver_add = 0
                    
                    if now - last_iron >= IRON_MINING_INTERVAL:
                        iron_add = 1
                        last_iron = now
                    
                    if now - last_silver >= SILVER_MINING_INTERVAL:
                        silver_add = 1
                        last_silver = now
                    
                    if iron_add or silver_add:
                        add_resources(user_id, iron=iron_add, silver=silver_add)
                        update_mining_times(user_id, last_iron, last_silver)
                        logger.info(f"Mining: user {user_id} +{iron_add} iron +{silver_add} silver")
                
                except Exception as e:
                    logger.exception(f"Error processing mining for user {user_id}: {e}")
        
        except Exception as e:
            logger.exception(f"Error in mining loop iteration: {e}")
    
    def stop(self):
        self.is_running = False
        if self.task:
            self.task.cancel()


mining_loop = MiningLoop()
