# Xerox Phaser 3020 on macOS 27+ (Apple Silicon)

**English** · [Português](README.pt-BR.md) · [Español](README.es.md)

Printing on a **Xerox Phaser 3020 / 3020BI** from a modern Mac — over **Wi-Fi**
and over **USB** — with no Rosetta 2 and no vendor driver.

Xerox's last macOS driver supports **macOS 10.14** and ships **Intel-only**
binaries (`i386`/`x86_64`). On Apple Silicon they fail with
`Bad CPU type in executable`, which CUPS reports as the unhelpful
*"Filter failed"*.

Verified end to end on **macOS 27.0.1 (26A434), Apple M5 Pro, arm64**, with a
Phaser 3020BI on firmware `V3.50.21.03` (Sep 2021) — both the Wi-Fi queue and
the USB queue confirmed by the printer's own fuser page counter.

---

## TL;DR

| Connection | What you need |
|---|---|
| **Wi-Fi** | **Nothing.** The printer has AirPrint built in. Just add it. |
| **USB** | A 60-line filter from this repo (`urftopjl`). |

---

## The Wi-Fi path needs no driver at all

The Phaser 3020 **has AirPrint in firmware**. Its own configuration sheet says so:

```
Installed Options
  AirPrint : Installed/Enabled
```

and it advertises over IPP:

```
ipp-features-supported    = document-object, airprint-1.3
urf-supported             = W8,RS600,IS1,CP1,IFU0,PQ4,OB10,V1.3
document-format-supported = application/octet-stream, application/x-QPDL, image/urf
```

So on Wi-Fi: **System Settings → Printers & Scanners → Add**, pick it, done.
macOS drives it natively (`cgpdftoraster` → URF → IPP), all arm64, no PPD from
anyone.

This is counter-intuitive, because the 3020 is a **host-based (GDI) printer** —
no PostScript, no PCL, 128 MB of RAM. It cannot rasterize a page on its own.
But its firmware *does* understand URF (Apple Raster), which arrives as
compressed bands rather than a whole page. Xerox kept updating the firmware
(ours is from **September 2021**) long after abandoning the Mac driver in 2014.
**The printer never became obsolete — the driver did.**

### Three traps that cost hours

1. **Power Saver ships set to 1 minute.** The printer sleeps, its Wi-Fi radio
   goes down, and it vanishes from the network — but CUPS still accepts the job
   and reports `successful-ok`. Symptom: *prints nothing, reports no error.*
   **Fix this first:** web UI → **Properties → General → Power Saver**, and
   raise it to **60 minutes — the maximum the firmware allows**. Anything
   shorter and the printer keeps dropping off the network between jobs, and
   every symptom above comes back.

2. **The radio is 2.4 GHz only** (802.11b/g/n). On a dual-band router you must
   press the **2.4 GHz** WPS button. The 5 GHz one will never pair.

3. **Toner level is useless for verifying a print.** `marker-levels` moves only
   once every few dozen pages. Use the page counter instead:
   ```sh
   curl -s http://<printer-ip>/sws/app/information/supplies/supplies.json \
     | tr -d ' \t' | grep -oE 'fuser_kit:[0-9]+'
   ```
   `fuser_kit` counts sheets that physically went through the fuser.

### Getting it onto Wi-Fi in the first place

Xerox's official tool for this — *Easy Wireless Setup* — is **Intel-only and
runs over USB**. That is a deadlock: you cannot put the printer on the network
using the same Mac that cannot run the driver.

**WPS breaks the deadlock.** Press WPS on the router (2.4 GHz, 1–3 s), then tap
WPS on the printer. Hold the printer's WPS for **10 s** to print a
configuration sheet with the IP address.

---

## The USB path: why it needs this repo

Over IPP the `document-format` attribute tells the printer what is arriving.
**A raw USB connection carries no such metadata**, so the firmware cannot tell
URF from anything else — and silently discards the job.

The printer's own IEEE-1284 device ID shows it speaks URF on the wire:

```
MFG:Xerox;MDL:Phaser 3020;CMD:SPL,URF,FWV,EXT;MODE:SPL3,R000105;
```

The fix is to announce the language in PJL, exactly as the vendor driver does
for its own format (`@PJL ENTER LANGUAGE=QPDL`):

```
\x1b%-12345X@PJL JOB NAME="..."
@PJL ENTER LANGUAGE=URF
<URF data>
\x1b%-12345X@PJL EOJ
\x1b%-12345X
```

That is all `urftopjl` does. The pipeline becomes:

```
PDF ──► cgpdftoraster ──► URF ──► urftopjl ──► backend usb ──► printer
        (Apple, arm64)            (this repo)   (Apple)
```

No reverse-engineered page description language. No vendor binaries.

### Install

```sh
git clone https://github.com/atilac/xerox-phaser-3020-macos.git
cd xerox-phaser-3020-macos
sudo ./scripts/install.sh
```

`sudo` is required because CUPS refuses to run filters that are not owned by
`root` and located under `/Library/Printers`.

Then:

```sh
lp -d Xerox_Phaser_3020_USB file.pdf
```

Uninstall with `sudo ./scripts/uninstall.sh`.

### Build only

```sh
clang -O2 -Wall -Wextra -arch arm64 -arch x86_64 -o src/urftopjl src/urftopjl.c
python3 scripts/make-ppd.py ppd/Xerox_Phaser_3020_USB.ppd
```

The PPD defaults to **A4**; edit `DEFAULT_PAPER` in `scripts/make-ppd.py` for
Letter and regenerate.

---

## Wi-Fi Direct

The printer can also act as its own access point — useful with no router at
all. Enable it under **Properties → Network Settings → Wi-Fi → Wi-Fi Direct**,
then join its network (`DIRECT-xx-<device name>`) and add the queue:

```sh
lpadmin -p Xerox_3020_WiFiDirect -E \
        -v ipp://192.168.3.1/ipp/print \
        -P /Library/Printers/PPDs/Contents/Resources/Xerox_Phaser_3020_USB.ppd
```

The firmware serves **IPP on this interface too**, so no PJL wrapper is needed
here — the same reason the normal Wi-Fi path works driverless. Reuse the USB
PPD only because it already carries the correct page geometry; its filter is
harmless over IPP.

Note that your Mac has no internet while joined to this network, and the other
two queues are unreachable until you rejoin your normal Wi-Fi.

---

## What this repo deliberately does not contain

**No Xerox binaries.** Not `rastertosec`, `prefilter`, `commandtosec`,
`libscmssc.dylib`, nor the original PPD. They are proprietary and
redistributing them is copyright infringement. Everything here is written from
scratch and MIT-licensed.

---

## If you need QPDL instead

The vendor driver's own format is **QPDL (SPL2)** — its binary emits
`@PJL ENTER LANGUAGE=QPDL`, and for this model JBIG compression is off
(`eJBIGSupH` is absent from the PPD). Static analysis of the unstripped
`rastertosec` gives the band header as 11 bytes:

| Offset | Size | Field |
|---|---|---|
| 0 | 1 | `0x0C` band marker |
| 1 | 1 | band number |
| 2 | 2 | width (big-endian) |
| 4 | 2 | height (big-endian) |
| 6 | 1 | compression method |
| 7 | 4 | data size + 4 (big-endian) |

which matches [SpliX](https://github.com/OpenPrinting/splix)'s QPDL
implementation. `BandHeight` is 64 at 300 dpi and 128 otherwise.

**You almost certainly don't need any of this** — URF works and is simpler.
It is documented here in case a model in this family lacks URF support.

## Credits & related work

- [OpenPrinting/splix](https://github.com/OpenPrinting/splix) — the QPDL/SPL reference implementation
- [boredjar-com/splix-macos](https://github.com/boredjar-com/splix-macos) — SpliX built natively for Apple Silicon
- [adpopescu338/xerox-phaser-3020-apple-silicon](https://github.com/adpopescu338/xerox-phaser-3020-apple-silicon) — the Rosetta 2 approach

## License

MIT — see [LICENSE](LICENSE).
