# Unity Weather Monitor

A lightweight weather monitoring indicator for Ubuntu/Unity desktop environments.

## Features

- Shows current weather conditions and temperature in the system tray
- Displays detailed information in a dropdown menu:
  - Current weather condition with icon
  - Current temperature
  - 15-day forecast with high/low temperatures
  - Weekend days visually separated
- Automatic location detection via IP address
- Unicode weather icons
- Configurable temperature units (°F or °C)
- Configurable update intervals (15, 30, or 60 minutes)
- Uses Open-Meteo free weather API (no API key required)

## Installation

### Prerequisites

First, install the required dependencies:

```bash
sudo apt update
sudo apt install python3 python3-pip python3-gi gir1.2-appindicator3-0.1
```

### Installation Steps

1. Clone or download this repository:

```bash
git clone https://github.com/khinds10/Unity-Weather-Monitor
cd Unity-Weather-Monitor
```

2. Make the script executable:

```bash
chmod +x unity_weather_monitor.py
```

## Usage

Run the script:

```bash
./unity_weather_monitor.py
```

The indicator will appear in your Unity desktop panel showing the current temperature and weather condition icon.
Click on the indicator to see the current weather details and a 15-day forecast.

### Preferences

You can configure the application through the Preferences menu:

- **Temperature Unit**: Choose between Imperial (°F) and Celsius (°C)
- **Update Interval**: Set how often weather data updates (15, 30, or 60 minutes)

You can also manually refresh the weather data at any time by selecting "Refresh Now" from the menu.

## Autostart

To have the weather monitor start automatically when you log in:

1. Create a desktop entry file:

```bash
mkdir -p ~/.config/autostart
cat > ~/.config/autostart/unity-weather-monitor.desktop << EOF
[Desktop Entry]
Type=Application
Exec=/path/to/unity_weather_monitor.py
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=Unity Weather Monitor
Comment=Weather Monitor for Unity Desktop
EOF
```

2. Replace `/path/to/` with the absolute path to the script.

## License

This project is licensed under the MIT License. 