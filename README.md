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

Ligacao recomendada (SPI0 CE0):
- **Pino 1**: 3V3 (VCC)
- **Pino 6**: GND
- **Pino 23**: SCLK / GPIO11
- **Pino 19**: MOSI / GPIO10
- **Pino 24**: CE0 / GPIO8 (CS)
- **Pino 18**: GPIO24 (DC/A0)
- **Pino 22**: GPIO25 (RST/RES)
- **Backlight (BL/LED)**: 3V3 (ou via controle externo)

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
