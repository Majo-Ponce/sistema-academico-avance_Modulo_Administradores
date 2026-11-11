// Módulo de Secciones — frontend (vanilla JS, sin dependencias).
// Consulta:  GET  /api/v1/secciones
// Registro:  POST /api/v1/secciones
// Esta página comparte el "login" guardado en localStorage por app.js
// (misma API, mismo origen → no hay problema de CORS).

const URL_BASE_API = "/api/v1";
const URL_SECCIONES = `${URL_BASE_API}/secciones`;

const MENSAJE_SIN_CONEXION =
  "No hay conexión con el servidor. Verifique que la API esté encendida " +
  "(uvicorn main:app --reload) y vuelva a intentarlo.";
const SERVIDOR_NO_DISPONIBLE = [502, 503, 504];

// ------------------------- Guardia de sesión -------------------------

// Solo el ADMINISTRADOR puede usar esta p?gina (el backend tambi?n lo exige).
const usuarioActual = obtenerUsuario();
if (!usuarioActual || !obtenerToken() || usuarioActual.rol !== "ADMIN") {
  window.location.href = "/index.html";
}

const chipUsuario = document.getElementById("chip-usuario");
const botonSalir = document.getElementById("boton-salir");
const botonActualizar = document.getElementById("boton-actualizar");

if (usuarioActual) {
  chipUsuario.textContent = `Rol: ${usuarioActual.rol}`;
}

botonSalir.addEventListener("click", cerrarSesion);

// ------------------------- Referencias del DOM -------------------------

const formularioSeccion = document.getElementById("formulario-seccion");
const campoSeccionId = document.getElementById("seccion-id");
const tituloFormularioSeccion = document.getElementById("titulo-formulario-seccion");
const botonCancelarEdicionSeccion = document.getElementById("boton-cancelar-edicion-seccion");
const campoCodigo = document.getElementById("seccion-codigo");
const campoAsignatura = document.getElementById("seccion-asignatura");
const campoDocente = document.getElementById("seccion-docente");
const campoPeriodo = document.getElementById("seccion-periodo");
const campoAula = document.getElementById("seccion-aula");
const campoDias = document.getElementById("seccion-dias");
const campoHoraInicio = document.getElementById("seccion-hora-inicio");
const campoHoraFin = document.getElementById("seccion-hora-fin");
const campoCupo = document.getElementById("seccion-cupo");
const campoEstado = document.getElementById("seccion-estado");
const botonGuardarSeccion = document.getElementById("boton-guardar-seccion");
const botonLimpiarSeccion = document.getElementById("boton-limpiar-seccion");
const alertaSeccion = document.getElementById("alerta-seccion");

const filtroPeriodo = document.getElementById("seccion-filtro-periodo");
const campoBuscar = document.getElementById("seccion-buscar");
const botonRecargar = document.getElementById("boton-recargar-secciones");
const cuerpoTabla = document.getElementById("cuerpo-tabla-secciones");
const textoEstado = document.getElementById("texto-secciones-estado");
const contadorSecciones = document.getElementById("contador-secciones");

let temporizadorBusqueda = null;
let secciones = [];
let catalogosSeccionCargados = Promise.resolve();

// Reglas de validación en el navegador (deben coincidir con
// app/schemas.py -> SeccionEntrada).
const REGLAS_TEXTO = [
  { clave: "codigo", etiqueta: "Código de sección", nodo: campoCodigo, min: 2, max: 10 },
  { clave: "dias", etiqueta: "Días", nodo: campoDias, min: 2, max: 30 },
];
const REGLAS_SELECT = [
  { clave: "asignatura_id", etiqueta: "Asignatura", nodo: campoAsignatura },
  { clave: "docente_id", etiqueta: "Docente", nodo: campoDocente },
  { clave: "periodo_id", etiqueta: "Período académico", nodo: campoPeriodo },
];

const ETIQUETAS_CAMPO = {
  codigo: "Código de sección",
  asignatura_id: "Asignatura",
  docente_id: "Docente",
  periodo_id: "Período académico",
  aula_id: "Aula",
  dias: "Días",
  hora_inicio: "Hora de inicio",
  hora_fin: "Hora de fin",
  cupo_maximo: "Cupo máximo",
  estado: "Estado",
};

// ------------------------- Alertas -------------------------

function mostrarAlerta(tipo, titulo, detalles = []) {
  alertaSeccion.className = `alerta alerta-${tipo}`;
  alertaSeccion.replaceChildren();

  const encabezado = document.createElement("strong");
  encabezado.textContent = titulo;
  alertaSeccion.appendChild(encabezado);

  if (detalles.length > 0) {
    const lista = document.createElement("ul");
    detalles.forEach((texto) => {
      const item = document.createElement("li");
      item.textContent = texto;
      lista.appendChild(item);
    });
    alertaSeccion.appendChild(lista);
  }
}

function ocultarAlerta() {
  alertaSeccion.className = "alerta oculto";
  alertaSeccion.replaceChildren();
}

function limpiarMarcas() {
  [...REGLAS_TEXTO, ...REGLAS_SELECT].forEach(({ nodo }) => {
    nodo.classList.remove("campo-invalido");
    nodo.removeAttribute("aria-invalid");
  });
  campoHoraInicio.classList.remove("campo-invalido");
  campoHoraFin.classList.remove("campo-invalido");
  campoCupo.classList.remove("campo-invalido");
}

function marcarInvalido(nodo) {
  nodo.classList.add("campo-invalido");
  nodo.setAttribute("aria-invalid", "true");
}

// ------------------------- Validación del lado del cliente -------------------------
// Doble validación: antes de llamar al fetch, se revisa que no haya
// campos vacíos y que los formatos sean coherentes.

function validarSeccion(datos) {
  limpiarMarcas();
  const problemas = [];

  REGLAS_TEXTO.forEach(({ clave, etiqueta, nodo, min, max }) => {
    const valor = datos[clave];
    if (!valor) {
      problemas.push({ nodo, texto: `${etiqueta} no puede estar vacío.` });
    } else if (valor.length < min || valor.length > max) {
      problemas.push({ nodo, texto: `${etiqueta} debe tener entre ${min} y ${max} caracteres.` });
    }
  });

  REGLAS_SELECT.forEach(({ etiqueta, nodo }) => {
    if (!nodo.value) {
      problemas.push({ nodo, texto: `Debe seleccionar ${etiqueta.toLowerCase()}.` });
    }
  });

  if (!datos.hora_inicio) {
    problemas.push({ nodo: campoHoraInicio, texto: "La hora de inicio no puede estar vacía." });
  }
  if (!datos.hora_fin) {
    problemas.push({ nodo: campoHoraFin, texto: "La hora de fin no puede estar vacía." });
  }
  if (datos.hora_inicio && datos.hora_fin && datos.hora_fin <= datos.hora_inicio) {
    problemas.push({ nodo: campoHoraFin, texto: "La hora de fin debe ser posterior a la hora de inicio." });
  }

  if (!campoCupo.value) {
    problemas.push({ nodo: campoCupo, texto: "El cupo máximo no puede estar vacío." });
  } else if (datos.cupo_maximo < 1 || datos.cupo_maximo > 200) {
    problemas.push({ nodo: campoCupo, texto: "El cupo máximo debe estar entre 1 y 200." });
  }

  if (problemas.length > 0) {
    problemas.forEach(({ nodo }) => marcarInvalido(nodo));
    return {
      titulo: "Revise los datos del formulario",
      detalles: problemas.map(({ texto }) => texto),
      primerNodo: problemas[0].nodo,
    };
  }
  return null;
}

// ------------------------- Errores devueltos por la API -------------------------

function traducirErrorValidacion(error) {
  const campo = error.loc?.[error.loc.length - 1];
  const etiqueta = ETIQUETAS_CAMPO[campo] ?? "Dato enviado";
  const ctx = error.ctx ?? {};
  switch (error.type) {
    case "missing":
      return `${etiqueta} es obligatorio.`;
    case "string_too_short":
      return `${etiqueta} debe tener al menos ${ctx.min_length} caracteres.`;
    case "string_too_long":
      return `${etiqueta} no puede superar ${ctx.max_length} caracteres.`;
    case "string_pattern_mismatch":
      return `${etiqueta} tiene un formato inválido (use HH:MM).`;
    case "greater_than_equal":
      return `${etiqueta} debe ser mayor o igual a ${ctx.ge}.`;
    case "less_than_equal":
      return `${etiqueta} debe ser menor o igual a ${ctx.le}.`;
    case "greater_than":
      return `${etiqueta} no es válido: seleccione una opción de la lista.`;
    case "literal_error":
      return `${etiqueta} tiene un valor no permitido.`;
    default:
      return `${etiqueta}: ${error.msg ?? "valor no válido"}.`;
  }
}

async function interpretarRespuestaError(respuesta) {
  const cuerpo = await respuesta.json().catch(() => null);
  const detalle = cuerpo?.detail;

  if (respuesta.status === 422 && Array.isArray(detalle)) {
    return { titulo: "La API rechazó el registro", detalles: detalle.map(traducirErrorValidacion) };
  }
  if (respuesta.status === 409) {
    return {
      titulo: "No se pudo crear la sección",
      detalles: [typeof detalle === "string" ? detalle : "Conflicto con una regla de negocio."],
    };
  }
  if (SERVIDOR_NO_DISPONIBLE.includes(respuesta.status)) {
    return { titulo: "Sin conexión con el servidor", detalles: [MENSAJE_SIN_CONEXION] };
  }
  if (respuesta.status >= 500) {
    return { titulo: "Error en el servidor", detalles: ["Intente de nuevo en unos momentos."] };
  }
  return {
    titulo: "La API rechazó el registro",
    detalles: [typeof detalle === "string" ? detalle : `No se pudo registrar la sección (código ${respuesta.status}).`],
  };
}

// ------------------------- Carga de combos (GET) -------------------------

async function cargarAsignaturas() {
  try {
    const respuesta = await fetchAuth(`${URL_BASE_API}/asignaturas?solo_activas=true`);
    const asignaturas = await respuesta.json();
    campoAsignatura.innerHTML = '<option value="">Seleccione una asignatura</option>';
    asignaturas.forEach((a) => {
      const opcion = document.createElement("option");
      opcion.value = a.id;
      opcion.textContent = `${a.codigo} — ${a.nombre}`;
      campoAsignatura.appendChild(opcion);
    });
  } catch (error) {
    campoAsignatura.innerHTML = '<option value="">No se pudieron cargar las asignaturas</option>';
  }
}

async function cargarDocentes() {
  try {
    const respuesta = await fetchAuth(`${URL_BASE_API}/docentes?estado=ACTIVO`);
    const docentes = await respuesta.json();
    campoDocente.innerHTML = '<option value="">Seleccione un docente</option>';
    docentes.forEach((d) => {
      const opcion = document.createElement("option");
      opcion.value = d.id;
      opcion.textContent = `${d.nombres} ${d.apellidos}`;
      campoDocente.appendChild(opcion);
    });
  } catch (error) {
    campoDocente.innerHTML = '<option value="">No se pudieron cargar los docentes</option>';
  }
}

async function cargarPeriodos() {
  try {
    const respuesta = await fetchAuth(`${URL_BASE_API}/periodos`);
    const periodos = await respuesta.json();
    campoPeriodo.innerHTML = '<option value="">Seleccione un período</option>';
    filtroPeriodo.innerHTML = '<option value="">Todos los períodos</option>';
    periodos.forEach((p) => {
      const opcion = document.createElement("option");
      opcion.value = p.id;
      opcion.textContent = `${p.nombre}${p.activo ? " (activo)" : ""}`;
      campoPeriodo.appendChild(opcion);

      const opcionFiltro = opcion.cloneNode(true);
      filtroPeriodo.appendChild(opcionFiltro);

      if (p.activo) campoPeriodo.value = p.id;
    });
  } catch (error) {
    campoPeriodo.innerHTML = '<option value="">No se pudieron cargar los períodos</option>';
  }
}

async function cargarAulas() {
  try {
    const respuesta = await fetchAuth(`${URL_BASE_API}/aulas?solo_activas=true`);
    const aulas = await respuesta.json();
    campoAula.innerHTML = '<option value="">Sin aula asignada</option>';
    aulas.forEach((a) => {
      const opcion = document.createElement("option");
      opcion.value = a.id;
      opcion.textContent = `${a.codigo} — ${a.edificio} (cap. ${a.capacidad})`;
      campoAula.appendChild(opcion);
    });
  } catch (error) {
    campoAula.innerHTML = '<option value="">No se pudieron cargar las aulas</option>';
  }
}

function cargarCatalogosSeccion() {
  return Promise.all([
    cargarAsignaturas(),
    cargarDocentes(),
    cargarPeriodos(),
    cargarAulas(),
  ]);
}

// ------------------------- Registro (POST) -------------------------

formularioSeccion.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  ocultarAlerta();

  const datos = {
    codigo: campoCodigo.value.trim(),
    asignatura_id: Number(campoAsignatura.value) || null,
    docente_id: Number(campoDocente.value) || null,
    periodo_id: Number(campoPeriodo.value) || null,
    aula_id: campoAula.value ? Number(campoAula.value) : null,
    dias: campoDias.value.trim(),
    hora_inicio: campoHoraInicio.value,
    hora_fin: campoHoraFin.value,
    cupo_maximo: Number(campoCupo.value) || 0,
    estado: campoEstado.value,
  };

  const errorLocal = validarSeccion(datos);
  if (errorLocal) {
    mostrarAlerta("error", errorLocal.titulo, errorLocal.detalles);
    errorLocal.primerNodo.focus();
    return;
  }

  const idEnEdicion = campoSeccionId.value;
  const esEdicion = Boolean(idEnEdicion);

  botonGuardarSeccion.disabled = true;
  botonGuardarSeccion.textContent = "Guardando...";

  try {
    const respuesta = await fetchAuth(
      `${URL_SECCIONES}${esEdicion ? `/${idEnEdicion}` : ""}`,
      {
        method: esEdicion ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(datos),
      }
    );

    if (!respuesta.ok) {
      const error = await interpretarRespuestaError(respuesta);
      mostrarAlerta("error", error.titulo, error.detalles);
      return;
    }

    const guardada = await respuesta.json();
    mostrarAlerta(
      "exito",
      esEdicion ? "¡Sección actualizada correctamente!" : "¡Sección registrada correctamente!",
      [`${guardada.asignatura_codigo} — sección ${guardada.codigo} (${guardada.periodo_nombre}) ya aparece en la lista.`]
    );
    cancelarEdicionSeccion();
    cargarSecciones();
  } catch (error) {
    mostrarAlerta("error", "Sin conexión con el servidor", [MENSAJE_SIN_CONEXION]);
  } finally {
    botonGuardarSeccion.disabled = false;
    botonGuardarSeccion.textContent = campoSeccionId.value ? "Guardar cambios" : "Registrar sección";
  }
});

function limpiarFormulario(ocultar = true) {
  formularioSeccion.reset();
  campoSeccionId.value = "";
  limpiarMarcas();
  if (ocultar) ocultarAlerta();
}

botonLimpiarSeccion.addEventListener("click", () => cancelarEdicionSeccion());

function editarSeccion(seccion) {
  campoSeccionId.value = seccion.id;
  campoCodigo.value = seccion.codigo;
  campoAsignatura.value = seccion.asignatura_id;
  campoDocente.value = seccion.docente_id;
  campoPeriodo.value = seccion.periodo_id;
  campoAula.value = seccion.aula_id ?? "";
  campoDias.value = seccion.dias;
  campoHoraInicio.value = seccion.hora_inicio;
  campoHoraFin.value = seccion.hora_fin;
  campoCupo.value = seccion.cupo_maximo;
  campoEstado.value = seccion.estado;

  tituloFormularioSeccion.textContent = `Editar sección — ${seccion.asignatura_codigo} ${seccion.codigo}`;
  botonGuardarSeccion.textContent = "Guardar cambios";
  botonCancelarEdicionSeccion.classList.remove("oculto");
  ocultarAlerta();
  formularioSeccion.scrollIntoView({ behavior: "smooth", block: "start" });
}

function cancelarEdicionSeccion() {
  limpiarFormulario(false);
  tituloFormularioSeccion.textContent = "Nueva sección";
  botonGuardarSeccion.textContent = "Registrar sección";
  botonCancelarEdicionSeccion.classList.add("oculto");
}

botonCancelarEdicionSeccion.addEventListener("click", cancelarEdicionSeccion);

async function eliminarSeccion(seccion) {
  const confirmado = window.confirm(
    `¿Eliminar la sección ${seccion.asignatura_codigo} — ${seccion.codigo}? Esta acción no se puede deshacer.`
  );
  if (!confirmado) return;

  try {
    const respuesta = await fetchAuth(`${URL_SECCIONES}/${seccion.id}`, {
      method: "DELETE",
    });
    if (!respuesta.ok) {
      const detalle = await respuesta.json().catch(() => null);
      window.alert(
        detalle?.detail ?? "No se pudo eliminar (puede tener estudiantes matriculados)."
      );
      return;
    }
    cargarSecciones();
  } catch (error) {
    window.alert("No se pudo conectar con la API.");
  }
}

// ------------------------- Listado (GET) -------------------------

function mostrarEstado(texto) {
  textoEstado.textContent = texto;
  textoEstado.classList.toggle("oculto", !texto);
}

function pastillaEstadoSeccion(estado) {
  if (estado === "ABIERTA") return `<span class="pastilla-estado pastilla-activo">Abierta</span>`;
  if (estado === "CERRADA") return `<span class="pastilla-estado pastilla-alerta">Cerrada</span>`;
  return `<span class="pastilla-estado pastilla-neutral">Finalizada</span>`;
}

async function cargarSecciones() {
  await catalogosSeccionCargados;
  const buscar = campoBuscar.value.trim();
  const periodoId = filtroPeriodo.value;

  cuerpoTabla.replaceChildren();
  contadorSecciones.textContent = "";
  mostrarEstado("Cargando secciones...");

  try {
    const parametros = new URLSearchParams();
    if (periodoId) parametros.set("periodo_id", periodoId);
    const respuesta = await fetchAuth(`${URL_SECCIONES}?${parametros.toString()}`);
    if (!respuesta.ok) {
      const error = new Error(`HTTP ${respuesta.status}`);
      error.sinConexion = SERVIDOR_NO_DISPONIBLE.includes(respuesta.status);
      throw error;
    }
    secciones = await respuesta.json();

    const filtradas = buscar
      ? secciones.filter((s) =>
          `${s.codigo} ${s.asignatura_codigo} ${s.asignatura_nombre}`
            .toLowerCase()
            .includes(buscar.toLowerCase())
        )
      : secciones;

    renderizarTabla(filtradas, buscar);
  } catch (error) {
    cuerpoTabla.replaceChildren();
    contadorSecciones.textContent = "";
    mostrarEstado(
      error instanceof TypeError || error.sinConexion
        ? MENSAJE_SIN_CONEXION
        : "No se pudo cargar la lista de secciones. Intente recargar."
    );
  }
}

function renderizarTabla(lista, buscar) {
  cuerpoTabla.replaceChildren();
  contadorSecciones.textContent = buscar
    ? `${lista.length} resultado(s) para “${buscar}”`
    : `${lista.length} sección(es) registrada(s)`;

  if (lista.length === 0) {
    mostrarEstado(
      buscar
        ? "No se encontraron secciones con ese criterio."
        : "Aún no hay secciones registradas. Use el formulario para crear la primera."
    );
    return;
  }
  mostrarEstado("");

  lista.forEach((seccion) => {
    const fila = document.createElement("tr");
    fila.innerHTML = `
      <td>${seccion.codigo}</td>
      <td>${seccion.asignatura_codigo} — ${seccion.asignatura_nombre}</td>
      <td>${seccion.docente_nombre}</td>
      <td>${seccion.periodo_nombre}</td>
      <td>${seccion.dias} ${seccion.hora_inicio}–${seccion.hora_fin}</td>
      <td>${seccion.aula_codigo ?? "—"}</td>
      <td>${seccion.matriculados}/${seccion.cupo_maximo}</td>
      <td>${pastillaEstadoSeccion(seccion.estado)}</td>
      <td>
        <div class="acciones-fila">
          <button type="button" class="boton-icono" data-accion="editar">Editar</button>
          <button type="button" class="boton-icono peligro" data-accion="eliminar">Eliminar</button>
        </div>
      </td>
    `;
    fila.querySelector('[data-accion="editar"]').addEventListener("click", () =>
      editarSeccion(seccion)
    );
    fila.querySelector('[data-accion="eliminar"]').addEventListener("click", () =>
      eliminarSeccion(seccion)
    );
    cuerpoTabla.appendChild(fila);
  });
}

botonRecargar.addEventListener("click", cargarSecciones);
filtroPeriodo.addEventListener("change", cargarSecciones);
campoBuscar.addEventListener("input", () => {
  clearTimeout(temporizadorBusqueda);
  temporizadorBusqueda = setTimeout(cargarSecciones, 300);
});

botonActualizar.addEventListener("click", async () => {
  catalogosSeccionCargados = cargarCatalogosSeccion();
  await catalogosSeccionCargados;
  await cargarSecciones();
});

// ------------------------- Arranque -------------------------

if (usuarioActual) {
  catalogosSeccionCargados = cargarCatalogosSeccion();
  cargarSecciones();
}
