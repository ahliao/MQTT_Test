# Docker on Embedded Linux Tradeoffs

## Context

This project targets an embedded Linux computer such as a LattePanda IOTA. Docker can be useful on this kind of device, but it is not automatically the best choice. For this project, Docker is intentionally not part of the initial workflow so the learning path stays focused on Linux, MQTT, protobuf, and Python.

The main decision is whether to run services directly on the device OS or inside containers.

## Good Uses for Docker

Docker is especially useful for repeatable infrastructure and multi-device deployments.

For this project, the preferred first setup is direct installation of Mosquitto on WSL Ubuntu and later on the embedded Linux device. Docker remains a useful option to understand, but it should not be used yet.

## Pros

- Repeatable setup: the same container image can run on your laptop and embedded device.
- Easier cleanup: removing a container is usually cleaner than undoing system package changes.
- Dependency isolation: the MQTT broker and Python services can avoid conflicting with other software on the device.
- Deployment consistency: containers can reduce differences between development and production.
- Service separation: sensor, processor, monitor, and broker can be packaged independently.

## Cons

- More moving parts: Docker adds its own commands, logs, networking, volumes, and failure modes.
- Resource overhead: containers are lightweight compared with virtual machines, but they still use CPU, memory, disk, and startup time.
- Hardware access can be more complex: real ADC, GPIO, I2C, SPI, USB, and serial devices may require device mapping and permissions.
- Networking can be confusing at first: `localhost` from inside a container is not always the host system.
- System integration can be less direct: `systemd`, hardware permissions, logging, and updates may need extra setup.
- Storage wear matters: embedded systems may use eMMC or SD storage, and container logs/images can consume space over time.

## Direct Install Pros

Running directly on the embedded Linux OS means installing Mosquitto and Python services on the device itself.

Advantages:

- Simpler hardware access
- Fewer layers to debug
- Easier to understand for a first embedded project
- Works well with `systemd` services
- Lower disk usage than container images in many cases

## Direct Install Cons

- More manual setup on each device
- Harder to reproduce exactly across machines
- System packages can drift over time
- Cleanup can be messier
- Dependency conflicts are more likely if the device runs other software

## Recommendation for This Project

Do not use Docker at this time.

Start with a direct install on WSL Ubuntu for development. Later, use the same direct-install mental model on the embedded Linux device. This keeps the learning path clearer because you can focus on MQTT, protobuf, Python services, and Linux service management before adding container orchestration.

A practical path:

1. Develop in WSL Ubuntu with Mosquitto installed directly from Ubuntu packages.
2. Run the Python services with `uv` directly in WSL Ubuntu.
3. Move to the embedded device and install Mosquitto directly with the OS package manager.
4. Run the Python services directly with `uv` or as `systemd` services.
5. Consider Docker later only if deployment repeatability becomes more important than simplicity.

## When Docker Is Worth It on the Device

Docker becomes more attractive when:

- You need to deploy the same stack to multiple devices.
- You want reliable rollback between versions.
- The device has enough CPU, RAM, and storage headroom.
- Hardware access requirements are simple or well understood.
- You already know Docker well enough that it reduces complexity instead of adding it.

## When to Avoid Docker on the Device

Avoid Docker at first when:

- You are still learning the basics of the system.
- You need direct access to hardware buses and are not yet comfortable with Linux permissions.
- The device has tight storage or memory limits.
- You want the simplest possible boot and service-management story.
