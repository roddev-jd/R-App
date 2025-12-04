# Sistema de Cumpleaños - Guía de Uso

## Descripción

Sistema automatizado para gestionar y mostrar cumpleaños del equipo. Muestra automáticamente solo los cumpleaños del mes actual con animaciones festivas y permite enviar saludos por email.

## Características

- ✅ **Actualización Automática**: Solo muestra cumpleaños del mes en curso
- ✅ **Categorización por Departamento**: Diseño, Redacción, Coordinación
- ✅ **Diseño Festivo**: Animaciones de tortas, confetti y colores celebratorios
- ✅ **Email Directo**: Botón para enviar saludos por correo
- ✅ **Responsive**: Funciona en desktop, tablet y móvil
- ✅ **API REST**: Endpoints para consultar cumpleaños programáticamente

## Estructura de Archivos

```
FlexStart/
├── data/
│   ├── birthdays.json          # Base de datos de cumpleaños
│   └── BIRTHDAYS_README.md     # Esta documentación
├── birthdays.html              # Página de visualización
├── backend/app.py              # API endpoints
└── assets/css/main.css         # Estilos del botón
```

## Formato del Archivo JSON

### Estructura Completa

```json
{
  "metadata": {
    "last_updated": "2025-10-20",
    "total_users": 24,
    "version": "1.0"
  },
  "users": [
    {
      "id": 1,
      "name": "Nombre Apellido",
      "birthday": "MM-DD",
      "email": "correo@ripley.cl",
      "photo": "/assets_flexstart/img/team/team-1.jpg",
      "department": "Diseño"
    }
  ]
}
```

### Campos Obligatorios

- **id**: Número único (entero)
- **name**: Nombre completo (string)
- **birthday**: Formato "MM-DD" (mes-día, ej: "10-15" para 15 de octubre)
- **email**: Correo electrónico válido
- **photo**: Ruta a la foto (usar `/assets_flexstart/img/team/team-X.jpg`)
- **department**: Departamento del usuario

### Departamentos Válidos

- **Diseño** → Ícono: 🎨 (palette)
- **Redacción** → Ícono: ✏️ (pen)
- **Coordinación** → Ícono: ⚙️ (gear)
- **Equipo** → Ícono: 👥 (people) [por defecto]

## Cómo Agregar una Persona

1. Abre el archivo `FlexStart/data/birthdays.json`

2. Agrega un nuevo objeto en el array `users`:

```json
{
  "id": 25,
  "name": "Nuevo Usuario",
  "birthday": "03-25",
  "email": "nuevo.usuario@ripley.cl",
  "photo": "/assets_flexstart/img/team/team-1.jpg",
  "department": "Diseño"
}
```

3. Actualiza el campo `total_users` en `metadata`

4. Actualiza la fecha en `last_updated`

5. Guarda el archivo

6. Reinicia el servidor (no es necesario, el cambio se refleja automáticamente)

## Cómo Editar una Persona

1. Busca el usuario por su `id` o `name`
2. Modifica los campos necesarios
3. Mantén el formato de fecha "MM-DD"
4. Guarda el archivo

## Cómo Eliminar una Persona

1. Elimina el objeto completo del array `users`
2. Actualiza `total_users` en `metadata`
3. Guarda el archivo

## API Endpoints

### 1. Cumpleaños del Mes Actual

```http
GET /api/birthdays/current-month
```

**Respuesta:**
```json
{
  "status": "success",
  "current_month": 10,
  "count": 2,
  "birthdays": [
    {
      "id": 19,
      "name": "Gabriel Ortiz",
      "birthday": "10-14",
      "email": "gabriel.ortiz@ripley.cl",
      "photo": "/assets_flexstart/img/team/team-3.jpg",
      "department": "Diseño",
      "day": 14
    }
  ]
}
```

### 2. Todos los Cumpleaños (Agrupados por Mes)

```http
GET /api/birthdays/all
```

**Respuesta:**
```json
{
  "status": "success",
  "metadata": {...},
  "total_users": 24,
  "birthdays_by_month": {
    "1": [...],
    "2": [...],
    ...
  }
}
```

### 3. Cumpleaños de un Mes Específico

```http
GET /api/birthdays/month/{month}
```

**Ejemplo:**
```http
GET /api/birthdays/month/12
```

**Respuesta:**
```json
{
  "status": "success",
  "month": 12,
  "count": 2,
  "birthdays": [...]
}
```

## Acceso a la Página

### Desde el Nav

1. Click en el botón **"Happy Birthday"** (botón rosa con torta animada)
2. Se abre la página de cumpleaños del mes actual

### Directo

```
http://127.0.0.1:8005/birthdays.html
```

## Fotos de Usuarios

### Ubicación

Las fotos deben estar en:
```
FlexStart/assets/img/team/
```

### Fotos Disponibles

- `team-1.jpg`
- `team-2.jpg`
- `team-3.jpg`
- `team-4.jpg`

### Agregar Nuevas Fotos

1. Coloca la foto en `FlexStart/assets/img/team/`
2. Nombre recomendado: `team-X.jpg` (donde X es un número)
3. Formato: JPG, PNG
4. Tamaño recomendado: 500x500px (cuadrado)
5. Actualiza el campo `photo` en el JSON

## Solución de Problemas

### La página muestra "No hay cumpleaños este mes"

- **Causa**: No hay usuarios con cumpleaños en el mes actual
- **Solución**: Verifica el archivo JSON y confirma que hay fechas para el mes

### Error 404 al abrir la página

- **Causa**: El servidor no está corriendo o la ruta no está configurada
- **Solución**: Reinicia el servidor con `python lanzador.py`

### Las fotos no se muestran

- **Causa**: La ruta de la foto es incorrecta
- **Solución**: Verifica que la ruta en el JSON coincida con la ubicación real

### El departamento no muestra el ícono correcto

- **Causa**: El nombre del departamento no coincide exactamente
- **Solución**: Usa exactamente: "Diseño", "Redacción", "Coordinación", o "Equipo"

## Personalización

### Cambiar Colores

Edita las variables CSS en `birthdays.html`:

```css
:root {
  --birthday-primary: #ff6b9d;    /* Rosa principal */
  --birthday-secondary: #ffd700;  /* Dorado */
  --birthday-light: #fff0f6;      /* Rosa claro */
  --birthday-dark: #c06c84;       /* Rosa oscuro */
}
```

### Agregar Nuevos Departamentos

1. Edita la función `getDepartmentIcon()` en `birthdays.html`:

```javascript
function getDepartmentIcon(department) {
  const icons = {
    'Diseño': 'bi bi-palette-fill',
    'Redacción': 'bi bi-pen-fill',
    'Coordinación': 'bi bi-gear-fill',
    'Tu Departamento': 'bi bi-icon-name', // Agregar aquí
    'Equipo': 'bi bi-people-fill'
  };
  return icons[department] || 'bi bi-star-fill';
}
```

2. Busca íconos en: [Bootstrap Icons](https://icons.getbootstrap.com/)

## Mantenimiento

### Actualización Mensual

El sistema se actualiza **automáticamente** cada mes. No requiere intervención manual.

### Backup

Recomendamos hacer backup del archivo `birthdays.json` regularmente:

```bash
cp FlexStart/data/birthdays.json FlexStart/data/birthdays.backup.json
```

### Validación del JSON

Para verificar que el JSON es válido:

```bash
python3 -c "import json; json.load(open('FlexStart/data/birthdays.json')); print('✓ JSON válido')"
```

## Ejemplos Completos

### Agregar 3 Personas Nuevas

```json
{
  "id": 25,
  "name": "José Martínez",
  "birthday": "06-15",
  "email": "jose.martinez@ripley.cl",
  "photo": "/assets_flexstart/img/team/team-1.jpg",
  "department": "Diseño"
},
{
  "id": 26,
  "name": "Carolina López",
  "birthday": "06-22",
  "email": "carolina.lopez@ripley.cl",
  "photo": "/assets_flexstart/img/team/team-2.jpg",
  "department": "Redacción"
},
{
  "id": 27,
  "name": "Ricardo Sánchez",
  "birthday": "07-10",
  "email": "ricardo.sanchez@ripley.cl",
  "photo": "/assets_flexstart/img/team/team-3.jpg",
  "department": "Coordinación"
}
```

## Notas Importantes

1. **Formato de Fecha**: Siempre usar "MM-DD" (dos dígitos para mes y día)
2. **IDs Únicos**: Cada usuario debe tener un ID único
3. **Comillas**: Usar comillas dobles (") en JSON, no simples (')
4. **Comas**: No olvidar la coma entre objetos (excepto el último)
5. **Encoding**: El archivo debe estar en UTF-8 para caracteres especiales

## Soporte

Para problemas o preguntas:
- Contactar al equipo de desarrollo
- Revisar logs del servidor en caso de errores
- Verificar la consola del navegador (F12) para errores JavaScript

---

**Última actualización**: 2025-10-20
**Versión**: 1.0
**Autor**: Rodrigo Jara Duarte
