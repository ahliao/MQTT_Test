# AK09940A Embedded C++ Driver

A small, MCU-agnostic C++ driver for the **AKM AK09940A 3-axis magnetometer**.

The driver is intended for bare-metal and RTOS applications. It does not depend on STM32 HAL, FreeRTOS, dynamic allocation, exceptions, or a specific C++ standard library implementation. Platform integration is done with user-supplied callbacks for SPI, I2C, and microsecond delays.

## Features

- SPI and I2C register access through callback interfaces
- STM32-friendly SPI integration examples
- Single measurement mode
- Continuous measurement modes:
  - 10 Hz
  - 20 Hz
  - 50 Hz
  - 100 Hz
  - 200 Hz
  - 400 Hz
  - 1000 Hz
  - 2500 Hz
- Power-down mode
- Who-Am-I read and verification
- Temperature register read and conversion to degrees Celsius
- Raw signed 18-bit magnetic data readout
- Converted magnetic data in microtesla
- Data-ready polling helper
- Overrun, invalid-data, and FIFO-count status reporting
- External trigger mode helper
- Basic self-test helper

## Files

```text
AK09940A.hpp   Public API, callback types, enums, and data structures
AK09940A.cpp   Driver implementation
README.md      This guide
```

Add `AK09940A.cpp` to your firmware build and include `AK09940A.hpp` from application code.

## Hardware notes

### SPI wiring

For SPI operation, connect the AK09940A for 4-wire SPI:

```text
AK09940A CSB      -> MCU GPIO chip-select output
AK09940A SCL/SK   -> MCU SPI SCK
AK09940A SDA/SI   -> MCU SPI MOSI
AK09940A SO       -> MCU SPI MISO
AK09940A DRDY/TRG -> MCU GPIO/EXTI input, optional but recommended
AK09940A RSTN     -> VID or MCU reset GPIO
AK09940A CAD0     -> VSS
AK09940A CAD1     -> VSS
```

The AK09940A SPI bus uses **SPI mode 3**:

```text
CPOL = 1
CPHA = 1
```

For STM32 HAL this usually means:

```c
hspi.Init.CLKPolarity = SPI_POLARITY_HIGH;
hspi.Init.CLKPhase    = SPI_PHASE_2EDGE;
```

Keep chip-select high when idle. The driver controls chip-select through the `spi_select` and `spi_deselect` callbacks.

### I2C wiring

For I2C operation, tie `CSB` high to `VID`. The 7-bit I2C address is selected with `CAD1` and `CAD0`:

```text
CAD1 CAD0  7-bit address
 0    0    0x0C
 0    1    0x0D
 1    0    0x0E
 1    1    0x0F
```

The driver expects a **7-bit** I2C address. STM32 HAL functions usually expect the address shifted left by one bit, so the callback example below performs that shift internally.

### Power and reset

The AK09940A has separate analog and digital supplies. Use the supply ranges specified by the sensor datasheet and add local decoupling capacitors near the device.

After power-up or reset, the device enters power-down mode. The driver `begin()` function performs a soft reset, waits, verifies the Who-Am-I registers by default, and synchronizes local control-register shadow state.

## Driver design overview

The driver class is `akm::AK09940A`. It is constructed with:

1. The selected interface type: `SPI` or `I2C`.
2. A `BusCallbacks` structure containing platform-specific functions.
3. The I2C address, only used when I2C mode is selected.

The driver owns no hardware directly. It only calls the callbacks you provide. This keeps it portable across STM32 HAL, STM32 LL, Zephyr, FreeRTOS, bare-metal register drivers, or another MCU family.

The important callback groups are:

```cpp
struct BusCallbacks {
    void *context;

    bool (*i2c_write)(void *context, uint8_t address, uint8_t reg,
                      const uint8_t *data, size_t length);
    bool (*i2c_read)(void *context, uint8_t address, uint8_t reg,
                     uint8_t *data, size_t length);

    void (*spi_select)(void *context);
    void (*spi_deselect)(void *context);
    uint8_t (*spi_transfer)(void *context, uint8_t byte);

    void (*delay_us)(void *context, uint32_t microseconds);
};
```

For SPI mode, the driver sends an 8-bit register command followed by one or more data bytes. For I2C mode, it calls your `i2c_read` and `i2c_write` register-access callbacks.

The sample read path follows the AK09940A required read sequence by reading from `ST1` through `ST2` in one burst. Reading `ST2` at the end is important because it releases the sensor's protected measurement-data registers and clears overrun state as defined by the device behavior.

## Basic SPI example for STM32 HAL

This is a minimal blocking example. It is suitable as a starting point for bare-metal or RTOS tasks. Replace pin, port, SPI handle, and delay function names with your project names.

```cpp
#include "AK09940A.hpp"
#include "main.h"

extern SPI_HandleTypeDef hspi1;

struct Ak09940aSpiContext {
    SPI_HandleTypeDef *spi;
    GPIO_TypeDef *cs_port;
    uint16_t cs_pin;
};

static void ak09940a_spi_select(void *context) {
    auto *ctx = static_cast<Ak09940aSpiContext *>(context);
    HAL_GPIO_WritePin(ctx->cs_port, ctx->cs_pin, GPIO_PIN_RESET);
}

static void ak09940a_spi_deselect(void *context) {
    auto *ctx = static_cast<Ak09940aSpiContext *>(context);
    HAL_GPIO_WritePin(ctx->cs_port, ctx->cs_pin, GPIO_PIN_SET);
}

static uint8_t ak09940a_spi_transfer(void *context, uint8_t byte) {
    auto *ctx = static_cast<Ak09940aSpiContext *>(context);
    uint8_t rx = 0;
    HAL_SPI_TransmitReceive(ctx->spi, &byte, &rx, 1, HAL_MAX_DELAY);
    return rx;
}

static void ak09940a_delay_us(void *context, uint32_t us) {
    (void)context;

    // Replace with your board's microsecond delay.
    // For simple bring-up, rounding up to milliseconds is often acceptable,
    // but use a real us delay for precise timing and short polling intervals.
    HAL_Delay((us + 999U) / 1000U);
}

static Ak09940aSpiContext ak_ctx {
    &hspi1,
    AK09940A_CS_GPIO_Port,
    AK09940A_CS_Pin
};

static akm::AK09940A::BusCallbacks ak_bus {
    .context = &ak_ctx,
    .i2c_write = nullptr,
    .i2c_read = nullptr,
    .spi_select = ak09940a_spi_select,
    .spi_deselect = ak09940a_spi_deselect,
    .spi_transfer = ak09940a_spi_transfer,
    .delay_us = ak09940a_delay_us
};

akm::AK09940A mag(akm::AK09940A::Interface::SPI, ak_bus);

void app_init(void) {
    // Configure hspi1 as SPI mode 3 before calling begin():
    // hspi1.Init.CLKPolarity = SPI_POLARITY_HIGH;
    // hspi1.Init.CLKPhase    = SPI_PHASE_2EDGE;

    auto err = mag.begin(true);
    if (err != akm::AK09940A::Error::Ok) {
        // Handle bus failure or Who-Am-I mismatch.
    }
}
```

## Basic I2C example for STM32 HAL

```cpp
#include "AK09940A.hpp"
#include "main.h"

extern I2C_HandleTypeDef hi2c1;

struct Ak09940aI2cContext {
    I2C_HandleTypeDef *i2c;
};

static bool ak09940a_i2c_write(void *context, uint8_t address, uint8_t reg,
                               const uint8_t *data, size_t length) {
    auto *ctx = static_cast<Ak09940aI2cContext *>(context);
    return HAL_I2C_Mem_Write(ctx->i2c,
                             static_cast<uint16_t>(address << 1),
                             reg,
                             I2C_MEMADD_SIZE_8BIT,
                             const_cast<uint8_t *>(data),
                             static_cast<uint16_t>(length),
                             HAL_MAX_DELAY) == HAL_OK;
}

static bool ak09940a_i2c_read(void *context, uint8_t address, uint8_t reg,
                              uint8_t *data, size_t length) {
    auto *ctx = static_cast<Ak09940aI2cContext *>(context);
    return HAL_I2C_Mem_Read(ctx->i2c,
                            static_cast<uint16_t>(address << 1),
                            reg,
                            I2C_MEMADD_SIZE_8BIT,
                            data,
                            static_cast<uint16_t>(length),
                            HAL_MAX_DELAY) == HAL_OK;
}

static void ak09940a_delay_us(void *context, uint32_t us) {
    (void)context;
    HAL_Delay((us + 999U) / 1000U);
}

static Ak09940aI2cContext ak_i2c_ctx { &hi2c1 };

static akm::AK09940A::BusCallbacks ak_i2c_bus {
    .context = &ak_i2c_ctx,
    .i2c_write = ak09940a_i2c_write,
    .i2c_read = ak09940a_i2c_read,
    .spi_select = nullptr,
    .spi_deselect = nullptr,
    .spi_transfer = nullptr,
    .delay_us = ak09940a_delay_us
};

akm::AK09940A mag_i2c(
    akm::AK09940A::Interface::I2C,
    ak_i2c_bus,
    akm::AK09940A::kDefaultI2CAddress // 0x0C when CAD1=0 and CAD0=0
);
```

## Reading Who-Am-I

```cpp
akm::AK09940A::WhoAmI id;
auto err = mag.readWhoAmI(id);

if (err == akm::AK09940A::Error::Ok) {
    // Expected values:
    // id.company_id == 0x48
    // id.device_id  == 0xA3
}
```

`begin(true)` already performs this check. Use `begin(false)` if you need to skip ID verification during early board bring-up.

## Single measurement example

```cpp
akm::AK09940A::Sample sample;

auto err = mag.singleMeasurement();
if (err == akm::AK09940A::Error::Ok) {
    err = mag.waitForDataReady(10000, 500);
}
if (err == akm::AK09940A::Error::Ok) {
    err = mag.readSample(sample);
}

if (err == akm::AK09940A::Error::Ok) {
    float mx_uT = sample.x_uT;
    float my_uT = sample.y_uT;
    float mz_uT = sample.z_uT;
    float temp_c = sample.temperature_c;

    bool overrun = sample.status.data_overrun;
    bool invalid = sample.status.invalid;
}
```

A single measurement automatically returns the device to power-down mode after the measurement completes.

## Continuous measurement example

```cpp
// Optional: choose a drive mode before starting continuous measurement.
// LowPower1 is the reset/default drive mode.
mag.setDrive(akm::AK09940A::Drive::LowPower1);

// Start 100 Hz continuous measurement.
auto err = mag.startContinuous(akm::AK09940A::ContinuousRate::Hz100);

while (err == akm::AK09940A::Error::Ok) {
    err = mag.waitForDataReady(20000, 1000);
    if (err != akm::AK09940A::Error::Ok) {
        break;
    }

    akm::AK09940A::Sample sample;
    err = mag.readSample(sample);
    if (err != akm::AK09940A::Error::Ok) {
        break;
    }

    // Use sample.x_uT, sample.y_uT, sample.z_uT, sample.temperature_c.
    // Check sample.status.data_overrun if the application may miss samples.
}

mag.stopContinuous(); // Same as setPowerDown().
```

### Continuous-rate drive-mode restrictions

Some high continuous rates are only valid with certain sensor drive modes:

```text
10, 20, 50, 100, 200 Hz: all drive modes
400 Hz:                 LowPower1, LowPower2, or UltraLowPower
1000 Hz:                LowPower1 or UltraLowPower
2500 Hz:                UltraLowPower only
```

If the requested rate is not valid for the current drive mode, `startContinuous()` returns `Error::InvalidModeForDrive`.

## Using DRDY with an interrupt

The driver includes `waitForDataReady()` for polling. For lower latency or lower CPU usage, connect `DRDY/TRG` to an MCU interrupt input and call `readSample()` when your ISR or task is notified.

A common FreeRTOS pattern is:

1. Configure the DRDY pin as rising-edge EXTI.
2. In the EXTI ISR, notify a sensor task.
3. In the sensor task, call `readSample()`.
4. Keep all SPI/I2C transactions out of the ISR unless your platform explicitly supports them.

Example outline:

```cpp
void HAL_GPIO_EXTI_Callback(uint16_t pin) {
    if (pin == AK09940A_DRDY_Pin) {
        BaseType_t woke = pdFALSE;
        vTaskNotifyGiveFromISR(magTaskHandle, &woke);
        portYIELD_FROM_ISR(woke);
    }
}

void MagTask(void *) {
    mag.startContinuous(akm::AK09940A::ContinuousRate::Hz100);

    for (;;) {
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);

        akm::AK09940A::Sample sample;
        if (mag.readSample(sample) == akm::AK09940A::Error::Ok) {
            // Process sample.
        }
    }
}
```

## Temperature data

Temperature measurement is enabled by default after reset. The driver converts the raw 8-bit two's-complement temperature value with:

```text
Temperature in deg C = 30 - raw / 1.7
```

Use:

```cpp
akm::AK09940A::Sample sample;
mag.readSample(sample);
float temperature_c = sample.temperature_c;
```

To disable temperature measurement:

```cpp
mag.setTemperatureEnabled(false);
```

Change the temperature-enable setting only while the device is in power-down mode. The driver handles this by entering power-down before writing the setting.

## Power-down mode

To stop measurement and enter power-down:

```cpp
mag.setPowerDown();
```

or, when continuous mode is active:

```cpp
mag.stopContinuous();
```

The driver waits after power-down before changing modes, matching the AK09940A mode-transition timing requirement.

## Self-test example

```cpp
akm::AK09940A::SelfTestResult result;
auto err = mag.selfTest(result);

if (err == akm::AK09940A::Error::Ok) {
    if (result.passed) {
        // Sensor self-test is within the expected limits.
    } else {
        // Self-test completed but the measured values were outside limits.
    }
}
```

The helper switches to `LowNoise2`, starts self-test mode, waits for data-ready, reads the sample, and checks the datasheet criteria.

## External trigger mode

External trigger mode is available through:

```cpp
mag.startExternalTriggerMode();
```

This configures the `DRDY/TRG` pin as a trigger input and enters external trigger mode. Your board must drive the trigger signal according to the AK09940A timing requirements. The driver does not generate the trigger pulse; it only configures the sensor mode.

## Error handling

Most driver functions return `akm::AK09940A::Error`:

```cpp
enum class Error : uint8_t {
    Ok,
    InvalidArgument,
    BusError,
    Timeout,
    DeviceIdMismatch,
    InvalidModeForDrive
};
```

Typical causes:

```text
InvalidArgument       Missing callback, null pointer, invalid polling interval
BusError              Platform callback reported an SPI/I2C failure
Timeout               Data-ready did not assert before timeout
DeviceIdMismatch      Who-Am-I was not 0x48/0xA3
InvalidModeForDrive   Requested continuous rate is invalid for selected drive mode
```

## Build notes

The driver is plain C++ and should build in embedded projects using GCC, Clang, or ARM toolchains. A typical compile command is:

```sh
arm-none-eabi-g++ -std=c++17 -ffreestanding -fno-exceptions -fno-rtti \
  -I./Drivers/AK09940A \
  -c AK09940A.cpp
```

The driver itself does not require exceptions or RTTI. It also does not allocate memory dynamically.

## STM32CubeMX checklist

For SPI projects:

- Configure SPI as master.
- Set clock polarity high.
- Set clock phase second edge.
- Use 8-bit data size.
- Use software-controlled chip-select GPIO, not automatic NSS, unless your board support package wraps it correctly.
- Set the AK09940A `CSB` pin high when idle.
- Connect `CAD0` and `CAD1` to ground for SPI.
- Optionally configure `DRDY/TRG` as an interrupt input.

For I2C projects:

- Tie `CSB` high.
- Configure I2C standard mode or fast mode.
- Add appropriate pull-up resistors on SCL and SDA.
- Pass the 7-bit AK09940A address to the driver.
- Shift the address left by one only inside STM32 HAL callback calls.

## Units and data format

Magnetic measurement data is signed 18-bit two's-complement data. The typical sensitivity is:

```text
10 nT/LSB = 0.01 uT/LSB
```

The driver returns:

```cpp
RawSample::x, y, z       // signed raw LSB counts
Sample::x_uT, y_uT, z_uT // converted microtesla values
```

Temperature is read from the `TMPS` register as a signed 8-bit value and converted to degrees Celsius.

## Limitations

- FIFO configuration is not exposed as a public API yet, although FIFO status fields are decoded when present in `ST1` and `ST2`.
- The driver uses blocking callback semantics. For DMA or fully asynchronous SPI/I2C, wrap the callbacks so they wait for transaction completion or adapt the class to your scheduler.
- External trigger pulse generation is application-specific and is not handled by the driver.
