# Implementación de pagos — guía para usuario (huésped)

Guía completa para implementar el flujo de pagos en la app desde el punto de vista del **usuario (huésped)**: qué enviar, qué recibir y cómo usar cada ruta.

---

## Flujo principal: checkout (reserva + pago en un paso)

- **La reserva en base de datos solo se guarda cuando el pago es exitoso (paid).**
- Mientras el usuario no paga, la app guarda la reserva **solo en local** (navegador/app).
- Para confirmar reserva y pago en un solo paso: **`POST /api/reservations/checkout/`** (ver [RESERVATIONS_API.md](RESERVATIONS_API.md)). Body: datos de reservación + `payment_method`, `payment_gateway`, `payment_token`. Si el pago es exitoso, se crea la reserva en backend con `payment_status: 'paid'` y se devuelve `data.reservation` + `data.payment`.
- **`POST /api/payments/`** (esta sección) se usa para **pagar una reservación ya existente** en backend (por ejemplo reservas creadas por admin o flujos legacy). En el flujo estándar de usuario, usar **checkout**.

---

## 1. Qué necesitas antes de implementar

### Autenticación

- **Todas** las rutas de pagos requieren usuario autenticado.
- Header en **todas** las peticiones:
  ```http
  Authorization: Bearer <access_token>
  ```
- El `access_token` se obtiene del **body** del login: **`data.access`** (no de una cookie).

### Respuesta estándar

- El backend siempre devuelve el payload útil dentro de **`data`**.
- En la app hay que leer **`response.data`** (o `response['data']`), no la raíz del JSON.
- Errores: **`response.error`** o **`response.detail`**.

### Rol del usuario

- Solo el **huésped** de una reservación puede **crear y procesar** el pago de esa reservación.
- El usuario puede **listar sus pagos**, ver **detalle**, **verificar estado** y ver **transacciones** y **estadísticas**.
- **Reembolsos** y **ganancias** son solo para propietarios; si el usuario necesita un reembolso, debe solicitarlo al propietario o soporte (la app no llama a refund como huésped).

---

## 2. Rutas que usa el usuario (huésped)

| Acción | Método | Ruta | Descripción |
|--------|--------|------|-------------|
| Pagar una reservación | POST | `/api/payments/` | Crear y procesar pago para una reservación |
| Listar mis pagos | GET | `/api/payments/` | Lista de pagos del usuario |
| Ver detalle de un pago | GET | `/api/payments/{id}/` | Detalle de un pago (por UUID del pago) |
| Verificar estado del pago | POST | `/api/payments/{id}/verify/` | Consultar estado en la pasarela |
| Ver transacciones del pago | GET | `/api/payments/{id}/transactions/` | Historial de transacciones del pago |
| Estadísticas de mis pagos | GET | `/api/payments/statistics/` | Resumen (total, completados, fallidos, etc.) |

**No usar como usuario:**  
`POST /api/payments/{id}/refund/` y `GET /api/payments/my-earnings/` son solo para **propietarios**.

---

## 3. Pagar una reservación — POST /api/payments/

### Cuándo usarlo

- Después de que el usuario haya creado una reservación (`POST /api/reservations/`) y tengas el **id** (o `reservation_id`) de esa reservación.
- En la pantalla de “Pagar reservación” o “Confirmar pago”.

### Qué enviar

**URL:** `POST /api/payments/`  
**Headers:** `Authorization: Bearer <access_token>`  
**Content-Type:** `application/json`

**Body (JSON):**

```json
{
  "reservation_id": "uuid-de-la-reservacion",
  "payment_method": "credit_card",
  "payment_gateway": "stripe",
  "payment_token": "tok_xxx",
  "save_payment_method": false,
  "metadata": {}
}
```

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `reservation_id` | string | **Sí** | UUID de la reservación a pagar (el `id` o `reservation_id` que devolvió `POST /api/reservations/`). |
| `payment_method` | string | **Sí** | `credit_card` \| `debit_card` \| `paypal` \| `bank_transfer` \| `other` |
| `payment_gateway` | string | No (default: `stripe`) | `stripe` \| `paypal` \| `mercadopago` \| `manual` |
| `payment_token` | string | No | Token que devuelve la pasarela en el cliente. Si **no** se envía, el backend solo crea el pago en estado **pending** (pagar después o manual). |
| `save_payment_method` | boolean | No (default: false) | Guardar método para uso futuro. |
| `metadata` | object | No | Datos extra (por ejemplo origen de la app). |

### Tokens de prueba (Stripe simulado)

Si el backend usa el gateway **Stripe simulado** (desarrollo):

| Token | Resultado |
|-------|-----------|
| Cualquier otro (ej. `"tok_test_123"`) | Pago exitoso |
| `"tok_fail"` | Tarjeta rechazada |
| `"tok_insufficient"` | Fondos insuficientes |
| `"tok_expired"` | Tarjeta expirada |

### Qué recibes

**Éxito — pago procesado (201):**

```json
{
  "message": "Pago procesado exitosamente",
  "data": {
    "id": "uuid-del-pago",
    "reservation_id": "uuid-reservacion",
    "user_email": "user@example.com",
    "user_name": "Nombre Usuario",
    "amount": "370.00",
    "currency": "USD",
    "status": "completed",
    "status_display": "Completado",
    "payment_method": "credit_card",
    "payment_method_display": "Tarjeta de Crédito",
    "payment_gateway": "stripe",
    "payment_gateway_display": "Stripe",
    "gateway_payment_id": "ch_sim_xxx",
    "gateway_response": { },
    "description": "Pago por reservación ...",
    "metadata": null,
    "error_code": null,
    "error_message": null,
    "is_completed": true,
    "is_refundable": true,
    "can_be_cancelled": false,
    "created_at": "2026-02-02T19:00:00Z",
    "updated_at": "2026-02-02T19:00:01Z",
    "completed_at": "2026-02-02T19:00:01Z",
    "failed_at": null,
    "refunded_at": null
  }
}
```

- **Dónde leer:** **`response.data`**.
- Si **`data.status === 'completed'`**: pago OK; la reservación en MongoDB queda con **`payment_status: 'paid'`**. Puedes refrescar la reservación con `GET /api/reservations/{id}/` para mostrar “Pagado”.

**Éxito — solo registro pendiente (201, sin token):**

```json
{
  "message": "Pago creado en estado pendiente",
  "data": { ... }
}
```

- **`data.status`** será `"pending"`. Útil para “pagar después” o flujo manual.

**Pago rechazado por la pasarela (402):**

```json
{
  "error": "Su tarjeta fue rechazada",
  "error_code": "card_declined",
  "data": { ... pago en estado failed ... }
}
```

- Leer **`response.error`** para el mensaje y **`response.data`** si quieres mostrar datos del pago (ej. `data.status === 'failed'`, `data.error_message`).

**Errores típicos (400/403):**

- **400:** `reservation_id` vacío, reservación no encontrada, o ya existe un pago completado para esa reservación.
- **403:** El usuario no es el huésped de la reservación.

Todos los mensajes de error en **`response.error`** (o **`response.detail`** según el caso).

### Forma de uso en la app

1. Tras crear la reservación, guardar **`data.id`** o **`data.reservation_id`**.
2. En la pantalla de pago, recoger método (ej. `credit_card`), pasarela (ej. `stripe`) y, si aplica, el **payment_token** del SDK (Stripe, etc.).
3. Llamar **POST /api/payments/** con `reservation_id`, `payment_method`, `payment_gateway` y opcionalmente `payment_token`.
4. Si status === 201 y **`data.status === 'completed'`** → mostrar éxito y actualizar la reservación (o navegar a “Mis reservaciones” / detalle).
5. Si status === 402 → mostrar **`response.error`** (y opcionalmente **`response.data.error_message`**).
6. Para desarrollo sin SDK real, usar tokens de prueba (ej. `tok_test_123` para éxito, `tok_fail` para rechazo).

---

## 4. Listar mis pagos — GET /api/payments/

### Cuándo usarlo

- En “Mis pagos” o “Historial de pagos” del usuario.

### Qué enviar

**URL:** `GET /api/payments/`  
**Headers:** `Authorization: Bearer <access_token>`

**Query params (opcionales):**

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `status` | string | Filtrar por estado: `pending`, `processing`, `completed`, `failed`, `refunded`, `cancelled` |
| `from_date` | string (ISO 8601) | Fecha desde (ej. `2026-01-01T00:00:00Z`) |
| `to_date` | string (ISO 8601) | Fecha hasta |

Ejemplo: `GET /api/payments/?status=completed`

### Qué recibes

**200 OK:**

```json
{
  "message": null,
  "data": {
    "count": 5,
    "payments": [
      {
        "id": "uuid-del-pago",
        "reservation_id": "uuid-reservacion",
        "user_email": "user@example.com",
        "amount": "370.00",
        "currency": "USD",
        "status": "completed",
        "status_display": "Completado",
        "payment_method": "credit_card",
        "payment_method_display": "Tarjeta de Crédito",
        "payment_gateway": "stripe",
        "created_at": "2026-02-02T19:00:00Z",
        "completed_at": "2026-02-02T19:00:01Z"
      }
    ]
  }
}
```

- **Dónde leer:** Lista en **`response.data.payments`**, total en **`response.data.count`**.
- **Tipos:** `amount` puede venir como string (Decimal). En la app parsear con `parseFloat` / `double.tryParse` si hace falta.

### Forma de uso en la app

1. Llamar **GET /api/payments/** (con filtros opcionales).
2. Mostrar **`data.payments`** en una lista y **`data.count`** para “Total: X pagos”.
3. Cada ítem tiene **`id`** para abrir el detalle con **GET /api/payments/{id}/**.

---

## 5. Ver detalle de un pago — GET /api/payments/{id}/

### Cuándo usarlo

- Al abrir “Detalle del pago” desde la lista de pagos (usar el **`id`** del pago, no el de la reservación).

### Qué enviar

**URL:** `GET /api/payments/{id}/`  
**Headers:** `Authorization: Bearer <access_token>`  
- **`{id}`**: UUID del pago (ej. `data.id` de la lista o del create).

### Qué recibes

**200 OK:** Objeto de pago completo en **`response.data`**, con los mismos campos que en el create (incluye `gateway_response`, `error_message`, `is_completed`, `is_refundable`, `can_be_cancelled`, fechas, etc.).

**403:** El usuario no es el dueño del pago ni el propietario de la reservación.  
**404:** Pago no encontrado.

### Forma de uso en la app

1. Desde la lista, al tocar un pago, navegar a detalle con **`GET /api/payments/{payment_id}/`**.
2. Mostrar **`response.data`** (monto, estado, método, fechas, mensaje de error si `status === 'failed'`).

---

## 6. Verificar estado del pago — POST /api/payments/{id}/verify/

### Cuándo usarlo

- Cuando el pago quedó en **pending** o **processing** y quieres consultar el estado actual en la pasarela (pagos asíncronos o “verificar de nuevo”).

### Qué enviar

**URL:** `POST /api/payments/{id}/verify/`  
**Headers:** `Authorization: Bearer <access_token>`  
- Sin body (o body vacío).

### Qué recibes

**200 OK:**

```json
{
  "message": "Estado del pago verificado",
  "data": {
    "gateway_status": "succeeded",
    "payment": { ... objeto pago actualizado ... }
  }
}
```

- **Dónde leer:** Estado actualizado en **`response.data.payment`** (ej. **`response.data.payment.status`**). Si la pasarela confirma el pago, el backend puede actualizar a `completed` y la reservación a `payment_status: 'paid'`.

**4xx/5xx:** Mensaje en **`response.error`**.

### Forma de uso en la app

1. En detalle de un pago con estado `pending` o `processing`, mostrar botón “Verificar estado”.
2. Llamar **POST /api/payments/{id}/verify/**.
3. Refrescar la UI con **`data.payment`** (o volver a llamar **GET /api/payments/{id}/**).

---

## 7. Ver transacciones del pago — GET /api/payments/{id}/transactions/

### Cuándo usarlo

- En la pantalla de detalle del pago, para mostrar el historial de transacciones (cargo, reembolso, etc.).

### Qué enviar

**URL:** `GET /api/payments/{id}/transactions/`  
**Headers:** `Authorization: Bearer <access_token>`  
- **`{id}`**: UUID del pago.

### Qué recibes

**200 OK:**

```json
{
  "message": null,
  "data": {
    "count": 2,
    "transactions": [
      {
        "id": "uuid-transaccion",
        "payment_id": "uuid-pago",
        "transaction_type": "charge",
        "transaction_type_display": "Cargo",
        "amount": "370.00",
        "status": "success",
        "status_display": "Exitosa",
        "gateway_transaction_id": "ch_sim_xxx",
        "error_code": null,
        "error_message": null,
        "response_data": { },
        "notes": "",
        "created_at": "2026-02-02T19:00:01Z",
        "is_successful": true
      }
    ]
  }
}
```

- **Dónde leer:** **`response.data.transactions`**, **`response.data.count`**.

### Forma de uso en la app

1. En detalle del pago, llamar **GET /api/payments/{id}/transactions/**.
2. Mostrar **`data.transactions`** (tipo, monto, estado, fecha).

---

## 8. Estadísticas de mis pagos — GET /api/payments/statistics/

### Cuándo usarlo

- En “Resumen de pagos” o dashboard del usuario (totales, completados, fallidos, etc.).

### Qué enviar

**URL:** `GET /api/payments/statistics/`  
**Headers:** `Authorization: Bearer <access_token>`

**Query params (opcionales):**

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `from_date` | string (ISO 8601) | Fecha desde |
| `to_date` | string (ISO 8601) | Fecha hasta |

### Qué recibes

**200 OK:**

```json
{
  "message": null,
  "data": {
    "total_payments": 10,
    "completed_payments": 8,
    "pending_payments": 1,
    "failed_payments": 1,
    "refunded_payments": 0
  }
}
```

- **Dónde leer:** **`response.data`** (todos los campos son números).

### Forma de uso en la app

1. Llamar **GET /api/payments/statistics/** (opcionalmente con rango de fechas).
2. Mostrar tarjetas o resumen con **total_payments**, **completed_payments**, **failed_payments**, etc.

---

## 9. Resumen de implementación (usuario)

| Paso | Acción | Ruta | Dónde está el resultado |
|------|--------|------|---------------------------|
| 1 | Login | (auth) | `data.access` → token para header |
| 2 | Crear reservación | POST /api/reservations/ | `data.id` o `data.reservation_id` |
| 3 | Pagar reservación | POST /api/payments/ | `data` (si `data.status === 'completed'` → reservación pagada) |
| 4 | Listar mis pagos | GET /api/payments/ | `data.payments`, `data.count` |
| 5 | Detalle de un pago | GET /api/payments/{id}/ | `data` |
| 6 | Verificar pago | POST /api/payments/{id}/verify/ | `data.payment` |
| 7 | Transacciones del pago | GET /api/payments/{id}/transactions/ | `data.transactions`, `data.count` |
| 8 | Estadísticas | GET /api/payments/statistics/ | `data` (total_payments, completed_payments, etc.) |

- **Siempre** header: `Authorization: Bearer <access_token>`.
- **Siempre** leer datos de éxito en **`response.data`**; errores en **`response.error`** o **`response.detail`**.
- Reembolsos: solo propietarios; el usuario debe solicitar reembolso al propietario o soporte (no se usa **POST /api/payments/{id}/refund/** como huésped).

Con esto puedes implementar en la app todo el flujo de pagos desde el punto de vista del usuario (huésped).
