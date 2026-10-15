# Syyngram assets

Everything visual that ships with Syyngram is generated from one palette and one mark, taken from the
SyynGram client kit (`tailwind.config.js` and `src/components/brand/Bolt.tsx`): night `#050403` to `#3A3022`,
sand `#F3ECDD` to `#6C604C`, gold `#F7E6B5` to `#7D6122`, and the bolt `#FFF6DD`.

Run the scripts from the repository root. They need Python 3 with Pillow and NumPy; the animation preview
also needs Node with `playwright-core` and `lottie-web` installed beside `render_tgs.mjs`.

| Script | What it writes |
| --- | --- |
| `make_icons.py` | The app icon family: `Telegram/Resources/art/ayu/<id>/app.png` and `app_icon.ico` for the eight icons in the picker (Ember, Vellum, Gilt, Obsidian, Signal, Ward, Circuit, Eclipse), the stock `art/icon*.png` and `icon256.ico`, and the bolt in the middle of the login QR. `--sheet out.png` draws a preview sheet instead. |
| `make_themes.py` | `night`, `night-custom-base`, `night-green` and `day-blue`, `day-custom-base` `.tdesktop-theme` packages (Ember, Obsidian, Vellum). Needs the stock palettes unpacked to a folder (`--stock`) and checks 43 foreground/background pairs for contrast (`--report`). |
| `preview_theme.py` | A mock of the client drawn from a theme's own colours, for a quick look without launching the app. |
| `make_animations.py` | `recolor` gilds the illustrated stock animations listed in `animations-gild.txt` onto the palette (shading and timing untouched); `bolt` writes `syyn_bolt_strike`, `syyn_bolt_pulse` and `syyn_bolt_lock`. |
| `render_tgs.mjs` | A contact sheet of `.tgs` animations in headless Chromium, to check them before they are built in. |

Notes:

* The icons are drawn per size, not scaled from one master: details drop out and the bolt thickens below 64 px.
* A theme never leaves a key on a stock blue by accident. `make_themes.py` refuses to run if a key that pointed
  at the (now dark) `windowFgActive` has no decision, and re-maps leftover blue and teal keys by lightness.
* Emoji art whose colours carry meaning (the dice, the star reactions, flags) is not gilded.
