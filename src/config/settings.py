import yaml
import os
from pydantic_settings import BaseSettings
from pydantic import BaseModel
from typing import Optional

class SystemSettings(BaseModel):
    log_level: str = "INFO"

class CommunicationSettings(BaseModel):
    wi_sun_device: str = "/dev/ttyUSB0"
    echonet_port: int = 3610

class SimulationSettings(BaseModel):
    update_interval_sec: float = 1.0
    scenario_file: str = "data/default_scenario.csv"

class Settings(BaseSettings):
    system: SystemSettings = SystemSettings()
    communication: CommunicationSettings = CommunicationSettings()
    simulation: SimulationSettings = SimulationSettings()

    @classmethod
    def load_from_yaml(cls, path: str = "src/config/default_config.yaml") -> "Settings":
        if not os.path.exists(path):
            return cls()
        
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # Simple recursive update or direct dict loading if structure matches
        return cls(**data)

# Global settings instance
settings = Settings.load_from_yaml()
