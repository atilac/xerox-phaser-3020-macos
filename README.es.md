# Xerox Phaser 3020 en macOS 27+ (Apple Silicon)

[English](README.md) · [Português](README.pt-BR.md) · **Español**

Imprimir en una **Xerox Phaser 3020 / 3020BI** desde un Mac moderno — por
**Wi-Fi** y por **USB** — sin Rosetta 2 y sin el controlador del fabricante.

El último controlador de Xerox para macOS llega hasta **macOS 10.14** e incluye
binarios **solo para Intel** (`i386`/`x86_64`). En Apple Silicon fallan con
`Bad CPU type in executable`, que CUPS traduce al inútil *"Filter failed"*.

Verificado de principio a fin en **macOS 27.0.1 (26A434), Apple M5 Pro, arm64**,
con una Phaser 3020BI con firmware `V3.50.21.03` (sep. 2021) — tanto la cola de
Wi-Fi como la de USB confirmadas mediante el contador de páginas del fusor de la
propia impresora.

---

## Resumen

| Conexión | Qué necesitas |
|---|---|
| **Wi-Fi** | **Nada.** La impresora ya trae AirPrint. Solo añádela. |
| **USB** | Un filtro de 60 líneas de este repositorio (`urftopjl`). |

---

## La vía Wi-Fi no necesita ningún controlador

La Phaser 3020 **tiene AirPrint en el firmware**. Su propia hoja de
configuración lo dice:

```
Installed Options
  AirPrint : Installed/Enabled
```

y lo anuncia por IPP:

```
ipp-features-supported    = document-object, airprint-1.3
urf-supported             = W8,RS600,IS1,CP1,IFU0,PQ4,OB10,V1.3
document-format-supported = application/octet-stream, application/x-QPDL, image/urf
```

Así que por Wi-Fi: **Ajustes del Sistema → Impresoras y escáneres → Añadir**,
selecciónala y listo. macOS la maneja de forma nativa
(`cgpdftoraster` → URF → IPP), todo en arm64, sin PPD de nadie.

Resulta contraintuitivo, porque la 3020 es una **impresora host-based (GDI)** —
sin PostScript, sin PCL, con 128 MB de RAM. No puede rasterizar una página por
sí sola. Pero su firmware *sí* entiende URF (Apple Raster), que llega en bandas
comprimidas en lugar de la página entera. Xerox siguió actualizando el firmware
(el nuestro es de **septiembre de 2021**) mucho después de abandonar el
controlador para Mac en 2014. **La impresora nunca quedó obsoleta — el
controlador sí.**

### Tres trampas que cuestan horas

1. **El Ahorro de energía viene configurado en 1 minuto.** La impresora se
   duerme, su radio Wi-Fi se apaga y desaparece de la red — pero CUPS sigue
   aceptando el trabajo e informando `successful-ok`. Síntoma: *no imprime nada
   y no da error.* **Corrige esto primero:** interfaz web → **Properties →
   General → Power Saver**, y súbelo a **60 minutos — el máximo que permite el
   firmware**. Con cualquier valor menor la impresora sigue desapareciendo de
   la red entre trabajos, y todos los síntomas anteriores vuelven.

2. **La radio es solo de 2.4 GHz** (802.11b/g/n). En un router de doble banda
   tienes que pulsar el botón WPS de **2.4 GHz**. El de 5 GHz nunca emparejará.

3. **El nivel de tóner no sirve para verificar una impresión.** `marker-levels`
   solo cambia cada varias decenas de páginas. Usa el contador de páginas:
   ```sh
   curl -s http://<ip-de-la-impresora>/sws/app/information/supplies/supplies.json \
     | tr -d ' \t' | grep -oE 'fuser_kit:[0-9]+'
   ```
   `fuser_kit` cuenta las hojas que pasaron físicamente por el fusor.

### Cómo ponerla en el Wi-Fi, para empezar

La herramienta oficial de Xerox para esto — *Easy Wireless Setup* — es **solo
para Intel y funciona por USB**. Eso es un callejón sin salida: no puedes poner
la impresora en la red usando el mismo Mac que no puede ejecutar el
controlador.

**WPS rompe el bloqueo.** Pulsa WPS en el router (2.4 GHz, 1–3 s) y luego toca
el WPS de la impresora. Mantén pulsado el WPS de la impresora **10 s** para
imprimir una hoja de configuración con la dirección IP.

---

## La vía USB: por qué necesita este repositorio

Por IPP, el atributo `document-format` le indica a la impresora qué está
llegando. **Una conexión USB cruda no lleva ese metadato**, así que el firmware
no puede distinguir URF de cualquier otra cosa — y descarta el trabajo en
silencio.

El propio device ID IEEE-1284 de la impresora muestra que habla URF:

```
MFG:Xerox;MDL:Phaser 3020;CMD:SPL,URF,FWV,EXT;MODE:SPL3,R000105;
```

La solución es anunciar el lenguaje en PJL, igual que hace el controlador del
fabricante con su propio formato (`@PJL ENTER LANGUAGE=QPDL`):

```
\x1b%-12345X@PJL JOB NAME="..."
@PJL ENTER LANGUAGE=URF
<datos URF>
\x1b%-12345X@PJL EOJ
\x1b%-12345X
```

Eso es todo lo que hace `urftopjl`. El pipeline queda así:

```
PDF ──► cgpdftoraster ──► URF ──► urftopjl ──► backend usb ──► impresora
        (Apple, arm64)            (este repo)   (Apple)
```

Ningún lenguaje de descripción de página obtenido por ingeniería inversa.
Ningún binario del fabricante.

### Instalación

```sh
git clone https://github.com/atilac/xerox-phaser-3020-macos.git
cd xerox-phaser-3020-macos
sudo ./scripts/install.sh
```

`sudo` es necesario porque CUPS se niega a ejecutar filtros que no pertenezcan
a `root` y que no estén dentro de `/Library/Printers`.

Después:

```sh
lp -d Xerox_Phaser_3020_USB archivo.pdf
```

Para desinstalar: `sudo ./scripts/uninstall.sh`.

### Solo compilar

```sh
clang -O2 -Wall -Wextra -arch arm64 -arch x86_64 -o src/urftopjl src/urftopjl.c
python3 scripts/make-ppd.py ppd/Xerox_Phaser_3020_USB.ppd
```

El PPD usa **A4** por defecto; para Carta, edita `DEFAULT_PAPER` en
`scripts/make-ppd.py` y vuelve a generarlo.

---

## Wi-Fi Direct

La impresora también puede actuar como su propio punto de acceso — útil cuando
no hay ningún router. Actívalo en **Properties → Network Settings → Wi-Fi →
Wi-Fi Direct**, conéctate a su red (`DIRECT-xx-<nombre del dispositivo>`) y crea
la cola:

```sh
lpadmin -p Xerox_3020_WiFiDirect -E \
        -v ipp://192.168.3.1/ipp/print \
        -P /Library/Printers/PPDs/Contents/Resources/Xerox_Phaser_3020_USB.ppd
```

El firmware ofrece **IPP en esta interfaz también**, así que aquí no hace falta
el envoltorio PJL — por la misma razón que la vía Wi-Fi normal funciona sin
controlador. Reutilizamos el PPD del USB solo porque ya trae la geometría de
página correcta; su filtro es inofensivo sobre IPP.

Ten en cuenta que tu Mac se queda **sin internet** mientras esté en esa red, y
las otras dos colas quedan inaccesibles hasta que vuelvas a tu Wi-Fi habitual.

---

## Lo que este repositorio deliberadamente no contiene

**Ningún binario de Xerox.** Ni `rastertosec`, ni `prefilter`, ni
`commandtosec`, ni `libscmssc.dylib`, ni el PPD original. Son propietarios y
redistribuirlos constituye una infracción de derechos de autor. Todo lo que hay
aquí está escrito desde cero y publicado bajo licencia MIT.

---

## Si necesitas QPDL

El formato propio del controlador del fabricante es **QPDL (SPL2)** — su
binario emite `@PJL ENTER LANGUAGE=QPDL`, y en este modelo la compresión JBIG
está desactivada (`eJBIGSupH` no aparece en el PPD). El análisis estático de
`rastertosec` (que no está stripped) da la cabecera de banda en 11 bytes:

| Offset | Tam. | Campo |
|---|---|---|
| 0 | 1 | marcador de banda `0x0C` |
| 1 | 1 | número de banda |
| 2 | 2 | ancho (big-endian) |
| 4 | 2 | alto (big-endian) |
| 6 | 1 | método de compresión |
| 7 | 4 | tamaño de datos + 4 (big-endian) |

lo que coincide con la implementación de QPDL de
[SpliX](https://github.com/OpenPrinting/splix). `BandHeight` es 64 a 300 dpi y
128 en las demás resoluciones.

**Es casi seguro que no necesitas nada de esto** — URF funciona y es más
sencillo. Queda documentado aquí por si algún modelo de esta familia no admite
URF.

## Créditos y trabajos relacionados

- [OpenPrinting/splix](https://github.com/OpenPrinting/splix) — la implementación de referencia de QPDL/SPL
- [boredjar-com/splix-macos](https://github.com/boredjar-com/splix-macos) — SpliX compilado de forma nativa para Apple Silicon
- [adpopescu338/xerox-phaser-3020-apple-silicon](https://github.com/adpopescu338/xerox-phaser-3020-apple-silicon) — el enfoque con Rosetta 2

## Licencia

MIT — véase [LICENSE](LICENSE).
