import time
import logging
from .models import SmartMeter, Solar, Battery, DeviceType, ElectricWaterHeater, V2H

logger = logging.getLogger(__name__)

from .battery_consts import BATTERY_STATIC_PROPS
from .water_heater_consts import WATER_HEATER_STATIC_PROPS
import struct

class SimulationEngine:
    def __init__(self):
        # Initialize devices with default IDs
        self.smart_meter = SmartMeter(device_id="sm_01")
        self.solar = Solar(device_id="sol_01")
        self.battery = Battery(device_id="bat_01")
        self.water_heater = ElectricWaterHeater(device_id="wh_01")
        self.v2h = V2H(device_id="v2h_01")
        
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

            except Exception as e:
                logger.error(f"Failed to parse Battery Property 0xD0: {e}")

        # Initialize Water Heater Properties
        # 1. Tank Capacity from Settings
        try:
            from src.config.settings import settings
            self.water_heater.tank_capacity = settings.echonet.water_heater_tank_capacity
            self.water_heater.heating_power_w = settings.echonet.water_heater_power_w
            logger.info(f"Water Heater configured: Cap={self.water_heater.tank_capacity}L, Power={self.water_heater.heating_power_w}W")
        except Exception as e:
            logger.error(f"Failed to load Water Heater settings: {e}")

        # 2. Remaining Hot Water = Half of Tank Capacity (User Request)
        self.water_heater.remaining_hot_water = float(self.water_heater.tank_capacity) / 2.0
        logger.info(f"Water Heater Remaining Hot Water initialized to half capacity: {self.water_heater.remaining_hot_water}L")

        # Initialize V2H Properties from Settings
        try:
            from src.config.settings import settings
            self.v2h.battery_capacity_wh = settings.echonet.v2h_battery_capacity_wh
            self.v2h.charge_power_w = settings.echonet.v2h_charge_power_w
            self.v2h.discharge_power_w = settings.echonet.v2h_discharge_power_w
            # 初期残容量 = 車載電池放電可能容量の50%
            self.v2h.remaining_capacity_wh = self.v2h.battery_capacity_wh * 0.5
            logger.info(f"V2H configured: Cap={self.v2h.battery_capacity_wh}Wh, "
                        f"Remain={self.v2h.remaining_capacity_wh}Wh, "
                        f"ChargePow={self.v2h.charge_power_w}W, DischargePow={self.v2h.discharge_power_w}W")
        except Exception as e:
            logger.error(f"Failed to load V2H settings: {e}")

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
        
        # 1.5 Update Water Heater State
        self._update_water_heater(dt)

        # 1.7 Update V2H State
        self._update_v2h(dt)
        
        # 2. Update Grid Power (Power Balance Formula)
        # Formula: P_grid = (P_load + P_charge) - (P_solar + P_discharge)
        
        p_load = self.current_load_w
        p_charge = self.battery.instant_charge_power if self.battery.is_charging else 0.0
        p_discharge = self.battery.instant_discharge_power if self.battery.is_discharging else 0.0
        p_solar = self.solar.instant_generation_power
        
        # Guard: Solar power cannot be negative
        if p_solar < 0: p_solar = 0
        
        # Water Heater Load
        p_wh = self.water_heater.heating_power_w if self.water_heater.is_heating else 0.0

        # V2H Load / Discharge
        p_v2h_charge = self.v2h.current_charge_w
        p_v2h_discharge = self.v2h.current_discharge_w

        p_grid = (p_load + p_charge + p_wh + p_v2h_charge) - (p_solar + p_discharge + p_v2h_discharge)
        
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

    def _update_water_heater(self, dt: float):
        """
        Handle Water Heater Logic
        """
        wh = self.water_heater
        if not wh.is_running:
            return

        # Decrease when stopped or auto (10 digit/hour)
        # Increase when heating (1 digit/minute = 60 digit/hour)
        
        # 0xB0 = 0x43 (Manual Stop) or 0x41 (Auto) -> Decrease 10/hour
        if wh.auto_setting == 0x43 or wh.auto_setting == 0x41:
            wh.is_heating = False
            # Decrease 10 per hour => 10/3600 per second
            decay_rate = 10.0 / 3600.0
            wh.remaining_hot_water -= decay_rate * dt
        
        # 0xB0 = 0x42 (Manual Start) -> Increase 1/minute
        elif wh.auto_setting == 0x42:
            wh.is_heating = True
            # Increase 60 per hour => 60/3600 per second = 1/60 per second
            fill_rate = 1.0 / 60.0
            wh.remaining_hot_water += fill_rate * dt
            
            # Stop if full
            if wh.remaining_hot_water >= wh.tank_capacity:
                wh.remaining_hot_water = float(wh.tank_capacity)
                wh.auto_setting = 0x41 # Revert to Auto
                wh.is_heating = False
                logger.info("Water Heater full. Stopping heating.")

        # Ensure bounds
        if wh.remaining_hot_water < 0:
            wh.remaining_hot_water = 0.0
        # Upper bound is tank capacity (handled above for heating, but clamp generally)
        if wh.remaining_hot_water > wh.tank_capacity:
            wh.remaining_hot_water = float(wh.tank_capacity)

    def _update_v2h(self, dt: float):
        """
        V2H (電気自動車充放電器) のシミュレーションロジック
        充電: V2Hを負荷としてグリッド計算式に加算（current_charge_wをセット）
        放電: V2Hを発電源としてグリッド計算式に加算（current_discharge_wをセット）
                放電判断は「正味ネット販電電力（太陽光/バッテリー差引後）」で判断
        """
        v2h = self.v2h
        # 前サイクルの電力値をリセット
        v2h.current_charge_w = 0.0
        v2h.current_discharge_w = 0.0

        if not v2h.is_running or not v2h.vehicle_connected:
            return

        mode = v2h.operation_mode

        if mode == 0x42:  # 充電
            # V2Hを負荷としてグリッド計算式に追加（グリッドから引く）
            charge_wh = v2h.charge_power_w * (dt / 3600.0)
            v2h.current_charge_w = v2h.charge_power_w
            v2h.remaining_capacity_wh += charge_wh

            # 満充電Check
            if v2h.remaining_capacity_wh >= v2h.battery_capacity_wh:
                v2h.remaining_capacity_wh = v2h.battery_capacity_wh
                v2h.operation_mode = 0x44  # 待機
                v2h.current_charge_w = 0.0
                logger.info("V2H: Fully charged. Mode -> Standby (0x44)")

        elif mode == 0x43:  # 放電
            # 「ネット販電電力」を計算（堆键買電量）
            # 太陽光・バッテリー放電を差し引いた後の正味販電量をV2Hが不足する
            bat = self.battery
            wh = self.water_heater
            p_solar = max(0.0, self.solar.instant_generation_power)
            p_bat_discharge = bat.instant_discharge_power if bat.is_discharging else 0.0
            p_bat_charge    = bat.instant_charge_power    if bat.is_charging    else 0.0
            p_wh            = wh.heating_power_w          if wh.is_heating       else 0.0

            # V2Hがない場合のネット販電電力（正=買電）
            net_grid = (self.current_load_w + p_bat_charge + p_wh) - (p_solar + p_bat_discharge)

            # 買電量が50Wを超えている場合にのみ放電
            over_50 = net_grid - 50.0
            if over_50 > 0:
                discharge_w = min(over_50, v2h.discharge_power_w)
                discharge_wh = discharge_w * (dt / 3600.0)

                v2h.current_discharge_w = discharge_w
                v2h.remaining_capacity_wh -= discharge_wh

                # 残量枯源Check
                if v2h.remaining_capacity_wh <= 0:
                    v2h.remaining_capacity_wh = 0.0
                    v2h.operation_mode = 0x44  # 待機
                    v2h.current_discharge_w = 0.0
                    logger.info("V2H: Battery empty. Mode -> Standby (0x44)")

        # 残容量クランプ
        v2h.remaining_capacity_wh = max(0.0, min(v2h.remaining_capacity_wh, v2h.battery_capacity_wh))


# Global Singleton
engine = SimulationEngine()
