# Hosyond 4.0" ESP32 touch display

Amazon B0FGJJ24S1. The plan for the kegerator display built on it is in [DESIGN.md](DESIGN.md). It is the LCDWiki **E32R40T** board under another brand (E32N40T is the same board without touch).

## What's on the board

| Part | Detail |
|---|---|
| MCU | ESP32-WROOM-32E: dual-core 240 MHz, 520 KB SRAM, 4 MB flash, **no PSRAM**, Wi-Fi + Bluetooth |
| Screen | 4.0" TFT, 320x480, ST7796S driver, 4-wire SPI |
| Touch | Resistive (use the stylus), XPT2046 controller, on the same SPI bus as the screen |
| Extras | microSD slot, RGB LED, speaker amp + connector, battery connector with voltage sense, BOOT and RESET buttons |
| Power | USB-C, 5 V |

## Pin map

From table 2.1 of the LCDWiki *E32R40T & E32N40T Arduino Demo Instructions* PDF.

| Function | GPIO | Notes |
|---|---|---|
| SPI SCK / MOSI / MISO | 14 / 13 / 12 | Shared by the screen and touch |
| Screen CS | 15 | |
| Screen DC (RS) | 2 | |
| Screen reset | EN | Tied to the ESP32 reset, so there's no reset pin to configure |
| Backlight | 27 | Lit when high, can be dimmed with PWM |
| Touch CS | 33 | |
| Touch IRQ | 36 | Input-only pin, goes low on a touch |
| RGB LED R / G / B | 22 / 16 / 17 | Common anode, so each color is lit when its pin is **low** |
| SD card CS / SCK / MOSI / MISO | 5 / 18 / 23 / 19 | Its own SPI bus |
| Battery ADC | 34 | |
| Audio DAC out | 26 | |
| Audio amp enable | 4 | Enabled when **low** |
| BOOT button | 0 | Hold while powering on to get into download mode |
| Serial | TX0 / RX0 | Through the USB-C port |

ESPHome warns that 2, 12 and 15 are strapping pins. That's expected on this board and harmless, because the board design already accounts for it.

## Ways to program it

1. **ESPHome + LVGL (recommended).** It joins Home Assistant like the keg scales do. Screens are written in YAML, values update from HA entities, and buttons can call HA actions. Updates go over Wi-Fi. This is what this repo uses.
2. **Arduino (TFT_eSPI + LVGL).** The vendor's demo pack is Arduino and covers graphics, touch calibration, SD-card JPEGs, WAV audio, and an LVGL demo. Good for poking at the hardware, but you'd have to write the HA connection yourself (MQTT or REST).
3. **openHASP.** A ready-made firmware for HA touch panels, with the layout in JSON and control over MQTT. It has no target for this exact board, so you'd need a custom build. Not worth it here.

## First boot

Flashing and setup are in the [README](../README.md).

### Tuning

- **Colors look like a photo negative:** set `invert_colors: true`. **Red and blue are swapped:** set `color_order: rgb`.
- **Garbled or flickering image:** lower `data_rate` from 40MHz to 20MHz.
- **Touch is off:** tap the four corners with the stylus, read `raw_x` and `raw_y` from the log, and put the smallest and largest values into `calibration`. If touches land mirrored or on the wrong axis, use `swap_xy` and `mirror_x`/`mirror_y`.
- **LVGL fails to start (out of memory):** lower `buffer_size` (it's 15%). If there's plenty of free heap, raise it to make the screen redraw faster.
