# Respuesta de la API de hoteles — qué recibe la app

Todas las respuestas de éxito envuelven el payload en **`data`**. La app debe leer siempre `response.data` (o `response['data']`) para obtener los datos.

---

## 1. Listado de hoteles — `GET /api/hotels/`

**Query params opcionales:** `page`, `page_size`, `city`, `country`, `property_type`

**Estructura de la respuesta (200):**

```json
{
  "message": null,
  "data": {
    "count": 10,
    "page": 1,
    "page_size": 20,
    "total_pages": 1,
    "results": [
      {
        "id": "697c470802c51d31d311ce4d",
        "owner_id": "4b9e896f-708f-4cfa-b603-b1469df6986d",
        "name": "Hotel Playa del Carmen",
        "description": "Hotel frente al mar...",
        "property_type": "resort",
        "address": {
          "street": "Av. Playacar 123",
          "city": "Playa del Carmen",
          "state": "Quintana Roo",
          "country": "México",
          "postal_code": "77710",
          "coordinates": {
            "lat": 20.6296,
            "lng": -87.0739
          }
        },
        "location": {
          "lat": 20.6296,
          "lng": -87.0739
        },
        "images": [
          "https://images.unsplash.com/photo-1582719508461-5c20733e85ef?w=800"
        ],
        "rating": 4.8,
        "total_reviews": 124,
        "is_active": true,
        "min_price": "75.50"
      }
    ]
  }
}
```

### Tipos por campo (para la app)

| Campo | Tipo en JSON | Notas |
|-------|--------------|--------|
| `data.count` | **number** (int) | Total de hoteles |
| `data.page` | **number** (int) | Página actual |
| `data.page_size` | **number** (int) | Tamaño de página |
| `data.total_pages` | **number** (int) | Total de páginas |
| `data.results` | **array** | Lista de hoteles |
| `data.results[].id` | **string** | ID del hotel |
| `data.results[].owner_id` | **string** (UUID) | ID del propietario |
| `data.results[].name` | **string** | |
| `data.results[].description` | **string** | |
| `data.results[].property_type` | **string** | `hotel`, `apartment`, `house`, `room`, `resort`, `hostel` |
| `data.results[].address` | **object** | Siempre presente |
| `data.results[].address.coordinates` | **object** o vacío `{}` | Si hay coordenadas: `{ "lat": number, "lng": number }` (siempre números) |
| `data.results[].location` | **object** o **null** | `{ "lat": number, "lng": number }` para mapa; `null` si no hay coordenadas válidas |
| `data.results[].images` | **array** de strings (URLs) | |
| `data.results[].rating` | **number** (float) | 0.0–5.0 |
| `data.results[].total_reviews` | **number** (int) | |
| `data.results[].is_active` | **boolean** | |
| `data.results[].min_price` | **string** | Precio mínimo (Decimal serializado como string, ej. `"75.50"`). En la app: `double.tryParse(minPrice) ?? 0.0` |

---

## 2. Detalle de un hotel — `GET /api/hotels/{id}/`

**Estructura de la respuesta (200):**

```json
{
  "message": null,
  "data": {
    "id": "697c470802c51d31d311ce4d",
    "owner_id": "4b9e896f-708f-4cfa-b603-b1469df6986d",
    "name": "Hotel Playa del Carmen",
    "description": "Hotel frente al mar con piscina infinita...",
    "property_type": "resort",
    "address": {
      "street": "Av. Playacar 123",
      "city": "Playa del Carmen",
      "state": "Quintana Roo",
      "country": "México",
      "postal_code": "77710",
      "coordinates": {
        "lat": 20.6296,
        "lng": -87.0739
      }
    },
    "location": {
      "lat": 20.6296,
      "lng": -87.0739
    },
    "rooms": [
      {
        "room_id": "a1b2c3d4-e5f6-4789-a012-111111111111",
        "name": "Habitación doble vista mar",
        "description": "Cama king, balcón con vista al mar...",
        "type": "double",
        "capacity": 2,
        "price_per_night": "185.00",
        "available": true,
        "amenities": ["WiFi", "TV", "Aire acondicionado"],
        "images": []
      }
    ],
    "amenities": ["WiFi", "Piscina", "Spa"],
    "services": ["Room service 24h", "Recepción 24h"],
    "images": ["https://..."],
    "rating": 4.8,
    "total_reviews": 124,
    "policies": {
      "check_in": "15:00",
      "check_out": "12:00",
      "cancellation": "Cancelación gratuita hasta 48h...",
      "house_rules": ["No fumar en habitaciones", "No mascotas"]
    },
    "contact": {
      "phone": "+52 984 123 4567",
      "email": "reservas@hotel.com",
      "website": "https://..."
    },
    "is_active": true,
    "created_at": "2026-01-30T05:52:08.338000Z",
    "updated_at": "2026-01-30T05:52:08.338000Z"
  }
}
```

### Tipos por campo (detalle)

| Campo | Tipo en JSON | Notas |
|-------|--------------|--------|
| `data.id` | **string** | ID del hotel |
| `data.owner_id` | **string** (UUID) | |
| `data.name`, `data.description`, `data.property_type` | **string** | |
| `data.address` | **object** | Igual que en listado |
| `data.address.coordinates` | **object** | `{ "lat": number, "lng": number }` o `{}` |
| `data.location` | **object** o **null** | `{ "lat": number, "lng": number }` |
| `data.rooms` | **array** | Lista de habitaciones; puede ser `[]` |
| `data.rooms[].room_id` | **string** (UUID) | Usar este ID en reservas y check-availability |
| `data.rooms[].name` | **string** | |
| `data.rooms[].description` | **string** | |
| `data.rooms[].type` | **string** | `single`, `double`, `twin`, `suite`, `deluxe`, `family`, `studio` |
| `data.rooms[].capacity` | **number** (int) | |
| `data.rooms[].price_per_night` | **string** | Decimal como string, ej. `"185.00"` → parsear con `double.tryParse()` |
| `data.rooms[].available` | **boolean** | |
| `data.rooms[].amenities` | **array** de strings | |
| `data.rooms[].images` | **array** de strings (URLs) | |
| `data.amenities` | **array** de strings | |
| `data.services` | **array** de strings | |
| `data.images` | **array** de strings | |
| `data.rating` | **number** (float) | |
| `data.total_reviews` | **number** (int) | |
| `data.policies` | **object** | `check_in`, `check_out`, `cancellation`, `house_rules` (array) |
| `data.contact` | **object** | `phone`, `email`, `website` (strings) |
| `data.is_active` | **boolean** | |
| `data.created_at`, `data.updated_at` | **string** (ISO 8601) | |

---

## Resumen para la app

1. **Raíz:** Los datos van siempre en **`response.data`** (no en la raíz del JSON).
2. **Coordenadas:** Tanto en `address.coordinates` como en `location` son **números** `lat` y `lng` (el backend ya normaliza GeoJSON a `{ lat, lng }`).
3. **Precios:** `min_price` (listado) y `rooms[].price_per_night` (detalle) vienen como **string** (ej. `"75.50"`). En Dart: usar `double.tryParse(value) ?? 0.0` para evitar el error `String is not a subtype of num?`.
4. **Habitaciones:** Se obtienen del detalle del hotel en **`data.rooms`**. No existe `GET /api/hotels/{id}/rooms/`; usar **`GET /api/hotels/{id}/`** y leer **`data.rooms`**.
5. **Reservas:** En `POST /api/reservations/` y en check-availability hay que enviar un **`room_id`** que exista en **`data.rooms[].room_id`** del hotel correspondiente.
