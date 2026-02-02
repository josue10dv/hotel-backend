# Prompt completo: reservas locales + TTL 3 horas + estados Completado/Pendiente

Usa este documento como especificación para implementar en la **app (móvil o web)** el flujo de reservas sin pagar guardadas en local, con caducidad de 3 horas y tarjetas que muestren **Completado** o **Pendiente** según el estado del pago.

---

## 1. Reglas de negocio (backend)

- **La reserva en base de datos solo se guarda cuando el pago es exitoso (paid).**
- Mientras el usuario no paga, la app debe guardar la reserva **solo en el dispositivo** (local).
- Para confirmar reserva + pago: **POST /api/reservations/checkout/** con datos de reserva + pago. Si el pago es OK, el backend crea la reserva con `payment_status: 'paid'` y la devuelve en `data.reservation`.
- **POST /api/reservations/** (crear reserva sin pagar) está deshabilitado (400). No se usa.

---

## 2. Objetivo en la app

1. **Guardar localmente** la reserva sin pagar en el celular (o navegador).
2. **Caducidad 3 horas:** si pasan 3 horas desde que se guardó, **borrarla automáticamente** de local y no mostrarla.
3. **Tarjetas de reservas:**
   - Reservas **pagadas** (vienen del backend con `payment_status: 'paid'`): mostrar estado **"Completado"** (o "Pagado").
   - Reservas **sin pagar** (solo en local, dentro de las 3 h): mostrar estado **"Pendiente"**.
4. **Unificar** en una misma lista/vista: reservas locales (pendientes) + reservas del backend (completadas), con el mismo diseño de tarjeta y el estado correspondiente.

---

## 3. Dónde guardar en el dispositivo

- **Móvil (Flutter / React Native / etc.):**  
  - Preferencias locales (SharedPreferences, AsyncStorage, etc.) o un pequeño archivo JSON en el directorio de la app.  
  - Clave sugerida: `unpaid_reservation` o `pending_reservation` (una sola reserva sin pagar por usuario, o una lista si quieres permitir varias; aquí se asume **una** reserva pendiente a la vez).
- **Web:**  
  - `localStorage` (clave ej. `unpaid_reservation`).  
  - Misma lógica: un objeto o lista con la reserva + timestamp.

---

## 4. Estructura del dato a guardar localmente

Guardar **un objeto** que incluya la reserva y el momento en que se guardó (para el TTL de 3 horas).

Ejemplo en JSON:

```json
{
  "savedAt": "2026-02-02T19:00:00.000Z",
  "reservation": {
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
    "hotel_name": "Hotel Playa del Carmen",
    "room_name": "Habitación doble vista mar",
    "total_price": 370,
    "currency": "USD",
    "nights": 2
  }
}
```

- **`savedAt`:** fecha/hora en ISO 8601 (UTC) en que se guardó. Se usa para calcular si ya pasaron 3 horas.
- **`reservation`:** todos los campos necesarios para:
  - Mostrar la tarjeta (nombre hotel, habitación, fechas, huéspedes, total, etc.).
  - Llamar después a **POST /api/reservations/checkout/** (hotel_id, room_id, check_in, check_out, number_of_guests, guest_details, special_requests + payment_method, payment_gateway, payment_token).

Puedes añadir en `reservation` campos extra solo para la UI (por ejemplo `hotel_name`, `room_name`, `total_price`, `nights`) rellenados desde la pantalla de detalle del hotel/habitación antes de guardar.

---

## 5. TTL de 3 horas: cuándo borrar

- **Al guardar:** guardar `savedAt` = ahora (UTC).
- **Cada vez que vayas a usar la reserva local** (pantalla "Mis reservaciones", pantalla de pago, o al abrir la app):
  1. Leer el objeto guardado.
  2. Calcular: `now = ahora en UTC`; `savedAt = fecha guardada`; `elapsed = now - savedAt`.
  3. Si `elapsed >= 3 horas` (por ejemplo 3 * 60 * 60 segundos, o 3 en la unidad que uses):
     - **Borrar** el dato de local (eliminar clave `unpaid_reservation` o equivalente).
     - No mostrar esa reserva como pendiente.
  4. Si `elapsed < 3 horas`: seguir mostrando la reserva como **Pendiente** y permitir pagar.

Puedes implementar una función tipo `isExpired(savedAt) => (now - savedAt) >= 3h` y, si es true, borrar y no usar el dato.

---

## 6. Flujo completo en la app

### 6.1 Usuario arma la reserva (sin pagar)

1. Usuario elige hotel, habitación, fechas, huéspedes, datos del huésped (nombre, email, teléfono).
2. Opcional: verificar disponibilidad con **GET /api/reservations/check-availability/** (hotel_id, room_id, check_in, check_out).
3. En la pantalla de confirmación (antes de pagar):
   - Construir el objeto `reservation` con los campos que exige el checkout (hotel_id, room_id, check_in, check_out, number_of_guests, guest_details, special_requests) y los que quieras para la tarjeta (hotel_name, room_name, total_price, nights, currency).
   - Guardar en local:
     - Clave: `unpaid_reservation` (o la que uses).
     - Valor: `{ "savedAt": "<ISO8601 ahora>", "reservation": { ... } }`.
   - Redirigir a "Mis reservaciones" o a una pantalla de pago para esa reserva.

No llamar a **POST /api/reservations/** (está deshabilitado).

### 6.2 Pantalla "Mis reservaciones" (lista unificada)

1. **Obtener reservas del backend:** **GET /api/reservations/** con `Authorization: Bearer <token>`. Leer **`response.data.reservations`**.
2. **Obtener reserva local:** leer la clave `unpaid_reservation` (o equivalente).
3. **Aplicar TTL:** si hay reserva local y `savedAt` tiene más de 3 horas, borrarla de local y no incluirla en la lista.
4. **Unificar lista para las tarjetas:**
   - Cada reserva del backend: considerar **completada** (payment_status viene como `'paid'`). Mostrar en la tarjeta: **"Completado"** (o "Pagado").
   - Si hay reserva local válida (dentro de 3 h): añadirla a la lista como un ítem más, con estado **"Pendiente"** (y opción "Pagar").
5. Ordenar como quieras (por ejemplo: primero pendientes por fecha de guardado, luego completadas por fecha de check_in o created_at).

Cada **tarjeta** debe mostrar de forma clara:
- **Completado:** para reservas que vienen del backend (ya pagadas).
- **Pendiente:** para la reserva guardada solo en local (y dentro de 3 h).

### 6.3 Usuario paga la reserva pendiente

1. Desde la tarjeta con estado "Pendiente", el usuario pulsa "Pagar" (o similar).
2. Ir a pantalla de pago: recoger método de pago y token (Stripe u otra pasarela).
3. Llamar **POST /api/reservations/checkout/** con:
   - Los campos de **reservation** que tienes en local (hotel_id, room_id, check_in, check_out, number_of_guests, guest_details, special_requests).
   - Los campos de pago: payment_method, payment_gateway, payment_token (y opcional save_payment_method, metadata).
4. **Si la respuesta es 201:**
   - Leer **`response.data.reservation`** y **`response.data.payment`**.
   - **Borrar** la reserva local (eliminar `unpaid_reservation`).
   - Mostrar éxito y redirigir a "Mis reservaciones" o al detalle de la reserva. Esa reserva ya viene del backend con `payment_status: 'paid'`, por tanto en la lista unificada se mostrará como **"Completado"**.
5. **Si la respuesta es 402 (u otro error):**
   - Mostrar el mensaje de **`response.error`** (y opcionalmente `response.data` si lo envía el backend).
   - No borrar la reserva local; sigue en "Pendiente" hasta que pague o pasen 3 horas.

### 6.4 Al abrir la app o volver a "Mis reservaciones"

- Siempre que leas la reserva local, **revisar el TTL**: si `savedAt` + 3 horas &lt; ahora, borrarla y no mostrarla. Así las reservas no pagadas desaparecen solas a los 3 horas.

---

## 7. Resumen de implementación

| Qué | Dónde | Cómo |
|-----|--------|------|
| Guardar reserva sin pagar | Local (SharedPreferences / AsyncStorage / localStorage) | Clave `unpaid_reservation`. Valor: `{ savedAt: "<ISO8601>", reservation: { ... } }`. |
| Caducidad 3 h | Al leer la reserva local (lista o pago) | Si `(ahora - savedAt) >= 3 horas` → borrar clave y no usar el dato. |
| Lista unificada | Pantalla "Mis reservaciones" | GET /api/reservations/ → items con estado "Completado". + Reserva local (si existe y no expirada) → 1 item con estado "Pendiente". |
| Tarjetas | Misma tarjeta para todos los ítems | Campo/etiqueta: "Completado" si viene del backend (paid). "Pendiente" si es la reserva local. |
| Pagar pendiente | Botón "Pagar" en la tarjeta pendiente | POST /api/reservations/checkout/ con reservation + payment. Si 201 → borrar local y mostrar la reserva de `data.reservation` como completada. |

---

## 8. Endpoints a usar (recordatorio)

- **GET /api/reservations/**  
  - Header: `Authorization: Bearer <access_token>`  
  - Respuesta: **`data.reservations`** (array), **`data.count`**.  
  - Todas estas reservas están pagadas en backend; mostrarlas como **"Completado"**.

- **POST /api/reservations/checkout/**  
  - Header: `Authorization: Bearer <access_token>`  
  - Body: reserva (hotel_id, room_id, check_in, check_out, number_of_guests, guest_details, special_requests) + pago (payment_method, payment_gateway, payment_token, opcionales).  
  - 201: **`data.reservation`** (ya con payment_status 'paid'), **`data.payment`**. Borrar reserva local y mostrar esta como "Completado".  
  - 402: pago rechazado; mensaje en **`response.error`**. No borrar local; seguir mostrando "Pendiente".

- **GET /api/reservations/check-availability/**  
  - Opcional; para comprobar disponibilidad antes de guardar en local.

---

## 9. Ejemplo de lógica (pseudocódigo)

```
Al abrir "Mis reservaciones":
  reservasBackend = GET /api/reservations/  → data.reservations
  reservaLocal = leerLocal("unpaid_reservation")

  si reservaLocal existe:
    savedAt = reservaLocal.savedAt
    si (ahora - savedAt) >= 3 horas:
      borrarLocal("unpaid_reservation")
      reservaLocal = null

  items = []
  para cada r in reservasBackend:
    items.push({ ...r, paymentStatus: "paid", label: "Completado" })
  si reservaLocal:
    items.push({ ...reservaLocal.reservation, paymentStatus: "pending", label: "Pendiente", savedAt })

  mostrar tarjetas con items; en cada tarjeta mostrar label ("Completado" o "Pendiente")
  en tarjetas "Pendiente" mostrar botón "Pagar"

Al pulsar "Pagar" en una tarjeta pendiente:
  token = obtenerTokenPasarela()  // Stripe, etc.
  body = { ...reservaLocal.reservation, payment_method: "credit_card", payment_gateway: "stripe", payment_token: token }
  resp = POST /api/reservations/checkout/ con body
  si resp.status == 201:
    borrarLocal("unpaid_reservation")
    mostrar data.reservation en lista como "Completado" (o recargar GET /api/reservations/)
    mostrar éxito
  sino:
    mostrar resp.error
```

---

## 10. Conjunto de implementaciones (checklist)

- [ ] Guardar reserva sin pagar en local con estructura `{ savedAt, reservation }`.
- [ ] Al leer reserva local, comprobar TTL 3 h; si pasó, borrarla y no mostrarla.
- [ ] Pantalla "Mis reservaciones": combinar reservas de GET /api/reservations/ (todas pagadas) + reserva local si existe y no expirada.
- [ ] Tarjetas: mismo diseño; estado **"Completado"** para reservas del backend, **"Pendiente"** para la reserva local.
- [ ] Botón "Pagar" solo en tarjetas Pendiente.
- [ ] Al pagar: POST /api/reservations/checkout/; si 201, borrar local y mostrar/actualizar lista con la nueva reserva como Completado; si error, mostrar mensaje y mantener Pendiente.
- [ ] No usar POST /api/reservations/ (está deshabilitado).

Con esto tienes el prompt completo para implementar en la app: guardar localmente, TTL 3 horas, borrado automático y estados Completado/Pendiente en las tarjetas de forma conjunta.
