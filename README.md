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

Home Assistant finds it on the network as a new ESPHome device. Adopt it and enter its api key from `secrets.yaml` (`kegerator_display_api_key` for the display).

## The scales

The keg and CO2 scales are ESPHome devices too (a XIAO ESP32-C3 and an HX711 load cell amplifier each), and their firmware is in this repo:

| File | What it is |
|---|---|
| `kegerator-scale-keg-1.yaml` | Keg 1's scale, on the left tap |
| `kegerator-scale-keg-2.yaml`, `kegerator-scale-keg-3.yaml` | Keg 2's and keg 3's scales (not built yet; calibration still to do) |
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

## Artwork

The keg and the beer bubbles background are drawn by [tools/make_art.py](tools/make_art.py) into `images/`. To change them, edit the script and run it, then rebuild:

```bash
.venv/bin/python tools/make_art.py
```

To try the other backgrounds (brushed steel, dark wood, chalkboard, slate, brushed copper, diamond plate, carbon fiber, hops, honeycomb), draw them all into `images/options/`, which isn't committed:

```bash
.venv/bin/python tools/make_art.py --all
```

To switch, set `USED_TEXTURE` in the script, run it, and point the `background_texture` image in `kegerator-display.yaml` at the new file.

## Building it in Home Assistant's ESPHome Builder

This is how the devices are normally built and updated: Home Assistant's ESPHome Builder pulls the config from this repo on GitHub, builds it, and sends it to the device over Wi-Fi. Building from a computer (above) is for debugging, or for a first flash over USB.

Each device has a short file in [builder/](builder/) that points the Builder at its config here. The Builder keeps its own copy; these are the originals.

| Device | Builder file | Its config |
|---|---|---|
| Display | `builder/kegerator-display.yaml` | `kegerator-display.yaml` |
| Keg 1 scale | `builder/kegerator-scale-keg-1.yaml` | `kegerator-scale-keg-1.yaml` |
| Keg 2 scale | `builder/kegerator-scale-keg-2.yaml` | `kegerator-scale-keg-2.yaml` |
| Keg 3 scale | `builder/kegerator-scale-keg-3.yaml` | `kegerator-scale-keg-3.yaml` |
| CO2 scale | `builder/kegerator-scale-co2.yaml` | `kegerator-scale-co2.yaml` |

The Builder's `secrets.yaml` (in Home Assistant at `/config/esphome/secrets.yaml`) needs the same names as [secrets.example.yaml](secrets.example.yaml): the Wi-Fi details and each device's api key.

**Updating a device:** commit and push the change, then press **Install → Wirelessly** on the device in the Builder. Each install pulls the latest from `main`.

**Adding a new scale** (keg 2 or 3):

1. Its key: add `kegerator_scale_keg_2_api_key` to the Builder's `secrets.yaml`, with a new key from `openssl rand -base64 32`, and the same line to your local `secrets.yaml`.
2. In the Builder, make a new device named `kegerator-scale-keg-2` and replace its YAML with [builder/kegerator-scale-keg-2.yaml](builder/kegerator-scale-keg-2.yaml).
3. Flash it once over USB, from the Builder (**Install → Plug into this computer**) or with `esphome run` here. A brand new board can't be updated over Wi-Fi yet.
4. Add it in Home Assistant (it shows up as discovered) with its api key.
5. Calibrate it: Tare the empty plate, put a known weight on it, and work out its `cal_` numbers in `kegerator-scale-keg-2.yaml` the way keg 1's were. Push and install again.
6. Point a tap at it: in `kegerator-display.yaml`, swap that tap's two template sensors in the `sensor:` section for `homeassistant` sensors reading the new scale's Gallons left and Percent full, like the left tap's.

## License

MIT, see [LICENSE](LICENSE).
