# i2c-rasp

Monitor em Python para Raspberry Pi Zero 2 W com display OLED SSD1306 via I2C,
consumindo metricas Prometheus expostas por pfSense/Kontrol via node exporter.

## Ligacao OLED SSD1306 (Raspberry Pi Zero 2 W)

- Pino 1: 3v3
- Pino 3: SDA (GPIO2)
- Pino 5: SCL (GPIO3)
- Pino 6: GND

## Configuracao

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
i2c_port = 1
i2c_address = 60 # 0x3C
rotate = 0
```

## Execucao

Instale normalmente (o suporte OLED SSD1306 ja vem nas dependencias padrao):

```bash
pip install -e .
```

Rodar normalmente (OLED):

```bash
python -m i2c_rasp.cli --config config.example.toml
```

Forcar modo terminal (debug):

```bash
python -m i2c_rasp.cli --config config.example.toml --terminal --once
```
