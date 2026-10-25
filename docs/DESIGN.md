# Kegerator display: design

A plan, nothing built yet. **The screen is vertical (320x480)**, decided 24 Oct 2026. Mockups (the vertical row is the one to build; the horizontal row is kept for reference): https://claude.ai/artifact/8hP9J5qWfZdYY6RTtP8vyb

## What it does

1. **Asleep:** backlight off, still listening to the scales.
2. **Wakes** on a tap, or by itself when a keg starts dropping. Wake-on-pour costs nothing extra, because the display is listening all the time anyway (see the next section). It can be switched off in the settings.
3. **Taps overview:** a keg graphic for each tap (labeled left, center and right, the same as on the kegerator), filled to the level in the beer's color, with gallons, percent and pints left, plus the CO2 tank.
4. **A keg starts dropping:** switches to the pour screen for that tap. It shows a big live ounce counter, the pour rate, a pint marker, and the keg draining. The other taps shrink to chips along the bottom.
5. **The pour stops:** shows the final ounces and a 2 minute countdown. If the same keg drops again in that window (topping off after the foam settles), it adds to the same pour.
6. **2 min after the pour:** back to the overview. **2 more minutes with no touch:** back to sleep.

## How the scales talk to the display

**ESPHome `packet_transport` over UDP.** This is ESPHome's built-in way for devices to share sensor readings with each other with no Home Assistant, broker, or server in between.

- Each scale sends its weight out on the network as small UDP messages (port 18511). The display listens and gets each scale's reading as an ordinary sensor.
- **No IP addresses to configure.** By default a scale sends to the network's broadcast address, and each scale is identified by its ESPHome name (`kegerator-scale-keg-1`). Adding keg 2 means flashing the scale and adding one sensor on the display that names it.
- No encryption. Anything on the LAN could read the keg weights, which doesn't matter. If it's ever wanted, `packet_transport` can encrypt with a passphrase that's put in every device's `secrets.yaml` and built into each firmware. Nothing is exchanged over the network.
- Checked against ESPHome 2026.9.1's source. Both the scale side and display side snippets below validate.

### Running it 24/7

There is no connection to keep up. UDP has no connection: each reading is one small message sent and forgotten. If the display reboots, or a scale drops off Wi-Fi for a minute, nothing has to reconnect, and the next reading just arrives. A websocket would be the opposite: a live connection per scale that has to notice drops and reconnect. That's more work for the C3s and more to go wrong.

The scales also send **only when the weight changes**:

- A filter on the scale sends a reading only when it moves by more than 0.01 lb (about 0.15 oz). A still keg jitters far less than that, so it sends nothing.
- Every scale still sends a heartbeat every 5 s. That's how the display knows a scale is still alive.
- During a pour the keg drops about 0.02 lb every 0.2 s, so every reading goes out. That's about 5 per second, each under 100 bytes, while the keg is draining.
- Network load when nobody is pouring: 3 scales × 1 message every 5 s. Nothing.

**The C3s can do this.** The CO2 scale (also a XIAO ESP32-C3) already reads the load cell 10 times a second, around the clock. It had been up 11.6 days when checked on 24 Oct. Sending a tiny UDP message a few times a second during a pour is less work than the HA connection it already keeps.

One setting goes on every device: `wifi: power_save_mode: none`. ESP32s default to a light Wi-Fi sleep that can add a delay and sometimes miss broadcast messages. Everything here runs on USB power, so the sleep saves nothing.

### Wi-Fi inside the kegerator

The CO2 scale's signal over the last 7 days: **-56 to -68 dBm, average -61**. Anything better than -70 is solid. But the CO2 scale sits **behind** the kegerator, not in it, so this says nothing about the keg scales. A fridge is a metal box, and inside one the signal can drop a lot. That's still unknown.

**Easy test, no new firmware needed:** keg 1's current firmware already reports a "WiFi signal" sensor to HA. Power the keg-1 scale inside the kegerator with the door shut and watch that sensor for a while. Better than -70 dBm is fine. -70 to -80 will mostly work but lose some messages. Worse than -80 needs a fix.

**Fixes if it's weak:** the XIAO ESP32-C3 uses a separate stick-on antenna on a short cable. That antenna can go on the outside of the kegerator, with its cable through the door seal next to the USB power cable that already has to get out. If the stock cable is too short, a U.FL extension or a larger external antenna will do it.

### Broadcast vs. sending to one address

The earlier open question, in plain terms: by default a scale sends its readings to *everyone* on the network (a broadcast). That's what makes "no IP addresses" work. Two things can stop a broadcast from reaching the display:

- The display has to be on the same network (VLAN) as the scales. Broadcasts don't cross from one VLAN to another.
- UniFi has options on a Wi-Fi network that thin out broadcast traffic ("Multicast Enhancement", multicast and broadcast filtering).

Wi-Fi also sends broadcasts at the slowest speed with no retry, so a weak signal loses more of them. If either becomes a problem, the fix is to give the display a fixed IP (a DHCP reservation in UniFi) and list it in each scale's `udp: addresses:`. Then each message goes straight to the display and gets retried when lost. Only the display's address is ever configured. Testing keg 1 will show whether this is needed (see the soak test below).

### Soak test before the display is built

Once keg 1 runs the new firmware, a small listener on the PC can count every message and log the gaps for a day or two. That shows message loss, latency, and the Wi-Fi in the kegerator before any display code exists.

## Changes to the scale firmware

Today the scales read 10 times a second but only send a 1 minute average, so a pour would show up a minute late. Each scale gets a fast stream for the display and keeps the slow average for HA:

```yaml
wifi:
  power_save_mode: none

sensor:
  - platform: hx711
    id: scale_live            # about 5 readings a second, kept on the scale
    internal: true
    update_interval: 100ms
    filters:
      - median:
          window_size: 5
          send_every: 2       # 10 readings/s in, 5/s out
      - calibrate_linear: [...]
      - lambda: return x - id(tare_offset);
  - platform: copy            # what HA sees, same as today
    source_id: scale_live
    name: "Scale"
    filters:
      - throttle_average: 60s
  - platform: copy            # what the display gets: only readings that moved
    id: scale_stream
    source_id: scale_live
    internal: true
    filters:
      - delta: 0.01

udp:
packet_transport:
  - platform: udp
    update_interval: 5s       # the heartbeat
    sensors:
      - id: scale_stream
        broadcast_id: weight
```

The display side:

```yaml
wifi:
  power_save_mode: none
udp:
packet_transport:
  - platform: udp
sensor:
  - platform: packet_transport
    provider: kegerator-scale-keg-1
    remote_id: weight
    id: keg1_weight
```

**Is 5 per second enough?** Yes. In `readings.csv` from the keg-scale testing (`~/projects/keg-scale-esp32-testing`), a single raw reading jitters by about 40 counts. With the current calibration (about 10,600 counts per lb) that's **0.06 oz**, and after the median filter about 0.03 oz. A pour drains around 1.5–2 oz a second, so a pour stands out within a few readings. The keg-1 calibration is still the CO2 scale's, so recheck this once keg 1 is calibrated.

## Pour detection (runs on the display)

For each keg, on every reading:

- **Baseline:** the last steady weight.
- **Start:** the weight sits more than 0.1 lb (about 1.5 oz) below the baseline for 3 readings in a row (0.6 s). This ignores a bump or a tug on a beer line, which jumps and comes back.
- **Live:** poured fl oz = (baseline − now) in oz of weight ÷ 1.04 (beer is about 1.04 oz of weight per fl oz). Pour rate comes from the last second of readings.
- **Stop:** no new reading for 2 s (the scale has gone quiet because the weight stopped moving), or the weight holds within ±0.03 lb for 2 s. The total is frozen and the 2 minute hold starts.
- **Top-off:** a new drop during the hold continues the same pour from where it stopped.
- **Foam doesn't matter:** the scale measures what left the keg, and the foam is still in the glass.

Things to watch for once it's running: the compressor vibrating the shelf, a CO2 line pulling on a keg, and the reading drifting slowly as the kegs chill. The thresholds will be numbers in the config, set from what we see on the real kegs.

## Keg levels and taring kegs

> **Changed 24 Oct 2026:** the keg math runs on **each scale**, not the display, so Home Assistant and Grafana get gallons directly. Each keg scale has an **Empty keg weight** setting and reports **Gallons left** and **Percent full**; the CO2 scale has tank settings and reports **Gas left**. The display shows what the scales report. The keg shells list and the **Kicked** button below are on hold; for now a keg's empty weight is set on its scale.

**All kegs are sixtels** (1/6 barrel, 5.16 gal, about 41 pints when full).

**Gallons left** = (scale reading − empty keg weight) ÷ 8.42 lb per gallon. **Percent** = gallons ÷ 5.16. Pints = gallons × 8. So the one number each keg needs is its **empty weight**. The sixtels are all the same size, but the two homebrew kegs and the commercial one weigh different amounts empty.

**Two different tares:**

- *Scale zero* (the existing Tare button on each scale): the empty plate. Only needed if the scale drifts, never per keg.
- *Empty keg weight* (per keg, a setting on its scale): the keg shell plus whatever hose weight rests on the scale.

**Kegs remember their empty weight.** The display keeps a short list of your keg shells, for example "Homebrew A", "Homebrew B" and "Commercial", each with its own empty weight. When you swap a keg, you pick which shell went on. The weight follows the keg, not the tap.

**Getting an empty weight, from best to roughest:**

1. **Learn it when the keg kicks.** When a keg runs dry, press **Kicked** on the display and it records what the scale reads right then as that shell's true empty weight. That includes the hose weight resting on the scale, which no stamped number does. From then on that shell is exact.
2. **Weigh it empty.** Put the empty keg on the scale and press "this is empty". Or use a tare weight stamped on the keg, if it has one.
3. **Tell it how much is left** (the in-progress kegs). Enter a rough "about 2.5 gal left". The display works backwards to an empty weight (reading − 2.5 × 8.42 lb). Gallons left will be off by however far the guess was, but **pour amounts are exact from day one**, because a pour is a drop in weight and doesn't depend on the tare. When that keg kicks, option 1 replaces the guess.
4. **Type a number** for the empty weight. An empty sixtel is somewhere around 14–17 lb depending on the make, so a guess there is close.

So the current half-drunk kegs get option 3 or 4 now and fix themselves at the first kick.

**Swapping a keg** (the "New keg" mockups): long-press a tap → New keg. The display checks the old keg is off (scale near 0), asks which shell went on, waits for the new keg to settle, and shows the weight and the gallons it works out. You press **Start keg**.

## Configuration

Typing on a resistive 4" screen is miserable, so text goes in from a phone and the touchscreen only does buttons.

| Setting | Where it's set |
|---|---|
| Beer name, style and color for each tap (left, center, right). No ABV | ESPHome `text`/`select` entities, editable on the display's own web page (`web_server`) and in HA if it's connected |
| Keg shells: name, empty weight | Same places, plus Kicked / "this is empty" on the touchscreen |
| CO2 tank: tare weight, size | Same places (see CO2 swap below) |
| Which scale feeds which tap | The display's YAML (each sensor's `provider`). Set once, changed by reflashing |
| Scale IP addresses | Not needed (see above) |
| Timeouts (hold 2 min, sleep 2 min), pour thresholds, wake on pour, night mode hours | `number`/`switch` entities |

All of these keep their values through a power cut (`restore_value`). The beer color is a short list of presets (pale, gold, amber, brown, black) that set the keg fill color, so a stout reads dark and a pilsner pale. It belongs to the beer, not the tap, and might be dropped in favor of one fill color for every keg (undecided).

Memory risk: the web page and LVGL both need RAM on an ESP32 without PSRAM. If they don't fit, the web page goes and the settings live in HA only.

## Home Assistant

**The scales report to HA directly**, the same way the CO2 scale does today: a 1 minute average weight, plus Wi-Fi signal and uptime. From HA it goes into the recorder and on to Grafana like everything else. This doesn't depend on the display at all. The scales send their fast stream to the display and the 1 minute average to HA at the same time (see the scale firmware above).

HA does the alerts that need history, starting with a **CO2 leak alarm**: the CO2 tank losing weight while no keg is pouring.

**The display works with HA off.** If it's connected (`api:`), beer names and keg settings can also be edited from HA's UI, and the keg levels can go on an HA dashboard or the TRMNL.

Gotcha: by default ESPHome **reboots after 15 minutes without an HA connection**. The display must set `api: reboot_timeout: 0s` so it doesn't restart during a pour if HA is down.

## Clock: keg age and night mode

Both need the time of day. The display gets it from the internet with ESPHome's `time: platform: sntp`, so it works with HA off. If HA is connected, HA's time is a fallback.

- **Keg age:** pressing **Start keg** records the date, and each tap shows "on tap 23 days" (in the vertical overview mockup).
- **Night mode:** a dimmer backlight between two set times, for example 9 pm to 7 am. The times are settings like the others.

## What the screen can do

The mockups use only what LVGL draws well on this chip: solid-color rounded rectangles for the keg bodies and fills, LVGL bars and arcs for the gauges, and fonts built into the firmware (Barlow Condensed for the numbers, Barlow for labels).

- **Fine:** a live counter updating 5 times a second, filling and draining kegs, a fade or slide between screens.
- **Avoid:** photos or large images (they use up the 4 MB flash), and full-screen animation at high frame rates. With no PSRAM, LVGL draws in strips over SPI, so a full-screen redraw takes at least 60 ms (a rough estimate, not measured).
- The striped "being poured" band in the mockups might be simplified to a lighter shade of the beer color. Stripes are possible in LVGL but cost more to draw.

## Open questions

1. ~~Horizontal or vertical?~~ Vertical.
2. ~~Should a pour wake the screen?~~ Yes, as a setting. Change-only sending makes it cheap.
3. ~~Keg sizes?~~ All sixtels (5.16 gal). Two homebrew, one commercial, each with its own empty weight, handled by keg shells.
4. ~~Is the CO2 scale inside the kegerator?~~ No, it's behind it. Keg Wi-Fi inside is untested: run keg 1 inside and watch its WiFi signal sensor.
5. Keg fill color: each beer's color, or one color for every keg?

## Later

Not now, but don't forget.

- **Animation.** Bubbles rising through the beer during a pour, the foam line wobbling as the level drops, the ounce counter rolling, a fade when the screen wakes. Small areas only, so they redraw fast.
- **CO2 swap screen.** Like the new keg flow: take the empty tank off, put the full one on, enter the tank's tare weight (stamped as "TW" on the collar) and size. Gas left = reading − tare. "Learn it when it runs out" works for CO2 too.
- **Recent usage graph.** Pints per tap per day for the last week or two, using LVGL's chart widget. The display keeps a small rolling log of pour totals. If HA is connected, HA's history can feed a longer graph.
- **Temperature probe tile.** A DS18B20 on the display's spare pins, or on one of the scales, sending its reading the same way.
- **Speaker** (eventually): a chime when a keg kicks. The board has an amp on GPIO26.
- **Kicked keg alert** (maybe): on screen, and an ntfy push through HA.

Decided against: pour log, days left on a keg, pour speed check, today's pours, RGB LED in the beer's color. The CO2 leak alarm moved to HA.
