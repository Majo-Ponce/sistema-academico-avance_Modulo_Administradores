// Módulo de Matrículas — frontend (vanilla JS, sin dependencias).
// Consulta:  GET  /api/v1/matriculas
// Registro:  POST /api/v1/matriculas
// Esta página comparte el "login" guardado en localStorage por app.js
// (misma API, mismo origen → no hay problema de CORS).

const URL_BASE_API = "/api/v1";
const URL_MATRICULAS = `${URL_BASE_API}/matriculas`;

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

const formularioMatricula = document.getElementById("formulario-matricula");
const campoEstudiante = document.getElementById("matricula-estudiante");
const campoSeccion = document.getElementById("matricula-seccion");
const botonGuardarMatricula = document.getElementById("boton-guardar-matricula");
const botonLimpiarMatricula = document.getElementById("boton-limpiar-matricula");
const botonCancelarEdicion = document.getElementById(
  "boton-cancelar-edicion-matricula"
);
const tituloFormularioMatricula = document.getElementById(
  "titulo-formulario-matricula"
);
const alertaMatricula = document.getElementById("alerta-matricula");

const filtroEstado = document.getElementById("matricula-filtro-estado");
const campoBuscar = document.getElementById("matricula-buscar");
const botonRecargar = document.getElementById("boton-recargar-matriculas");
const cuerpoTabla = document.getElementById("cuerpo-tabla-matriculas");
const textoEstado = document.getElementById("texto-matriculas-estado");
const contadorMatriculas = document.getElementById("contador-matriculas");

let temporizadorBusqueda = null;
let matriculas = [];
let matriculaEditandoId = null;

const ETIQUETAS_CAMPO = {
  estudiante_id: "Estudiante",
  seccion_id: "Sección",
};

// ------------------------- Alertas -------------------------

function mostrarAlerta(tipo, titulo, detalles = []) {
  alertaMatricula.className = `alerta alerta-${tipo}`;
  alertaMatricula.replaceChildren();

  const encabezado = document.createElement("strong");
  encabezado.textContent = titulo;
  alertaMatricula.appendChild(encabezado);

  if (detalles.length > 0) {
    const lista = document.createElement("ul");
    detalles.forEach((texto) => {
      const item = document.createElement("li");
      item.textContent = texto;
      lista.appendChild(item);
    });
    alertaMatricula.appendChild(lista);
  }
}

function ocultarAlerta() {
  alertaMatricula.className = "alerta oculto";
  alertaMatricula.replaceChildren();
}

function marcarInvalido(nodo) {
  nodo.classList.add("campo-invalido");
  nodo.setAttribute("aria-invalid", "true");
}

function limpiarMarcas() {
  [campoEstudiante, campoSeccion].forEach((nodo) => {
    nodo.classList.remove("campo-invalido");
    nodo.removeAttribute("aria-invalid");
  });
}

// ------------------------- Validación del lado del cliente -------------------------
// Doble validación: antes de llamar al fetch, se revisa que no haya
// campos vacíos (estudiante y sección son obligatorios).

function validarMatricula(datos) {
  limpiarMarcas();
  const problemas = [];

  if (!datos.estudiante_id) {
    problemas.push({ nodo: campoEstudiante, texto: "Debe seleccionar un estudiante." });
  }
  if (!datos.seccion_id) {
    problemas.push({ nodo: campoSeccion, texto: "Debe seleccionar una sección." });
  }

  if (problemas.length > 0) {
    problemas.forEach(({ nodo }) => marcarInvalido(nodo));
    return {
      titulo: "Faltan datos obligatorios",
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
    case "greater_than":
      return `${etiqueta} no es válido: seleccione una opción de la lista.`;
    case "int_parsing":
    case "int_type":
      return `${etiqueta} debe ser un número entero.`;
    default:
      return `${etiqueta}: ${error.msg ?? "valor no válido"}.`;
  }
}

async function interpretarRespuestaError(respuesta) {
  const cuerpo = await respuesta.json().catch(() => null);
  const detalle = cuerpo?.detail;

  if (respuesta.status === 422 && Array.isArray(detalle)) {
    return { titulo: "La API rechazó la matrícula", detalles: detalle.map(traducirErrorValidacion) };
  }
  if (respuesta.status === 409) {
    return {
      titulo: "No se pudo matricular",
      detalles: [typeof detalle === "string" ? detalle : "Conflicto con una regla de negocio."],
    };
  }
  if (respuesta.status === 404) {
    return {
      titulo: "No se pudo matricular",
      detalles: [typeof detalle === "string" ? detalle : "Estudiante o sección no encontrados."],
    };
  }
  if (SERVIDOR_NO_DISPONIBLE.includes(respuesta.status)) {
    return { titulo: "Sin conexión con el servidor", detalles: [MENSAJE_SIN_CONEXION] };
  }
  if (respuesta.status >= 500) {
    return { titulo: "Error en el servidor", detalles: ["Intente de nuevo en unos momentos."] };
  }
  return {
    titulo: "La API rechazó la matrícula",
    detalles: [typeof detalle === "string" ? detalle : `No se pudo registrar la matrícula (código ${respuesta.status}).`],
  };
}

// ------------------------- Carga de combos (GET) -------------------------

async function cargarEstudiantes() {
  try {
    const respuesta = await fetchAuth(`${URL_BASE_API}/estudiantes?estado=ACTIVO&limite=100`);
    const estudiantes = await respuesta.json();
    campoEstudiante.innerHTML = '<option value="">Seleccione un estudiante</option>';
    estudiantes.forEach((e) => {
      const opcion = document.createElement("option");
      opcion.value = e.id;
      opcion.textContent = `${e.cuenta} — ${e.nombres} ${e.apellidos}`;
      campoEstudiante.appendChild(opcion);
    });
  } catch (error) {
    campoEstudiante.innerHTML = '<option value="">No se pudieron cargar los estudiantes</option>';
  }
}

async function cargarSeccionesDisponibles() {
  try {
    const respuesta = await fetchAuth(`${URL_BASE_API}/secciones/disponibles`);
    const disponibles = await respuesta.json();
    campoSeccion.innerHTML = '<option value="">Seleccione una sección</option>';
    disponibles.forEach((s) => {
      const opcion = document.createElement("option");
      opcion.value = s.id;
      opcion.textContent =
        `${s.asignatura_codigo} — ${s.asignatura_nombre} · sección ${s.codigo} ` +
        `(${s.periodo_nombre}, cupos: ${s.cupos_disponibles})`;
      campoSeccion.appendChild(opcion);
    });
    if (disponibles.length === 0) {
      campoSeccion.innerHTML = '<option value="">No hay secciones con cupo disponible</option>';
    }
  } catch (error) {
    campoSeccion.innerHTML = '<option value="">No se pudieron cargar las secciones</option>';
  }
}

// ------------------------- Registro (POST) -------------------------

formularioMatricula.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  ocultarAlerta();

  const datos = {
    estudiante_id: Number(campoEstudiante.value) || null,
    seccion_id: Number(campoSeccion.value) || null,
  };

  const errorLocal = validarMatricula(datos);
  if (errorLocal) {
    mostrarAlerta("error", errorLocal.titulo, errorLocal.detalles);
    errorLocal.primerNodo.focus();
    return;
  }

  const esEdicion = matriculaEditandoId !== null;
  botonGuardarMatricula.disabled = true;
  botonGuardarMatricula.textContent = "Guardando...";

  try {
    const respuesta = await fetchAuth(
      `${URL_MATRICULAS}${esEdicion ? `/${matriculaEditandoId}` : ""}`,
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

    const creada = await respuesta.json();
    mostrarAlerta(
      "exito",
      esEdicion
        ? "¡Matrícula actualizada correctamente!"
        : "¡Matrícula registrada correctamente!",
      [
        `${creada.estudiante_nombre} — ${creada.asignatura_codigo} (sección ${creada.seccion_codigo}), estado ${creada.estado.toLowerCase()}.`,
      ]
    );
    limpiarFormulario(false);
    cargarSeccionesDisponibles();
    cargarMatriculas();
  } catch (error) {
    mostrarAlerta("error", "Sin conexión con el servidor", [MENSAJE_SIN_CONEXION]);
  } finally {
    botonGuardarMatricula.disabled = false;
    botonGuardarMatricula.textContent = matriculaEditandoId
      ? "Guardar cambios"
      : "Registrar matrícula";
  }
});

function limpiarFormulario(ocultar = true) {
  formularioMatricula.reset();
  matriculaEditandoId = null;
  tituloFormularioMatricula.textContent = "Nueva matrícula";
  botonGuardarMatricula.textContent = "Registrar matrícula";
  botonCancelarEdicion.classList.add("oculto");
  limpiarMarcas();
  if (ocultar) ocultarAlerta();
}

botonLimpiarMatricula.addEventListener("click", () => limpiarFormulario());
botonCancelarEdicion.addEventListener("click", () => limpiarFormulario());

// Anular conserva el historial y libera el cupo de la sección.

async function anularMatricula(matricula) {
  const confirmado = window.confirm(
    `¿Anular la matrícula de ${matricula.estudiante_nombre} en ` +
      `${matricula.asignatura_codigo} (sección ${matricula.seccion_codigo})? ` +
      "Si ya estaba cancelada, se mantendrá sin cambios."
  );
  if (!confirmado) return;

  try {
    const respuesta = await fetchAuth(`${URL_MATRICULAS}/${matricula.id}/cancelar`, {
      method: "PATCH",
    });
    if (!respuesta.ok) {
      const error = await interpretarRespuestaError(respuesta);
      window.alert(error.detalles.join("\n"));
      return;
    }
    cargarSeccionesDisponibles();
    cargarMatriculas();
  } catch (error) {
    window.alert(MENSAJE_SIN_CONEXION);
  }
}

async function reactivarMatricula(matricula) {
  const confirmado = window.confirm(
    `¿Reactivar la matrícula de ${matricula.estudiante_nombre} en ` +
      `${matricula.asignatura_codigo} (sección ${matricula.seccion_codigo})? ` +
      "Se validarán nuevamente cupos y reglas académicas."
  );
  if (!confirmado) return;

  try {
    const respuesta = await fetchAuth(`${URL_MATRICULAS}/${matricula.id}/reactivar`, {
      method: "PATCH",
    });
    if (!respuesta.ok) {
      const error = await interpretarRespuestaError(respuesta);
      window.alert(`No se pudo reactivar la matrícula:\n${error.detalles.join("\n")}`);
      return;
    }
    const resultado = await respuesta.json();
    window.alert(resultado.mensaje);
    await Promise.all([cargarSeccionesDisponibles(), cargarMatriculas()]);
  } catch (error) {
    window.alert(MENSAJE_SIN_CONEXION);
  }
}

// ------------------------- Listado (GET) -------------------------

function mostrarEstado(texto) {
  textoEstado.textContent = texto;
  textoEstado.classList.toggle("oculto", !texto);
}

function pastillaEstadoMatricula(estado) {
  if (estado === "MATRICULADA") {
    return '<span class="pastilla-estado pastilla-activo">Matriculada</span>';
  }
  return `<span class="pastilla-estado pastilla-neutral">Cancelada</span>`;
}

async function cargarMatriculas() {
  const buscar = campoBuscar.value.trim();
  const estado = filtroEstado.value;

  cuerpoTabla.replaceChildren();
  contadorMatriculas.textContent = "";
  mostrarEstado("Cargando matrículas...");

  try {
    const parametros = new URLSearchParams();
    if (estado) parametros.set("estado", estado);
    const respuesta = await fetchAuth(`${URL_MATRICULAS}?${parametros.toString()}`);
    if (!respuesta.ok) {
      const error = new Error(`HTTP ${respuesta.status}`);
      error.sinConexion = SERVIDOR_NO_DISPONIBLE.includes(respuesta.status);
      throw error;
    }
    matriculas = await respuesta.json();

    const filtradas = buscar
      ? matriculas.filter((m) =>
          `${m.estudiante_nombre} ${m.estudiante_cuenta} ${m.asignatura_codigo} ${m.asignatura_nombre}`
            .toLowerCase()
            .includes(buscar.toLowerCase())
        )
      : matriculas;

    renderizarTabla(filtradas, buscar);
  } catch (error) {
    cuerpoTabla.replaceChildren();
    contadorMatriculas.textContent = "";
    mostrarEstado(
      error instanceof TypeError || error.sinConexion
        ? MENSAJE_SIN_CONEXION
        : "No se pudo cargar la lista de matrículas. Intente recargar."
    );
  }
}

function renderizarTabla(lista, buscar) {
  cuerpoTabla.replaceChildren();
  contadorMatriculas.textContent = buscar
    ? `${lista.length} resultado(s) para “${buscar}”`
    : `${lista.length} matrícula(s) registrada(s)`;

  if (lista.length === 0) {
    mostrarEstado(
      buscar
        ? "No se encontraron matrículas con ese criterio."
        : "Aún no hay matrículas registradas. Use el formulario para crear la primera."
    );
    return;
  }
  mostrarEstado("");

  lista.forEach((matricula) => {
    const fila = document.createElement("tr");

    const celdas = [
      ["Estudiante", matricula.estudiante_nombre],
      ["Cuenta", matricula.estudiante_cuenta],
      ["Asignatura", `${matricula.asignatura_codigo} — ${matricula.asignatura_nombre}`],
      ["Sección", matricula.seccion_codigo],
      ["Período", matricula.periodo_nombre],
      ["Fecha", matricula.fecha_matricula?.slice(0, 10) ?? "—"],
    ];
    celdas.forEach(([etiqueta, valor]) => {
      const celda = document.createElement("td");
      celda.textContent = valor;
      celda.dataset.label = etiqueta;
      fila.appendChild(celda);
    });

    const celdaEstado = document.createElement("td");
    celdaEstado.innerHTML = pastillaEstadoMatricula(matricula.estado);
    celdaEstado.dataset.label = "Estado";
    fila.appendChild(celdaEstado);

    const celdaAcciones = document.createElement("td");
    celdaAcciones.dataset.label = "Acciones";
    const acciones = document.createElement("div");
    acciones.className = "acciones-fila";
    const botonEditar = document.createElement("button");
    botonEditar.type = "button";
    botonEditar.className = "boton-icono";
    botonEditar.textContent = "Editar";
    botonEditar.addEventListener("click", () => editarMatricula(matricula));
    acciones.appendChild(botonEditar);

    const botonEstado = document.createElement("button");
    botonEstado.type = "button";
    botonEstado.className = matricula.estado === "CANCELADA"
      ? "boton-icono boton-reactivar"
      : "boton-icono peligro";
    if (matricula.estado === "CANCELADA") {
      botonEstado.textContent = "Reactivar";
      botonEstado.addEventListener("click", () => reactivarMatricula(matricula));
    } else {
      botonEstado.textContent = "Anular";
      botonEstado.addEventListener("click", () => anularMatricula(matricula));
    }
    acciones.appendChild(botonEstado);
    celdaAcciones.appendChild(acciones);
    fila.appendChild(celdaAcciones);

    cuerpoTabla.appendChild(fila);
  });
}

function seleccionarOpcion(select, value, label) {
  const valor = String(value);
  if (![...select.options].some((opcion) => opcion.value === valor)) {
    const opcion = document.createElement("option");
    opcion.value = valor;
    opcion.textContent = label;
    select.appendChild(opcion);
  }
  select.value = valor;
}

function editarMatricula(matricula) {
  seleccionarOpcion(
    campoEstudiante,
    matricula.estudiante_id,
    `${matricula.estudiante_cuenta} — ${matricula.estudiante_nombre}`
  );
  seleccionarOpcion(
    campoSeccion,
    matricula.seccion_id,
    `${matricula.asignatura_codigo} — ${matricula.asignatura_nombre} · sección ${matricula.seccion_codigo} (${matricula.periodo_nombre})`
  );
  matriculaEditandoId = matricula.id;
  tituloFormularioMatricula.textContent = `Editar matrícula — ${matricula.estudiante_nombre}`;
  botonGuardarMatricula.textContent = "Guardar cambios";
  botonCancelarEdicion.classList.remove("oculto");
  ocultarAlerta();
  formularioMatricula.scrollIntoView({ behavior: "smooth", block: "start" });
}

botonRecargar.addEventListener("click", cargarMatriculas);
filtroEstado.addEventListener("change", cargarMatriculas);
campoBuscar.addEventListener("input", () => {
  clearTimeout(temporizadorBusqueda);
  temporizadorBusqueda = setTimeout(cargarMatriculas, 300);
});

botonActualizar.addEventListener("click", () => {
  cargarEstudiantes();
  cargarSeccionesDisponibles();
  cargarMatriculas();
});

// ------------------------- Arranque -------------------------

if (usuarioActual) {
  cargarEstudiantes();
  cargarSeccionesDisponibles();
  cargarMatriculas();
}
