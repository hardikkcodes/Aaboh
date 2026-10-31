#!/bin/sh
# Production ingestion schedule: alerts every 15 minutes, weather and air quality
# hourly. One failed run is logged and retried on the next pass.

pass=0
while true; do
  python manage.py fetch_alerts || echo "fetch_alerts failed"
  if [ $((pass % 4)) -eq 0 ]; then
    python manage.py fetch_weather --area kolkata || echo "fetch_weather failed"
    python manage.py fetch_cpcb || echo "fetch_cpcb failed"
    python manage.py fetch_air_forecast || echo "fetch_air_forecast failed"
  fi
  python manage.py send_alerts || echo "send_alerts failed"
  pass=$((pass + 1))
  sleep 900
done
