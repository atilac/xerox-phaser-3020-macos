# Xerox Phaser 3020 no macOS 27+ (Apple Silicon)

[English](README.md) · **Português** · [Español](README.es.md)

Imprimir numa **Xerox Phaser 3020 / 3020BI** a partir de um Mac moderno — por
**Wi-Fi** e por **USB** — sem Rosetta 2 e sem driver do fabricante.

O último driver da Xerox para macOS suporta até o **macOS 10.14** e traz
binários **somente Intel** (`i386`/`x86_64`). No Apple Silicon eles falham com
`Bad CPU type in executable`, que o CUPS reporta como o inútil
*"Filter failed"*.

Verificado de ponta a ponta no **macOS 27.0.1 (26A434), Apple M5 Pro, arm64**,
com uma Phaser 3020BI no firmware `V3.50.21.03` (set/2021) — tanto a fila de
Wi-Fi quanto a de USB confirmadas pelo contador de páginas do fusor da própria
impressora.

---

## Resumo

| Conexão | O que você precisa |
|---|---|
| **Wi-Fi** | **Nada.** A impressora já tem AirPrint. É só adicionar. |
| **USB** | Um filtro de 60 linhas deste repositório (`urftopjl`). |

---

## O caminho Wi-Fi não precisa de driver nenhum

A Phaser 3020 **tem AirPrint no firmware**. A própria folha de configuração dela diz:

```
Installed Options
  AirPrint : Installed/Enabled
```

e ela anuncia por IPP:

```
ipp-features-supported    = document-object, airprint-1.3
urf-supported             = W8,RS600,IS1,CP1,IFU0,PQ4,OB10,V1.3
document-format-supported = application/octet-stream, application/x-QPDL, image/urf
```

Então, no Wi-Fi: **Ajustes do Sistema → Impressoras e Scanners → Adicionar**,
escolha ela, pronto. O macOS cuida de tudo nativamente
(`cgpdftoraster` → URF → IPP), em arm64, sem PPD de ninguém.

Isso é contraintuitivo, porque a 3020 é uma **impressora host-based (GDI)** —
sem PostScript, sem PCL, com 128 MB de RAM. Ela não consegue rasterizar uma
página sozinha. Mas o firmware *entende* URF (Apple Raster), que chega em
bandas comprimidas em vez da página inteira. A Xerox continuou atualizando o
firmware (o nosso é de **setembro de 2021**) muito depois de abandonar o driver
de Mac em 2014. **A impressora nunca ficou obsoleta — o driver ficou.**

### Três armadilhas que custam horas

1. **O Power Saver vem de fábrica em 1 minuto.** A impressora dorme, o rádio
   Wi-Fi desliga e ela some da rede — mas o CUPS continua aceitando o trabalho e
   reportando `successful-ok`. Sintoma: *não imprime nada e não dá erro.*
   **Corrija isso primeiro:** interface web → **Properties → General → Power
   Saver**, e aumente para **60 minutos — o máximo que o firmware permite**.
   Com qualquer valor menor a impressora continua saindo da rede entre um
   trabalho e outro, e todos os sintomas acima voltam.

2. **O rádio é só 2.4 GHz** (802.11b/g/n). Num roteador de duas bandas, você
   precisa apertar o botão WPS de **2.4 GHz**. O de 5 GHz nunca vai parear.

3. **O nível de toner não serve para verificar impressão.** O `marker-levels`
   só muda a cada dezenas de páginas. Use o contador de páginas:
   ```sh
   curl -s http://<ip-da-impressora>/sws/app/information/supplies/supplies.json \
     | tr -d ' \t' | grep -oE 'fuser_kit:[0-9]+'
   ```
   O `fuser_kit` conta folhas que passaram fisicamente pelo fusor.

### Como colocar ela no Wi-Fi, para começar

A ferramenta oficial da Xerox para isso — o *Easy Wireless Setup* — é **somente
Intel e funciona por USB**. Isso é um impasse: você não consegue colocar a
impressora na rede usando o mesmo Mac que não roda o driver.

**O WPS quebra o impasse.** Aperte o WPS no roteador (2.4 GHz, 1–3 s) e, em
seguida, dê um toque no WPS da impressora. Segure o WPS da impressora por
**10 s** para imprimir a folha de configuração com o endereço IP.

---

## O caminho USB: por que precisa deste repositório

Por IPP, o atributo `document-format` informa à impressora o que está chegando.
**Uma conexão USB crua não carrega esse metadado**, então o firmware não
consegue distinguir URF de qualquer outra coisa — e descarta o trabalho em
silêncio.

O device ID IEEE-1284 da própria impressora mostra que ela fala URF:

```
MFG:Xerox;MDL:Phaser 3020;CMD:SPL,URF,FWV,EXT;MODE:SPL3,R000105;
```

A correção é anunciar a linguagem em PJL, exatamente como o driver do
fabricante faz para o formato dele (`@PJL ENTER LANGUAGE=QPDL`):

```
\x1b%-12345X@PJL JOB NAME="..."
@PJL ENTER LANGUAGE=URF
<dados URF>
\x1b%-12345X@PJL EOJ
\x1b%-12345X
```

É só isso que o `urftopjl` faz. O pipeline fica assim:

```
PDF ──► cgpdftoraster ──► URF ──► urftopjl ──► backend usb ──► impressora
        (Apple, arm64)            (este repo)   (Apple)
```

Nenhuma linguagem de página obtida por engenharia reversa. Nenhum binário do
fabricante.

### Instalação

```sh
git clone https://github.com/atilac/xerox-phaser-3020-macos.git
cd xerox-phaser-3020-macos
sudo ./scripts/install.sh
```

O `sudo` é necessário porque o CUPS se recusa a executar filtros que não
pertençam ao `root` e que não estejam em `/Library/Printers`.

Depois:

```sh
lp -d Xerox_Phaser_3020_USB arquivo.pdf
```

Para desinstalar: `sudo ./scripts/uninstall.sh`.

### Só compilar

```sh
clang -O2 -Wall -Wextra -arch arm64 -arch x86_64 -o src/urftopjl src/urftopjl.c
python3 scripts/make-ppd.py ppd/Xerox_Phaser_3020_USB.ppd
```

O PPD usa **A4** por padrão; para Carta, edite `DEFAULT_PAPER` em
`scripts/make-ppd.py` e gere de novo.

---

## Wi-Fi Direct

A impressora também pode funcionar como ponto de acesso próprio — útil quando
não há roteador nenhum. Ative em **Properties → Network Settings → Wi-Fi →
Wi-Fi Direct**, conecte-se à rede dela (`DIRECT-xx-<nome do dispositivo>`) e
crie a fila:

```sh
lpadmin -p Xerox_3020_WiFiDirect -E \
        -v ipp://192.168.3.1/ipp/print \
        -P /Library/Printers/PPDs/Contents/Resources/Xerox_Phaser_3020_USB.ppd
```

O firmware serve **IPP nessa interface também**, então aqui não é preciso o
invólucro PJL — pelo mesmo motivo que o Wi-Fi normal funciona sem driver.
Reutilizamos o PPD do USB apenas porque ele já traz a geometria de página
correta; o filtro dele é inofensivo por IPP.

Atenção: seu Mac fica **sem internet** enquanto estiver nessa rede, e as outras
duas filas ficam inacessíveis até você voltar para o Wi-Fi normal.

---

## O que este repositório deliberadamente não contém

**Nenhum binário da Xerox.** Nem `rastertosec`, nem `prefilter`, nem
`commandtosec`, nem `libscmssc.dylib`, nem o PPD original. São proprietários e
redistribuí-los é violação de direitos autorais. Tudo aqui foi escrito do zero
e está sob licença MIT.

---

## Se você precisar de QPDL

O formato do driver do fabricante é o **QPDL (SPL2)** — o binário dele emite
`@PJL ENTER LANGUAGE=QPDL`, e neste modelo a compressão JBIG está desligada
(`eJBIGSupH` não aparece no PPD). A análise estática do `rastertosec` (que não
está strippado) dá o cabeçalho de banda com 11 bytes:

| Offset | Tam. | Campo |
|---|---|---|
| 0 | 1 | marcador de banda `0x0C` |
| 1 | 1 | número da banda |
| 2 | 2 | largura (big-endian) |
| 4 | 2 | altura (big-endian) |
| 6 | 1 | método de compressão |
| 7 | 4 | tamanho dos dados + 4 (big-endian) |

o que coincide com a implementação de QPDL do
[SpliX](https://github.com/OpenPrinting/splix). O `BandHeight` é 64 a 300 dpi e
128 nas demais resoluções.

**Você quase certamente não precisa disso** — o URF funciona e é mais simples.
Está documentado aqui caso algum modelo desta família não suporte URF.

## Créditos e trabalhos relacionados

- [OpenPrinting/splix](https://github.com/OpenPrinting/splix) — a implementação de referência de QPDL/SPL
- [boredjar-com/splix-macos](https://github.com/boredjar-com/splix-macos) — SpliX compilado nativamente para Apple Silicon
- [adpopescu338/xerox-phaser-3020-apple-silicon](https://github.com/adpopescu338/xerox-phaser-3020-apple-silicon) — a abordagem via Rosetta 2

## Licença

MIT — veja [LICENSE](LICENSE).
