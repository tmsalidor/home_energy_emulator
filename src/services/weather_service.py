import urllib.request
import json
import logging
import time

logger = logging.getLogger(__name__)

class WeatherService:
    def __init__(self):
        self.cached_hourly_cloudcover = []
        self.last_fetch_time = 0
        self.manual_factors = {
            "sunny": 1.0,
            "cloudy": 0.4,
            "rainy": 0.1
        }
        self.current_factor = 1.0

    def fetch_weather(self, lat: float, lon: float):
        # Fetch at most once per hour (3600 seconds)
        now = time.time()
        if now - self.last_fetch_time < 3600 and self.cached_hourly_cloudcover:
            return

        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=cloudcover&timezone=auto&forecast_days=1"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                if "hourly" in data and "cloudcover" in data["hourly"]:
                    self.cached_hourly_cloudcover = data["hourly"]["cloudcover"]
                    self.last_fetch_time = now
                    logger.info(f"Weather data fetched successfully for lat:{lat}, lon:{lon}")
        except Exception as e:
            logger.error(f"Failed to fetch weather data from open-meteo: {e}")

    def get_solar_factor(self, mode: str, manual_weather: str, lat: float, lon: float, time_struct=None) -> float:
        if mode == "manual":
            self.current_factor = self.manual_factors.get(manual_weather, 1.0)
            return self.current_factor
        
        # Auto mode
        self.fetch_weather(lat, lon)
        
        if not self.cached_hourly_cloudcover:
            self.current_factor = 1.0
            return 1.0 # fallback

        if time_struct is None:
            time_struct = time.localtime()
            
        hour = time_struct.tm_hour
        
        if 0 <= hour < len(self.cached_hourly_cloudcover):
            cloudcover = self.cached_hourly_cloudcover[hour]
            # Convert cloudcover (0-100%) to a factor between 1.0 and 0.1
            factor = 1.0 - (cloudcover / 100.0) * 0.9
            self.current_factor = factor
            return factor

        self.current_factor = 1.0
        return 1.0
        
    def get_daily_factors(self, mode: str, manual_weather: str, lat: float, lon: float) -> list[float]:
        """ダッシュボードグラフ描画用: 1日(24時間)分のファクター配列(長さ24)を返す"""
        if mode == "manual":
            f = self.manual_factors.get(manual_weather, 1.0)
            return [f] * 24
            
        # Auto mode
        self.fetch_weather(lat, lon)
        if not self.cached_hourly_cloudcover:
            return [1.0] * 24
            
        factors = []
        for h in range(24):
            if h < len(self.cached_hourly_cloudcover):
                cc = self.cached_hourly_cloudcover[h]
                factors.append(1.0 - (cc / 100.0) * 0.9)
            else:
                factors.append(1.0)
        return factors
        
weather_service = WeatherService()
