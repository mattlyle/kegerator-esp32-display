# kegerator-esp32-display

ESP32 source code for the display on my kegerator: a 4" touch screen that shows how much beer is left in each keg, and follows a pour live as it happens.

It reads the kegs' weights straight from the ESP32 keg scales over the local network, so it works with or without Home Assistant. If Home Assistant is running, the display shows up there as an ESPHome device too.

- **Status:** early. The config in this repo is the first play-around version (a CO2 readout, a backlight slider, touch logging). The full design is in [docs/DESIGN.md](docs/DESIGN.md).
- **Mockups:** https://claude.ai/artifact/8hP9J5qWfZdYY6RTtP8vyb

## Hardware

A Hosyond 4.0" 320x480 ESP32 touch display (Amazon B0FGJJ24S1), which is the LCDWiki **E32R40T** board: an ESP32-WROOM-32E, an ST7796S screen and XPT2046 resistive touch. Pins and board details are in [docs/hardware.md](docs/hardware.md).

## Building it

It's an [ESPHome](https://esphome.io) project, built and flashed from a computer with the ESPHome command line.

### One-time setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp secrets.example.yaml secrets.yaml
```

Then fill in `secrets.yaml` with your Wi-Fi details and a new API key (`openssl rand -base64 32`). It's in `.gitignore`, so it never gets committed.

### First flash, over USB

Plug the display into the computer with a USB-C cable and run:

```bash
.venv/bin/esphome run kegerator-display.yaml
```

Pick the USB port when it asks. If it can't connect, hold the board's BOOT button while plugging it in.

### Every flash after that, over Wi-Fi

The same command again. This time pick the network option, and it compiles, sends the new firmware over Wi-Fi, and then shows the display's logs.

```bash
.venv/bin/esphome run kegerator-display.yaml
```

To just watch the logs: `.venv/bin/esphome logs kegerator-display.yaml`

### Adding it to Home Assistant

Home Assistant finds it on the network as a new ESPHome device. Adopt it and enter the `api_encryption_key` from `secrets.yaml`.

## Building it in Home Assistant's ESPHome Builder instead

Make a new device in the Builder and replace its YAML with this, which pulls the config from this repo:

```yaml
packages:
  kegerator_display: github://mattlyle/kegerator-esp32-display/kegerator-display.yaml@main
```

The Builder's own `secrets.yaml` needs the same names as [secrets.example.yaml](secrets.example.yaml).

## License

MIT, see [LICENSE](LICENSE).
