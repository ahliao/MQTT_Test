# AK09940A RTOS Batched Streaming Implementation Plan

This document describes a recommended RTOS task architecture and Protocol Buffers message layout for streaming AK09940A magnetometer data using bounded batches, nanopb, and an existing AES-GCM protected transport.

The design focuses on two primary operating modes:

- **100 Hz continuous mode** for normal/low-bandwidth streaming
- **1000 Hz continuous mode** for high-rate streaming

It is designed to remain flexible enough to support all AK09940A continuous measurement modes, including future expansion to 2500 Hz.

---

## 1. Design Goals

1. Support all AK09940A continuous measurement rates.
2. Optimize the architecture for 100 Hz and 1000 Hz operation.
3. Use bounded, fixed-capacity buffers suitable for nanopb and embedded systems.
4. Avoid heap allocation in the data path.
5. Support SPI DMA and UART DMA where available.
6. Keep interrupt handlers short and deterministic.
7. Batch samples before protobuf encoding and AES-GCM encryption.
8. Preserve raw sensor counts on the wire to avoid unnecessary MCU-side floating-point work.
9. Include enough metadata for the host to detect dropped batches, sensor overruns, invalid FIFO reads, and timing gaps.

---

## 2. Relevant AK09940A Behavior

The AK09940A supports continuous measurement modes at:

| Continuous mode | Output rate | `MODE[4:0]` | Notes |
|---:|---:|---:|---|
| Mode 1 | 10 Hz | `00010` | Valid in all drive modes |
| Mode 2 | 20 Hz | `00100` | Valid in all drive modes |
| Mode 3 | 50 Hz | `00110` | Valid in all drive modes |
| Mode 4 | 100 Hz | `01000` | Main recommended normal streaming mode |
| Mode 5 | 200 Hz | `01010` | Valid in all drive modes |
| Mode 6 | 400 Hz | `01100` | Low-power 1, low-power 2, or ultra-low-power only |
| Mode 7 | 1000 Hz | `01110` | Low-power 1 or ultra-low-power only |
| Mode 8 | 2500 Hz | `01111` | Ultra-low-power only |

Important device behavior:

- Mode changes should go through **power-down mode** first.
- After entering power-down mode, wait at least **100 us** before configuring another mode.
- Magnetometer data is 18-bit two's-complement raw count data.
- Sensitivity is typically **10 nT/LSB**, or **0.01 uT/LSB**.
- If temperature measurement is enabled, temperature data is available in `TMPS`.
- Temperature conversion is:

```text
Temperature_C = 30 - TMPS / 1.7
```

- The sensor has an 8-sample FIFO available in continuous modes.
- When FIFO is enabled, read each sample set starting at `HXL` and ending at `ST2`.
- Reading `ST2` completes the sample read and releases/pops the protected data set.

---

## 3. Recommended High-Level Architecture

Use a dedicated magnetometer service task that owns all AK09940A access.

```text
Application / CLI / Control Task
        |
        | MagCommand queue
        v
Magnetometer RTOS Task
        |
        | SPI/I2C transactions
        v
AK09940A
        |
        | bounded MagSampleBatch objects
        v
Streaming / Telemetry Task
        |
        | nanopb encode
        | AES-GCM encrypt/sign
        | UART DMA transmit
        v
Host
```

The magnetometer task should be the only code that directly calls the AK09940A driver while streaming. Other tasks should interact with it through commands.

---

## 4. Recommended RTOS Objects

### 4.1 Command Queue

Used by the application to control the magnetometer task.

```cpp
enum class MagCommandType : uint8_t {
    StartSingle,
    StartContinuous,
    Stop,
    SetDriveMode,
    SetTemperatureEnabled,
    ReadWhoAmI,
    SelfTest,
    SoftReset,
};

struct MagCommand {
    MagCommandType type;
    AK09940A::ContinuousRate rate;
    AK09940A::DriveMode drive;
    bool temperature_enabled;
    bool fifo_enabled;
    uint8_t fifo_watermark;
};
```

Recommended queue depth:

```text
4 to 8 commands
```

Commands are low-frequency control messages, so this queue does not need to be large.

### 4.2 DRDY Notification

Use a task notification from the DRDY EXTI interrupt.

```cpp
extern "C" void EXTIx_IRQHandler()
{
    BaseType_t woken = pdFALSE;
    vTaskNotifyGiveFromISR(g_mag_task_handle, &woken);
    portYIELD_FROM_ISR(woken);
}
```

The ISR should not perform SPI/I2C transactions, protobuf encoding, encryption, or UART transmission.

### 4.3 Sample Batch Queue

The magnetometer task publishes bounded sample batches to the streaming task.

```cpp
constexpr size_t MAG_MAX_SAMPLES_PER_BATCH = 16;

struct MagSampleRaw {
    uint16_t dt_us;
    int32_t x_counts;
    int32_t y_counts;
    int32_t z_counts;
    int8_t temp_raw;
    uint8_t status_flags;
};

struct MagSampleBatch {
    uint32_t sequence;
    uint64_t t0_us;
    uint32_t sample_period_us;
    uint8_t sample_count;
    uint8_t sensor_mode;
    uint8_t drive_mode;
    uint8_t batch_flags;
    MagSampleRaw samples[MAG_MAX_SAMPLES_PER_BATCH];
};
```

Recommended batch queue depth:

```text
2 to 4 batches
```

For high-rate modes, do not allow this queue to grow indefinitely. If the streaming task cannot keep up, increment a drop counter and publish that loss in a later status message.

---

## 5. Recommended Batch Sizes

| Sensor rate | Suggested batch size | Latency contribution | Notes |
|---:|---:|---:|---|
| 100 Hz | 1 to 4 samples | 10 to 40 ms | Use 1 if low latency matters |
| 200 Hz | 4 to 8 samples | 20 to 40 ms | Good middle ground |
| 400 Hz | 4 to 8 samples | 10 to 20 ms | FIFO useful |
| 1000 Hz | 8 to 16 samples | 8 to 16 ms | Main high-rate target |
| 2500 Hz | 16 to 32 samples | 6.4 to 12.8 ms | Use only if protocol/bandwidth allows |

The AK09940A FIFO depth is 8 samples. A protocol batch of 16 samples can be built by draining the FIFO twice or by combining multiple DRDY/FIFO events before publishing.

Recommended initial defaults:

```text
100 Hz:  batch size = 4
1000 Hz: batch size = 16, FIFO watermark = 8
```

For tighter latency at 1000 Hz, use:

```text
1000 Hz: batch size = 8, FIFO watermark = 4 or 8
```

---

## 6. Magnetometer Task State Machine

Recommended states:

```cpp
enum class MagTaskState : uint8_t {
    Init,
    PowerDown,
    Idle,
    Configure,
    SingleWaitDrdy,
    ContinuousWaitDrdy,
    ReadSamples,
    PublishBatch,
    ErrorRecovery,
};
```

Typical flow:

```text
Init
  -> soft reset
  -> read Who-Am-I
  -> power down
  -> Idle

StartContinuous command
  -> PowerDown
  -> wait 100 us
  -> Configure drive/temperature/FIFO
  -> write continuous mode
  -> ContinuousWaitDrdy

DRDY notification
  -> ReadSamples
  -> append samples to current batch
  -> if batch full, PublishBatch
  -> ContinuousWaitDrdy

Stop command
  -> PowerDown
  -> Idle
```

---

## 7. Mode Configuration Policy

Mode changes should be handled inside the magnetometer task so application code does not need to remember AK09940A transition rules.

Recommended helper:

```cpp
Status MagService::startContinuous(const MagContinuousConfig& cfg)
{
    driver.powerDown();
    delay_us(100);

    driver.setTemperatureEnabled(cfg.temperature_enabled);
    driver.setDriveMode(cfg.drive_mode);

    if (cfg.fifo_enabled) {
        driver.configureFifo(true, cfg.fifo_watermark);
    } else {
        driver.configureFifo(false, 1);
    }

    return driver.startContinuous(cfg.rate);
}
```

Recommended default modes:

| Application mode | Rate | Drive mode | FIFO | Batch size |
|---|---:|---|---|---:|
| Normal | 100 Hz | Low-noise-drive 1 or 2 | Optional/off | 4 |
| Fast | 1000 Hz | Low-power-drive 1 | On | 16 |
| Low-power fast | 1000 Hz | Ultra-low-power | On | 16 |

---

## 8. SPI and DMA Notes for STM32

For SPI operation:

- Use **SPI mode 3**.
- Configure clock polarity high and clock phase second edge:

```text
CPOL = 1
CPHA = 1
```

- Use 8-bit transfers unless your platform abstraction is built around 16-bit transactions.
- Use GPIO-controlled chip select if it simplifies multi-byte DMA reads.
- Prefer SPI DMA for high-rate streaming modes.
- Use DRDY EXTI to wake the magnetometer task.

Example STM32 HAL SPI setting:

```cpp
hspi1.Init.CLKPolarity = SPI_POLARITY_HIGH;
hspi1.Init.CLKPhase    = SPI_PHASE_2EDGE;
hspi1.Init.DataSize    = SPI_DATASIZE_8BIT;
hspi1.Init.FirstBit    = SPI_FIRSTBIT_MSB;
```

For 100 Hz, blocking SPI inside the magnetometer task is usually acceptable.

For 1000 Hz and above, prefer:

```text
DRDY EXTI -> task notification -> SPI DMA read -> DMA completion notification -> process samples
```

---

## 9. Sensor Read Strategy

### 9.1 Non-FIFO Read

Use this for 100 Hz or lower-latency single-sample streaming.

```text
Read ST1
Read HXL..HZH, optional TMPS
Read ST2
```

`ST2` must be read at the end of the data read sequence.

### 9.2 FIFO Read

Use this for 1000 Hz streaming.

Recommended flow:

```text
1. DRDY interrupt fires when FIFO watermark is reached.
2. Read ST1 to obtain FNUM.
3. Drain up to min(FNUM, available batch space) samples.
4. For each FIFO sample:
   - read HXL..TMPS..ST2, or HXL..HZH..ST2 if temperature is disabled/not needed
   - decode x/y/z 18-bit two's-complement values
   - record status bits from ST2
5. Publish batch when full or when flush timeout expires.
```

Because FIFO depth is 8, the task should service DRDY promptly at 1000 Hz. At 1000 Hz, 8 samples correspond to only 8 ms of buffering.

---

## 10. Sample Timing Model

Use one absolute timestamp per batch and relative offsets per sample.

```text
t0_us = timestamp of first sample in batch
sample_period_us = nominal period for configured rate
sample[i].dt_us = relative offset from t0_us
```

For fixed-rate continuous modes, `dt_us` can be derived as:

```cpp
sample[i].dt_us = i * sample_period_us;
```

Recommended periods:

| Rate | `sample_period_us` |
|---:|---:|
| 10 Hz | 100000 |
| 20 Hz | 50000 |
| 50 Hz | 20000 |
| 100 Hz | 10000 |
| 200 Hz | 5000 |
| 400 Hz | 2500 |
| 1000 Hz | 1000 |
| 2500 Hz | 400 |

If the task observes dropped FIFO samples or late servicing, set a batch/sample flag and allow the host to treat timing as discontinuous.

---

## 11. Protobuf Message Design

Two possible protobuf layouts are recommended:

1. **Structured repeated samples**: easier to inspect and debug.
2. **Packed bytes payload**: more efficient for high-rate streaming.

For 1000 Hz streaming, the packed bytes payload is preferred.

---

## 12. Option A: Structured Repeated Samples

This is readable and simple. It is a good first implementation and is adequate for 100 Hz.

```proto
syntax = "proto3";

import "nanopb.proto";

message Ak09940aSample {
  sint32 dt_us = 1;
  sint32 x_counts = 2;
  sint32 y_counts = 3;
  sint32 z_counts = 4;
  sint32 temp_raw = 5;
  uint32 status_flags = 6;
}

message Ak09940aBatch {
  uint32 sequence = 1;
  uint64 t0_us = 2;
  uint32 sample_period_us = 3;
  uint32 sample_count = 4;
  uint32 sensor_mode = 5;
  uint32 drive_mode = 6;
  uint32 batch_flags = 7;

  repeated Ak09940aSample samples = 8 [(nanopb).max_count = 16];
}
```

Pros:

- Easy to decode and inspect.
- Natural protobuf representation.
- Good for debugging and early bring-up.

Cons:

- More protobuf overhead per sample.
- More encoding CPU cost than packed bytes.

---

## 13. Option B: Packed Sample Bytes

This is recommended for the high-rate path.

```proto
syntax = "proto3";

import "nanopb.proto";

message Ak09940aPackedBatch {
  uint32 sequence = 1;
  uint64 t0_us = 2;
  uint32 sample_period_us = 3;
  uint32 sample_count = 4;
  uint32 sensor_mode = 5;
  uint32 drive_mode = 6;
  uint32 batch_flags = 7;

  // Packed little-endian records.
  // Record format v1:
  //   uint16 dt_us
  //   int24  x_counts, little-endian, sign-extended on decode
  //   int24  y_counts, little-endian, sign-extended on decode
  //   int24  z_counts, little-endian, sign-extended on decode
  //   int8   temp_raw
  //   uint8  status_flags
  // Total: 13 bytes/sample
  bytes packed_samples = 8 [(nanopb).max_size = 416];

  // Optional monotonic counters for diagnostics.
  uint32 sensor_overrun_count = 9;
  uint32 transport_drop_count = 10;
}
```

Recommended packed record size:

```text
13 bytes/sample
```

Record layout:

| Offset | Size | Field | Encoding |
|---:|---:|---|---|
| 0 | 2 | `dt_us` | uint16 little-endian |
| 2 | 3 | `x_counts` | signed int24 little-endian |
| 5 | 3 | `y_counts` | signed int24 little-endian |
| 8 | 3 | `z_counts` | signed int24 little-endian |
| 11 | 1 | `temp_raw` | signed int8 |
| 12 | 1 | `status_flags` | uint8 bitfield |

For `max_size = 416`, the message can hold up to 32 packed samples:

```text
32 samples * 13 bytes/sample = 416 bytes
```

Recommended runtime limits:

```text
100 Hz:  up to 4 samples per batch
1000 Hz: up to 16 samples per batch
2500 Hz: up to 32 samples per batch, if latency budget allows
```

Pros:

- Much lower per-sample protobuf overhead.
- Lower nanopb CPU cost.
- Works well with AES-GCM because the full protobuf message is still authenticated/encrypted.

Cons:

- Host decoder must understand the packed binary record layout.
- Less self-describing than repeated protobuf fields.

---

## 14. Recommended Status Flags

### 14.1 Per-Sample Flags

```cpp
enum MagSampleStatusFlags : uint8_t {
    MAG_SAMPLE_STATUS_DOR          = 1u << 0, // AK09940A data overrun
    MAG_SAMPLE_STATUS_INV          = 1u << 1, // AK09940A invalid FIFO read
    MAG_SAMPLE_STATUS_TEMP_VALID   = 1u << 2, // temp_raw is valid
    MAG_SAMPLE_STATUS_OVERFLOW     = 1u << 3, // axis clipped/overflow indication detected
    MAG_SAMPLE_STATUS_TIMING_GAP   = 1u << 4, // discontinuity before this sample
};
```

### 14.2 Batch Flags

```cpp
enum MagBatchFlags : uint32_t {
    MAG_BATCH_FLAG_FIFO_ENABLED        = 1u << 0,
    MAG_BATCH_FLAG_TEMP_ENABLED        = 1u << 1,
    MAG_BATCH_FLAG_SENSOR_OVERRUN      = 1u << 2,
    MAG_BATCH_FLAG_TRANSPORT_DROPPED   = 1u << 3,
    MAG_BATCH_FLAG_TIME_DISCONTINUITY  = 1u << 4,
    MAG_BATCH_FLAG_LOW_LATENCY_FLUSH   = 1u << 5,
};
```

---

## 15. AES-GCM Integration

Encrypt/sign one encoded protobuf batch, not individual samples.

Recommended order:

```text
1. Fill MagSampleBatch object.
2. Encode protobuf using nanopb into a plaintext buffer.
3. Encrypt plaintext buffer with AES-GCM.
4. Send encrypted frame over existing UART protocol.
```

Recommended AES-GCM Additional Authenticated Data, AAD:

```text
protocol_version
message_type
sequence
nonce/session id
timestamp or t0_us
plaintext length or ciphertext length
```

Recommended nonce strategy:

```text
nonce = session_random_or_boot_id || monotonically_increasing_packet_counter
```

Do not reuse an AES-GCM nonce with the same key.

Batching reduces AES-GCM call rate significantly:

| Sensor rate | Batch size | AES-GCM operations per second |
|---:|---:|---:|
| 100 Hz | 4 | 25 ops/s |
| 1000 Hz | 8 | 125 ops/s |
| 1000 Hz | 16 | 62.5 ops/s |
| 2500 Hz | 32 | 78.125 ops/s |

This is much more manageable than encrypting each sample individually.

---

## 16. Streaming Task Responsibilities

The streaming task should be separate from the magnetometer task.

Responsibilities:

1. Wait for `MagSampleBatch` from the sample batch queue.
2. Encode the batch with nanopb.
3. Encrypt/sign with AES-GCM.
4. Wrap the encrypted payload in the existing UART protocol frame.
5. Submit the frame to UART DMA.
6. Track queue overflows, encryption failures, and UART backpressure.

The magnetometer task should not block on UART transmission. If the streaming path cannot keep up, drop the oldest or newest batch according to system requirements and increment `transport_drop_count`.

Recommended policy:

```text
For logging: prefer dropping newest if storage/transport is overloaded.
For real-time visualization/control: prefer dropping oldest and keeping latest data.
```

---

## 17. Buffering Strategy

Recommended static buffers:

```cpp
alignas(4) static MagSampleBatch g_mag_batch_pool[4];
alignas(4) static uint8_t g_nanopb_plaintext_buffer[512];
alignas(4) static uint8_t g_ciphertext_buffer[512];
alignas(4) static uint8_t g_uart_frame_buffer_a[640];
alignas(4) static uint8_t g_uart_frame_buffer_b[640];
```

Suggested buffer sizes should be verified against the final protobuf schema and UART framing overhead.

For packed 16-sample batches:

```text
sample payload = 16 * 13 = 208 bytes
protobuf metadata overhead is small
AES-GCM tag = commonly 16 bytes
nonce/header/frame overhead depends on existing protocol
```

A 512-byte plaintext/ciphertext buffer should usually be enough for 16-sample packed batches. Use nanopb's generated size macros or test encodes to confirm.

---

## 18. Example Magnetometer Task Pseudocode

```cpp
void MagnetometerTask(void* arg)
{
    MagCommand cmd{};
    MagRuntime runtime{};

    driver.softReset();
    driver.powerDown();

    if (!driver.verifyWhoAmI()) {
        runtime.state = MagTaskState::ErrorRecovery;
    } else {
        runtime.state = MagTaskState::Idle;
    }

    for (;;) {
        while (xQueueReceive(g_mag_command_queue, &cmd, 0) == pdTRUE) {
            handleMagCommand(cmd, runtime);
        }

        switch (runtime.state) {
        case MagTaskState::Idle:
            xQueueReceive(g_mag_command_queue, &cmd, portMAX_DELAY);
            handleMagCommand(cmd, runtime);
            break;

        case MagTaskState::ContinuousWaitDrdy:
            if (ulTaskNotifyTake(pdTRUE, runtime.drdy_timeout_ticks) > 0) {
                runtime.state = MagTaskState::ReadSamples;
            } else {
                runtime.timeout_count++;
                // Optional: poll ST register or recover.
            }
            break;

        case MagTaskState::ReadSamples:
            readAvailableSamplesIntoBatch(runtime);
            if (runtime.active_batch.sample_count >= runtime.config.batch_size) {
                runtime.state = MagTaskState::PublishBatch;
            } else {
                runtime.state = MagTaskState::ContinuousWaitDrdy;
            }
            break;

        case MagTaskState::PublishBatch:
            publishBatchOrRecordDrop(runtime.active_batch);
            resetActiveBatch(runtime);
            runtime.state = MagTaskState::ContinuousWaitDrdy;
            break;

        case MagTaskState::ErrorRecovery:
            recoverSensor(runtime);
            break;

        default:
            runtime.state = MagTaskState::ErrorRecovery;
            break;
        }
    }
}
```

---

## 19. Host Decoder Notes

For the packed format, the host should:

1. Receive and authenticate/decrypt the UART frame.
2. Decode the protobuf batch.
3. Validate `sample_count` and `packed_samples.size`.
4. Decode each 13-byte sample record.
5. Sign-extend int24 x/y/z values to int32.
6. Convert counts to uT if needed:

```text
uT = counts * 0.01
```

7. Convert temperature if needed:

```text
Temperature_C = 30 - temp_raw / 1.7
```

8. Detect sequence gaps.
9. Detect timestamp discontinuities.
10. Check per-sample status flags.

---

## 20. Bring-Up Plan

### Phase 1: Sensor Task Without Encryption

- Verify Who-Am-I.
- Verify 100 Hz continuous mode.
- Read one sample at a time.
- Print or log raw x/y/z counts.
- Confirm `ST2` is always read at the end of sample reads.

### Phase 2: Bounded Batch Queue

- Add `MagSampleBatch` queue.
- Start with 100 Hz, batch size 4.
- Verify batch timestamps and sequence numbers.
- Add drop counters.

### Phase 3: nanopb Encoding

- Encode structured repeated sample message first.
- Confirm encoded sizes.
- Add static assertions or runtime checks for maximum encoded size.

### Phase 4: AES-GCM Transport

- Encrypt one protobuf batch per UART frame.
- Verify nonce uniqueness.
- Verify AAD coverage.
- Confirm host can decrypt and decode.

### Phase 5: High-Rate Mode

- Switch to 1000 Hz, low-power-drive 1.
- Enable FIFO with watermark 8.
- Use batch size 16.
- Use packed sample bytes if structured protobuf overhead is too high.
- Verify no sensor overrun at expected UART baud rate.

### Phase 6: Stress Testing

- Run 1000 Hz for extended duration.
- Track sequence gaps.
- Track sensor `DOR`/`INV` flags.
- Track queue drops.
- Track UART DMA underrun/backpressure.
- Confirm host-side timestamps and batch periods.

---

## 21. Recommended Initial Configuration

```cpp
MagContinuousConfig normal_100hz {
    .rate = AK09940A::ContinuousRate::Hz100,
    .drive = AK09940A::DriveMode::LowNoise1,
    .temperature_enabled = true,
    .fifo_enabled = false,
    .fifo_watermark = 1,
    .batch_size = 4,
};

MagContinuousConfig fast_1000hz {
    .rate = AK09940A::ContinuousRate::Hz1000,
    .drive = AK09940A::DriveMode::LowPower1,
    .temperature_enabled = true,
    .fifo_enabled = true,
    .fifo_watermark = 8,
    .batch_size = 16,
};
```

Use SPI mode 3 and DRDY EXTI for both modes. Use SPI DMA and UART DMA for the 1000 Hz path.

---

## 22. Final Recommendation

Use the following production-oriented architecture:

```text
AK09940A continuous mode
  -> DRDY EXTI
  -> magnetometer task drains sensor/FIFO
  -> bounded MagSampleBatch queue
  -> streaming task nanopb-encodes batch
  -> AES-GCM encrypts/authenticates batch
  -> UART DMA sends encrypted frame
```

For the protobuf design, start with the structured repeated sample message for ease of debugging. Once basic functionality is stable, move the high-rate 1000 Hz path to `Ak09940aPackedBatch` using the 13-byte packed sample record.

Recommended defaults:

```text
100 Hz:  low-noise-drive 1, no FIFO initially, batch size 4
1000 Hz: low-power-drive 1, FIFO watermark 8, batch size 16, packed_samples bytes
```
