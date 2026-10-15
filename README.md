# termux-imu-live

Live visualization of a phone's IMU (accelerometer and gyroscope), including a **position estimate from double integration** that visibly drifts away even while the phone lies still. It is meant as a teaching demo for why an IMU alone is good for orientation but not for position. It was built as a live demo for a university talk on input technologies in virtual reality.

**Try it on your phone:** https://imudemo.puchstein.lu

![screenshot](screenshot.png)

Two ways to run it:

| | Browser-only (`web/`) | Termux stream (`imu_server.py`) |
|---|---|---|
| Sensors read by | the phone's browser (DeviceMotion API) | Termux:API on the phone |
| Shown on | the phone itself | a laptop or projector browser |
| Needs | any static host with HTTPS | Python 3 on the laptop, Termux + Termux:API on the phone |

## Views

- **Acceleration** (m/s², incl. gravity), x/y/z over the last 10 s
- **Rotation rate** (gyroscope), x/y/z over the last 10 s
- **Position from double integration**: linear acceleration integrated twice, top view, with the distance from the start

The UI labels are in German, like the talk.

## Browser-only version

`web/index.html` is a single self-contained file without external assets. A hosted copy runs at https://imudemo.puchstein.lu. To host it yourself, serve it from any static host **over HTTPS**, since browsers expose motion sensors only in a secure context. Open it on a phone and tap the start button (iOS asks for permission). No data leaves the device.

If the host sends a `Permissions-Policy` header, it must allow `accelerometer` and `gyroscope` for `self`.

## Termux stream to a laptop

On the laptop:

```sh
python3 imu_server.py
# open http://localhost:8000
```

On the phone (Termux with the [Termux:API](https://wiki.termux.com/wiki/Termux:API) app and `pkg install termux-api`):

```sh
bash -c 'termux-sensor -s "Accelerometer,Gyroscope,Linear" -d 20 > /dev/tcp/LAPTOP-IP/9000'
```

`/dev/tcp` is a bash feature, hence `bash -c` if your shell is zsh or fish.

On networks that block device-to-device traffic, use a USB cable instead (USB debugging enabled):

```sh
adb reverse tcp:9000 tcp:9000
# then use 127.0.0.1 as LAPTOP-IP on the phone
```

A mesh VPN works as well.

Browser keys: `R` resets the integrated position, `Space` pauses. `http://localhost:8000/?test` shows synthetic data without a phone.

## How it works

`termux-sensor` prints pretty-printed JSON objects (`{"<sensor name>": {"values": [x, y, z]}, ...}`). The server accepts this stream on TCP port 9000, splits it into complete objects by counting braces and forwards each one to the browser as a Server-Sent Event. The page classifies sensors by name (`accel`, `gyro`, `linear`), plots them on canvases and integrates the linear acceleration twice. Without a linear-acceleration sensor, gravity is estimated with a low-pass filter and subtracted.

Only the Python standard library is used. `python3 imu_server.py --selftest` checks the stream parser.

## AI disclosure

This project was co-authored with Claude Opus 5.5 (Anthropic): the code, the browser version and this README were written with Claude, then tested on a real phone and published by Matthias Puchstein.

## License

MIT, see [LICENSE](LICENSE).
