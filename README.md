# i2c-rasp

Monitor em Python para Raspberry Pi Zero 2 W com display LCD I2C, consumindo
metricas Prometheus expostas por pfSense/Kontrol via node exporter.

## Configuracao

Os equipamentos entram como lista de hosts, sem informar `/metrics`:

```toml
[[hosts]]
name = "kontrol-lab"
host = "10.0.0.1"
port = 9100

[[hosts]]
name = "kontrol-cloud"
host = "lab.kontrol.com.br"
port = 9100
```

O programa monta a URL final no formato `http://host:porta/metrics` e percorre
os hosts um por um.

## Estado inicial

O alvo local `http://10.0.0.1:9100/metrics` respondeu durante os testes.
O endpoint remoto `http://lab.kontrol.com.br:9100/metrics` recusou conexao na
porta 9100 durante os testes iniciais; quando isso ocorre, o monitor mostra uma
pagina de erro para o host e continua para o proximo.

Por enquanto o scraper filtra apenas as metricas necessarias para:

- `node_cpu_seconds_total`
- `node_cpu_temperature_celsius`
- `node_hwmon_temp_celsius`, `node_thermal_zone_temp`
- `node_memory_size_bytes`, `node_memory_free_bytes`, `node_memory_inactive_bytes`
- `node_memory_MemTotal_bytes`, `node_memory_MemAvailable_bytes`
- `node_memory_swap_size_bytes`, `node_memory_swap_used_bytes`
- `node_memory_SwapTotal_bytes`, `node_memory_SwapFree_bytes`
- `node_network_receive_bytes_total`, `node_network_transmit_bytes_total`
- `node_pfsense_interface_info`, `node_pfsense_interface_up`
- `node_filesystem_size_bytes`, `node_filesystem_avail_bytes`
- `node_uname_info`

## Rodando em modo terminal

```powershell
python -m i2c_rasp.cli --config config.example.toml --once
```

Ou apontando direto para outro host:

```powershell
python -m i2c_rasp.cli --host 10.0.0.1 --port 9100 --once
```

## Proximos passos

1. Validar as paginas do modo terminal com o equipamento real.
2. Adicionar o driver LCD I2C usando `RPLCD`/`smbus2`.
3. Instalar como servico `systemd` no Raspberry Pi.
