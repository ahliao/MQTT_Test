# Protobuf Overview

## What Protobuf Is

Protocol Buffers, usually called protobuf, is a way to define structured messages in a schema file and serialize those messages into compact binary data.

In this project, protobuf is the message format carried inside MQTT payloads.

MQTT answers this question:

```text
How do messages move between services?
```

Protobuf answers this question:

```text
What does each message contain, and how is it encoded?
```

## Basic Flow

The project will define messages in a `.proto` file:

```proto
syntax = "proto3";

message AdcReading {
  string sensor_id = 1;
  int64 timestamp_ms = 2;
  uint32 channel = 3;
  uint32 raw_value = 4;
  double voltage = 5;
}
```

Then Python code is generated from that schema.

The sensor service creates a Python `AdcReading` object, fills in its fields, serializes it to bytes, and publishes those bytes over MQTT.

The processor service receives the MQTT payload bytes, parses them back into an `AdcReading`, processes the data, then publishes a different protobuf message.

## Why Generated Code Exists

The `.proto` file is the source of truth. The generated Python file is a convenience layer that gives Python classes for those messages.

Conceptually:

```text
proto/sensor_platform.proto
        |
        v
generated Python code
        |
        v
normal Python imports used by sensor, processor, and monitor
```

Generated code should usually not be edited by hand. If the schema changes, regenerate the Python code.

## Why the Numbers Matter

Each protobuf field has a number:

```proto
double voltage = 5;
```

The number `5` is not just decoration. It is the field identifier used in the binary encoding.

Once messages are in use, field numbers should be treated carefully. Renaming a field is usually safe for the binary format, but changing or reusing field numbers can break compatibility.

## Pros of Protobuf

- Compact payloads: protobuf is usually smaller than JSON because it uses a binary format.
- Explicit schema: producers and consumers agree on message structure.
- Typed fields: values such as integers, floating-point numbers, strings, and booleans are defined clearly.
- Good for multi-language systems: the same `.proto` file can generate code for Python, C++, Go, Java, and other languages.
- Good MQTT fit: MQTT payloads are bytes, and protobuf produces bytes naturally.
- Safer evolution than ad hoc formats: fields can be added over time if field numbers are managed correctly.

## Cons of Protobuf

- Less human-readable on the wire: MQTT payloads are binary, not plain text.
- Requires code generation: the `.proto` file must be compiled into Python code.
- Adds tooling: developers need protobuf compiler tooling such as `grpcio-tools`.
- Debugging needs helpers: inspecting a raw MQTT payload is harder than reading JSON.
- Schema discipline matters: careless field-number changes can cause compatibility problems.

## Protobuf vs JSON

JSON is often the simplest option for early prototypes.

JSON advantages:

- Human-readable
- No code generation
- Built into Python with the `json` module
- Easy to inspect with command-line tools

JSON disadvantages:

- Larger payloads
- No enforced schema by default
- Numeric types can be less precise across languages
- Producers and consumers can drift unless validation is added

Use JSON when readability and simplicity matter more than compactness and schema enforcement.

Use protobuf when message structure, compact payloads, and cross-language compatibility matter.

## Protobuf vs MessagePack

MessagePack is a compact binary serialization format that feels like binary JSON.

MessagePack advantages:

- Smaller than JSON
- No required schema
- Easier to adopt quickly than protobuf in some projects

MessagePack disadvantages:

- No built-in schema contract
- Less explicit than protobuf for long-lived systems
- Cross-service compatibility depends on documentation and discipline

Use MessagePack when you want compact binary messages but do not want schema generation.

Use protobuf when the schema itself is part of the learning goal or system design.

## Protobuf vs Plain CSV or Text

Plain text formats are useful for logs, simple files, and manual debugging.

Advantages:

- Very easy to read
- Easy to produce manually
- Good for simple one-off data

Disadvantages:

- Fragile parsing
- Weak typing
- Poor fit for nested or evolving message structures
- Easy for producer and consumer assumptions to drift

For this project, plain text would make MQTT easier to inspect, but it would not teach typed message contracts as well as protobuf.

## Recommendation for This Project

Use protobuf for the MQTT payloads because one goal is to learn how real sensor platforms define and exchange typed messages.

To keep the project approachable:

- Keep the first schema small.
- Generate protobuf files automatically.
- Add helper functions for serialization and deserialization.
- Print decoded values in the CLI monitor so the binary format is still easy to observe.
