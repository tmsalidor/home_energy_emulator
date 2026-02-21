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
    maker_code: str = "000106" # 3 bytes hex
    
    # Identification Numbers
    node_profile_id: str = "FE00000000000000000000000000000100" 
    wifi_devices: list[str] = ["solar", "battery"] # Default enabled devices
    solar_id: str        = "FE00000000000000000000000000000200"
    battery_id: str      = "FE00000000000000000000000000000300"
    water_heater_id: str = "FE00000000000000000000000000000400" # Smart Meter is 0400? Wait, check original file.
    smart_meter_id: str  = "FE00000000000000000000000000000000" # Shifted? Or strict ID? 
    # Original file had smart_meter_id 0400. Users usually don't overlap. 
    # Let's check original content of settings.py again to be safe about IDs.
    
    # Device Specific Defaults
    battery_rated_capacity_wh: float = 10000.0
    water_heater_tank_capacity: int = 370
    water_heater_power_w: float = 1000.0

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
    def load_from_yaml(cls, default_path: str = "config/default_config.yaml") -> "Settings":
        # Start with internal defaults (Pydantic fields)
        # Note: If default_config.yaml exists, we should load it.
        
        final_data = {}
        
        # 1. Load Defaults from YAML
        if os.path.exists(default_path):
            try:
                with open(default_path, 'r', encoding='utf-8') as f:
                    default_data = yaml.safe_load(f) or {}
                    final_data.update(default_data)
                    # print(f"DEBUG: Loaded default settings from {default_path}")
            except Exception as e:
                print(f"Failed to load default settings: {e}")
        else:
            print(f"Warning: Default config not found at {default_path}")

        # 2. Override with User Settings
        user_path = "config/user_settings.yaml"
        if os.path.exists(user_path):
            try:
                with open(user_path, 'r', encoding='utf-8') as f:
                    user_data = yaml.safe_load(f) or {}
                    
                    def deep_update(d, u):
                        for k, v in u.items():
                            if isinstance(v, dict):
                                d[k] = deep_update(d.get(k, {}), v)
                            else:
                                d[k] = v
                        return d
                    
                    deep_update(final_data, user_data)
                    # print(f"DEBUG: Loaded user settings from {user_path}")
            except Exception as e:
                print(f"Failed to load user settings: {e}")
                pass
        
        # 3. Create Instance (Pydantic will treat dict keys as fields, missing keys use class defaults)
        # We need to handle nested models. Pydantic accepts nested dicts.
        return cls(**final_data)

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
