# Servidor sistemas-sp

Documento de referencia para conexion SSH al servidor sistemas-sp y acceso a la infraestructura SmartPadel.

---

## Conexion a sistemas-sp

### Datos del Servidor

| Campo    | Valor                               |
| -------- | ----------------------------------- |
| Host SSH | `sistemas-sp`                       |
| HostName | `sistemas.smartpadelautomation.com` |
| Puerto   | 22                                  |

### Conexion

```bash
# Conexion con clave RSA
ssh -i ~/.ssh/rsa_sistemas-sp_<usuario> -o IdentitiesOnly=yes <usuario>@sistemas.smartpadelautomation.com

# Ejecutar comando remoto
ssh -i ~/.ssh/rsa_sistemas-sp_<usuario> -o IdentitiesOnly=yes <usuario>@sistemas.smartpadelautomation.com "comando"
```

---

## Acceso a Clubs Domotica

Clubs SmartPadel conectados via VPN. Formato: `spNNNN` donde NNNN son 4 digitos.

### Nomenclatura

| Host      | VPN   | Red       | Ejemplo IP            |
| --------- | ----- | --------- | --------------------- |
| `spNNNNa` | VPN A | 10.88.x.x | sp0323a -> 10.88.2.69 |
| `spNNNNb` | VPN B | 10.8.x.x  | sp0323b -> 10.8.2.69  |

### Conexion desde sistemas-sp

```bash
# Conectar a club (requiere ejecutar como root en sistemas-sp)
sudo ssh sp0323b

# Ejecutar comando remoto
sudo ssh sp0323b "hostname && uptime"
```

### Verificar IP de un Club

La IP de cada club esta definida en el archivo de configuracion SSH:

```bash
# Ver configuracion de un club
sudo grep -A5 "Host sp0323b" /root/.ssh/config_clubs
```

### Claves SSH

```bash
# Ubicacion claves en sistemas-sp
/opt/sp_domotica/ssh/spNNNN_rsa      # Privada
/opt/sp_domotica/ssh/spNNNN_rsa.pub  # Publica
```

---

## Acceso a Maquinas Vending

Maquinas de vending conectadas via VPN B. Formato: `v####b`.

### Nomenclatura

| Host     | Red        | Ejemplo              |
| -------- | ---------- | -------------------- |
| `v####b` | 10.8.200.x | v0001b -> 10.8.200.1 |

### Conexion desde sistemas-sp

```bash
# Conectar a maquina vending (requiere root)
sudo ssh v0001b

# Ejecutar comando remoto
sudo ssh v0001b "hostname"
```

### Verificar IP de una Maquina Vending

```bash
# Ver configuracion de una maquina
sudo grep -A5 "Host v0001b" /root/.ssh/sp-vending/config-sp-vending
```

### Claves SSH

```bash
# Ubicacion claves en sistemas-sp
/root/.ssh/sp-vending/v####_rsa      # Privada
/root/.ssh/sp-vending/v####_rsa.pub  # Publica
```

---

## Acceso a Servidores VPN

### VPN A (AWS)

| Campo    | Valor                           |
| -------- | ------------------------------- |
| Host SSH | `vpna`                          |
| HostName | `vpna.smartpadelautomation.com` |
| Usuario  | `root`                          |
| Clave    | `/root/.ssh/vpna_rsa`           |

```bash
# Desde sistemas-sp
sudo ssh vpna "hostname"
```

### VPN B (GCP)

| Campo    | Valor                           |
| -------- | ------------------------------- |
| Host SSH | `vpnb`                          |
| HostName | `vpnb.smartpadelautomation.com` |
| Usuario  | `root`                          |
| Clave    | `/root/.ssh/vpnb_rsa`           |

```bash
# Desde sistemas-sp
sudo ssh vpnb "hostname"
```

### Directorios VPN

| Servidor | Ruta CCD            | Contenido                           |
| -------- | ------------------- | ----------------------------------- |
| vpna     | `/etc/openvpn/ccd/` | Configuracion clubs VPN A           |
| vpnb     | `/etc/openvpn/ccd/` | Configuracion clubs VPN B + vending |

---

## Acceso a Servidor Booking (Reservas)

Servidor AWS que gestiona el sistema de reservas SmartPadel.

### Datos del Servidor

| Campo    | Valor                                                 |
| -------- | ----------------------------------------------------- |
| Host SSH | `booking`                                             |
| HostName | `ec2-18-100-123-167.eu-south-2.compute.amazonaws.com` |
| Usuario  | `admin`                                               |
| Puerto   | 22                                                    |

### Conexion (desde equipo local)

```bash
# Interactiva
ssh booking

# Para scripts
ssh -o "RemoteCommand=none" booking "comando"
```

### Servicios en el Servidor

| Servicio                 | Puerto | Ruta                      |
| ------------------------ | ------ | ------------------------- |
| SmartPadelBooking (Java) | 8082   | `/opt/SmartPadelBooking/` |
| SmartPadelSubscribers    | -      | -                         |

### Logs

```bash
# Log principal booking
sudo tail -100 /opt/SmartPadelBooking/log/smartpadelBooking.log
```

---

## Acceso a Servidor Cloud Domotica (AWS)

Servidor AWS que gestiona SmartPadelCloud (domotica cloud).

### Datos del Servidor

| Campo    | Valor                                              |
| -------- | -------------------------------------------------- |
| Nombre   | `smartpadel-cloud`                                 |
| HostName | `ec2-18-101-2-34.eu-south-2.compute.amazonaws.com` |
| Usuario  | `admin`                                            |

### Conexion (desde equipo local)

```bash
ssh -o IdentitiesOnly=yes -i ~/.ssh/id_rsa_smartpadelcloud_admin admin@ec2-18-101-2-34.eu-south-2.compute.amazonaws.com
```

---

## Resumen de Redes

| Red           | Rango      | Uso                          |
| ------------- | ---------- | ---------------------------- |
| VPN A         | 10.88.x.x  | Clubs domotica (alternativa) |
| VPN B         | 10.8.x.x   | Clubs domotica (principal)   |
| VPN B Vending | 10.8.200.x | Maquinas vending             |
| AWS VPC       | 172.31.x.x | Servidores cloud AWS         |
| GCP           | 10.204.x.x | Servidores GCP               |

---

## Resumen de Conexiones desde sistemas-sp

```bash
# Ejecutar como root en sistemas-sp

# Club domotica
sudo ssh sp0323b "hostname"

# Maquina vending
sudo ssh v0001b "hostname"

# Servidor VPN A
sudo ssh vpna "hostname"

# Servidor VPN B
sudo ssh vpnb "hostname"
```

---

*Documento generado: 2026-02-04*
*Version: 1.1.0*
