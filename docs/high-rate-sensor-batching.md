# High-Rate Sensor Batching

## Goal

Demonstrate how to publish faster ADC data, such as `10 kHz`, without sending one MQTT message per sample.

At `10 kHz`, one sample at a time would mean:

```text
10,000 MQTT messages per second
```

That is usually wasteful. Each MQTT message has overhead from MQTT framing, TCP/IP, broker routing, and client callbacks.

Instead, this project packages many ADC samples into one protobuf message.

Example:

```text
10,000 samples per second / 500 samples per batch = 20 MQTT messages per second
```

The data rate is still `10 kHz`, but the MQTT message rate is much lower.

## MQTT Topics

High-rate raw batches:

```text
sensor/adc/high-rate/batches
```

High-rate processed batch results:

```text
processor/adc/high-rate/results
```

## Protobuf Schema

The high-rate sensor publishes `AdcSampleBatch`:

```proto
message AdcSampleBatch {
  string sensor_id = 1;
  int64 start_timestamp_us = 2;
  uint32 channel = 3;
  uint32 sample_rate_hz = 4;
  uint32 sample_count = 5;
  double reference_voltage = 6;
  repeated uint32 raw_values = 7;
}
```

Important fields:

- `start_timestamp_us`: timestamp of the first sample in the batch.
- `sample_rate_hz`: tells the receiver how far apart samples are in time.
- `sample_count`: number of samples expected in the batch.
- `reference_voltage`: ADC reference voltage used to convert raw counts to volts.
- `repeated uint32 raw_values`: the actual ADC samples.

The `repeated` keyword is the key protobuf feature here. It means the message contains a list of values.

Instead of this:

```text
MQTT message 1: sample 1
MQTT message 2: sample 2
MQTT message 3: sample 3
...
```

The project sends this:

```text
MQTT message 1: samples 1 through 500
MQTT message 2: samples 501 through 1000
MQTT message 3: samples 1001 through 1500
...
```

## Reconstructing Sample Times

Only the first timestamp is sent. The receiver can reconstruct the time for every sample using the sample rate.

For sample index `i` inside the batch:

```text
sample_timestamp_us = start_timestamp_us + (i * 1_000_000 / sample_rate_hz)
```

At `10 kHz`, samples are spaced by:

```text
1 / 10,000 seconds = 0.0001 seconds = 100 microseconds
```

## Processing

The high-rate processor subscribes to raw batches, computes summary values, and publishes `ProcessedSampleBatch`:

```proto
message ProcessedSampleBatch {
  string sensor_id = 1;
  int64 start_timestamp_us = 2;
  uint32 channel = 3;
  uint32 sample_rate_hz = 4;
  uint32 sample_count = 5;
  double min_voltage = 6;
  double max_voltage = 7;
  double average_voltage = 8;
  double rms_voltage = 9;
  repeated double downsampled_voltages = 10;
}
```

The processor publishes:

- minimum voltage
- maximum voltage
- average voltage
- RMS voltage
- downsampled voltages for plotting

The GUI plots the downsampled voltages in a separate high-rate plot. The high-rate plot stores a rolling time window instead of only showing the latest batch.

The high-rate GUI plot treats the simulator as a continuous sample stream. If a Python or WSL scheduling delay creates an unrealistic wall-clock timestamp gap between batches, the GUI smooths that gap and places the next batch where it should be based on the sample rate. This keeps the educational plot focused on the sampled waveform rather than operating-system timing jitter.

## Run the High-Rate Example

Start Mosquitto first.

Terminal 1, run the high-rate sensor:

```bash
uv run sensor-platform-high-rate-sensor --sample-rate-hz 10000 --batch-size 500
```

Terminal 2, run the high-rate processor:

```bash
uv run sensor-platform-high-rate-processor
```

Terminal 3, run the GUI monitor:

```bash
uv run sensor-platform-monitor-gui
```

By default, the high-rate plot keeps the latest `10` seconds of processed batch data. You can change that window:

```bash
uv run sensor-platform-monitor-gui --high-rate-window-seconds 10
```

For a longer capture, for example `30` seconds:

```bash
uv run sensor-platform-monitor-gui --high-rate-window-seconds 30
```

The GUI will show the original low-rate plot if the original sensor/processor are running, and the separate high-rate batch plot if the high-rate sensor/processor are running.

## Educational Tradeoff

This example simulates high-rate sampling in Python. It is useful for learning message packaging and processing.

For a real 10 kHz ADC on embedded Linux, exact timing usually needs hardware support, kernel drivers, DMA, or buffered hardware APIs. Python can process batches, but it should not be trusted to precisely toggle or sample hardware every 100 microseconds in userspace.
