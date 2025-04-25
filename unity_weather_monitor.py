#!/usr/bin/env python3
"""
Unity Weather Monitor
-------------------
A lightweight weather monitoring indicator for Ubuntu/Unity desktop environments.
Displays current weather conditions and temperature in the system tray.
Shows 15-day forecast in the dropdown menu.

Features:
- Current weather conditions display in system tray
- 15-day forecast in dropdown menu
- Unicode weather icons
- Configurable update intervals
- Uses Open-Meteo free weather API
- Temperature in imperial (°F) or metric (°C)
- Automatic location detection

License: MIT License
Copyright (c) 2024

Version: 1.0.0
Author: Kevin Hinds
GitHub: https://github.com/khinds10/Unity-Weather-Monitor
"""

import gi
import os
import time
import threading
import json
import signal
import requests
from threading import Thread
from datetime import datetime, timedelta

gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, GLib, AppIndicator3

class UnityWeatherMonitor:
    def __init__(self):
        # Initialize running state
        self.running = True
        
        # Get the path to the icon file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(script_dir, "weather-icon.png")
        
        # Create the app indicator
        self.indicator = AppIndicator3.Indicator.new(
            "unity-weather-monitor",
            icon_path,
            AppIndicator3.IndicatorCategory.SYSTEM_SERVICES
        )
        
        # Set indicator properties
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        
        # Default location (fallback if geolocation fails)
        self.latitude = 47.6062  # Seattle
        self.longitude = -122.3321
        self.location_name = "Default Location"
        
        # Temperature unit (imperial/celsius)
        self.use_imperial = True  # Default to imperial (Fahrenheit)
        
        # Weather data
        self.current_temp = None
        self.current_condition = None
        self.forecast = []
        
        # Weather condition codes to Unicode mapping
        self.weather_icons = {
            0: "☀️",    # Clear sky
            1: "🌤️",    # Mainly clear
            2: "⛅",    # Partly cloudy
            3: "☁️",    # Overcast
            45: "🌫️",   # Fog
            48: "🌫️",   # Depositing rime fog
            51: "🌧️",   # Light drizzle
            53: "🌧️",   # Moderate drizzle
            55: "🌧️",   # Dense drizzle
            56: "🌨️",   # Light freezing drizzle
            57: "🌨️",   # Dense freezing drizzle
            61: "🌦️",   # Slight rain
            63: "🌧️",   # Moderate rain
            65: "🌧️",   # Heavy rain
            66: "🌨️",   # Light freezing rain
            67: "🌨️",   # Heavy freezing rain
            71: "❄️",   # Slight snow fall
            73: "❄️",   # Moderate snow fall
            75: "❄️",   # Heavy snow fall
            77: "❄️",   # Snow grains
            80: "🌦️",   # Slight rain showers
            81: "🌧️",   # Moderate rain showers
            82: "🌧️",   # Violent rain showers
            85: "🌨️",   # Slight snow showers
            86: "🌨️",   # Heavy snow showers
            95: "⛈️",   # Thunderstorm
            96: "⛈️",   # Thunderstorm with slight hail
            99: "⛈️"    # Thunderstorm with heavy hail
        }
        
        # Weather condition codes to text descriptions
        self.weather_descriptions = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            56: "Light freezing drizzle",
            57: "Dense freezing drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            66: "Light freezing rain",
            67: "Heavy freezing rain",
            71: "Slight snow fall",
            73: "Moderate snow fall",
            75: "Heavy snow fall",
            77: "Snow grains",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            85: "Slight snow showers",
            86: "Heavy snow showers",
            95: "Thunderstorm",
            96: "Thunderstorm with slight hail",
            99: "Thunderstorm with heavy hail"
        }
        
        # Create a menu
        self.menu = Gtk.Menu()
        
        # Location item
        self.location_item = self.create_monospace_menu_item("Location: Detecting...")
        self.location_item.set_sensitive(False)
        self.menu.append(self.location_item)
        
        # Current weather item
        self.current_item = self.create_monospace_menu_item("Current Weather: Loading...")
        self.current_item.set_sensitive(False)
        self.menu.append(self.current_item)
        
        # Separator
        self.menu.append(Gtk.SeparatorMenuItem())
        
        # 15-day forecast items
        self.forecast_items = []
        
        # Create the forecast items
        for i in range(15):
            item = self.create_monospace_menu_item(f"Day {i+1}: Loading...")
            item.set_sensitive(False)
            self.forecast_items.append(item)
            self.menu.append(item)
        
        # Separator
        self.menu.append(Gtk.SeparatorMenuItem())
        
        # Preferences submenu
        prefs_item = Gtk.MenuItem(label="Preferences")
        prefs_submenu = Gtk.Menu()
        
        # Temperature unit submenu
        unit_item = Gtk.MenuItem(label="Temperature Unit")
        unit_submenu = Gtk.Menu()
        
        # Temperature unit options
        imperial_item = Gtk.RadioMenuItem(label="Imperial (°F)")
        imperial_item.set_active(self.use_imperial)
        imperial_item.connect("toggled", self.on_unit_toggled, True)
        unit_submenu.append(imperial_item)
        
        celsius_item = Gtk.RadioMenuItem.new_with_label_from_widget(imperial_item, "Celsius (°C)")
        celsius_item.set_active(not self.use_imperial)
        celsius_item.connect("toggled", self.on_unit_toggled, False)
        unit_submenu.append(celsius_item)
        
        unit_item.set_submenu(unit_submenu)
        prefs_submenu.append(unit_item)
        
        # Update interval
        interval_item = Gtk.MenuItem(label="Update Interval")
        interval_submenu = Gtk.Menu()
        
        # Update interval options
        interval_group = None
        for interval in [15, 30, 60]:
            if interval_group is None:
                item = Gtk.RadioMenuItem(label=f"{interval} minutes")
                interval_group = item
            else:
                item = Gtk.RadioMenuItem.new_with_label_from_widget(interval_group, f"{interval} minutes")
            item.set_active(interval == 15)  # Default is 15 minutes
            item.connect("toggled", self.on_interval_toggled, interval)
            interval_submenu.append(item)
        
        interval_item.set_submenu(interval_submenu)
        prefs_submenu.append(interval_item)
        prefs_item.set_submenu(prefs_submenu)
        self.menu.append(prefs_item)
        
        # Separator
        self.menu.append(Gtk.SeparatorMenuItem())
        
        # Refresh item
        refresh_item = Gtk.MenuItem(label="Refresh Now")
        refresh_item.connect("activate", self.refresh_weather)
        self.menu.append(refresh_item)
        
        # Quit item
        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", self.quit)
        self.menu.append(quit_item)
        
        self.menu.show_all()
        self.indicator.set_menu(self.menu)
        
        # Initialize update interval in minutes
        self.update_interval = 15
        
        # Start the update thread
        self.update_thread = Thread(target=self.update_weather_loop)
        self.update_thread.daemon = True
        self.update_thread.start()
    
    def create_monospace_menu_item(self, text):
        """Create a menu item with monospace font"""
        item = Gtk.MenuItem()
        label = Gtk.Label()
        label.set_markup(f'<span font_family="monospace">{text}</span>')
        label.set_xalign(0.0)  # Left-align text
        item.add(label)
        return item
    
    def update_monospace_menu_item(self, item, text):
        """Update the label of a monospace menu item"""
        label = item.get_child()
        label.set_markup(f'<span font_family="monospace">{text}</span>')
    
    def on_interval_toggled(self, widget, interval):
        """Handle radio menu item toggled signal for update interval"""
        if widget.get_active():
            self.update_interval = interval
    
    def on_unit_toggled(self, widget, use_imperial):
        """Handle radio menu item toggled signal for temperature unit"""
        if widget.get_active() and use_imperial != self.use_imperial:
            self.use_imperial = use_imperial
            # Update the display immediately
            GLib.idle_add(self.update_weather_ui)
    
    def celsius_to_fahrenheit(self, celsius):
        """Convert Celsius to Fahrenheit"""
        return (celsius * 9/5) + 32
    
    def get_location_from_ip(self):
        """Get location coordinates based on IP address"""
        try:
            # Use ipinfo.io to get location from IP (free tier)
            response = requests.get("https://ipinfo.io/json")
            if response.status_code != 200:
                print(f"Failed to get location data: {response.status_code}")
                return False
                
            data = response.json()
            if "loc" not in data:
                print("Location data not found in response")
                return False
                
            # Format is "latitude,longitude"
            lat_long = data["loc"].split(",")
            if len(lat_long) != 2:
                print(f"Invalid location format: {data['loc']}")
                return False
                
            self.latitude = float(lat_long[0])
            self.longitude = float(lat_long[1])
            
            # Get location name
            location_parts = []
            if "city" in data and data["city"]:
                location_parts.append(data["city"])
            if "region" in data and data["region"]:
                location_parts.append(data["region"])
            if "country" in data and data["country"]:
                location_parts.append(data["country"])
                
            self.location_name = ", ".join(location_parts) if location_parts else "Unknown Location"
            
            print(f"Location detected: {self.location_name} ({self.latitude}, {self.longitude})")
            return True
        except Exception as e:
            print(f"Error getting location: {e}")
            return False
    
    def get_weather_data(self):
        """Fetch weather data from Open-Meteo API"""
        try:
            url = f"https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "current": ["temperature_2m", "weather_code"],
                "daily": ["weather_code", "temperature_2m_max", "temperature_2m_min"],
                "timezone": "auto",
                "forecast_days": 15
            }
            
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"API error: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error fetching weather data: {e}")
            return None
    
    def update_weather_data(self):
        """Update weather data from API"""
        data = self.get_weather_data()
        if not data:
            return False
        
        try:
            # Update current weather
            self.current_temp = data["current"]["temperature_2m"]
            self.current_condition = data["current"]["weather_code"]
            
            # Update location item
            GLib.idle_add(self.update_location_item)
            
            # Update forecast
            self.forecast = []
            for i in range(len(data["daily"]["time"])):
                date = data["daily"]["time"][i]
                condition = data["daily"]["weather_code"][i]
                max_temp = data["daily"]["temperature_2m_max"][i]
                min_temp = data["daily"]["temperature_2m_min"][i]
                
                self.forecast.append({
                    "date": date,
                    "condition": condition,
                    "max_temp": max_temp,
                    "min_temp": min_temp
                })
            
            return True
        except Exception as e:
            print(f"Error parsing weather data: {e}")
            return False
    
    def get_condition_icon(self, condition_code):
        """Get the Unicode icon for a weather condition code"""
        return self.weather_icons.get(condition_code, "❓")
    
    def get_condition_description(self, condition_code):
        """Get the text description for a weather condition code"""
        return self.weather_descriptions.get(condition_code, "Unknown")
    
    def update_location_item(self):
        """Update the location menu item"""
        self.update_monospace_menu_item(
            self.location_item,
            f"Location: {self.location_name}"
        )
        return False  # Required for GLib.idle_add
    
    def update_weather_ui(self):
        """Update the weather UI elements"""
        if self.current_temp is None or self.current_condition is None:
            return False
        
        # Get condition icon
        icon = self.get_condition_icon(self.current_condition)
        
        # Convert temperature if needed
        display_temp = self.current_temp
        unit = "°C"
        if self.use_imperial:
            display_temp = self.celsius_to_fahrenheit(self.current_temp)
            unit = "°F"
        
        # Update indicator label
        label_text = f"{icon} {display_temp:.1f}{unit}"
        self.indicator.set_label(label_text, "")
        
        # Get condition description
        condition_desc = self.get_condition_description(self.current_condition)
        
        # Update current weather menu item
        self.update_monospace_menu_item(
            self.current_item, 
            f"Current: {icon} {condition_desc}, {display_temp:.1f}{unit}"
        )
        
        # Temporarily store all items we need to remove
        items_to_remove = []
        
        # Remove forecast items and any weekend separators
        for item in self.menu.get_children():
            # Skip the first few items (location, current, first separator)
            # and the last few items (preferences separator and below)
            if item in [self.location_item, self.current_item]:
                continue
                
            # Check if this is a menu item that's part of the forecast or a weekend separator
            if isinstance(item, Gtk.MenuItem) and not isinstance(item, Gtk.SeparatorMenuItem):
                label = item.get_child()
                if label and hasattr(label, 'get_text'):
                    text = label.get_text()
                    # Match any date format or day indicator
                    if text and (text.startswith("Mon") or
                               text.startswith("Tue") or
                               text.startswith("Wed") or
                               text.startswith("Thu") or
                               text.startswith("Fri") or
                               text.startswith("Sat") or
                               text.startswith("Sun") or
                               text.startswith("Day")):
                        items_to_remove.append(item)
        
        # Remove the items outside the loop
        for item in items_to_remove:
            self.menu.remove(item)
        
        # List to store all items we'll add
        new_items = []
        last_was_weekend = False
        
        # Create forecast items with weekend separators
        for i, day_data in enumerate(self.forecast):
            date_obj = datetime.fromisoformat(day_data["date"])
            date_str = date_obj.strftime("%a, %b %d")
            weekday = date_obj.weekday()  # 0-6, where 5 is Saturday and 6 is Sunday
            is_weekend = weekday >= 5
            
            # Handle weekend transitions
            if is_weekend and not last_was_weekend:
                # Starting a weekend - add separator before
                separator = self.create_monospace_menu_item("")
                separator.set_sensitive(False)
                new_items.append(separator)
            elif not is_weekend and last_was_weekend:
                # Ending a weekend - add separator after
                separator = self.create_monospace_menu_item("")
                separator.set_sensitive(False)
                new_items.append(separator)
            
            # Update forecast item
            condition_icon = self.get_condition_icon(day_data["condition"])
            max_temp = day_data["max_temp"]
            min_temp = day_data["min_temp"]
            
            # Convert temperatures if needed
            if self.use_imperial:
                max_temp = self.celsius_to_fahrenheit(max_temp)
                min_temp = self.celsius_to_fahrenheit(min_temp)
            
            # Get condition description
            condition_desc = self.get_condition_description(day_data["condition"])
            
            # Create forecast item
            forecast_item = self.create_monospace_menu_item(
                f"{date_str}: {condition_icon} {condition_desc}, {max_temp:.1f}{unit} / {min_temp:.1f}{unit}"
            )
            forecast_item.set_sensitive(False)
            new_items.append(forecast_item)
            
            # Update for next iteration
            last_was_weekend = is_weekend
        
        # If the last day was a weekend, add closing separator
        if last_was_weekend:
            separator = self.create_monospace_menu_item("")
            separator.set_sensitive(False)
            new_items.append(separator)
        
        # Find the position to insert items - after the first separator
        insert_position = 3  # After location, current weather, and the first separator
        
        # Insert all the new items
        for item in new_items:
            self.menu.insert(item, insert_position)
            insert_position += 1
        
        # Make sure all items are visible
        self.menu.show_all()
        
        return False  # Required for GLib.idle_add
    
    def update_weather_loop(self):
        """Background thread to update weather data"""
        # First try to get location from IP
        self.get_location_from_ip()
        
        while self.running:
            if self.update_weather_data():
                GLib.idle_add(self.update_weather_ui)
            
            # Sleep for the specified interval (in minutes)
            for _ in range(self.update_interval * 60):
                if not self.running:
                    break
                time.sleep(1)
    
    def refresh_weather(self, widget=None):
        """Manually refresh weather data"""
        # Try to update location first
        self.get_location_from_ip()
        
        if self.update_weather_data():
            GLib.idle_add(self.update_weather_ui)
    
    def quit(self, widget):
        """Handle quit event"""
        self.running = False
        Gtk.main_quit()

if __name__ == "__main__":
    # Handle Ctrl+C
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    # Create and start the indicator
    indicator = UnityWeatherMonitor()
    Gtk.main()
