# Router Manager

Aplicación de escritorio para gestionar dispositivos conectados a tu router a través de la API ubus.

## Características

- **Panel de control**: Vista general de dispositivos conectados, horarios activos e información del router
- **Gestión de dispositivos**: Ver, buscar, filtrar, bloquear/desbloquear dispositivos
- **Horarios**: Crear y gestionar horarios de acceso a internet por dispositivo
- **Dispositivos invitados**: Marcar dispositivos como invitados con acceso temporal
- **Configuración**: Conexión al router, intervalo de actualización automática

## Requisitos

- Python 3.12+
- Router compatible con API ubus (OpenWrt, etc.)

## Instalación

### Desde el ejecutable (Windows)

Descarga `RouterManager-Windows.exe` desde [Releases](../../releases/latest).

### Desde código fuente

```bash
# Clonar el repositorio
git clone https://github.com/axelmrak/router-app-v2.git
cd router-app-v2

# Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar
python main.py
```

## Uso

1. Ejecuta la aplicación
2. Ve a **Configuración**
3. Ingresa la IP de tu router, usuario y contraseña
4. Haz clic en **Probar conexión**
5. Si la conexión es exitosa, haz clic en **Guardar y conectar**

## Desarrollo

### Estructura del proyecto

```
router-app-v2/
├── app/
│   ├── ui/           # Interfaces de usuario
│   ├── widgets/      # Componentes reutilizables
│   ├── dialogs/      # Diálogos modales
│   ├── services/     # Lógica de negocio
│   ├── router/       # Cliente API del router
│   ├── models/       # Modelos de datos
│   ├── store/        # Estado global
│   ├── utils/        # Utilidades
│   └── styles/       # Estilos y temas
├── config/           # Configuración
├── database/         # Base de datos local
├── assets/           # Recursos estáticos
└── main.py          # Punto de entrada
```

### Tecnologías

- **PySide6**: Framework de UI
- **requests**: Cliente HTTP
- **SQLite**: Base de datos local
- **PyInstaller**: Empaquetado

## Licencia

MIT

## Autor

Hecho por [Axel Mrak](https://github.com/axelmrak)
