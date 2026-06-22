#include "AK09940A.hpp"

namespace akm {

AK09940A::AK09940A(Interface iface, BusCallbacks callbacks, uint8_t i2c_address)
    : interface_(iface), cb_(callbacks), i2c_address_(i2c_address) {}

AK09940A::Error AK09940A::begin(bool verify_id) {
    Error err = softReset();
    if (err != Error::Ok) {
        return err;
    }

    delayUs(100); // Datasheet Twait before mode setting after reset/power-down.

    cntl1_ = 0x00;
    cntl2_ = CNTL2_TEM;
    cntl3_ = 0x00;
    drive_ = Drive::LowPower1;

    if (verify_id) {
        WhoAmI id;
        err = readWhoAmI(id);
        if (err != Error::Ok) {
            return err;
        }
        if (id.company_id != kCompanyId || id.device_id != kDeviceId) {
            return Error::DeviceIdMismatch;
        }
    }

    return syncControlShadows();
}

AK09940A::Error AK09940A::softReset() {
    Error err = writeRegister(REG_CNTL4, CNTL4_SRST);
    if (err != Error::Ok) {
        return err;
    }
    delayUs(100);
    return Error::Ok;
}

AK09940A::Error AK09940A::readWhoAmI(WhoAmI &id) {
    uint8_t buf[2] = {0, 0};
    Error err = readRegisters(REG_WIA1, buf, sizeof(buf));
    if (err != Error::Ok) {
        return err;
    }
    id.company_id = buf[0];
    id.device_id = buf[1];
    return Error::Ok;
}

AK09940A::Error AK09940A::setPowerDown() {
    Error err = readRegister(REG_CNTL3, cntl3_);
    if (err != Error::Ok) {
        return err;
    }
    cntl3_ = static_cast<uint8_t>(cntl3_ & ~CNTL3_MODE_MASK);
    err = writeRegister(REG_CNTL3, cntl3_);
    if (err == Error::Ok) {
        delayUs(100); // Twait before a following mode change.
    }
    return err;
}

AK09940A::Error AK09940A::setDrive(Drive drive) {
    Error err = setPowerDown();
    if (err != Error::Ok) {
        return err;
    }

    err = syncControlShadows();
    if (err != Error::Ok) {
        return err;
    }

    uint8_t new_cntl1 = static_cast<uint8_t>(cntl1_ & ~CNTL1_MT2);
    uint8_t new_cntl3 = static_cast<uint8_t>(cntl3_ & ~(CNTL3_MT1 | CNTL3_MT0 | CNTL3_MODE_MASK));

    switch (drive) {
    case Drive::LowPower1:
        break;
    case Drive::LowPower2:
        new_cntl3 |= CNTL3_MT0;
        break;
    case Drive::LowNoise1:
        new_cntl3 |= CNTL3_MT1;
        break;
    case Drive::LowNoise2:
        new_cntl3 |= (CNTL3_MT1 | CNTL3_MT0);
        break;
    case Drive::UltraLowPower:
        new_cntl1 |= CNTL1_MT2;
        break;
    default:
        return Error::InvalidArgument;
    }

    err = writeRegister(REG_CNTL1, new_cntl1);
    if (err != Error::Ok) {
        return err;
    }
    err = writeRegister(REG_CNTL3, new_cntl3);
    if (err != Error::Ok) {
        return err;
    }

    cntl1_ = new_cntl1;
    cntl3_ = new_cntl3;
    drive_ = drive;
    return Error::Ok;
}

AK09940A::Error AK09940A::setTemperatureEnabled(bool enabled) {
    Error err = setPowerDown();
    if (err != Error::Ok) {
        return err;
    }

    err = readRegister(REG_CNTL2, cntl2_);
    if (err != Error::Ok) {
        return err;
    }

    if (enabled) {
        cntl2_ |= CNTL2_TEM;
    } else {
        cntl2_ &= static_cast<uint8_t>(~CNTL2_TEM);
    }
    return writeRegister(REG_CNTL2, cntl2_);
}

AK09940A::Error AK09940A::singleMeasurement() {
    return setMode(MODE_SINGLE);
}

AK09940A::Error AK09940A::startContinuous(ContinuousRate rate) {
    if (!isRateAllowed(rate)) {
        return Error::InvalidModeForDrive;
    }
    return setMode(rateToMode(rate));
}

AK09940A::Error AK09940A::startExternalTriggerMode() {
    Error err = setPowerDown();
    if (err != Error::Ok) {
        return err;
    }

    err = readRegister(REG_CNTL1, cntl1_);
    if (err != Error::Ok) {
        return err;
    }
    cntl1_ |= CNTL1_DTSET;
    err = writeRegister(REG_CNTL1, cntl1_);
    if (err != Error::Ok) {
        return err;
    }
    delayUs(300); // tPCON stabilization before trigger use.
    return setMode(MODE_EXTERNAL_TRIGGER);
}

AK09940A::Error AK09940A::selfTest(SelfTestResult &result, uint32_t timeout_us) {
    Error err = setDrive(Drive::LowNoise2);
    if (err != Error::Ok) {
        return err;
    }

    err = setMode(MODE_SELF_TEST);
    if (err != Error::Ok) {
        return err;
    }

    err = waitForDataReady(timeout_us);
    if (err != Error::Ok) {
        return err;
    }

    err = readRawSample(result.raw);
    if (err != Error::Ok) {
        return err;
    }

    result.passed = (result.raw.x >= -1200 && result.raw.x <= -300) &&
                    (result.raw.y >= 300 && result.raw.y <= 1200) &&
                    (result.raw.z >= -1600 && result.raw.z <= -400);
    return Error::Ok;
}

AK09940A::Error AK09940A::readStatus(Status &status) {
    uint8_t st = 0;
    Error err = readRegister(REG_ST, st);
    if (err != Error::Ok) {
        return err;
    }
    status.data_ready = (st & ST_DRDY) != 0;
    status.data_overrun = (st & ST_DOR) != 0;
    status.invalid = false;
    status.fifo_count = 0;
    return Error::Ok;
}

AK09940A::Error AK09940A::readRawSample(RawSample &sample) {
    // Read ST1 through ST2 in one transaction. This follows the required data-read sequence and
    // releases protected data by reading ST2 at the end.
    uint8_t buf[12] = {0};
    Error err = readRegisters(REG_ST1, buf, sizeof(buf));
    if (err != Error::Ok) {
        return err;
    }

    const uint8_t st1 = buf[0];
    const uint8_t *d = &buf[1];
    const uint8_t st2 = buf[11];

    uint32_t x = static_cast<uint32_t>(d[0]) | (static_cast<uint32_t>(d[1]) << 8) |
                 ((static_cast<uint32_t>(d[2]) & 0x03u) << 16);
    uint32_t y = static_cast<uint32_t>(d[3]) | (static_cast<uint32_t>(d[4]) << 8) |
                 ((static_cast<uint32_t>(d[5]) & 0x03u) << 16);
    uint32_t z = static_cast<uint32_t>(d[6]) | (static_cast<uint32_t>(d[7]) << 8) |
                 ((static_cast<uint32_t>(d[8]) & 0x03u) << 16);

    sample.x = signExtend18(x);
    sample.y = signExtend18(y);
    sample.z = signExtend18(z);
    sample.temperature_raw = static_cast<int8_t>(d[9]);
    sample.status.data_ready = (st1 & ST_DRDY) != 0;
    sample.status.fifo_count = static_cast<uint8_t>((st1 >> 1) & 0x0F);
    sample.status.data_overrun = (st2 & ST2_DOR) != 0;
    sample.status.invalid = (st2 & ST2_INV) != 0;
    return Error::Ok;
}

AK09940A::Error AK09940A::readSample(Sample &sample) {
    RawSample raw;
    Error err = readRawSample(raw);
    if (err != Error::Ok) {
        return err;
    }
    sample.x_uT = rawMagToMicroTesla(raw.x);
    sample.y_uT = rawMagToMicroTesla(raw.y);
    sample.z_uT = rawMagToMicroTesla(raw.z);
    sample.temperature_c = rawTemperatureToCelsius(raw.temperature_raw);
    sample.status = raw.status;
    return Error::Ok;
}

AK09940A::Error AK09940A::waitForDataReady(uint32_t timeout_us, uint32_t poll_interval_us) {
    if (poll_interval_us == 0) {
        return Error::InvalidArgument;
    }

    uint32_t elapsed = 0;
    while (elapsed <= timeout_us) {
        Status status;
        Error err = readStatus(status);
        if (err != Error::Ok) {
            return err;
        }
        if (status.data_ready) {
            return Error::Ok;
        }
        delayUs(poll_interval_us);
        elapsed += poll_interval_us;
    }
    return Error::Timeout;
}

AK09940A::Error AK09940A::readRegister(uint8_t reg, uint8_t &value) {
    return readRegisters(reg, &value, 1);
}

AK09940A::Error AK09940A::readRegisters(uint8_t reg, uint8_t *data, size_t length) {
    if (data == nullptr || length == 0) {
        return Error::InvalidArgument;
    }

    if (interface_ == Interface::I2C) {
        if (cb_.i2c_read == nullptr) {
            return Error::InvalidArgument;
        }
        return cb_.i2c_read(cb_.context, i2c_address_, reg, data, length) ? Error::Ok : Error::BusError;
    }

    if (cb_.spi_select == nullptr || cb_.spi_deselect == nullptr || cb_.spi_transfer == nullptr) {
        return Error::InvalidArgument;
    }

    cb_.spi_select(cb_.context);
    cb_.spi_transfer(cb_.context, static_cast<uint8_t>(0x80u | (reg & 0x7Fu)));
    for (size_t i = 0; i < length; ++i) {
        data[i] = cb_.spi_transfer(cb_.context, 0x00);
    }
    cb_.spi_deselect(cb_.context);
    return Error::Ok;
}

AK09940A::Error AK09940A::writeRegister(uint8_t reg, uint8_t value) {
    if (interface_ == Interface::I2C) {
        if (cb_.i2c_write == nullptr) {
            return Error::InvalidArgument;
        }
        return cb_.i2c_write(cb_.context, i2c_address_, reg, &value, 1) ? Error::Ok : Error::BusError;
    }

    if (cb_.spi_select == nullptr || cb_.spi_deselect == nullptr || cb_.spi_transfer == nullptr) {
        return Error::InvalidArgument;
    }

    cb_.spi_select(cb_.context);
    cb_.spi_transfer(cb_.context, static_cast<uint8_t>(reg & 0x7Fu));
    cb_.spi_transfer(cb_.context, value);
    cb_.spi_deselect(cb_.context);
    return Error::Ok;
}

void AK09940A::delayUs(uint32_t us) {
    if (cb_.delay_us != nullptr) {
        cb_.delay_us(cb_.context, us);
    }
}

AK09940A::Error AK09940A::setMode(Mode mode) {
    Error err = setPowerDown();
    if (err != Error::Ok) {
        return err;
    }

    err = readRegister(REG_CNTL3, cntl3_);
    if (err != Error::Ok) {
        return err;
    }
    cntl3_ = static_cast<uint8_t>((cntl3_ & ~CNTL3_MODE_MASK) | (static_cast<uint8_t>(mode) & CNTL3_MODE_MASK));
    return writeRegister(REG_CNTL3, cntl3_);
}

AK09940A::Error AK09940A::syncControlShadows() {
    Error err = readRegister(REG_CNTL1, cntl1_);
    if (err != Error::Ok) {
        return err;
    }
    err = readRegister(REG_CNTL2, cntl2_);
    if (err != Error::Ok) {
        return err;
    }
    err = readRegister(REG_CNTL3, cntl3_);
    if (err != Error::Ok) {
        return err;
    }

    if ((cntl1_ & CNTL1_MT2) != 0) {
        drive_ = Drive::UltraLowPower;
    } else {
        switch (cntl3_ & (CNTL3_MT1 | CNTL3_MT0)) {
        case 0x00:
            drive_ = Drive::LowPower1;
            break;
        case CNTL3_MT0:
            drive_ = Drive::LowPower2;
            break;
        case CNTL3_MT1:
            drive_ = Drive::LowNoise1;
            break;
        default:
            drive_ = Drive::LowNoise2;
            break;
        }
    }
    return Error::Ok;
}

int32_t AK09940A::signExtend18(uint32_t value) {
    value &= 0x3FFFFu;
    if ((value & 0x20000u) != 0) {
        return static_cast<int32_t>(value | 0xFFFC0000u);
    }
    return static_cast<int32_t>(value);
}

AK09940A::Mode AK09940A::rateToMode(ContinuousRate rate) {
    switch (rate) {
    case ContinuousRate::Hz10:
        return MODE_CONT_10HZ;
    case ContinuousRate::Hz20:
        return MODE_CONT_20HZ;
    case ContinuousRate::Hz50:
        return MODE_CONT_50HZ;
    case ContinuousRate::Hz100:
        return MODE_CONT_100HZ;
    case ContinuousRate::Hz200:
        return MODE_CONT_200HZ;
    case ContinuousRate::Hz400:
        return MODE_CONT_400HZ;
    case ContinuousRate::Hz1000:
        return MODE_CONT_1000HZ;
    case ContinuousRate::Hz2500:
        return MODE_CONT_2500HZ;
    default:
        return MODE_POWER_DOWN;
    }
}

bool AK09940A::isRateAllowed(ContinuousRate rate) const {
    switch (rate) {
    case ContinuousRate::Hz10:
    case ContinuousRate::Hz20:
    case ContinuousRate::Hz50:
    case ContinuousRate::Hz100:
    case ContinuousRate::Hz200:
        return true;
    case ContinuousRate::Hz400:
        return drive_ == Drive::LowPower1 || drive_ == Drive::LowPower2 || drive_ == Drive::UltraLowPower;
    case ContinuousRate::Hz1000:
        return drive_ == Drive::LowPower1 || drive_ == Drive::UltraLowPower;
    case ContinuousRate::Hz2500:
        return drive_ == Drive::UltraLowPower;
    default:
        return false;
    }
}

} // namespace akm

