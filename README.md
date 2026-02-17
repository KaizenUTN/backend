# Django API Project

API REST desarrollada con Django y Django REST Framework con soporte para múltiples ambientes.

## 📋 Requisitos

- Python 3.12+
- PostgreSQL 15+ (para producción)
- Docker & Docker Compose (opcional)

## 🚀 Inicio Rápido

### Opción 1: Local (sin Docker)

```bash
# Clonar el repositorio
git clone <your-repo-url>
cd Cliente

# Crear y activar ambiente virtual
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows PowerShell
# source venv/bin/activate    # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env.dev

# Ejecutar migraciones
python manage.py migrate --settings=config.settings.dev

# Crear superusuario
python manage.py createsuperuser --settings=config.settings.dev

# Iniciar servidor
python manage.py runserver --settings=config.settings.dev
```

### Opción 2: Con Docker

```bash
# Desarrollo
docker-compose -f docker-compose.dev.yaml up --build

# Testing
docker-compose -f docker-compose.test.yaml up --build

# Producción
docker-compose -f docker-compose.prod.yaml up -d --build
```

## 📚 Documentación

Ver [docs/comandos-ambientes.md](docs/comandos-ambientes.md) para la guía completa de comandos.

## 🔧 Ambientes

- **Development**: SQLite, DEBUG=True, CORS abierto
- **Testing**: SQLite en memoria, fixtures, cobertura
- **Production**: PostgreSQL, DEBUG=False, Gunicorn, WhiteNoise

## 🧪 Tests

```bash
# Ejecutar todos los tests
pytest --ds=config.settings.test

# Con cobertura
pytest --ds=config.settings.test --cov=apps --cov-report=html
```

## 📦 Estructura del Proyecto

```
Cliente/
├── apps/               # Aplicaciones Django
│   └── users/         # App de usuarios
├── config/            # Configuración del proyecto
│   └── settings/      # Settings por ambiente
├── scripts/           # Scripts de utilidad
├── docs/              # Documentación (ignorado por git)
└── docker-compose.*.yaml
```

## 🔐 Seguridad

- Nunca commitear archivos `.env*` (excepto `.env.example`)
- Cambiar `SECRET_KEY` en producción
- Configurar correctamente `ALLOWED_HOSTS`
- Usar HTTPS en producción

## 📄 Licencia

[Tu Licencia Aquí]
