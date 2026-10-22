# Registro da investigação

Diário técnico de como a Xerox Phaser 3020BI voltou a imprimir no macOS 27 /
Apple Silicon. Inclui as hipóteses **erradas**, porque elas custaram a maior
parte do tempo e são o que falta na documentação pública existente.

Data: 21 de outubro de 2026.
Máquina: Apple M5 Pro, macOS 27.0.1 (build 26A434), arm64.

> Este documento está em português. O [README](../README.md) público está em
> inglês, português e espanhol.

---

## 1. Ponto de partida

Material disponível: a pasta `Printer Driver` do driver oficial (versão
1.06.00) e, depois, o `Xerox_Phaser_3020_CD-Driver_1.02.01.dmg`.

Sintoma: a impressora funcionava até o macOS 10.6 e não funciona mais.

### Por que parou — três causas empilhadas

| # | Causa | Evidência |
|---|---|---|
| 1 | Nenhum binário tem fatia arm64 | `lipo -archs` → `i386 x86_64` em todos |
| 2 | Rosetta 2 não instalado | `./rastertosec` → `bad CPU type in executable` |
| 3 | A Xerox parou no macOS 10.14 | página oficial de downloads |

O CUPS reporta isso como *"Filter failed"*, que não diz nada sobre a causa
real.

### O DMG não acrescentou nada

Montado, extraído e comparado: traz a versão **1.04.00**, mais antiga que a
1.06.00 já disponível. Os PPDs são byte-idênticos exceto a linha
`*FileVersion`. Nenhuma versão tem fatia arm64.

---

## 2. Plano original (descartado)

O plano inicial era reimplementar o driver:

1. Portar o [SpliX](https://github.com/OpenPrinting/splix) para arm64
2. Escrever um PPD da 3020 (o SpliX não tem)
3. Substituir o halftoning do `libscmssc.dylib` proprietário
4. Validar contra a saída do binário original

**Nada disso foi necessário.** Ver seções 4 e 6.

### O que a engenharia reversa rendeu

O `rastertosec` **não está strippado** — 283 símbolos com nomes originais
(`WriteBandHeaderQPDL`, `compressBandedJBIG`, `MonoFBBDistribute`,
`DoBandProcessCMS3`…). Isso permitiu análise estática sem executar nada,
substituindo os *golden files* que exigiriam Rosetta.

Desmontando `WriteBandHeaderQPDL` saiu o cabeçalho de banda byte a byte:

| Offset | Tam. | Campo |
|---|---|---|
| 0 | 1 | marcador `0x0C` |
| 1 | 1 | número da banda |
| 2 | 2 | largura (big-endian) |
| 4 | 2 | altura (big-endian) |
| 6 | 1 | método de compressão |
| 7 | 4 | tamanho dos dados + 4 (big-endian) |

Coincide com a implementação de QPDL do SpliX — confirmação independente,
vinda do binário do fabricante. Também se extraiu que `BandHeight` é 64 a
300 dpi e 128 nas demais resoluções (batendo com `eband6: "128"` do PPD), e que
o JBIG está **desligado** para este modelo (`eJBIGSupH` ausente do PPD).

Isso está preservado no README como contingência, caso algum modelo irmão não
suporte URF. **Não entrou em nenhuma linha de código.**

---

## 3. Hipóteses erradas

Registradas porque o sintoma era idêntico em todas: o trabalho sai da fila, o
CUPS reporta `successful-ok`, nenhum erro em lugar nenhum, e nada é impresso.

### 3.1 "O nível de toner caiu, logo imprimiu" — errado

`marker-levels` foi de 46 para 45 e isso foi tomado como prova de impressão.
Era coincidência: as folhas de configuração que o usuário imprimiu pelo botão
WPS caíram na mesma janela de tempo.

**`marker-levels` tem granularidade de dezenas de páginas** e não serve nem
para confirmar nem para descartar uma impressão. O indicador correto é o
contador do fusor (seção 7).

### 3.2 "Mandei um .txt, por isso não imprimiu" — errado

Plausível: o PPD declara só `image/urf`. Mas o PDF também não imprimiu.

### 3.3 "O CUPS manda PDF sem converter para URF" — errado

Também plausível, porque `application/pdf` não está em
`document-format-supported`. O log de depuração desmentiu: a cadeia
`cgpdftoraster (application/pdf to image/urf)` estava correta e completa.

### 3.4 A causa real: Power Saver de 1 minuto

A impressora adormecia, o rádio Wi-Fi desligava e ela sumia da rede. O CUPS
entregava para o vazio e marcava sucesso. Ajustado para 60 min, a fila de
Wi-Fi passou a funcionar sem nenhuma outra mudança.

**Recomendação: deixe sempre no máximo (60 minutos).** É o maior valor que o
firmware aceita. Qualquer coisa menor e a impressora volta a sair da rede entre
um trabalho e outro, trazendo de volta todos os sintomas — inclusive o pior
deles, o `successful-ok` sem impressão.

### 3.5 Um falso positivo no USB

Um envio de URF sem invólucro PJL pelo backend USB coincidiu com a conclusão
atrasada de um trabalho de Wi-Fi, e o contador subiu. Pareceu que URF cru
funcionava no USB. O teste de controle seguinte não reproduziu — foi o que
levou à investigação do PJL (seção 6).

**Lição:** com uma impressora que dorme e tem fila interna, medir
imediatamente antes e depois de **cada** envio, um de cada vez.

---

## 4. Descoberta: o Wi-Fi não precisa de driver

A impressora declara, por IPP:

```
ipp-features-supported    = document-object, airprint-1.3
urf-supported             = W8,RS600,IS1,CP1,IFU0,PQ4,OB10,V1.3
document-format-supported = application/octet-stream, application/x-QPDL, image/urf
document-format-preferred = image/urf
```

E a folha de configuração confirma: `AirPrint : Installed/Enabled`.

Isso era contraintuitivo o bastante para ter sido ativamente duvidado durante a
análise: a 3020 é host-based (GDI), sem PostScript nem PCL, com 128 MB de RAM.
A explicação é que URF chega em bandas comprimidas, não como página inteira — e
que a Xerox continuou atualizando o firmware (o desta máquina é de **setembro
de 2021**) por sete anos depois de abandonar o driver de Mac.

### O impasse do Easy Wireless Setup

O utilitário oficial para colocar a impressora no Wi-Fi é **Intel-only e roda
por USB** — travado pelo mesmo motivo que o driver. Não dá para pôr a
impressora na rede usando o Mac que não roda o driver.

**O WPS quebra o impasse**, e o rádio é **só 2.4 GHz** (802.11b/g/n):
num roteador dual-band, o botão de 5 GHz nunca vai parear.

---

## 5. Por que o USB é diferente

Sobre IPP, o atributo `document-format` identifica o fluxo. **USB cru não
carrega metadado nenhum** — é um fluxo de bytes sem rótulo. O firmware recebe
os bytes corretos, não consegue identificar o que são e descarta em silêncio.

O device ID IEEE-1284 mostra que a impressora fala URF no cabo:

```
MFG:Xerox;MDL:Phaser 3020;CMD:SPL,URF,FWV,EXT;MODE:SPL3,R000105;
CLS:PRINTER;CID:XR_GDI3_Class01_Mono;SERN:<serial>;
```

`CMD` inclui `URF` — foi isso que tornou o filtro QPDL desnecessário.

### IPP-over-USB foi verificado e não existe

```
bInterfaceClass    = 7   (Printer)
bInterfaceProtocol = 2   (bidirecional / IEEE 1284.4)
```

IPP-USB exigiria protocolo **4**. Confirmado também pelo `lpinfo -v`, que lista
`usb://` e nunca `ippusb://`.

---

## 6. A solução do USB

Anunciar a linguagem em PJL, exatamente como o driver do fabricante faz com o
formato dele (`@PJL ENTER LANGUAGE=QPDL`):

```
\x1b%-12345X@PJL JOB NAME="..."
@PJL ENTER LANGUAGE=URF
<dados URF>
\x1b%-12345X@PJL EOJ
\x1b%-12345X
```

Medido de forma controlada: **sem** o invólucro o contador não se move; **com**
ele vai de 354 para 355.

O pipeline final:

```
PDF ──► cgpdftoraster ──► URF ──► urftopjl ──► backend usb ──► impressora
        (Apple, arm64)            (este repo)   (Apple)
```

### Detalhe de implantação

O CUPS recusa filtros que não pertençam ao `root` ou estejam fora de
`/Library/Printers` — a mensagem é `Unable to start filter … Invalid argument`,
que não menciona permissões. Daí o `sudo` no instalador.

Note que `lpadmin` e `cupsctl` **não** precisam de `sudo` se o usuário estiver
no grupo `_lpadmin` (padrão para contas de administrador no macOS).

---

## 7. Ferramentas de diagnóstico

### Contador de páginas (o indicador confiável)

```sh
curl -s http://<ip>/sws/app/information/supplies/supplies.json \
  | tr -d ' \t' | grep -oE 'fuser_kit:[0-9]+'
```

`fuser_kit` conta folhas que passaram fisicamente pelo fusor. Esse endpoint
responde **sem autenticação**. Outros campos úteis no mesmo JSON:
`toner_black.cnt`, `toner_black.remaining`, `capa`, `serial`.

### Estado por IPP

```sh
ipptool -tv ipp://<ip>/ipp/print \
  /usr/share/cups/ipptool/get-printer-attributes.test
```

### A impressora está no USB?

```sh
/usr/libexec/cups/backend/usb          # roda sem sudo, mostra o device ID
```

### Enviar um arquivo direto, sem o CUPS

```sh
DEVICE_URI="usb://Xerox/Phaser%203020?serial=<serial>" \
  /usr/libexec/cups/backend/usb 1 "$USER" titulo 1 "" arquivo.urf
```

### Gerar URF a partir de um PDF

```sh
cupsfilter -p /etc/cups/ppd/<fila>.ppd -m image/urf -o media=A4 in.pdf > out.urf
```

Deve começar com `UNIRAST\0`. Se começar com `3SaR`, saiu CUPS Raster em vez de
URF — falta a variável `FINAL_CONTENT_TYPE` que o cupsd define nos jobs reais.

### Log de depuração do CUPS

```sh
cupsctl --debug-logging        # sem sudo se estiver no grupo _lpadmin
# … reproduzir o problema …
grep -E '\[Job N\]' /var/log/cups/error_log
cupsctl --no-debug-logging     # não esquecer: o log cresce sem limite
```

---

## 8. Configuração verificada

Três filas, todas confirmadas pelo contador do fusor:

| Fila | Caminho | Verificação |
|---|---|---|
| `Xerox_Phaser_3020__XRX…_` | Wi-Fi / AirPrint (`dnssd://…_ipp._tcp`) | 353 → 354 |
| `Xerox_Phaser_3020_USB` | USB + `urftopjl` | 355 → 356 |
| `Xerox_3020_WiFiDirect` | Wi-Fi Direct (`ipp://192.168.3.1`) | 356 → 357 |

O firmware serve IPP na interface de Wi-Fi Direct também, então ali também não
é preciso o invólucro PJL.

### Dados do hardware

```
Modelo           Phaser 3020 (BI)        21 ppm, 128 MB RAM, 600 MHz
Firmware         V3.50.21.03 (set/2021)  IOT V1.00.07, NIC V6.01.16
SPL              5.90 (mai/2014)
Rádio            802.11b/g/n, 2.4 GHz    (sem 5 GHz)
USB              VID 0x0924 / PID 0x42D5
```

### Ajustes feitos na impressora

- Power Saver: 1 min → **60 min, o máximo** (crítico; ver 3.4)
- Bandeja 1: Letter → **A4**
- Wi-Fi Direct: desativado → **ativado**

---

## 9. Pendências

- A senha de administrador da impressora continua a padrão. A própria API
  confirma: `GXI_ADMIN_WUI_HAS_DEFAULT_PASS: 1`. Qualquer pessoa na rede local
  pode reconfigurá-la.
- A chave do Wi-Fi Direct é a de fábrica e foi exposta em fotos da folha de
  configuração durante a investigação. Convém trocar.

---

## 10. Notas sobre a interface web (SWS)

A interface CentreWare é ExtJS de 2014 e **não navega no Chrome atual** — a
página carrega, o login funciona, mas nenhum link responde. O Safari funciona.

A API JSON por trás dela é utilizável com uma sessão autenticada
(`admin` / senha padrão). Endpoints confirmados:

| Endpoint | Autenticação |
|---|---|
| `/sws/app/information/home/home.json` | não |
| `/sws/app/information/supplies/supplies.json` | não |
| `/sws/app/settings/network/wireless/wireless.json` | **sim** |

Sem sessão, os endpoints protegidos devolvem
`{success: false, authRequired: true}`. Basic e Digest **não** funcionam — a
sessão tem que vir da aplicação. Links profundos
(`index.html?link=…`) são ignorados.

`GSI_WIRELESS_P2P_ENABLE` é o campo do Wi-Fi Direct. Escrever nesse endpoint
reconfigura **toda** a parte sem fio — um POST malformado pode derrubar a
impressora da rede e exigir novo pareamento por WPS.

---

## 11. Conclusão

Nenhuma linha do driver original foi reaproveitada, e nenhuma linha de código
foi necessária para os dois caminhos sem fio. A impressora já falava uma
linguagem moderna (URF) nas três interfaces desde um firmware de 2021.

O que faltava era colocá-la na rede — bloqueado por um utilitário Intel-only —
e, no cabo, um rótulo de 90 bytes dizendo o que estava chegando.

**O diagnóstico levou uma sessão inteira. A correção tem 87 linhas de C, das
quais 3 importam.**
