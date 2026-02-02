# API de reservaciones — qué recibe la app

**Importante:** Todas las respuestas de éxito ponen el payload dentro de **`data`**. La app debe leer siempre **`response.data`** (o `response['data']`) para obtener los datos. Si la app lee el JSON en la raíz (por ejemplo `response.reservations`), no encontrará nada: la lista está en **`response.data.reservations`**.

---

## Autenticación

**Todos** los endpoints de reservaciones requieren **usuario autenticado**:

- Header: `Authorization: Bearer <access_token>`
- El `access_token` se obtiene del **body** de la respuesta del login (`data.access`), no de una cookie.

Sin token válido la respuesta será **401 Unauthorized** y no habrá `data`.

---

## Regla de negocio: reserva solo cuando el pago es exitoso

- **La reserva en base de datos solo se guarda cuando el pago está pagado (paid).**
- Mientras el usuario no paga, la app/navegador guarda la reserva **solo en local** (no se llama al backend para guardarla).
- Para confirmar reserva + pago en un solo paso: **`POST /api/reservations/checkout/`** (reserva + pago). Si el pago es exitoso, se crea la reserva en MongoDB con `payment_status: 'paid'`.
- **`POST /api/reservations/`** (crear reserva sin pago) está **deshabilitado**: responde 400 indicando usar checkout.

---

## Rutas base

- Base: **`/api/reservations/`**
- **Checkout (reserva + pago):** **`POST /api/reservations/checkout/`** → reserva guardada solo si pago OK
- Listar reservaciones del huésped: **`GET /api/reservations/`**
- Crear reservación sin pago: **`POST /api/reservations/`** → **deshabilitado** (400, usar checkout)
- Detalle: **`GET /api/reservations/{id}/`**
- Check availability: **`GET /api/reservations/check-availability/`**
- Cancelar: **`PATCH /api/reservations/{id}/cancel/`**
- (Propietarios) Mis propiedades: **`GET /api/reservations/my-properties/`**
- (Propietarios) Confirmar / Rechazar / Completar: **`PATCH /api/reservations/{id}/confirm/`**, etc.
- (Propietarios) Calendario: **`GET /api/reservations/calendar/`**

---

## 1. Listar mis reservaciones (huésped) — `GET /api/reservations/`

**Auth:** Bearer token (usuario debe ser tipo **guest** en la práctica; el backend filtra por `request.user.id`).

**Query params opcionales:** `status`, `from_date`, `to_date` (ISO 8601).

**Respuesta 200:**

```json
{
  "message": null,
  "data": {
    "count": 2,
    "reservations": [
      {
        "id": "675a1b2c3d4e5f6789012345",
        "reservation_id": "a1b2c3d4-e5f6-7890-abcd-111111111111",
        "hotel_id": "697c470802c51d31d311ce4d",
        "room_id": "a1b2c3d4-e5f6-4789-a012-111111111111",
        "check_in": "2026-02-03T14:00:00Z",
        "check_out": "2026-02-05T12:00:00Z",
        "nights": 2,
        "number_of_guests": 2,
        "total_price": 370.0,
        "currency": "USD",
        "status": "pending",
        "payment_status": "pending",
        "created_at": "2026-02-02T18:30:00Z"
      }
    ]
  }
}
```

**En la app:** Los datos útiles están en **`data`**:

- `data.count` → number (cantidad de reservaciones).
- `data.reservations` → array de reservaciones (lista para pantalla “Mis reservaciones”).

Si la app no recibe nada, revisar:

1. Que la petición lleve **`Authorization: Bearer <access_token>`**.
2. Que se lea **`response.data`** (o `response['data']`), no la raíz del JSON.
3. Que la lista sea **`response.data.reservations`**, no `response.reservations`.

---

## 2. Checkout (reserva + pago) — `POST /api/reservations/checkout/`

**Auth:** Bearer token. Solo usuarios tipo **guest**.

La reserva **solo se guarda en backend cuando el pago es exitoso**. Si el pago falla, no se crea ninguna reserva. Mientras el usuario no paga, la app debe guardar la reserva **solo en local** (navegador/app).

**Body (JSON):** datos de reservación + datos de pago en un solo objeto.

```json
{
  "hotel_id": "697c470802c51d31d311ce4d",
  "room_id": "a1b2c3d4-e5f6-4789-a012-111111111111",
  "check_in": "2026-02-03T14:00:00Z",
  "check_out": "2026-02-05T12:00:00Z",
  "number_of_guests": 2,
  "guest_details": {
    "name": "Alejandro Córdova",
    "email": "david098359@gmail.com",
    "phone": "0963004511",
    "special_requests": ""
  },
  "special_requests": "",
  "payment_method": "credit_card",
  "payment_gateway": "stripe",
  "payment_token": "tok_xxx",
  "save_payment_method": false,
  "metadata": {}
}
```

- **Reservación:** `hotel_id`, `room_id`, `check_in`, `check_out`, `number_of_guests`, `guest_details`, `special_requests` (opcional). `room_id` debe ser un `room_id` real del hotel.
- **Pago:** `payment_method` (credit_card, debit_card, paypal, bank_transfer, other), `payment_gateway` (stripe, paypal, mercadopago, manual), **`payment_token`** (requerido; el que devuelve la pasarela en el cliente). Opcionales: `save_payment_method`, `metadata`.

**Respuesta 201 (éxito):**

```json
{
  "message": "Reserva y pago realizados correctamente",
  "data": {
    "reservation": {
      "id": "675a1b2c3d4e5f6789012345",
      "reservation_id": "a1b2c3d4-e5f6-7890-abcd-111111111111",
      "hotel_id": "697c470802c51d31d311ce4d",
      "room_id": "a1b2c3d4-e5f6-4789-a012-111111111111",
      "guest_id": "...",
      "owner_id": "...",
      "check_in": "2026-02-03T14:00:00Z",
      "check_out": "2026-02-05T12:00:00Z",
      "nights": 2,
      "number_of_guests": 2,
      "guest_details": { "name": "...", "email": "...", "phone": "..." },
      "price_per_night": 185.0,
      "total_price": 370.0,
      "currency": "USD",
      "status": "pending",
      "payment_status": "paid",
      "special_requests": "",
      "cancellation_reason": null,
      "created_at": "...",
      "updated_at": "...",
      "cancelled_at": null,
      "confirmed_at": null
    },
    "payment": {
      "id": "uuid-pago",
      "reservation_id": "a1b2c3d4-e5f6-7890-abcd-111111111111",
      "amount": "370.00",
      "currency": "USD",
      "status": "completed",
      "payment_method": "credit_card",
      "payment_gateway": "stripe",
      "completed_at": "...",
      ...
    }
  }
}
```

**En la app:** Reserva en **`response.data.reservation`**, pago en **`response.data.payment`**. La reserva ya está guardada en backend con **`payment_status: 'paid'`**.

**Errores:** 400 (validación o habitación no disponible), 402 (pago rechazado; no se crea reserva). Mensaje en **`response.error`**.

---

## 2b. Crear reservación sin pago — `POST /api/reservations/` (deshabilitado)

**Respuesta 400:** El backend responde con un mensaje indicando que las reservas se confirman solo al pagar y que se debe usar **`POST /api/reservations/checkout/`**. La reserva sin pagar debe guardarse **solo en local** (navegador/app).

---

## 3. Detalle de una reservación — `GET /api/reservations/{id}/`

**Auth:** Bearer token. Solo el **guest** o el **owner** de esa reservación pueden verla.

**Respuesta 200:**

```json
{
  "message": null,
  "data": {
    "id": "675a1b2c3d4e5f6789012345",
    "reservation_id": "a1b2c3d4-...",
    "hotel_id": "697c470802c51d31d311ce4d",
    "room_id": "a1b2c3d4-e5f6-4789-a012-111111111111",
    "guest_id": "...",
    "owner_id": "...",
    "check_in": "2026-02-03T14:00:00Z",
    "check_out": "2026-02-05T12:00:00Z",
    "nights": 2,
    "number_of_guests": 2,
    "guest_details": { "name": "...", "email": "...", "phone": "...", "special_requests": "" },
    "price_per_night": 185.0,
    "total_price": 370.0,
    "currency": "USD",
    "status": "pending",
    "payment_status": "pending",
    "special_requests": "",
    "cancellation_reason": null,
    "created_at": "...",
    "updated_at": "...",
    "cancelled_at": null,
    "confirmed_at": null
  }
}
```

**En la app:** Detalle en **`response.data`**.

---

## 4. Verificar disponibilidad — `GET /api/reservations/check-availability/`

**Auth:** Bearer token.

**Query params (todos requeridos):** `hotel_id`, `room_id`, `check_in`, `check_out` (ISO 8601).

Ejemplo:  
`GET /api/reservations/check-availability/?hotel_id=697c470802c51d31d311ce4d&room_id=a1b2c3d4-e5f6-4789-a012-111111111111&check_in=2026-02-03T14:00:00Z&check_out=2026-02-05T12:00:00Z`

**Respuesta 200:**

```json
{
  "message": "La habitación está disponible",
  "data": {
    "available": true
  }
}
```

o, si no está disponible:

```json
{
  "message": "La habitación no está disponible en las fechas seleccionadas",
  "data": {
    "available": false
  }
}
```

**En la app:** El booleano está en **`response.data.available`**, no en `response.available`.

---

## 5. Errores

- **401:** Falta token o token inválido → no hay `data`.
- **403:** Usuario no es guest (al crear) o no es guest/owner de la reservación (al ver/cancelar) → cuerpo con **`error`**.
- **400:** Validación o negocio (ej. habitación no encontrada, no disponible) → cuerpo con **`error`** (string) o diccionario de errores por campo.
- **404:** Reservación no encontrada → cuerpo con **`detail`**.

En todos los errores, la app debe leer **`response.error`** o **`response.detail`** según lo que envíe el backend; los datos de éxito siempre están en **`response.data`**.

---

## Resumen para que la app reciba datos

1. Enviar **`Authorization: Bearer <access_token>`** en todas las peticiones a `/api/reservations/`.
2. Leer siempre el payload de éxito desde **`response.data`** (no desde la raíz del JSON).
3. Listado: **`response.data.reservations`** (array).
4. Crear reservación: reservación creada en **`response.data`**.
5. Check availability: **`response.data.available`** (boolean).
6. Detalle: **`response.data`** (objeto reservación).
7. Usar **`room_id`** real de **`GET /api/hotels/{id}/`** → **`data.rooms[].room_id`** en POST y check-availability.
