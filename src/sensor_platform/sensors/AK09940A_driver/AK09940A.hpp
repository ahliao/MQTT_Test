#pragma once

#include <cstddef>
#include <cstdint>

namespace akm {

class AK09940A {
public:
    enum class Interface : uint8_t { I2C, SPI };

    enum class Error : uint8_t {
        Ok = 0,
        InvalidArgument,
        BusError,
        Timeout,
        DeviceIdMismatch,
        InvalidModeForDrive
    };

    enum class Drive : uint8_t {
        LowPower1,       // MT2=0, MT[1:0]=00. Default.
        LowPower2,       // MT2=0, MT[1:0]=01
        LowNoise1,       // MT2=0, MT[1:0]=10
        LowNoise2,       // MT2=0, MT[1:0]=11
        UltraLowPower    // MT2=1, MT[1:0] ignored by device
    };

    enum class ContinuousRate : uint16_t {
        Hz10   = 10,
        Hz20   = 20,
        Hz50   = 50,
        Hz100  = 100,
        Hz200  = 200,
        Hz400  = 400,
        Hz1000 = 1000,
        Hz2500 = 2500
    };

    struct BusCallbacks {
        void *context = nullptr;

        // I2C register operations. Address is the 7-bit target address, normally 0x0C..0x0F.
        bool (*i2c_write)(void *context, uint8_t address, uint8_t reg, const uint8_t *data, size_t length) = nullptr;
        bool (*i2c_read)(void *context, uint8_t address, uint8_t reg, uint8_t *data, size_t length) = nullptr;

        // SPI byte transfer plus chip-select hooks. SPI must be configured mode 3.
        void (*spi_select)(void *context) = nullptr;
        void (*spi_deselect)(void *context) = nullptr;
        uint8_t (*spi_transfer)(void *context, uint8_t byte) = nullptr;

        // Required for safe mode transitions and polling timeouts.
        void (*delay_us)(void *context, uint32_t microseconds) = nullptr;
    };

    struct WhoAmI {
        uint8_t company_id = 0; // Expected 0x48.
        uint8_t device_id = 0;  // Expected 0xA3.
    };

    struct Status {
        bool data_ready = false;
        bool data_overrun = false;
        bool invalid = false;
        uint8_t fifo_count = 0;
    };

    struct RawSample {
        int32_t x = 0;       // signed 18-bit LSB count
        int32_t y = 0;       // signed 18-bit LSB count
        int32_t z = 0;       // signed 18-bit LSB count
        int8_t temperature_raw = 0;
        Status status;
    };

    struct Sample {
        float x_uT = 0.0f;
        float y_uT = 0.0f;
        float z_uT = 0.0f;
        float temperature_c = 0.0f;
        Status status;
    };

    struct SelfTestResult {
        RawSample raw;
        bool passed = false;
    };

    static constexpr uint8_t kDefaultI2CAddress = 0x0C;
    static constexpr uint8_t kCompanyId = 0x48;
    static constexpr uint8_t kDeviceId = 0xA3;
    static constexpr float kMicroTeslaPerLsb = 0.01f; // 10 nT/LSB = 0.01 uT/LSB.

    AK09940A(Interface iface, BusCallbacks callbacks, uint8_t i2c_address = kDefaultI2CAddress);

    Error begin(bool verify_id = true);
    Error softReset();
    Error readWhoAmI(WhoAmI &id);

    Error setPowerDown();
    Error setDrive(Drive drive);
    Drive drive() const { return drive_; }

    // TEM defaults enabled after reset. Set while in power-down mode.
    Error setTemperatureEnabled(bool enabled);

    Error singleMeasurement();
    Error startContinuous(ContinuousRate rate);
    Error stopContinuous() { return setPowerDown(); }

    // External-trigger support is optional for applications but included here.
    Error startExternalTriggerMode();
    Error selfTest(SelfTestResult &result, uint32_t timeout_us = 10000);

    Error readStatus(Status &status);
    Error readRawSample(RawSample &sample);
    Error readSample(Sample &sample);

    Error waitForDataReady(uint32_t timeout_us, uint32_t poll_interval_us = 1000);

    static float rawTemperatureToCelsius(int8_t raw) { return 30.0f - (static_cast<float>(raw) / 1.7f); }
    static float rawMagToMicroTesla(int32_t raw) { return static_cast<float>(raw) * kMicroTeslaPerLsb; }

private:
    enum Register : uint8_t {
        REG_WIA1   = 0x00,
        REG_WIA2   = 0x01,
        REG_ST     = 0x0F,
        REG_ST1    = 0x10,
        REG_HXL    = 0x11,
        REG_TMPS   = 0x1A,
        REG_ST2    = 0x1B,
        REG_CNTL1  = 0x30,
        REG_CNTL2  = 0x31,
        REG_CNTL3  = 0x32,
        REG_CNTL4  = 0x33,
        REG_I2CDIS = 0x36
    };

    enum Mode : uint8_t {
        MODE_POWER_DOWN = 0x00,
        MODE_SINGLE = 0x01,
        MODE_CONT_10HZ = 0x02,
        MODE_CONT_20HZ = 0x04,
        MODE_CONT_50HZ = 0x06,
        MODE_CONT_100HZ = 0x08,
        MODE_CONT_200HZ = 0x0A,
        MODE_CONT_400HZ = 0x0C,
        MODE_CONT_1000HZ = 0x0E,
        MODE_CONT_2500HZ = 0x0F,
        MODE_SELF_TEST = 0x10,
        MODE_EXTERNAL_TRIGGER = 0x18
    };

    static constexpr uint8_t CNTL1_MT2 = 0x80;
    static constexpr uint8_t CNTL1_DTSET = 0x20;
    static constexpr uint8_t CNTL2_TEM = 0x40;
    static constexpr uint8_t CNTL3_FIFO = 0x80;
    static constexpr uint8_t CNTL3_MT1 = 0x40;
    static constexpr uint8_t CNTL3_MT0 = 0x20;
    static constexpr uint8_t CNTL3_MODE_MASK = 0x1F;
    static constexpr uint8_t CNTL4_SRST = 0x01;
    static constexpr uint8_t ST_DRDY = 0x01;
    static constexpr uint8_t ST_DOR = 0x02;
    static constexpr uint8_t ST2_DOR = 0x01;
    static constexpr uint8_t ST2_INV = 0x02;

    Error readRegister(uint8_t reg, uint8_t &value);
    Error readRegisters(uint8_t reg, uint8_t *data, size_t length);
    Error writeRegister(uint8_t reg, uint8_t value);
    void delayUs(uint32_t us);
    Error setMode(Mode mode);
    Error syncControlShadows();
    static int32_t signExtend18(uint32_t value);
    static Mode rateToMode(ContinuousRate rate);
    bool isRateAllowed(ContinuousRate rate) const;

    Interface interface_;
    BusCallbacks cb_;
    uint8_t i2c_address_;
    Drive drive_ = Drive::LowPower1;
    uint8_t cntl1_ = 0x00;
    uint8_t cntl2_ = CNTL2_TEM;
    uint8_t cntl3_ = 0x00;
};

} // namespace akm

