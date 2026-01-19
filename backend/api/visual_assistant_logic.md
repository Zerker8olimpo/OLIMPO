# Lógica del Asistente Visual (UI/UX)

**Estado:** Definición Congelada
**Propósito:** Guiar el comportamiento del asistente en el frontend según el estado de la cuenta y dispositivo.

---

## 1. Rol del Asistente

El asistente **NO** es un chatbot libre. Es un **intérprete de estado** cuyo objetivo es:

- Explicar al usuario qué está pasando.
- Anticipar errores.
- Explicar restricciones sin lenguaje técnico.
- Guiar decisiones (no imponerlas).

---

## 2. Estados Reconocidos

### 🟢 Estado 1: Cuenta nueva (primer ingreso)

- **Mensaje:** "Bienvenido a OLIMPO. Tu cuenta aún no tiene una suscripción activa."
- **Acción:** Botón "Activar suscripción (30 días)".
- **Tooltip:** "La suscripción se asocia a este dispositivo."
- **Oculto:** Modelos, simulaciones, advertencias técnicas.

### 🟢 Estado 2: Suscripción activa – mismo dispositivo

- **Mensaje:** "Tu suscripción está activa."
- **Info:** Plan y Días restantes.
- **Acciones:** "Continuar", "Ver modelos", "Ayuda".
- **Oculto:** Menciones a dispositivo, restricciones o reset.

### 🟡 Estado 3: Suscripción activa – otro dispositivo detectado

_Caso crítico. El asistente aparece automáticamente._

- **Mensaje:** "Tu cuenta ya está asociada a otro dispositivo."
- **Explicación:** "Por seguridad, cada cuenta solo puede usarse en un dispositivo a la vez. Tu suscripción sigue activa."
- **Acciones Obligatorias:**
  1. 🔘 **Usar este dispositivo** (resetear el anterior).
  2. 🔘 **Cancelar** e ingresar desde el dispositivo original.
- **Advertencia:** "Al continuar, el dispositivo anterior perderá acceso."

### 🟡 Estado 4: Reset de dispositivo (confirmación)

_Si el usuario elige resetear._

- **Pregunta:** "¿Confirmas que deseas usar OLIMPO en este dispositivo?"
- **Aclaraciones:**
  - ❌ No se pierde la suscripción.
  - ❌ No se reinician los 30 días.
  - ✔️ Solo cambia el dispositivo activo.
- **Botones:** Confirmar / Cancelar.

### 🔴 Estado 5: Suscripción vencida

_Aparición automática._

- **Mensaje:** "Tu suscripción ha finalizado."
- **Info:** Fecha de término, Plan anterior.
- **Acciones:** Renovar suscripción / Salir.
- **Bloqueado:** Simulaciones, acceso a modelos, reset de dispositivo.

### 🔴 Estado 6: Error técnico / conexión

- **Mensaje:** "No pudimos verificar el estado de tu cuenta en este momento."
- **Acciones:** Reintentar / Contactar soporte.
- **Nota:** No culpar al usuario.

---

## 3. Reglas Visuales

- ❌ No hablar de JWT, tokens, backend, API.
- ❌ No usar lenguaje legal.
- ❌ No mostrar errores crudos.
- ✔️ Usar frases cortas.
- ✔️ Siempre explicar el “por qué”.
- ✔️ Siempre ofrecer una acción clara.

---

## 4. Regla de Negocio Subyacente

> **1 cuenta Gmail = 1 dispositivo = suscripción activa por 30 días**

El reset de dispositivo:

- **NO** borra la suscripción.
- **NO** reinicia el contador de días.
- **NO** cambia el plan.
- **SOLO** invalida el `device_id` anterior y permite registrar el nuevo.
