# Remote MQTT Monitoring

## Goal

Run the MQTT broker, sensor service, and processor service on an embedded Linux computer such as a LattePanda IOTA, then run the GUI monitor from another PC on the same network.

This lets the embedded computer collect and process data while a more comfortable PC displays the live dashboard.

## Example Network

```text
IOTA / embedded Linux
IP address: 192.168.1.50

+-----------------------------------+
| Mosquitto MQTT broker             |
| Sensor service                    |
| Processor service                 |
+------------------+----------------+
                   |
                   | Ethernet / LAN
                   |
+------------------v----------------+
| PC                                |
| PySide6 GUI monitor               |
+-----------------------------------+
```

The PC connects to the broker using the IOTA IP address:

```bash
uv run sensor-platform-monitor-gui --mqtt-host 192.168.1.50
```

## Security Recommendation

For a good learning setup, do not expose an anonymous MQTT broker to the network.

Recommended baseline:

- Listen only on the network port you need, usually TCP `1883`.
- Disable anonymous access.
- Use username/password authentication.
- Use firewall rules to allow only trusted client IP addresses.
- Keep this on a trusted lab network, not the public internet.

TLS is better for production, but username/password plus firewall restrictions is a practical first secure setup for a private Ethernet or lab LAN.

## Install Mosquitto on the IOTA

On Ubuntu or Debian-based embedded Linux:

```bash
sudo apt update
sudo apt install mosquitto mosquitto-clients
```

Enable and start Mosquitto:

```bash
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

Check status:

```bash
systemctl status mosquitto
```

## Find the IOTA IP Address

On the IOTA, run:

```bash
hostname -I
```

Or inspect network interfaces:

```bash
ip addr
```

Use the IP address on the same network as the PC.

## Create MQTT Users

Create a password file:

```bash
sudo mosquitto_passwd -c /etc/mosquitto/passwd sensor_monitor
```

You will be prompted to enter a password.

To add another user later, omit `-c` because `-c` creates a new file:

```bash
sudo mosquitto_passwd /etc/mosquitto/passwd another_user
```

Suggested users for this project:

- `sensor_service`
- `processor_service`
- `sensor_monitor`

For a simple lab setup, one shared user is acceptable. For better separation, create different users for each service.

## Configure Mosquitto for Remote Authenticated Access

Create a project-specific config file:

```bash
sudo nano /etc/mosquitto/conf.d/sensor-platform.conf
```

Add:

```text
listener 1883 0.0.0.0
allow_anonymous false
password_file /etc/mosquitto/passwd
```

What this means:

- `listener 1883 0.0.0.0` listens on all network interfaces on port `1883`.
- `allow_anonymous false` rejects clients without credentials.
- `password_file` tells Mosquitto where valid users are stored.

Restart Mosquitto:

```bash
sudo systemctl restart mosquitto
```

Check for errors:

```bash
sudo journalctl -u mosquitto --no-pager -n 50
```

## Restrict Access With a Firewall

If `ufw` is enabled, allow MQTT only from the trusted PC IP address.

Example PC IP address: `192.168.1.25`

```bash
sudo ufw allow from 192.168.1.25 to any port 1883 proto tcp
```

Check firewall status:

```bash
sudo ufw status verbose
```

If you do not know the PC IP yet, find it from the PC network settings or with an OS-specific command.

Avoid this broader rule unless you are on a trusted isolated lab network:

```bash
sudo ufw allow 1883/tcp
```

## Test From the PC

From the PC, subscribe to a test topic:

```bash
mosquitto_sub -h 192.168.1.50 -p 1883 -u sensor_monitor -P 'your-password' -t test/topic
```

From another PC terminal, publish a message:

```bash
mosquitto_pub -h 192.168.1.50 -p 1883 -u sensor_monitor -P 'your-password' -t test/topic -m 'hello from pc'
```

The subscriber should print:

```text
hello from pc
```

## Project Code Credentials

The current Python services already support remote brokers through `--mqtt-host` and `--mqtt-port`, but they do not yet include username/password command-line options.

To use the secure broker above, the project should be extended to accept:

```text
--mqtt-username
--mqtt-password
```

Then each service can call the MQTT client's username/password setup before connecting.

Expected future commands:

```bash
uv run sensor-platform-sensor \
  --mqtt-host localhost \
  --mqtt-username sensor_service \
  --mqtt-password 'your-password'
```

```bash
uv run sensor-platform-processor \
  --mqtt-host localhost \
  --mqtt-username processor_service \
  --mqtt-password 'your-password'
```

```bash
uv run sensor-platform-monitor-gui \
  --mqtt-host 192.168.1.50 \
  --mqtt-username sensor_monitor \
  --mqtt-password 'your-password'
```

Storing passwords directly in shell history is not ideal. A later improvement should support environment variables such as:

```text
MQTT_USERNAME
MQTT_PASSWORD
```

## Running the Services on the IOTA

On the IOTA, the broker is local, so the sensor and processor can use `localhost`:

```bash
uv run sensor-platform-sensor --mqtt-host localhost
```

```bash
uv run sensor-platform-processor --mqtt-host localhost
```

On the PC, the GUI uses the IOTA IP address:

```bash
uv run sensor-platform-monitor-gui --mqtt-host 192.168.1.50
```

## TLS Option

TLS encrypts MQTT traffic and helps clients verify they are connecting to the right broker.

TLS is recommended when:

- The network is shared or untrusted.
- Sensor data is sensitive.
- The deployment will be long-lived.
- Devices may connect over Wi-Fi.

TLS adds more setup:

- Create a certificate authority.
- Create a server certificate for Mosquitto.
- Configure Mosquitto with `cafile`, `certfile`, and `keyfile`.
- Configure clients to trust the certificate authority.

For this project, start with username/password plus firewall rules on a private lab network. Add TLS later when the basic remote workflow is working.

## Common Problems

### PC Cannot Connect

Check that the IOTA and PC can reach each other:

```bash
ping 192.168.1.50
```

Check that Mosquitto is listening:

```bash
sudo ss -ltnp | grep 1883
```

Check the Mosquitto logs:

```bash
sudo journalctl -u mosquitto --no-pager -n 50
```

### Authentication Fails

Confirm the username exists in the password file:

```bash
sudo mosquitto_passwd /etc/mosquitto/passwd sensor_monitor
```

This command updates the password for that user.

### Works Locally But Not Remotely

Likely causes:

- Mosquitto is only listening on `localhost`.
- The firewall blocks port `1883`.
- The PC is on a different network or VLAN.
- The wrong IOTA IP address is being used.
