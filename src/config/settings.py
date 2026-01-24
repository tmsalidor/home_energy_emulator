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
    # Wi-SUN B-Route Settings
    b_route_id: str = "00112233445566778899AABBCCDDEEFF"
    b_route_password: str = "0123456789AB"
    wi_sun_channel: Optional[str] = None # Auto or specific channel

class EchonetSettings(BaseModel):
    # Common
    maker_code: str = "000000" # 3 bytes hex
    
    # Identification Numbers
    node_profile_id: str = "FE00000000000000000000000000000100" 
    solar_id: str        = "FE00000000000000000000000000000200"
    battery_id: str      = "FE00000000000000000000000000000300"
    smart_meter_id: str  = "FE00000000000000000000000000000400"
    
    # Device Specific Defaults
    battery_rated_capacity_wh: float = 10000.0

class SimulationSettings(BaseModel):
    update_interval_sec: float = 1.0
    scenario_file: str = "data/default_scenario.csv"

class Settings(BaseSettings):
    system: SystemSettings = SystemSettings()
    communication: CommunicationSettings = CommunicationSettings()
    echonet: EchonetSettings = EchonetSettings()
    simulation: SimulationSettings = SimulationSettings()
    
    _user_config_path: str = "config/user_settings.yaml"

    @classmethod
    def load_from_yaml(cls, default_path: str = "src/config/default_config.yaml") -> "Settings":
        # Load default
        base_settings = cls()
        
        # Override with user settings if exists
        user_path = "config/user_settings.yaml"
        if os.path.exists(user_path):
            try:
                with open(user_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                    # Deep update logic simplified for Pydantic V2 compat or just re-init
                    # For simplicity, we assume user_settings.yaml mirrors the structure
                    # We can use update or parse_obj/model_validate in V2, but here we construct dict first
                    base_dict = base_settings.model_dump() # Pydantic v2
                    
                    def deep_update(d, u):
                        for k, v in u.items():
                            if isinstance(v, dict):
                                d[k] = deep_update(d.get(k, {}), v)
                            else:
                                d[k] = v
                        return d
                    
                    final_data = deep_update(base_dict, data)
                    
                    # Debug: Print loaded keys to verify structure
                    if 'communication' in final_data:
                        print(f"DEBUG: Loaded Communication Settings keys: {final_data['communication'].keys()}")
                    
                    return cls(**final_data)
                    
            except Exception as e:
                print(f"Failed to load user settings: {e}")
                pass
                
        return base_settings

    def save_to_yaml(self):
        # Save current state to user_settings.yaml
        try:
            with open(self._user_config_path, 'w', encoding='utf-8') as f:
                # Pydantic v2 use model_dump
                yaml.dump(self.model_dump(), f, default_flow_style=False)
        except Exception as e:
            print(f"Failed to save settings: {e}")

# Global settings instance
settings = Settings.load_from_yaml()
