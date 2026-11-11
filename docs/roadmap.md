# Software roadmap

## Architecture

The camera is always in one **mode**; each mode decides what the controls do and what the overlay draws.

| Mode | Purpose | Enter / leave |
| --- | --- | --- |
| Shoot | Live view, info overlay, shutter takes a photo | Default |
| Magnify | 5× / 10× crop of the centre for focusing | OK in Shoot; OK again steps 5× → 10× → off |
| Menu | Change settings | Menu button; Back steps out |
| Playback | Review photos | Play button; Play or half-press returns to Shoot |

Planned modules in `evfcam/`:

| Module | Job |
| --- | --- |
| `app.py` | Main loop: reads input events, passes them to the current mode, redraws |
| `camcore.py` | Owns Picamera2: preview config, still capture, controls, metadata |
| `ui.py` | Draws the overlay (Pillow RGBA) for the current mode |
| `menu.py` | Menu defined as data; one renderer and navigator for every page |
| `settings.py` | All adjustable settings in one object, saved to JSON |
| `inputs.py` | Turns key and dial events into actions (`UP`, `OK`, `DIAL+1`, `SHUTTER_FULL`...) |

**Input:** the gpio-key and rotary-encoder overlays turn buttons and dials into Linux input events, the same kind a USB keyboard produces. A keyboard stands in for every control until the real ones are wired.

## Menu (two levels)

- **Shooting:** JPEG / RAW+JPEG, quality, aspect (4:3, 3:2, 1:1), self-timer
- **Exposure:** Auto / Shutter priority / Manual, shutter, ISO, exposure compensation, metering (aperture is on the lens)
- **Colour:** white balance, contrast, saturation, black and white
- **Lens:** 9 mm / 17 mm, written to each photo's EXIF
- **Display:** focus square, focus bar, info level, EVF brightness
- **Setup:** date and time, Wi-Fi, storage, battery, power off

Navigation: pad up/down moves, OK or right enters, Back or left leaves, thumb wheel changes the value.

## Milestones

- [x] 0. Bench bring-up: preview, overlay, focus meter, shutter button (`bench/`)
- [ ] 1. App skeleton: modes, keyboard input, overlay
- [ ] 2. Settings + menu
- [ ] 3. Playback
- [ ] 4. Lens selection and EXIF
- [ ] 5. Real buttons and dials (gpio-key / rotary-encoder overlays)
- [ ] 6. Start at boot (systemd service)
- [ ] 7. Clean power-off
- [ ] Later: battery gauge (MAX17048) and eye sensor (VCNL4040), deferred to save space
- [ ] 8. Polish: speed, look, field testing
