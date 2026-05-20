# LattePanda IOTA Ubuntu Boot Setup

## Goal

Run this project on a LattePanda IOTA with Ubuntu and have the sensor platform start automatically when the IOTA boots.

This guide starts the embedded-side services:

- Mosquitto MQTT broker
- Sensor publisher
- Processor service

The GUI monitor is usually better run from a separate development PC connected to the same network. See `docs/remote-mqtt-monitoring.md` if you want to monitor the IOTA remotely.

## Assumptions

This guide uses these example values:

- Ubuntu user: `iota`
- Project directory: `/home/iota/SensorPlatformTest`
- Local MQTT broker: `localhost:1883`
- Project startup mode: low-rate sensor path

Replace `iota` and `/home/iota/SensorPlatformTest` if your Ubuntu username or project path is different.

## Install System Packages

Update Ubuntu and install the required system packages:

```bash
sudo apt update
sudo apt install git curl mosquitto mosquitto-clients
```

Enable Mosquitto so the MQTT broker starts on boot:

```bash
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

Check that it is running:

```bash
systemctl status mosquitto
```

## Install uv

Install `uv` for the `iota` user:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Reload your shell environment, or log out and back in. Then verify:

```bash
uv --version
```

The service files below assume `uv` is installed at:

```text
/home/iota/.local/bin/uv
```

If your path is different, check it with:

```bash
command -v uv
```

Then use that full path in the systemd unit files.

## Clone and Prepare the Project

Clone the repository onto the IOTA:

```bash
cd /home/iota
git clone <your-repository-url> SensorPlatformTest
cd /home/iota/SensorPlatformTest
```

Install Python dependencies:

```bash
uv sync
```

Generate protobuf code:

```bash
uv run generate-protobuf
```

Run tests before installing boot services:

```bash
uv run pytest
```

## Verify Manually First

Before adding boot services, confirm the project runs from the terminal.

Terminal 1:

```bash
uv run sensor-platform-sensor --mqtt-host localhost --sample-rate-hz 2
```

Terminal 2:

```bash
uv run sensor-platform-processor --mqtt-host localhost
```

Optional Terminal 3:

```bash
uv run sensor-platform-monitor --mqtt-host localhost
```

Stop the processes with `Ctrl+C` after confirming messages are flowing.

## Create systemd Services

Use system-level `systemd` services so the platform starts at boot without a user login.

Create the sensor service:

```bash
sudo nano /etc/systemd/system/sensor-platform-sensor.service
```

Add:

```ini
[Unit]
Description=Sensor Platform Sensor Publisher
After=network-online.target mosquitto.service
Wants=network-online.target
Requires=mosquitto.service

[Service]
Type=simple
User=iota
WorkingDirectory=/home/iota/SensorPlatformTest
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/iota/.local/bin/uv run sensor-platform-sensor --mqtt-host localhost --sample-rate-hz 2
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Create the processor service:

```bash
sudo nano /etc/systemd/system/sensor-platform-processor.service
```

Add:

```ini
[Unit]
Description=Sensor Platform Processor
After=network-online.target mosquitto.service sensor-platform-sensor.service
Wants=network-online.target
Requires=mosquitto.service

[Service]
Type=simple
User=iota
WorkingDirectory=/home/iota/SensorPlatformTest
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/iota/.local/bin/uv run sensor-platform-processor --mqtt-host localhost
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Reload `systemd` after creating or editing unit files:

```bash
sudo systemctl daemon-reload
```

Start the services immediately:

```bash
sudo systemctl start sensor-platform-sensor
sudo systemctl start sensor-platform-processor
```

Enable them for future boots:

```bash
sudo systemctl enable sensor-platform-sensor
sudo systemctl enable sensor-platform-processor
```

## Check Service Status and Logs

Check status:

```bash
systemctl status sensor-platform-sensor
systemctl status sensor-platform-processor
```

Follow logs live:

```bash
sudo journalctl -u sensor-platform-sensor -f
```

```bash
sudo journalctl -u sensor-platform-processor -f
```

View recent logs without following:

```bash
sudo journalctl -u sensor-platform-sensor --no-pager -n 100
sudo journalctl -u sensor-platform-processor --no-pager -n 100
```

## Test Boot Startup

Reboot the IOTA:

```bash
sudo reboot
```

After it comes back online, check the services:

```bash
systemctl status mosquitto
systemctl status sensor-platform-sensor
systemctl status sensor-platform-processor
```

From the IOTA, you can also verify MQTT traffic directly:

```bash
mosquitto_sub -h localhost -t 'sensor/adc/readings'
```

## Run the High-Rate Path Instead

If you want the high-rate example to start on boot, use these commands in the unit files instead of the low-rate commands.

High-rate sensor `ExecStart`:

```ini
ExecStart=/home/iota/.local/bin/uv run sensor-platform-high-rate-sensor --mqtt-host localhost --sample-rate-hz 10000 --batch-size 500
```

High-rate processor `ExecStart`:

```ini
ExecStart=/home/iota/.local/bin/uv run sensor-platform-high-rate-processor --mqtt-host localhost
```

Do not run both the low-rate and high-rate unit pairs unless you intentionally want both examples active.

## Updating the Project Later

When you pull new code onto the IOTA, stop the services first:

```bash
sudo systemctl stop sensor-platform-sensor
sudo systemctl stop sensor-platform-processor
```

Update and verify the project:

```bash
cd /home/iota/SensorPlatformTest
git pull
uv sync
uv run generate-protobuf
uv run pytest
```

Start the services again:

```bash
sudo systemctl start sensor-platform-sensor
sudo systemctl start sensor-platform-processor
```

If you changed a systemd unit file, also run:

```bash
sudo systemctl daemon-reload
sudo systemctl restart sensor-platform-sensor
sudo systemctl restart sensor-platform-processor
```

## Troubleshooting

If a service fails immediately, check the full log:

```bash
sudo journalctl -u sensor-platform-sensor --no-pager -n 200
```

Common issues:

- `uv: No such file or directory`: update `ExecStart` to the full path from `command -v uv`.
- `WorkingDirectory=... failed`: update the service file to the real project path.
- MQTT connection refused: confirm `mosquitto` is running with `systemctl status mosquitto`.
- Imports or package errors: run `uv sync` from the project directory.
- Missing protobuf modules: run `uv run generate-protobuf` from the project directory.
