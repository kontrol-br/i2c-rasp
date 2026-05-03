# i2c-rasp

Monitor em Python para Raspberry Pi Zero 2 W, consumindo metricas Prometheus expostas por pfSense/Kontrol via node exporter.

Agora o projeto suporta **dois perfis de display**:
- **SSD1306 (OLED monocromatico, I2C, 128x64)**
- **ST7735 (display colorido SPI, 80x160)**

---

## Ligacao GPIO por perfil de display (Raspberry Pi Zero 2 W)

## 1) Perfil OLED SSD1306 (I2C)

Ligacao minima:
- **Pino 1**: 3V3 (VCC)
- **Pino 3**: SDA / GPIO2
- **Pino 5**: SCL / GPIO3
- **Pino 6**: GND

Configuracao relacionada:
- `oled.model = "ssd1306"`
- `oled.i2c_port = 1`
- `oled.i2c_address = 60` (0x3C)

## 2) Perfil ST7735 colorido (SPI, 80x160)

Pinagem tipica do modulo ST7735: **GND, VCC, SCL, SDA, RES, DC, CS, BLK**.

Ligacao recomendada no Raspberry Pi Zero 2 W (SPI0 CE0):
- **GND (display)** -> **Pino 6 (GND)**
- **VCC (display)** -> **Pino 1 (3V3)**
- **SCL (display)** -> **Pino 23 (GPIO11 / SCLK)**
- **SDA (display)** -> **Pino 19 (GPIO10 / MOSI)**
- **RES (display)** -> **Pino 22 (GPIO25)**
- **DC (display)** -> **Pino 18 (GPIO24)**
- **CS (display)** -> **Pino 24 (GPIO8 / CE0)**
- **BLK (display)** -> **Pino 1 (3V3)** (ou em pino PWM/transistor para controle de brilho)

Configuracao relacionada:
- `oled.model = "st7735"`
- `oled.spi_port = 0`
- `oled.spi_device = 0`
- `oled.spi_dc_pin = 24`
- `oled.spi_rst_pin = 25`

> Importante: habilite as interfaces no Raspberry (`raspi-config`):
> - **I2C** para SSD1306
> - **SPI** para ST7735

---

## Configuracao

Exemplo completo:

```toml
[[hosts]]
name = "kontrol-lab"
host = "10.0.0.1"
port = 9100

[display]
width = 20
height = 4
page_seconds = 4.0
refresh_seconds = 2.0

[oled]
enabled = true
model = "ssd1306" # ou "st7735"

# I2C (SSD1306)
i2c_port = 1
i2c_address = 60 # 0x3C

# Comum
rotate = 0

# SPI (ST7735)
spi_port = 0
spi_device = 0
spi_dc_pin = 24
spi_rst_pin = 25

[alert_thresholds]
cpu_percent = 85
memory_percent = 90
storage_percent = 90
temperature_celsius = 75

[buzzer]
enabled = false
gpio_pin = 18
```

---

## Comportamento das telas

- Cada metrica principal fica em sua propria tela: **CPU, Memoria, Interfaces, Storage e Temperatura**.
- Quando um limite e atingido, a pagina correspondente entra em modo flash.
- CPU, Memoria, Storage e Temperatura disparam alerta individual por tela.
- Se o buzzer estiver habilitado, ele toca enquanto a pagina em alerta estiver ativa.

### Recursos visuais do perfil ST7735

Ao escolher `oled.model = "st7735"`:
- Os textos sao renderizados em layout adaptado ao display 80x160.
- Cada linha aparece com uma cor diferente (efeito visual colorido).
- No final de cada ciclo de paginas e exibido um **arco-iris diagonal animado**, inspirado no estilo ZX Spectrum.

---

## Execucao

Instalacao:

```bash
pip install -e .
```

Rodar normalmente:

```bash
python -m i2c_rasp.cli --config config.example.toml
```

Forcar modo terminal (debug):

```bash
python -m i2c_rasp.cli --config config.example.toml --terminal --once
```

Se ocorrer `ModuleNotFoundError: No module named 'i2c_rasp'`, reinstale no mesmo interpretador que executa o comando:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m i2c_rasp.cli --config config.example.toml --once
```

Dica rapida de diagnostico:

```bash
which python3
python3 -m pip show i2c-rasp
```

- Se `pip show` nao encontrar o pacote, ele nao foi instalado nesse Python.
- Sempre use `python -m pip ...` com o mesmo `python` usado para executar o app.

---

## Troubleshooting (detectar display SPI ST7735)

Se o display colorido nao inicializar e aparecer fallback para terminal, siga este checklist.

### 1) Confirmar que SPI esta habilitado no Raspberry Pi

```bash
sudo raspi-config nonint get_spi
```

Resultado esperado:
- `0` = SPI habilitado
- `1` = SPI desabilitado

Para habilitar via CLI:

```bash
sudo raspi-config nonint do_spi 0
sudo reboot
```

### 2) Validar que o kernel expôs os devices SPI

```bash
ls -l /dev/spidev*
```

Resultado esperado (exemplo):
- `/dev/spidev0.0`
- `/dev/spidev0.1` (opcional, depende do CE usado)

Se nao existir `/dev/spidev0.0`, o display ST7735 nao sera detectado pelo perfil padrao (`spi_port=0`, `spi_device=0`).

### 3) Verificar overlays/configuracao de boot

```bash
grep -E '^(dtparam=spi=on|dtoverlay=)' /boot/firmware/config.txt
```

Resultado esperado:
- Deve existir `dtparam=spi=on`.

### 4) Checar permissao do usuario para acessar SPI

```bash
groups
```

Resultado esperado:
- Usuario deve estar no grupo `spi` (ou executar como root).

### 5) Confirmar dependencias Python do display

```bash
python -m pip show luma-core luma-oled luma-lcd pillow gpiozero RPi.GPIO spidev
```

Se `RPi.GPIO` nao estiver instalado, execute:

```bash
python -m pip install RPi.GPIO
```

Se `spidev` nao estiver instalado, execute:

```bash
python -m pip install spidev
```

Se estiver em ambiente virtual, ative antes:

```bash
source .venv/bin/activate
```

### 6) Rodar validacao rapida do app com perfil ST7735

Configure no TOML:
- `oled.enabled = true`
- `oled.model = "st7735"`
- `oled.spi_port = 0`
- `oled.spi_device = 0`
- `oled.spi_dc_pin = 24`
- `oled.spi_rst_pin = 25`

Teste de execucao unica:

```bash
python -m i2c_rasp.cli --config config.example.toml --once
```

Se aparecer erro de SPI/OLED e cair no terminal, revise:
- Pinagem fisica (SCLK/MOSI/DC/RST/CS/GND/3V3)
- `spi_device` (CE0 vs CE1)
- Alimentacao do BLK (backlight)
