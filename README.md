# kegerator-esp32-display

ESP32 source code for the display on my kegerator: a 4" touch screen that shows how much beer is left in each keg, and follows a pour live as it happens.

It reads the kegs' weights straight from the ESP32 keg scales over the local network, so it works with or without Home Assistant. If Home Assistant is running, the display shows up there as an ESPHome device too.

- **Status:** early. The overview screen works: the left, center and right taps and the CO2 tank. The scales work out gallons themselves, and the display reads them through Home Assistant for now. There's no pour screen yet. The full design is in [docs/DESIGN.md](docs/DESIGN.md).
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

## The scales

The keg and CO2 scales are ESPHome devices too (a XIAO ESP32-C3 and an HX711 load cell amplifier each), and their firmware is in this repo:

| File | What it is |
|---|---|
| `kegerator-scale-keg-1.yaml` | Keg 1's scale, on the left tap |
| `kegerator-scale-co2.yaml` | The CO2 tank's scale |
| `scales/common.yaml` | What every scale has: the load cell, the weight, Tare |
| `scales/keg.yaml` | A keg scale's gallons and percent |
| `scales/co2.yaml` | The CO2 scale's gas left and percent |

Each scale reports to Home Assistant once a minute: the weight, and either the gallons and percent left in the keg or the gas left in the tank. Build and flash a scale the same way as the display:

```bash
.venv/bin/esphome run kegerator-scale-keg-1.yaml
```

## Settings

On each **keg scale** (its device page in Home Assistant):

| Setting | What it's for |
|---|---|
| Empty keg weight | The empty keg shell plus any hose weight resting on the scale. Gallons left = (weight − this) ÷ 8.42 lb per gallon. Every keg is a sixtel (5.16 gal) |

On the **CO2 scale**:

| Setting | What it's for |
|---|---|
| Tank empty weight | The tank's tare weight, stamped "TW" on its collar |
| Tank size | How much gas the tank holds full, in lb |

On the **display**, at http://kegerator-display.local or its device page in Home Assistant:

| Setting | What it's for |
|---|---|
| Left / Center / Right beer name, beer style | Shown on each tap's card |

Settings are kept through a power cut. Which scale feeds which tap is set in the display's `sensor:` section. The low-keg warning level and the colors are `substitutions` at the top of `kegerator-display.yaml`.

## Building it in Home Assistant's ESPHome Builder instead

Make a new device in the Builder and replace its YAML with this, which pulls the config from this repo:

```yaml
packages:
  kegerator_display: github://mattlyle/kegerator-esp32-display/kegerator-display.yaml@main
```

The Builder's own `secrets.yaml` needs the same names as [secrets.example.yaml](secrets.example.yaml).

## License

MIT, see [LICENSE](LICENSE).
