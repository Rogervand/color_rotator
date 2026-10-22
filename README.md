# Color Rotator

A Home Assistant integration and dashboard card that rotates RGB lights through a list of colors, on an interval and an optional schedule. A single HACS install provides both: the integration serves and registers its own card.

## Concepts

- **Rotation group.** One config entry. Each group has its own lights, colors, timing and schedule, and gets a switch entity (`switch.<group_name>`). The switch is on while the group is rotating.
- **Card.** A `custom:color-rotator-card` is bound to one group. You can use as many cards as you like. Two cards pointing at the same group show the same settings.

Rotation runs inside Home Assistant, not in the browser. It keeps going with no dashboard open and resumes after a restart.

## Install (HACS custom repository)

1. Push this folder to a GitHub repo, which can be private.
2. In HACS, open **⋮ → Custom repositories**, add the repo URL and choose type **Integration**.
3. Install **Color Rotator** and restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration → Color Rotator** and name your first group. You can also create groups from the card editor.
5. Hard-refresh the browser once so the card JS loads.

**Manual install:** copy `custom_components/color_rotator` into `/config/custom_components/` and restart.

You do **not** need to add a dashboard resource. The integration registers the card automatically.

## Card

```yaml
type: custom:color-rotator-card
entry_id: <picked in the visual editor>
title: Porch            # optional
```

Use the visual editor to choose an existing group or create a new one. The card has these sections:

- **Status.** State, current color, a countdown to the next change, and the next schedule start or end. Buttons for **Start**, **Stop** and **Next color**.
- **Lights.** Add or remove lights. Only lights that support RGB/HS/XY color are offered.
- **Colors.** Add from the palette of standard HTML/CSS named colors, or a custom color. Each color has its own brightness slider and can be reordered or removed. **Global brightness**, when enabled, replaces every color's brightness.
- **Timing.**
  - Interval: 5 seconds to 8 hours.
  - Fade: 0 snaps.
  - Order: in order, or random. Random has an option to never repeat a color twice in a row.
  - Lights: all show the same color, or *offset*, where each light is one color further along the list for a chase effect.
- **Schedule.**
  - Days of the week.
  - Start and end: each can be a fixed time, or sunrise or sunset with an offset in minutes.
  - An end earlier than the start runs past midnight. Days refer to the day the window starts.
  - **When stopped** sets what happens to the lights: restore their previous state, turn them off, or leave them on the last color.

Edits are held locally until you press **Save**.

## Behavior notes

- Starting a group takes a snapshot of each light's state. **Restore previous state** replays that snapshot, and the snapshot survives restarts.
- **Manual starts.** Turning the switch on outside the schedule runs until you turn it off, or until the next scheduled end.
- **Manual stops.** Turning it off during a scheduled window stops it until the next scheduled start.
- **Manual light changes** during rotation are overwritten at the next change.
- **Removing a light** from a running group restores that light, or turns it off, according to the group's end action.
- **Unavailable lights** are skipped on each change.
- **Very short intervals.** With a 5-second interval and many lights, consider a fade of 1–2 s. Zigbee and Z-Wave networks may lag at the shortest intervals.
- **Dark colors.** Black and the darkest grays render as off on most bulbs.

## Automations

```yaml
action: switch.turn_on
target: { entity_id: switch.porch }
```

```yaml
action: color_rotator.next_color
target: { entity_id: switch.porch }
```

The switch's attributes include:

- `current_color`
- `next_change`
- `schedule_active`
- `next_schedule_event`
- `next_schedule_is_start`
- `entities`
- `interval`

## Development

```bash
pip install pytest-homeassistant-custom-component
pytest tests
```
