import time
import logging
from .models import SmartMeter, Solar, Battery, DeviceType

logger = logging.getLogger(__name__)

from .battery_consts import BATTERY_STATIC_PROPS
import struct

class SimulationEngine:
    def __init__(self):
        # Initialize devices with default IDs
        self.smart_meter = SmartMeter(device_id="sm_01")
        self.solar = Solar(device_id="sol_01")
        self.battery = Battery(device_id="bat_01")
        
        # Simulation State
        self.current_load_w: float = 500.0  # Base household load
        self.last_update_time: float = time.time()
        
        # Scenario Data
        self.use_scenario = True
        self.scenario_data = [] # List of {'time_sec': int, 'load': float, 'solar': float}
        self._load_scenario("data/default_scenario.csv")
        
        if 0xD0 in BATTERY_STATIC_PROPS:
            try:
                # 0xD0 is 4 bytes unsigned long (Wh) ? Or 225?
                # Usually D0 is Rated Electric Energy.
                # User config has D0 (208) as [0,0,54,176] -> 14000
                data = BATTERY_STATIC_PROPS[0xD0]
                # Assuming 4 bytes big endian
                val = struct.unpack(">L", data)[0]
                self.battery.rated_capacity_wh = float(val)
                logger.info(f"Battery Rated Capacity initialized from property 0xD0: {val} Wh")
            except Exception as e:
                logger.error(f"Failed to parse Battery Property 0xD0: {e}")

        logger.info("Simulation Engine Initialized")

    def _load_scenario(self, filepath: str):
        import csv
        import os
        if not os.path.exists(filepath):
            logger.warning(f"Scenario file not found: {filepath}")
            return
            
        try:
            with open(filepath, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Parse time HH:MM -> seconds from midnight
                    hh, mm = map(int, row['time'].split(':'))
                    t_sec = hh * 3600 + mm * 60
                    self.scenario_data.append({
                        'time_sec': t_sec,
                        'load': float(row['load_w']),
                        'solar': float(row['solar_w'])
                    })
            self.scenario_data.sort(key=lambda x: x['time_sec'])
            logger.info(f"Loaded {len(self.scenario_data)} scenario points")
        except Exception as e:
            logger.error(f"Failed to load scenario: {e}")

    def _get_current_scenario_values(self):
        if not self.scenario_data:
            return 500.0, 0.0 # Default fallback
            
        # Get current time of day in seconds
        now_struct = time.localtime()
        current_sec = now_struct.tm_hour * 3600 + now_struct.tm_min * 60 + now_struct.tm_sec
        
        # Find interval
        prev_point = self.scenario_data[-1]
        next_point = self.scenario_data[0]
        
        for point in self.scenario_data:
            if point['time_sec'] > current_sec:
                next_point = point
                break
            prev_point = point
            
        # Linear Interpolation
        t1 = prev_point['time_sec']
        t2 = next_point['time_sec']
        
        # Build logic for wrap-around (23:59 -> 00:00) if needed, 
        # but simple bounded search handles day cycle if inputs are 00:00 to 23:59.
        # If wrapped (prev > next), we are across midnight conceptually, but `tm_sec` resets.
        # Simple approach: if t1 > t2 (last point to first point), handling is tricky with 0-86400 wrap.
        # If current_sec is between last and first (e.g. 23:59:30), t1=23:59, t2=00:00?
        # Let's keep it simple: just use prev_point values if exact interpolation is too complex for this step,
        # OR implementation standard linear interp.
        
        if t1 == t2: return prev_point['load'], prev_point['solar']
        
        # Handle wrap around case for logic correctness if needed, 
        # but for now let's assume valid bounds or simple nearest/hold to simplify code complexity risk.
        # Let's do simple Linear Interp between t1 and t2.
        if t2 < t1: # Wrap around midnight case
             # e.g. t1=23:00 (82800), t2=06:00 (21600). current=02:00 (7200).
             # Shift t2 and current by +24h for calculation
             t2 += 86400
             if current_sec < t1: current_sec += 86400
        
        ratio = (current_sec - t1) / (t2 - t1)
        ratio = max(0.0, min(1.0, ratio))
        
        load = prev_point['load'] + (next_point['load'] - prev_point['load']) * ratio
        solar = prev_point['solar'] + (next_point['solar'] - prev_point['solar']) * ratio
        
        return load, solar

    def update_simulation(self):
        """
        Periodic update function to calculate power balance and update device states.
        Should be called every ~1 second.
        """
        now = time.time()
        dt = now - self.last_update_time
        self.last_update_time = now
        
        if self.use_scenario:
            s_load, s_solar = self._get_current_scenario_values()
            # Override only if not manually overridden? 
            # For emulator, scenario usually drives unless manual override.
            # Let's overwrite for now, manual controls effectively offset or disable scenario logic?
            # Or simple: Scenario drives base values.
            self.current_load_w = s_load
            self.solar.instant_generation_power = s_solar
        
        # 1. Update Battery State (SOC Logic)
        self._update_battery(dt)
        
        # 2. Update Grid Power (Power Balance Formula)
        # Formula: P_grid = (P_load + P_charge) - (P_solar + P_discharge)
        
        p_load = self.current_load_w
        p_charge = self.battery.instant_charge_power if self.battery.is_charging else 0.0
        p_discharge = self.battery.instant_discharge_power if self.battery.is_discharging else 0.0
        p_solar = self.solar.instant_generation_power
        
        # Guard: Solar power cannot be negative
        if p_solar < 0: p_solar = 0
        
        p_grid = (p_load + p_charge) - (p_solar + p_discharge)
        
        self.smart_meter.instant_current_power = p_grid
        
        # 3. Update Cumulative Values (Integration)
        # W * s / 3600 / 1000 = kWh
        kwh_increment_factor = dt / 3600.0 / 1000.0
        
        if p_grid > 0:
            self.smart_meter.cumulative_power_buy_kwh += p_grid * kwh_increment_factor
        else:
            self.smart_meter.cumulative_power_sell_kwh += abs(p_grid) * kwh_increment_factor
            
        self.solar.cumulative_generation_kwh += p_solar * kwh_increment_factor

    def _update_battery(self, dt: float):
        """
        Handle battery SOC and guards.
        """
        bat = self.battery
        
        # SOC Guard Logic
        if bat.soc >= 100.0:
            if bat.is_charging:
                logger.info("Battery fully charged. Stopping charge.")
                bat.is_charging = False
                bat.instant_charge_power = 0.0
                
        if bat.soc <= 0.0:
            if bat.is_discharging:
                logger.info("Battery empty. Stopping discharge.")
                bat.is_discharging = False
                bat.instant_discharge_power = 0.0
                
        # Calculate Energy Flow
        # Wh change
        energy_delta_wh = 0.0
        if bat.is_charging:
            wh_step = bat.instant_charge_power * (dt / 3600.0)
            energy_delta_wh += wh_step
            bat.cumulative_charge_wh += wh_step
        if bat.is_discharging:
            wh_step = bat.instant_discharge_power * (dt / 3600.0)
            energy_delta_wh -= wh_step
            bat.cumulative_discharge_wh += wh_step
            
        # Update SOC
        # soc_delta = (Wh change / Capacity) * 100
        if bat.rated_capacity_wh > 0:
            soc_delta = (energy_delta_wh / bat.rated_capacity_wh) * 100.0
            bat.soc += soc_delta
            
        # Clamp SOC
        bat.soc = max(0.0, min(100.0, bat.soc))

# Global Singleton
engine = SimulationEngine()
