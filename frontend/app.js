// Sistema Académico — frontend (vanilla JS, sin dependencias).
// Como este archivo se sirve desde la misma API (FastAPI + StaticFiles),
// las rutas son relativas: no hay problema de CORS.

const URL_BASE_API = "/api/v1";



const vistaLogin = document.getElementById("vista-login");
const vistaDashboard = document.getElementById("vista-dashboard");

const formularioLogin = document.getElementById("formulario-login");
const campoUsuario = document.getElementById("campo-usuario");
const campoClave = document.getElementById("campo-clave");
const botonEntrar = document.getElementById("boton-entrar");
const mensajeLogin = document.getElementById("mensaje-login");
const modalCambioPassword = document.getElementById("modal-cambio-password");
const formularioCambioPassword = document.getElementById("formulario-cambio-password");
const campoClaveActual = document.getElementById("clave-actual");
const campoClaveNueva = document.getElementById("clave-nueva");
const campoClaveNuevaConfirmacion = document.getElementById("clave-nueva-confirmacion");
const botonCambiarPassword = document.getElementById("boton-cambiar-password");
const mensajeCambioPassword = document.getElementById("mensaje-cambio-password");

const tituloBienvenida = document.getElementById("titulo-bienvenida");
const chipUsuario = document.getElementById("chip-usuario");
const botonAdministradores = document.getElementById("boton-administradores");
const botonActualizar = document.getElementById("boton-actualizar");
const botonSalir = document.getElementById("boton-salir");
const filaTarjetas = document.getElementById("fila-tarjetas");
const textoPeriodo = document.getElementById("texto-periodo");
const filaTarjetasDocente = document.getElementById("fila-tarjetas-docente");
const textoPeriodoDocente = document.getElementById("texto-periodo-docente");
const campoBuscar = document.getElementById("campo-buscar");
const cuerpoTablaEstudiantes = document.getElementById("cuerpo-tabla-estudiantes");
const textoSinResultados = document.getElementById("texto-sin-resultados");

const tituloFormulario = document.getElementById("titulo-formulario");
const formularioEstudiante = document.getElementById("formulario-estudiante");
const campoEstudianteId = document.getElementById("estudiante-id");
const campoNombres = document.getElementById("estudiante-nombres");
const campoApellidos = document.getElementById("estudiante-apellidos");
const campoCuenta = document.getElementById("estudiante-cuenta");
const campoCorreo = document.getElementById("estudiante-correo");
const campoTelefono = document.getElementById("estudiante-telefono");
const campoNacimiento = document.getElementById("estudiante-nacimiento");
const campoCarrera = document.getElementById("estudiante-carrera");
const campoEstado = document.getElementById("estudiante-estado");
const botonGuardarEstudiante = document.getElementById("boton-guardar-estudiante");
const botonCancelarEdicion = document.getElementById("boton-cancelar-edicion");
const mensajeFormulario = document.getElementById("mensaje-formulario");

let usuarioActual = null;
let temporizadorBusqueda = null;
const formularioAdministrador = document.getElementById("formulario-administrador");
const campoAdministradorId = document.getElementById("administrador-id");
const campoAdministradorUsuario = document.getElementById("administrador-usuario");
const campoAdministradorNombre = document.getElementById("administrador-nombre");
const campoAdministradorEmail = document.getElementById("administrador-email");
const campoAdministradorActivo = document.getElementById("administrador-activo");
const tituloFormularioAdministrador = document.getElementById("titulo-formulario-administrador");
const botonGuardarAdministrador = document.getElementById("boton-guardar-administrador");
const botonCancelarAdministrador = document.getElementById("boton-cancelar-administrador");
const mensajeAdministrador = document.getElementById("mensaje-administrador");
const cuerpoTablaAdministradores = document.getElementById("cuerpo-tabla-administradores");
const textoAdministradoresEstado = document.getElementById("texto-administradores-estado");

const TARJETAS_KPI = [
  { clave: "estudiantes_activos", etiqueta: "Estudiantes activos" },
  { clave: "docentes_activos", etiqueta: "Docentes activos" },
  { clave: "carreras_activas", etiqueta: "Carreras activas" },
  { clave: "asignaturas_activas", etiqueta: "Asignaturas activas" },
  { clave: "secciones_abiertas", etiqueta: "Secciones abiertas" },
  { clave: "matriculas_activas", etiqueta: "Matrículas activas" },
];

const TARJETAS_KPI_DOCENTE = [
  { clave: "mis_secciones", etiqueta: "Mis secciones (período activo)" },
  { clave: "mis_estudiantes", etiqueta: "Mis estudiantes (período activo)" },
];

// ------------------------- Autenticación -------------------------

formularioLogin.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  mensajeLogin.textContent = "";
  botonEntrar.disabled = true;
  botonEntrar.textContent = "Entrando...";

  try {
    // Login público: se usa fetch() normal, NO fetchAuth(). fetchAuth()
    // intercepta cualquier respuesta 401 llamando a cerrarSesion() (que
    // redirige a index.html); si lo usáramos aquí, una contraseña
    // incorrecta (401) dispararía esa redirección en vez de mostrar el
    // mensaje de error en el propio formulario.
    const respuesta = await fetch(`${URL_BASE_API}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: campoUsuario.value.trim(),
        password: campoClave.value,
      }),
    });

    if (!respuesta.ok) {
      mensajeLogin.textContent =
        respuesta.status === 401
          ? "Usuario o contraseña incorrectos."
          : "No se pudo iniciar sesión.";
      return;
    }

    // La API (app/routers/auth.py) responde con los datos del usuario
    // más el token: {id, usuario, nombre_completo, rol, access_token, ...}
    const cuerpo = await respuesta.json();
    usuarioActual = {
      id: cuerpo.id,
      docente_id: cuerpo.docente_id ?? null,
      usuario: cuerpo.usuario,
      nombre_completo: cuerpo.nombre_completo,
      rol: cuerpo.rol,
      debe_cambiar_password:
        cuerpo.debe_cambiar_password ?? cuerpo.cambiar_password,
    };
    guardarSesion(cuerpo.access_token, usuarioActual);
    mostrarDashboard();
  } catch (error) {
    mensajeLogin.textContent =
      "No se pudo conectar con la API. ¿Está corriendo uvicorn?";
  } finally {
    botonEntrar.disabled = false;
    botonEntrar.textContent = "Iniciar sesión";
  }
});

// Mantiene la sesión activa al cargar/recargar la página, y al navegar
// desde/hacia secciones.html y matriculas.html (comparten el mismo
// localStorage: misma API, mismo origen). Se invoca al final del archivo,
// una vez que ya existen moduloEstudiantes, moduloDocentes,
// moduloAsignaturas y botonesMenu (declarados más abajo).
//
// Esta es la ÚNICA rutina que decide si se muestra el login o el
// dashboard al cargar la página. Antes existía un segundo bloque al final
// del archivo que volvía a comprobar un "token" que el login nunca llegó
// a guardar, y forzaba otra vez la pantalla de login justo después de que
// esta función mostrara el dashboard: por eso la vista parecía "trabada"
// o no transicionaba tras iniciar sesión.
function restaurarSesion() {
  const usuario = obtenerUsuario();
  const token = obtenerToken();
  if (!usuario || !token) {
    vistaLogin.classList.remove("oculto");
    vistaDashboard.classList.add("oculto");
    return;
  }
  usuarioActual = usuario;
  if (!MODULOS_POR_ROL[usuarioActual.rol]) {
    cerrarSesion();
    return;
  }
  mostrarDashboard();
  if (usuarioActual.debe_cambiar_password) return;
  const moduloSolicitado = window.location.hash.replace("#", "");
  if (MODULOS_POR_ROL[usuarioActual.rol].includes(moduloSolicitado)) {
    mostrarModulo(moduloSolicitado);
  }
}

// ------------------------- Roles -------------------------

// Qué módulos puede ver cada rol. El primero es el módulo inicial.
// El backend aplica la misma regla (403 si el rol no corresponde).
const MODULOS_POR_ROL = {
  ADMIN: [
    "estudiantes",
    "docentes",
    "asignaturas",
    "carreras",
    "periodos",
    "aulas",
    "administradores",
  ],
  DOCENTE: [
    "inicio",
    "mis-secciones",
    "estudiantes-docente",
    "calificaciones-docente",
    "detalle-clase-docente",
  ],
};

const esAdmin = () => usuarioActual?.rol === "ADMIN";

function aplicarPermisosDeRol() {
  const admin = esAdmin();
  botonAdministradores.classList.toggle("oculto", !admin);
  botonActualizar.classList.toggle("oculto", !admin);
  document.querySelectorAll(".solo-admin").forEach((nodo) =>
    nodo.classList.toggle("oculto", !admin)
  );
  document.querySelectorAll(".solo-docente").forEach((nodo) =>
    nodo.classList.toggle("oculto", admin)
  );
  document.getElementById("titulo-menu-rol").textContent = admin
    ? "ADMINISTRACIÓN GLOBAL"
    : "PANEL DEL DOCENTE";
}

// ------------------------- Dashboard -------------------------

function mostrarDashboard() {
  vistaLogin.classList.add("oculto");
  vistaDashboard.classList.remove("oculto");

  tituloBienvenida.textContent =
    `Hola, ${usuarioActual.nombre_completo || usuarioActual.usuario || "Administrador"}`;
  chipUsuario.textContent = esAdmin() ? "Rol: Administrador" : "Rol: Docente";

  aplicarPermisosDeRol();

  if (usuarioActual.debe_cambiar_password) {
    modalCambioPassword.classList.remove("oculto");
    campoClaveActual.focus();
    return;
  }
  modalCambioPassword.classList.add("oculto");

  if (esAdmin()) {
    construirTarjetasVacias(TARJETAS_KPI);
    mostrarModulo("estudiantes");
    cargarDashboard();
    cargarCarreras();
    cargarEstudiantes();
  } else {
    construirTarjetasVacias(TARJETAS_KPI_DOCENTE, filaTarjetasDocente);
    mostrarModulo("inicio");
    cargarResumenDocente();
    cargarPerfilDocente();
    cargarMisSecciones();
  }
}

formularioCambioPassword.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  mensajeCambioPassword.textContent = "";
  if (campoClaveNueva.value !== campoClaveNuevaConfirmacion.value) {
    mensajeCambioPassword.textContent = "Las contraseñas nuevas no coinciden.";
    campoClaveNuevaConfirmacion.focus();
    return;
  }
  if (campoClaveNueva.value.length < 8) {
    mensajeCambioPassword.textContent = "La nueva contraseña debe tener al menos 8 caracteres.";
    campoClaveNueva.focus();
    return;
  }

  botonCambiarPassword.disabled = true;
  botonCambiarPassword.textContent = "Guardando...";
  try {
    const respuesta = await fetchAuth(`${URL_BASE_API}/auth/cambiar-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        clave_actual: campoClaveActual.value,
        clave_nueva: campoClaveNueva.value,
      }),
    });
    const resultado = await respuesta.json().catch(() => null);
    if (!respuesta.ok) {
      throw new Error(resultado?.detail ?? "No se pudo actualizar la contraseña.");
    }

    usuarioActual.debe_cambiar_password = false;
    usuarioActual.cambiar_password = false;
    guardarSesion(obtenerToken(), usuarioActual);
    formularioCambioPassword.reset();
    modalCambioPassword.classList.add("oculto");
    mostrarDashboard();
  } catch (error) {
    mensajeCambioPassword.textContent = error.message;
  } finally {
    botonCambiarPassword.disabled = false;
    botonCambiarPassword.textContent = "Guardar contraseña";
  }
});

botonAdministradores.addEventListener("click", () => mostrarModulo("administradores"));

formularioAdministrador.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  mensajeAdministrador.className = "mensaje-error";
  mensajeAdministrador.textContent = "";
  const id = campoAdministradorId.value;
  const datos = {
    usuario: campoAdministradorUsuario.value.trim(),
    nombre: campoAdministradorNombre.value.trim(),
    email: campoAdministradorEmail.value.trim(),
    activo: campoAdministradorActivo.checked,
  };
  botonGuardarAdministrador.disabled = true;
  try {
    const respuesta = await fetchAuth(
      `${URL_BASE_API}/administradores${id ? `/${id}` : ""}`,
      {
        method: id ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(datos),
      }
    );
    const resultado = await respuesta.json().catch(() => null);
    if (!respuesta.ok) {
      throw new Error(resultado?.detail ?? "No se pudo guardar la cuenta.");
    }
    limpiarFormularioAdministrador();
    mensajeAdministrador.className = "mensaje-exito";
    mensajeAdministrador.textContent = id
      ? "Administrador actualizado."
      : "Administrador creado. Deberá cambiar la contraseña en su primer ingreso.";
    await cargarAdministradores();
  } catch (error) {
    mensajeAdministrador.textContent = error.message;
  } finally {
    botonGuardarAdministrador.disabled = false;
  }
});

botonCancelarAdministrador.addEventListener("click", limpiarFormularioAdministrador);

function limpiarFormularioAdministrador() {
  formularioAdministrador.reset();
  campoAdministradorId.value = "";
  campoAdministradorActivo.checked = true;
  tituloFormularioAdministrador.textContent = "Nueva cuenta de administrador";
  botonGuardarAdministrador.textContent = "Crear administrador";
  botonCancelarAdministrador.classList.add("oculto");
}

function editarAdministrador(administrador) {
  campoAdministradorId.value = administrador.id;
  campoAdministradorUsuario.value = administrador.usuario;
  campoAdministradorNombre.value = administrador.nombre;
  campoAdministradorEmail.value = administrador.email;
  campoAdministradorActivo.checked = administrador.activo;
  tituloFormularioAdministrador.textContent = `Editar administrador — ${administrador.nombre}`;
  botonGuardarAdministrador.textContent = "Guardar cambios";
  botonCancelarAdministrador.classList.remove("oculto");
  formularioAdministrador.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function cargarAdministradores() {
  cuerpoTablaAdministradores.replaceChildren();
  textoAdministradoresEstado.textContent = "Cargando administradores...";
  textoAdministradoresEstado.classList.remove("oculto");
  try {
    const respuesta = await fetchAuth(`${URL_BASE_API}/administradores`);
    const administradores = await respuesta.json();
    if (!respuesta.ok) throw new Error(administradores?.detail ?? "No se pudo cargar.");
    if (!administradores.length) {
      textoAdministradoresEstado.textContent = "No hay cuentas de administrador.";
      return;
    }
    textoAdministradoresEstado.classList.add("oculto");
    administradores.forEach((administrador) => {
      const fila = document.createElement("tr");
      [
        administrador.usuario,
        administrador.nombre,
        administrador.email,
        administrador.activo ? "Activa" : "Inactiva",
        administrador.debe_cambiar_password ? "Pendiente" : "Completado",
      ].forEach((valor) => {
        const celda = document.createElement("td");
        celda.textContent = valor;
        fila.appendChild(celda);
      });

      const acciones = document.createElement("td");
      acciones.className = "acciones-tabla";
      const botonEditar = document.createElement("button");
      botonEditar.type = "button";
      botonEditar.className = "boton-icono";
      botonEditar.textContent = "Editar";
      botonEditar.addEventListener("click", () => editarAdministrador(administrador));
      const botonEstado = document.createElement("button");
      botonEstado.type = "button";
      botonEstado.className = "boton-secundario";
      botonEstado.textContent = administrador.activo ? "Desactivar" : "Activar";
      botonEstado.addEventListener("click", () =>
        cambiarEstadoAdministrador(administrador)
      );
      const botonEliminar = document.createElement("button");
      botonEliminar.type = "button";
      botonEliminar.className = "boton-secundario";
      botonEliminar.textContent = "Eliminar";
      botonEliminar.addEventListener("click", () =>
        eliminarAdministrador(administrador)
      );
      acciones.append(botonEditar, botonEstado, botonEliminar);
      fila.appendChild(acciones);
      cuerpoTablaAdministradores.appendChild(fila);
    });
  } catch (error) {
    textoAdministradoresEstado.textContent = `No se pudieron cargar las cuentas: ${error.message}`;
    textoAdministradoresEstado.classList.remove("oculto");
  }
}

async function guardarEstadoAdministrador(administrador, activo) {
  const respuesta = await fetchAuth(
    `${URL_BASE_API}/administradores/${administrador.id}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        usuario: administrador.usuario,
        nombre: administrador.nombre,
        email: administrador.email,
        activo,
      }),
    }
  );
  const resultado = await respuesta.json().catch(() => null);
  if (!respuesta.ok) throw new Error(resultado?.detail ?? "No se pudo actualizar.");
  await cargarAdministradores();
}

async function cambiarEstadoAdministrador(administrador) {
  try {
    await guardarEstadoAdministrador(administrador, !administrador.activo);
  } catch (error) {
    window.alert(error.message);
  }
}

async function eliminarAdministrador(administrador) {
  if (!window.confirm(`¿Eliminar la cuenta de ${administrador.nombre}?`)) return;
  try {
    const respuesta = await fetchAuth(
      `${URL_BASE_API}/administradores/${administrador.id}`,
      { method: "DELETE" }
    );
    const resultado = await respuesta.json().catch(() => null);
    if (!respuesta.ok) throw new Error(resultado?.detail ?? "No se pudo eliminar.");
    await cargarAdministradores();
  } catch (error) {
    window.alert(error.message);
}
}

function construirTarjetasVacias(tarjetas, contenedor = filaTarjetas) {
  contenedor.innerHTML = "";
  tarjetas.forEach(({ clave, etiqueta }) => {
    const tarjeta = document.createElement("article");
    tarjeta.className = "tarjeta-kpi";
    tarjeta.innerHTML = `
      <div class="valor" data-kpi="${clave}">—</div>
      <div class="etiqueta-kpi">${etiqueta}</div>
    `;
    contenedor.appendChild(tarjeta);
  });
}

async function cargarDashboard() {
  try {
    const respuesta = await fetchAuth(`${URL_BASE_API}/reportes/dashboard`);
    if (!respuesta.ok) throw new Error("dashboard no disponible");
    const resumen = await respuesta.json();

    TARJETAS_KPI.forEach(({ clave }) => {
      const nodo = filaTarjetas.querySelector(`[data-kpi="${clave}"]`);
      if (nodo) nodo.textContent = resumen[clave] ?? "—";
    });

    textoPeriodo.textContent = resumen.periodo_activo
      ? `Período académico activo: ${resumen.periodo_activo}`
      : "No hay un período académico activo.";
  } catch (error) {
    textoPeriodo.textContent = "No se pudieron cargar los indicadores.";
  }
}

// ------------------------- Carreras (para el <select>) -------------------------

async function cargarCarreras() {
  try {
    const respuesta = await fetchAuth(`${URL_BASE_API}/carreras?solo_activas=true`);
    if (!respuesta.ok) throw new Error("carreras no disponible");
    const carreras = await respuesta.json();

    campoCarrera.innerHTML = '<option value="">Seleccione una carrera</option>';
    carreras.forEach((carrera) => {
      const opcion = document.createElement("option");
      opcion.value = carrera.id;
      opcion.textContent = `${carrera.codigo} — ${carrera.nombre}`;
      campoCarrera.appendChild(opcion);
    });
  } catch (error) {
    campoCarrera.innerHTML = '<option value="">No se pudieron cargar las carreras</option>';
  }
}

// ------------------------- Crear / editar estudiante -------------------------

formularioEstudiante.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  mensajeFormulario.textContent = "";
  mensajeFormulario.className = "mensaje-error";

  const datos = {
    nombres: campoNombres.value.trim(),
    apellidos: campoApellidos.value.trim(),
    cuenta: campoCuenta.value.trim(),
    correo: campoCorreo.value.trim(),
    telefono: campoTelefono.value.trim() || null,
    fecha_nacimiento: campoNacimiento.value,
    carrera_id: Number(campoCarrera.value),
    estado: campoEstado.value,
  };

  const idEnEdicion = campoEstudianteId.value;
  const esEdicion = Boolean(idEnEdicion);

  botonGuardarEstudiante.disabled = true;
  botonGuardarEstudiante.textContent = "Guardando...";

  try {
    const respuesta = await fetchAuth(
      `${URL_BASE_API}/estudiantes${esEdicion ? `/${idEnEdicion}` : ""}`,
      {
        method: esEdicion ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(datos),
      }
    );

    if (!respuesta.ok) {
      const detalle = await respuesta.json().catch(() => null);
      mensajeFormulario.textContent =
        detalle?.detail ?? "No se pudo guardar el estudiante. Revise los datos.";
      return;
    }

    mensajeFormulario.textContent = esEdicion
      ? "Estudiante actualizado correctamente."
      : "Estudiante creado correctamente.";
    mensajeFormulario.className = "mensaje-exito";

    cancelarEdicion();
    cargarDashboard();
    cargarEstudiantes(campoBuscar.value.trim());
  } catch (error) {
    mensajeFormulario.textContent = "No se pudo conectar con la API.";
  } finally {
    botonGuardarEstudiante.disabled = false;
    botonGuardarEstudiante.textContent = "Guardar estudiante";
  }
});

function editarEstudiante(estudiante) {
  campoEstudianteId.value = estudiante.id;
  campoNombres.value = estudiante.nombres;
  campoApellidos.value = estudiante.apellidos;
  campoCuenta.value = estudiante.cuenta;
  campoCorreo.value = estudiante.correo;
  campoTelefono.value = estudiante.telefono ?? "";
  campoNacimiento.value = estudiante.fecha_nacimiento;
  campoCarrera.value = estudiante.carrera_id;
  campoEstado.value = estudiante.estado;

  tituloFormulario.textContent = `Editar estudiante — ${estudiante.nombres} ${estudiante.apellidos}`;
  botonGuardarEstudiante.textContent = "Guardar cambios";
  botonCancelarEdicion.classList.remove("oculto");
  mensajeFormulario.textContent = "";
  formularioEstudiante.scrollIntoView({ behavior: "smooth", block: "start" });
}

function cancelarEdicion() {
  formularioEstudiante.reset();
  campoEstudianteId.value = "";
  tituloFormulario.textContent = "Nuevo estudiante";
  botonGuardarEstudiante.textContent = "Guardar estudiante";
  botonCancelarEdicion.classList.add("oculto");
}

botonCancelarEdicion.addEventListener("click", cancelarEdicion);

async function eliminarEstudiante(estudiante) {
  const confirmado = window.confirm(
    `¿Eliminar a ${estudiante.nombres} ${estudiante.apellidos}? Esta acción no se puede deshacer.`
  );
  if (!confirmado) return;

  try {
    const respuesta = await fetchAuth(`${URL_BASE_API}/estudiantes/${estudiante.id}`, {
      method: "DELETE",
    });
    if (!respuesta.ok) {
      const detalle = await respuesta.json().catch(() => null);
      window.alert(
        detalle?.detail ?? "No se pudo eliminar (puede tener historial de matrículas)."
      );
      return;
    }
    cargarDashboard();
    cargarEstudiantes(campoBuscar.value.trim());
  } catch (error) {
    window.alert("No se pudo conectar con la API.");
  }
}

// ------------------------- Listado de estudiantes -------------------------

async function cargarEstudiantes(buscar = "") {
  try {
    const parametros = buscar ? `?buscar=${encodeURIComponent(buscar)}` : "";
    const respuesta = await fetchAuth(`${URL_BASE_API}/estudiantes${parametros}`);
    if (!respuesta.ok) throw new Error("estudiantes no disponible");
    const estudiantes = await respuesta.json();
    renderizarTablaEstudiantes(estudiantes);
  } catch (error) {
    cuerpoTablaEstudiantes.innerHTML = "";
    textoSinResultados.textContent = "No se pudo cargar la lista de estudiantes.";
    textoSinResultados.classList.remove("oculto");
  }
}

function renderizarTablaEstudiantes(estudiantes) {
  cuerpoTablaEstudiantes.innerHTML = "";

  if (estudiantes.length === 0) {
    textoSinResultados.textContent = "No se encontraron estudiantes con ese criterio.";
    textoSinResultados.classList.remove("oculto");
    return;
  }
  textoSinResultados.classList.add("oculto");

  estudiantes.forEach((estudiante) => {
    const fila = document.createElement("tr");
    fila.innerHTML = `
      <td>${estudiante.cuenta}</td>
      <td>${estudiante.nombres} ${estudiante.apellidos}</td>
      <td>${estudiante.correo}</td>
      <td>${estudiante.carrera_nombre}</td>
      <td>${pastillaEstado(estudiante.estado)}</td>
      <td>
        <div class="acciones-fila">
          <button type="button" class="boton-icono" data-accion="editar">Editar</button>
          <button type="button" class="boton-icono peligro" data-accion="eliminar">Eliminar</button>
        </div>
      </td>
    `;
    fila.querySelector('[data-accion="editar"]').addEventListener("click", () =>
      editarEstudiante(estudiante)
    );
    fila.querySelector('[data-accion="eliminar"]').addEventListener("click", () =>
      eliminarEstudiante(estudiante)
    );
    cuerpoTablaEstudiantes.appendChild(fila);
  });
}

function pastillaEstado(estado) {
  if (estado === "ACTIVO") {
    return `<span class="pastilla-estado pastilla-activo">Activo</span>`;
  }
  const etiquetas = { INACTIVO: "Inactivo", GRADUADO: "Graduado" };
  return `<span class="pastilla-estado pastilla-neutral">${etiquetas[estado] ?? estado}</span>`;
}

botonActualizar.addEventListener("click", () => {
  if (!esAdmin()) {
    cargarResumenDocente();
    cargarMisSecciones();
    if (moduloActivo === "calificaciones-docente") cargarSeccionesSelectorDocente();
    if (moduloActivo === "estudiantes-docente") cargarSelectorEstudiantesDocente();
    if (moduloActivo === "detalle-clase-docente" && seccionDocenteSeleccionada) {
      cargarEstudiantesSeccion(seccionDocenteSeleccionada.id);
      if (pestanaClaseActiva === "asistencia") cargarAsistenciaSeccion();
    }
    return;
  }
  cargarDashboard();
  if (moduloActivo === "docentes") {
    cargarDocentes();
  } else if (moduloActivo === "asignaturas") {
    cargarAsignaturas();
  } else if (["carreras", "periodos", "aulas"].includes(moduloActivo)) {
    window.cargarCatalogoAdmin?.(moduloActivo);
  } else if (moduloActivo === "administradores") {
    cargarAdministradores();
  } else {
    cargarEstudiantes(campoBuscar.value.trim());
  }
});

campoBuscar.addEventListener("input", () => {
  clearTimeout(temporizadorBusqueda);
  temporizadorBusqueda = setTimeout(() => {
    cargarEstudiantes(campoBuscar.value.trim());
  }, 300);
});

// ============================================================
// MÓDULO DE DOCENTES
// Consulta:  GET  /api/v1/docentes
// Registro:  POST /api/v1/docentes
// ============================================================

const URL_DOCENTES = `${URL_BASE_API}/docentes`;

const MENSAJE_SIN_CONEXION =
  "No hay conexión con el servidor. Verifique que la API esté encendida " +
  "(uvicorn main:app --reload) y vuelva a intentarlo.";

// 502/503/504: lo que devuelve un proxy cuando la API detrás de él no responde.
const SERVIDOR_NO_DISPONIBLE = [502, 503, 504];

const moduloEstudiantes = document.getElementById("modulo-estudiantes");
const moduloDocentes = document.getElementById("modulo-docentes");
const moduloAsignaturas = document.getElementById("modulo-asignaturas");
const botonesMenu = document.querySelectorAll(".boton-menu");

const formularioDocente = document.getElementById("formulario-docente");
const campoDocenteId = document.getElementById("docente-id");
const campoDocNumero = document.getElementById("docente-numero");
const campoDocNombres = document.getElementById("docente-nombres");
const campoDocApellidos = document.getElementById("docente-apellidos");
const campoDocCorreo = document.getElementById("docente-correo");
const campoDocClave = document.getElementById("docente-clave");
const etiquetaClaveDocente = document.getElementById("etiqueta-clave-docente");
const campoDocEspecialidad = document.getElementById("docente-especialidad");
const campoDocEstado = document.getElementById("docente-estado");
const botonGuardarDocente = document.getElementById("boton-guardar-docente");
const botonLimpiarDocente = document.getElementById("boton-limpiar-docente");
const botonCancelarEdicionDocente = document.getElementById("boton-cancelar-edicion-docente");
const tituloFormularioDocente = document.getElementById("titulo-formulario-docente");
const alertaDocente = document.getElementById("alerta-docente");

const campoDocBuscar = document.getElementById("docente-buscar");
const botonRecargarDocentes = document.getElementById("boton-recargar-docentes");
const cuerpoTablaDocentes = document.getElementById("cuerpo-tabla-docentes");
const textoDocentesEstado = document.getElementById("texto-docentes-estado");
const contadorDocentes = document.getElementById("contador-docentes");

let moduloActivo = "estudiantes";
let temporizadorBusquedaDocentes = null;
let ultimaConsultaDocentes = 0;

// Reglas iguales a las de la API (schemas.py -> DocenteEntrada).
const REGLAS_DOCENTE = [
  { clave: "numero_empleado", etiqueta: "Número de empleado", nodo: campoDocNumero, min: 3, max: 20 },
  { clave: "nombres", etiqueta: "Nombres", nodo: campoDocNombres, min: 2, max: 80 },
  { clave: "apellidos", etiqueta: "Apellidos", nodo: campoDocApellidos, min: 2, max: 80 },
  { clave: "correo", etiqueta: "Correo electrónico", nodo: campoDocCorreo, min: 5, max: 120 },
  { clave: "especialidad", etiqueta: "Especialidad", nodo: campoDocEspecialidad, min: 3, max: 120 },
];

const ETIQUETAS_CAMPO = Object.fromEntries(
  REGLAS_DOCENTE.map((regla) => [regla.clave, regla.etiqueta])
);
ETIQUETAS_CAMPO.estado = "Estado";
ETIQUETAS_CAMPO.clave = "Contraseña";

const PATRON_CORREO = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

// ------------------------- Menú -------------------------

function mostrarModulo(nombre) {
  // Seguridad en la interfaz: nunca se muestra un módulo de otro rol.
  const permitidos = MODULOS_POR_ROL[usuarioActual?.rol] ?? [];
  if (!permitidos.includes(nombre)) nombre = permitidos[0];
  if (!nombre) return;

  moduloActivo = nombre;
  document.querySelectorAll(".modulo").forEach((modulo) =>
    modulo.classList.toggle("oculto", modulo.id !== `modulo-${nombre}`)
  );

  botonesMenu.forEach((boton) => {
    const moduloMenu = nombre === "detalle-clase-docente" ? "mis-secciones" : nombre;
    const activo = boton.dataset.modulo === moduloMenu;
    boton.classList.toggle("activo", activo);
    if (activo) {
      boton.setAttribute("aria-current", "page");
    } else {
      boton.removeAttribute("aria-current");
    }
  });

  if (nombre === "docentes") {
    cargarDocentes();
  }
  if (nombre === "asignaturas") {
    cargarCarrerasAsignatura().then(cargarAsignaturas);
  }
  if (["carreras", "periodos", "aulas"].includes(nombre)) {
    window.cargarCatalogoAdmin?.(nombre);
  }
  if (nombre === "administradores") {
    cargarAdministradores();
  }
  if (nombre === "mis-secciones") {
    cargarMisSecciones();
  }
  if (nombre === "calificaciones-docente") {
    cargarSeccionesSelectorDocente();
  }
  if (nombre === "estudiantes-docente") {
    cargarSelectorEstudiantesDocente();
  }
}

botonesMenu.forEach((boton) => {
  boton.addEventListener("click", () => mostrarModulo(boton.dataset.modulo));
});
document.querySelectorAll("[data-abrir-modulo]").forEach((boton) => {
  boton.addEventListener("click", () => mostrarModulo(boton.dataset.abrirModulo));
});

// ------------------------- Alertas -------------------------

function mostrarAlertaDocente(tipo, titulo, detalles = []) {
  alertaDocente.className = `alerta alerta-${tipo}`;
  alertaDocente.replaceChildren();

  const encabezado = document.createElement("strong");
  encabezado.textContent = titulo;
  alertaDocente.appendChild(encabezado);

  if (detalles.length > 0) {
    const lista = document.createElement("ul");
    detalles.forEach((texto) => {
      const item = document.createElement("li");
      item.textContent = texto;
      lista.appendChild(item);
    });
    alertaDocente.appendChild(lista);
  }
}

function ocultarAlertaDocente() {
  alertaDocente.className = "alerta oculto";
  alertaDocente.replaceChildren();
}

function limpiarMarcasDocente() {
  REGLAS_DOCENTE.forEach(({ nodo }) => {
    nodo.classList.remove("campo-invalido");
    nodo.removeAttribute("aria-invalid");
  });
}

function marcarCampoInvalido(nodo) {
  nodo.classList.add("campo-invalido");
  nodo.setAttribute("aria-invalid", "true");
}

REGLAS_DOCENTE.forEach(({ nodo }) => {
  nodo.addEventListener("input", () => {
    nodo.classList.remove("campo-invalido");
    nodo.removeAttribute("aria-invalid");
  });
});

// ------------------------- Validación en el navegador -------------------------

function validarDocente(datos) {
  limpiarMarcasDocente();

  const vacios = REGLAS_DOCENTE.filter(({ clave }) => datos[clave] === "");
  if (vacios.length > 0) {
    vacios.forEach(({ nodo }) => marcarCampoInvalido(nodo));
    return {
      titulo: "Faltan datos obligatorios",
      detalles: vacios.map(({ etiqueta }) => `${etiqueta} no puede estar vacío.`),
      primerNodo: vacios[0].nodo,
    };
  }

  const problemas = [];
  REGLAS_DOCENTE.forEach(({ clave, etiqueta, nodo, min, max }) => {
    const valor = datos[clave];
    if (clave === "correo") {
      if (!PATRON_CORREO.test(valor)) {
        problemas.push({ nodo, texto: "El correo electrónico no es válido. Ejemplo: nombre@dominio.com" });
      } else if (valor.length > max) {
        problemas.push({ nodo, texto: `${etiqueta} no puede superar ${max} caracteres.` });
      }
      return;
    }
    if (valor.length < min) {
      problemas.push({ nodo, texto: `${etiqueta} debe tener al menos ${min} caracteres.` });
    } else if (valor.length > max) {
      problemas.push({ nodo, texto: `${etiqueta} no puede superar ${max} caracteres.` });
    }
  });

  if (datos.estado !== "ACTIVO" && datos.estado !== "INACTIVO") {
    problemas.push({ nodo: campoDocEstado, texto: "El estado debe ser ACTIVO o INACTIVO." });
  }

  if (problemas.length > 0) {
    problemas.forEach(({ nodo }) => {
      if (nodo !== campoDocEstado) marcarCampoInvalido(nodo);
    });
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
    case "literal_error":
      return `${etiqueta} tiene un valor no permitido.`;
    case "int_parsing":
    case "int_from_float":
    case "int_type":
      return `${etiqueta} debe ser un número entero.`;
    case "greater_than_equal":
      return `${etiqueta} debe ser mayor o igual a ${ctx.ge}.`;
    case "less_than_equal":
      return `${etiqueta} debe ser menor o igual a ${ctx.le}.`;
    case "greater_than":
      return `${etiqueta} no es válido: seleccione una opción de la lista.`;
    default:
      if (campo === "correo") {
        return "El correo electrónico no es válido. Ejemplo: nombre@dominio.com";
      }
      return `${etiqueta}: ${error.msg ?? "valor no válido"}.`;
  }
}

async function interpretarRespuestaError(respuesta) {
  const cuerpo = await respuesta.json().catch(() => null);
  const detalle = cuerpo?.detail;

  if (respuesta.status === 422 && Array.isArray(detalle)) {
    const textos = detalle.map(traducirErrorValidacion);
    detalle.forEach((error) => {
      const clave = error.loc?.[error.loc.length - 1];
      const regla = REGLAS_DOCENTE.find((r) => r.clave === clave);
      if (regla) marcarCampoInvalido(regla.nodo);
    });
    return { titulo: "La API rechazó el registro", detalles: textos };
  }

  if (respuesta.status === 409) {
    const texto = typeof detalle === "string" ? detalle : "El número de empleado o el correo ya existe.";
    if (/correo/i.test(texto)) marcarCampoInvalido(campoDocCorreo);
    if (/empleado/i.test(texto)) marcarCampoInvalido(campoDocNumero);
    return {
      titulo: "El docente ya existe",
      detalles: [`${texto}. Use un número de empleado y un correo distintos.`],
    };
  }

  if (SERVIDOR_NO_DISPONIBLE.includes(respuesta.status)) {
    return { titulo: "Sin conexión con el servidor", detalles: [MENSAJE_SIN_CONEXION] };
  }

  if (respuesta.status >= 500) {
    return {
      titulo: "Error en el servidor",
      detalles: ["La API tuvo un problema al procesar la solicitud. Intente de nuevo en unos momentos."],
    };
  }

  return {
    titulo: "La API rechazó el registro",
    detalles: [typeof detalle === "string" ? detalle : `No se pudo registrar el docente (código ${respuesta.status}).`],
  };
}

// ------------------------- Registro (POST) -------------------------

formularioDocente.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  ocultarAlertaDocente();

  const datos = {
    numero_empleado: campoDocNumero.value.trim(),
    nombres: campoDocNombres.value.trim(),
    apellidos: campoDocApellidos.value.trim(),
    correo: campoDocCorreo.value.trim(),
    clave: campoDocClave.value || null,
    especialidad: campoDocEspecialidad.value.trim(),
    estado: campoDocEstado.value,
  };

  const idEnEdicion = campoDocenteId.value;
  const esEdicion = Boolean(idEnEdicion);
  const errorLocal = validarDocente(datos);
  if (errorLocal) {
    mostrarAlertaDocente("error", errorLocal.titulo, errorLocal.detalles);
    errorLocal.primerNodo.focus();
    return;
  }

  if (datos.clave && datos.clave.length < 8) {
    mostrarAlertaDocente(
      "error",
      "Contraseña no válida",
      ["La contraseña inicial debe tener al menos 8 caracteres."]
    );
    campoDocClave.focus();
    return;
  }

  botonGuardarDocente.disabled = true;
  botonGuardarDocente.textContent = "Guardando...";

  try {
    const respuesta = await fetchAuth(
      `${URL_DOCENTES}${esEdicion ? `/${idEnEdicion}` : ""}`,
      {
        method: esEdicion ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(datos),
      }
    );

    if (!respuesta.ok) {
      const error = await interpretarRespuestaError(respuesta);
      mostrarAlertaDocente("error", error.titulo, error.detalles);
      return;
    }

    const guardado = await respuesta.json();
    mostrarAlertaDocente(
      "exito",
      esEdicion ? "¡Docente actualizado correctamente!" : "¡Docente registrado correctamente!",
      [
        `${guardado.nombres} ${guardado.apellidos} (${guardado.numero_empleado}) ya aparece en la lista.`,
        esEdicion
          ? "La contraseña se actualizó solo si escribió una nueva."
          : `La cuenta puede iniciar sesión con su correo y ${datos.clave ? "la contraseña indicada" : "password.docente"}; deberá cambiarla al ingresar.`,
      ]
    );
    cancelarEdicionDocente();
    campoDocBuscar.value = "";
    cargarDocentes();
    cargarDashboard();
  } catch (error) {
    mostrarAlertaDocente("error", "Sin conexión con el servidor", [MENSAJE_SIN_CONEXION]);
  } finally {
    botonGuardarDocente.disabled = false;
    // Se vuelve a leer campoDocenteId (y no la variable "esEdicion" capturada
    // antes del fetch) porque, si la operación tuvo éxito, cancelarEdicionDocente()
    // ya limpió el formulario y el botón debe quedar en modo "crear".
    botonGuardarDocente.textContent = campoDocenteId.value ? "Guardar cambios" : "Registrar docente";
  }
});

function limpiarFormularioDocente(ocultarAlerta = true) {
  formularioDocente.reset();
  campoDocenteId.value = "";
  campoDocClave.required = false;
  campoDocClave.placeholder = "Vacío: password.docente";
  etiquetaClaveDocente.textContent = "(opcional; contraseña inicial estándar)";
  limpiarMarcasDocente();
  tituloFormularioDocente.textContent = "Registrar docente";
  botonGuardarDocente.textContent = "Registrar docente";
  botonCancelarEdicionDocente.classList.add("oculto");
  if (ocultarAlerta) ocultarAlertaDocente();
}

botonLimpiarDocente.addEventListener("click", () => limpiarFormularioDocente());

function editarDocente(docente) {
  campoDocenteId.value = docente.id;
  campoDocNumero.value = docente.numero_empleado;
  campoDocNombres.value = docente.nombres;
  campoDocApellidos.value = docente.apellidos;
  campoDocCorreo.value = docente.correo;
  campoDocClave.value = "";
  campoDocClave.required = false;
  campoDocClave.placeholder = "Dejar en blanco para conservarla";
  etiquetaClaveDocente.textContent = "(opcional; déjela en blanco para conservarla)";
  campoDocEspecialidad.value = docente.especialidad;
  campoDocEstado.value = docente.estado;

  tituloFormularioDocente.textContent = `Editar docente — ${docente.nombres} ${docente.apellidos}`;
  botonGuardarDocente.textContent = "Guardar cambios";
  botonCancelarEdicionDocente.classList.remove("oculto");
  ocultarAlertaDocente();
  formularioDocente.scrollIntoView({ behavior: "smooth", block: "start" });
}

function cancelarEdicionDocente() {
  limpiarFormularioDocente(false);
}

botonCancelarEdicionDocente.addEventListener("click", cancelarEdicionDocente);

async function eliminarDocente(docente) {
  const confirmado = window.confirm(
    `¿Eliminar al docente ${docente.nombres} ${docente.apellidos}? Esta acción no se puede deshacer.`
  );
  if (!confirmado) return;

  try {
    const respuesta = await fetchAuth(`${URL_DOCENTES}/${docente.id}`, {
      method: "DELETE",
    });
    if (!respuesta.ok) {
      const detalle = await respuesta.json().catch(() => null);
      window.alert(
        detalle?.detail ?? "No se pudo eliminar (puede tener secciones asignadas)."
      );
      return;
    }
    cargarDocentes();
    cargarDashboard();
  } catch (error) {
    window.alert("No se pudo conectar con la API.");
  }
}

// ------------------------- Consulta (GET) -------------------------

function mostrarEstadoDocentes(texto) {
  textoDocentesEstado.textContent = texto;
  textoDocentesEstado.classList.toggle("oculto", !texto);
}

async function cargarDocentes() {
  const numeroConsulta = ++ultimaConsultaDocentes;
  const buscar = campoDocBuscar.value.trim();
  const parametros = buscar ? `?buscar=${encodeURIComponent(buscar)}` : "";

  cuerpoTablaDocentes.replaceChildren();
  contadorDocentes.textContent = "";
  mostrarEstadoDocentes("Cargando docentes...");

  try {
    const respuesta = await fetchAuth(`${URL_DOCENTES}${parametros}`);
    if (!respuesta.ok) {
      const error = new Error(`HTTP ${respuesta.status}`);
      error.sinConexion = SERVIDOR_NO_DISPONIBLE.includes(respuesta.status);
      throw error;
    }
    const docentes = await respuesta.json();
    if (numeroConsulta !== ultimaConsultaDocentes) return;
    renderizarTablaDocentes(docentes, buscar);
  } catch (error) {
    if (numeroConsulta !== ultimaConsultaDocentes) return;
    cuerpoTablaDocentes.replaceChildren();
    contadorDocentes.textContent = "";
    mostrarEstadoDocentes(
      error instanceof TypeError || error.sinConexion
        ? MENSAJE_SIN_CONEXION
        : "No se pudo cargar la lista de docentes. Intente recargar."
    );
  }
}

function renderizarTablaDocentes(docentes, buscar) {
  cuerpoTablaDocentes.replaceChildren();

  contadorDocentes.textContent = buscar
    ? `${docentes.length} resultado(s) para “${buscar}”`
    : `${docentes.length} docente(s) registrado(s)`;

  if (docentes.length === 0) {
    mostrarEstadoDocentes(
      buscar
        ? "No se encontraron docentes con ese criterio."
        : "Aún no hay docentes registrados. Use el formulario para agregar el primero."
    );
    return;
  }
  mostrarEstadoDocentes("");

  docentes.forEach((docente) => {
    const fila = document.createElement("tr");

    const valores = [
      docente.numero_empleado,
      `${docente.nombres} ${docente.apellidos}`,
      docente.correo,
      docente.especialidad,
    ];
    valores.forEach((valor) => {
      const celda = document.createElement("td");
      celda.textContent = valor;
      fila.appendChild(celda);
    });

    const celdaEstado = document.createElement("td");
    celdaEstado.innerHTML = pastillaEstado(docente.estado);
    fila.appendChild(celdaEstado);

    const celdaAcciones = document.createElement("td");
    celdaAcciones.innerHTML = `
      <div class="acciones-fila">
        <button type="button" class="boton-icono" data-accion="editar">Editar</button>
        <button type="button" class="boton-icono peligro" data-accion="eliminar">Eliminar</button>
      </div>
    `;
    celdaAcciones.querySelector('[data-accion="editar"]').addEventListener("click", () =>
      editarDocente(docente)
    );
    celdaAcciones.querySelector('[data-accion="eliminar"]').addEventListener("click", () =>
      eliminarDocente(docente)
    );
    fila.appendChild(celdaAcciones);

    cuerpoTablaDocentes.appendChild(fila);
  });
}

botonRecargarDocentes.addEventListener("click", cargarDocentes);

campoDocBuscar.addEventListener("input", () => {
  clearTimeout(temporizadorBusquedaDocentes);
  temporizadorBusquedaDocentes = setTimeout(cargarDocentes, 300);
});

// ============================================================
// LÓGICA DE ASIGNATURAS (Añadido)
// ============================================================
const URL_ASIGNATURAS = `${URL_BASE_API}/asignaturas`;

const formularioAsignatura = document.getElementById("formulario-asignatura");
const campoAsignaturaId = document.getElementById("asignatura-id");
const campoAsigCodigo = document.getElementById("asignatura-codigo");
const campoAsigNombre = document.getElementById("asignatura-nombre");
const campoAsigUnidades = document.getElementById("asignatura-unidades");
const selectorCarrerasAsignatura = document.getElementById("selector-carreras-asignatura");
const botonCarrerasAsignatura = document.getElementById("asignatura-carreras-boton");
const resumenCarrerasAsignatura = document.getElementById("asignatura-carreras-resumen");
const opcionesCarrerasAsignatura = document.getElementById("asignatura-carreras-opciones");
const campoAsigRequisito = document.getElementById("asignatura-requisito");
const campoAsigEstado = document.getElementById("asignatura-estado");
const botonGuardarAsignatura = document.getElementById("boton-guardar-asignatura");
const botonLimpiarAsignatura = document.getElementById("boton-limpiar-asignatura"); // Agregado para que no falle si lo usas
const botonCancelarEdicionAsignatura = document.getElementById("boton-cancelar-edicion-asignatura");
const tituloFormularioAsignatura = document.getElementById("titulo-formulario-asignatura");
const alertaAsignatura = document.getElementById("alerta-asignatura"); // Agregado por seguridad

const campoAsigBuscar = document.getElementById("asignatura-buscar");
const botonRecargarAsignaturas = document.getElementById("boton-recargar-asignaturas");
const cuerpoTablaAsignaturas = document.getElementById("cuerpo-tabla-asignaturas");
const textoAsignaturasEstado = document.getElementById("texto-asignaturas-estado");
const contadorAsignaturas = document.getElementById("contador-asignaturas");

let temporizadorBusquedaAsignaturas = null;
let ultimaConsultaAsignaturas = 0;
let carrerasAsignatura = [];
const carrerasSeleccionadas = new Set();

function obtenerCarreraIdsSeleccionadas() {
  return [...carrerasSeleccionadas];
}

function cerrarSelectorCarreras() {
  opcionesCarrerasAsignatura.classList.add("oculto");
  botonCarrerasAsignatura.setAttribute("aria-expanded", "false");
}

function actualizarResumenCarreras() {
  const seleccionadas = carrerasAsignatura.filter((carrera) =>
    carrerasSeleccionadas.has(Number(carrera.id))
  );
  resumenCarrerasAsignatura.textContent = seleccionadas.length
    ? `${seleccionadas.length} ${seleccionadas.length === 1 ? "carrera seleccionada" : "carreras seleccionadas"}`
    : "Seleccione una o varias carreras";
  botonCarrerasAsignatura.setAttribute("aria-invalid", "false");
}

function renderizarOpcionesCarreras() {
  opcionesCarrerasAsignatura.replaceChildren();
  carrerasAsignatura.forEach((carrera) => {
    const etiqueta = document.createElement("label");
    etiqueta.className = "opcion-carrera";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.value = carrera.id;
    checkbox.checked = carrerasSeleccionadas.has(Number(carrera.id));

    const texto = document.createElement("span");
    texto.textContent = `${carrera.codigo} — ${carrera.nombre}`;

    etiqueta.append(checkbox, texto);
    opcionesCarrerasAsignatura.appendChild(etiqueta);
  });
  actualizarResumenCarreras();
}

async function cargarCarrerasAsignatura() {
  try {
    const respuesta = await fetchAuth(`${URL_BASE_API}/carreras?solo_activas=true`);
    if (!respuesta.ok) throw new Error(`HTTP ${respuesta.status}`);
    carrerasAsignatura = await respuesta.json();
    renderizarOpcionesCarreras();
  } catch (error) {
    carrerasAsignatura = [];
    opcionesCarrerasAsignatura.replaceChildren();
    resumenCarrerasAsignatura.textContent = "No se pudieron cargar las carreras";
    textoAsignaturasEstado.textContent = "No se pudieron cargar las carreras; recargue el módulo.";
    textoAsignaturasEstado.classList.remove("oculto");
  }
}

async function cargarRequisitosAsignatura(asignaturaId = null) {
  const carreraIds = obtenerCarreraIdsSeleccionadas().map(String);
  campoAsigRequisito.innerHTML = '<option value="">Sin requisito</option>';
  if (!carreraIds.length) return;

  const respuestas = await Promise.all(
    carreraIds.map(async (carreraId) => {
      const respuesta = await fetchAuth(
        `${URL_ASIGNATURAS}?carrera_id=${encodeURIComponent(carreraId)}`
      );
      if (!respuesta.ok) {
        throw new Error(`No se pudieron cargar los requisitos (${respuesta.status})`);
      }
      return respuesta.json();
    })
  );
  const requisitos = new Map();
  respuestas.flat().forEach((asignatura) => {
    if (
      String(asignatura.id) !== String(asignaturaId) &&
      carreraIds.some((id) => (asignatura.carrera_ids ?? [asignatura.carrera_id]).includes(Number(id)))
    ) {
      requisitos.set(asignatura.id, asignatura);
    }
  });
  requisitos.forEach((asignatura) => {
    const opcion = document.createElement("option");
    opcion.value = asignatura.id;
    opcion.textContent = `${asignatura.codigo} — ${asignatura.nombre}`;
    campoAsigRequisito.appendChild(opcion);
  });
}

async function cargarAsignaturas() {
  const numeroConsulta = ++ultimaConsultaAsignaturas;
  const buscar = campoAsigBuscar.value.trim();
  const parametros = buscar ? `?buscar=${encodeURIComponent(buscar)}` : "";
  cuerpoTablaAsignaturas.replaceChildren();
  contadorAsignaturas.textContent = "";
  textoAsignaturasEstado.textContent = "Cargando asignaturas...";
  textoAsignaturasEstado.classList.remove("oculto");
  
  try {
    const respuesta = await fetchAuth(`${URL_ASIGNATURAS}${parametros}`);
    if (!respuesta.ok) throw new Error(`HTTP ${respuesta.status}`);
    const asignaturas = await respuesta.json();
    if (numeroConsulta !== ultimaConsultaAsignaturas) return;
    contadorAsignaturas.textContent = `${asignaturas.length} asignatura(s)`;

    if (asignaturas.length === 0) {
      textoAsignaturasEstado.textContent = "No se encontraron asignaturas.";
      return;
    }
    
    textoAsignaturasEstado.classList.add("oculto");
    
    asignaturas.forEach((asig) => {
      const fila = document.createElement("tr");
      [
        asig.codigo,
        asig.nombre,
        asig.unidades_valorativas,
      ].forEach((valor) => {
        const celda = document.createElement("td");
        celda.textContent = valor;
        fila.appendChild(celda);
      });

      const celdaCarreras = document.createElement("td");
      const cantidadCarreras = (asig.carrera_ids ?? [asig.carrera_id]).length;
      if (cantidadCarreras > 1) {
        const insignia = document.createElement("span");
        insignia.className = "insignia-multicarrera";
        insignia.textContent = `Multicarrera (${cantidadCarreras})`;
        celdaCarreras.appendChild(insignia);
      } else {
        celdaCarreras.textContent = asig.carrera_nombre;
      }
      fila.appendChild(celdaCarreras);

      const celdaRequisito = document.createElement("td");
      celdaRequisito.textContent = asig.requisito_codigo ?? "—";
      fila.appendChild(celdaRequisito);

      const celdaEstado = document.createElement("td");
      celdaEstado.innerHTML = pastillaEstado(asig.activo ? "ACTIVO" : "INACTIVO");
      fila.appendChild(celdaEstado);

      const celdaAcciones = document.createElement("td");
      celdaAcciones.innerHTML = `
        <div class="acciones-fila">
          <button type="button" class="boton-icono" data-accion="editar">Editar</button>
          <button type="button" class="boton-icono peligro" data-accion="eliminar">Eliminar</button>
        </div>
      `;
      celdaAcciones.querySelector('[data-accion="editar"]').addEventListener("click", () =>
        editarAsignatura(asig)
      );
      celdaAcciones.querySelector('[data-accion="eliminar"]').addEventListener("click", () =>
        eliminarAsignatura(asig)
      );
      fila.appendChild(celdaAcciones);
      cuerpoTablaAsignaturas.appendChild(fila);
    });
  } catch (error) {
    if (numeroConsulta !== ultimaConsultaAsignaturas) return;
    textoAsignaturasEstado.textContent = "No se pudo cargar la lista de asignaturas. Intente recargar.";
    textoAsignaturasEstado.classList.remove("oculto");
  }
}

formularioAsignatura.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  if (!carrerasSeleccionadas.size) {
    botonCarrerasAsignatura.setAttribute("aria-invalid", "true");
    botonCarrerasAsignatura.focus();
    return;
  }

  const datos = {
    codigo: campoAsigCodigo.value.trim(),
    nombre: campoAsigNombre.value.trim(),
    unidades_valorativas: parseInt(campoAsigUnidades.value),
    carrera_ids: obtenerCarreraIdsSeleccionadas(),
    requisito_id: campoAsigRequisito.value ? parseInt(campoAsigRequisito.value) : null,
    activo: campoAsigEstado.value === "ACTIVO"
  };

  const idEnEdicion = campoAsignaturaId.value;
  const esEdicion = Boolean(idEnEdicion);

  botonGuardarAsignatura.disabled = true;
  botonGuardarAsignatura.textContent = "Guardando...";

  try {
    const respuesta = await fetchAuth(
      `${URL_ASIGNATURAS}${esEdicion ? `/${idEnEdicion}` : ""}`,
      {
        method: esEdicion ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(datos),
      }
    );

    if (respuesta.ok) {
      cancelarEdicionAsignatura();
      await cargarAsignaturas();
      await cargarDashboard();
      alert(esEdicion ? "¡Asignatura actualizada correctamente!" : "¡Asignatura registrada correctamente!");
    } else {
      const detalle = await respuesta.json().catch(() => null);
      alert(detalle?.detail ?? "Error: El código de la asignatura ya existe o faltan datos.");
    }
  } catch (error) {
    alert("Error de conexión con el servidor.");
  } finally {
    botonGuardarAsignatura.disabled = false;
    botonGuardarAsignatura.textContent = campoAsignaturaId.value ? "Guardar cambios" : "Registrar asignatura";
  }
});

async function editarAsignatura(asignatura) {
  campoAsignaturaId.value = asignatura.id;
  campoAsigCodigo.value = asignatura.codigo;
  campoAsigNombre.value = asignatura.nombre;
  campoAsigUnidades.value = asignatura.unidades_valorativas;
  const idsCarrerasEdicion = new Set(
    (asignatura.carrera_ids ?? [asignatura.carrera_id]).map(String)
  );
  carrerasSeleccionadas.clear();
  idsCarrerasEdicion.forEach((id) => carrerasSeleccionadas.add(Number(id)));
  renderizarOpcionesCarreras();
  campoAsigEstado.value = asignatura.activo ? "ACTIVO" : "INACTIVO";

  tituloFormularioAsignatura.textContent = `Editar asignatura — ${asignatura.codigo}`;
  botonGuardarAsignatura.textContent = "Guardar cambios";
  botonCancelarEdicionAsignatura.classList.remove("oculto");
  try {
    await cargarRequisitosAsignatura(asignatura.id);
    campoAsigRequisito.value = asignatura.requisito_id ?? "";
  } catch (error) {
    window.alert(error.message);
    return;
  }
  formularioAsignatura.scrollIntoView({ behavior: "smooth", block: "start" });
}

function cancelarEdicionAsignatura() {
  formularioAsignatura.reset();
  campoAsignaturaId.value = "";
  carrerasSeleccionadas.clear();
  renderizarOpcionesCarreras();
  cerrarSelectorCarreras();
  campoAsigRequisito.innerHTML = '<option value="">Sin requisito</option>';
  tituloFormularioAsignatura.textContent = "Registrar asignatura";
  botonGuardarAsignatura.textContent = "Registrar asignatura";
  botonCancelarEdicionAsignatura.classList.add("oculto");
}

async function eliminarAsignatura(asignatura) {
  const confirmado = window.confirm(
    `¿Eliminar la asignatura ${asignatura.codigo} — ${asignatura.nombre}? Esta acción no se puede deshacer.`
  );
  if (!confirmado) return;

  try {
    const respuesta = await fetchAuth(`${URL_ASIGNATURAS}/${asignatura.id}`, {
      method: "DELETE",
    });
    if (!respuesta.ok) {
      const detalle = await respuesta.json().catch(() => null);
      window.alert(
        detalle?.detail ?? "No se pudo eliminar (puede tener secciones asociadas)."
      );
      return;
    }
    cargarAsignaturas();
    cargarDashboard();
  } catch (error) {
    window.alert("No se pudo conectar con la API.");
  }
}

botonRecargarAsignaturas.addEventListener("click", cargarAsignaturas);
botonLimpiarAsignatura.addEventListener("click", () => cancelarEdicionAsignatura());
botonCancelarEdicionAsignatura.addEventListener("click", cancelarEdicionAsignatura);
botonCarrerasAsignatura.addEventListener("click", () => {
  const estaAbierto = botonCarrerasAsignatura.getAttribute("aria-expanded") === "true";
  opcionesCarrerasAsignatura.classList.toggle("oculto", estaAbierto);
  botonCarrerasAsignatura.setAttribute("aria-expanded", String(!estaAbierto));
});
opcionesCarrerasAsignatura.addEventListener("change", (evento) => {
  const checkbox = evento.target.closest('input[type="checkbox"]');
  if (!checkbox) return;
  const carreraId = Number(checkbox.value);
  if (checkbox.checked) carrerasSeleccionadas.add(carreraId);
  else carrerasSeleccionadas.delete(carreraId);
  actualizarResumenCarreras();
  cargarRequisitosAsignatura().catch((error) => window.alert(error.message));
});
document.addEventListener("click", (evento) => {
  if (!selectorCarrerasAsignatura.contains(evento.target)) cerrarSelectorCarreras();
});
document.addEventListener("keydown", (evento) => {
  if (evento.key === "Escape" && botonCarrerasAsignatura.getAttribute("aria-expanded") === "true") {
    cerrarSelectorCarreras();
    botonCarrerasAsignatura.focus();
  }
});
campoAsigBuscar.addEventListener("input", () => {
  clearTimeout(temporizadorBusquedaAsignaturas);
  temporizadorBusquedaAsignaturas = setTimeout(cargarAsignaturas, 300);
});

// ============================================================
// PANEL DEL DOCENTE (solo rol DOCENTE)
// GET /api/v1/panel-docente/resumen
// GET /api/v1/panel-docente/mis-secciones
// ============================================================
const URL_PANEL_DOCENTE = `${URL_BASE_API}/panel-docente`;

const formularioPerfilDocente = document.getElementById("formulario-perfil-docente");
const nombrePerfilDocente = document.getElementById("nombre-perfil-docente");
const nombreCompletoPerfilDocente = document.getElementById("perfil-docente-nombre-completo");
const campoNombreCompletoPerfil = document.getElementById("campo-nombre-completo-perfil");
const botonEditarPerfilDocente = document.getElementById("boton-editar-perfil-docente");
const botonCancelarPerfilDocente = document.getElementById("boton-cancelar-perfil-docente");
const accionesPerfilDocente = document.getElementById("acciones-perfil-docente");
const estadoPerfilDocente = document.getElementById("estado-perfil-docente");
const fotoPerfilDocente = document.getElementById("foto-perfil-docente");
const marcadorFotoDocente = document.getElementById("marcador-foto-docente");
const archivoFotoPerfilDocente = document.getElementById("archivo-foto-perfil-docente");
const etiquetaSubirFoto = document.getElementById("etiqueta-subir-foto");
const camposPerfilDocente = {
  nombres: document.getElementById("perfil-docente-nombres"),
  apellidos: document.getElementById("perfil-docente-apellidos"),
  numero_identidad: document.getElementById("perfil-docente-identidad"),
  fecha_nacimiento: document.getElementById("perfil-docente-nacimiento"),
  nacionalidad: document.getElementById("perfil-docente-nacionalidad"),
  tipo_nacionalidad: document.getElementById("perfil-docente-tipo-nacionalidad"),
  fecha_ingreso: document.getElementById("perfil-docente-ingreso"),
};
const edadPerfilDocente = document.getElementById("perfil-docente-edad");
let perfilDocenteActual = null;
let fotoPerfilPendiente = null;

const cuerpoTablaMisSecciones = document.getElementById("cuerpo-tabla-mis-secciones");
const textoMisSeccionesEstado = document.getElementById("texto-mis-secciones-estado");
const contadorMisSecciones = document.getElementById("contador-mis-secciones");
const cuerpoTablaMisEstudiantes = document.getElementById("cuerpo-tabla-mis-estudiantes");
const textoMisEstudiantesEstado = document.getElementById("texto-mis-estudiantes-estado");
const contadorMisEstudiantes = document.getElementById("contador-mis-estudiantes");
const tituloEstudiantesSeccion = document.getElementById("titulo-estudiantes-seccion");
const selectorSeccionDocente = document.getElementById("selector-seccion-docente");
const botonAbrirNotasSeccion = document.getElementById("boton-abrir-notas-seccion");
const textoSeleccionNotas = document.getElementById("texto-seleccion-notas");
const selectorEstudiantesDocente = document.getElementById("selector-estudiantes-docente");
const detalleEstudiantesDocente = document.getElementById("detalle-estudiantes-docente");
const cuerpoEstudiantesDocente = document.getElementById("cuerpo-estudiantes-docente");
const estadoEstudiantesDocente = document.getElementById("estado-estudiantes-docente");
const tituloListadoEstudiantesDocente = document.getElementById("titulo-listado-estudiantes-docente");
const contadorListadoEstudiantesDocente = document.getElementById("contador-listado-estudiantes-docente");
const cuerpoMatriculaClase = document.getElementById("cuerpo-matricula-clase");
const estadoMatriculaClase = document.getElementById("estado-matricula-clase");
const mensajeMatriculaClase = document.getElementById("mensaje-matricula-clase");
const selectorSesionAsistencia = document.getElementById("selector-sesion-asistencia");
const formularioSesionAsistencia = document.getElementById("formulario-sesion-asistencia");
const fechaSesionAsistencia = document.getElementById("fecha-sesion-asistencia");
const cuerpoAsistenciaClase = document.getElementById("cuerpo-asistencia-clase");
const botonGuardarAsistencia = document.getElementById("boton-guardar-asistencia");
const mensajeAsistenciaClase = document.getElementById("mensaje-asistencia-clase");
let seccionDocenteSeleccionada = null;
let seccionesDocente = [];
let pestanaClaseActiva = "matricula";

function actualizarVisualFotoPerfil(foto) {
  if (foto) {
    fotoPerfilDocente.src = foto;
    fotoPerfilDocente.classList.remove("oculto");
    marcadorFotoDocente.classList.add("oculto");
  } else {
    fotoPerfilDocente.removeAttribute("src");
    fotoPerfilDocente.classList.add("oculto");
    marcadorFotoDocente.classList.remove("oculto");
  }
}

function mostrarPerfilDocente(perfil) {
  perfilDocenteActual = perfil;
  nombrePerfilDocente.textContent = perfil.nombre_completo;
  nombreCompletoPerfilDocente.value = perfil.nombre_completo;
  Object.entries(camposPerfilDocente).forEach(([clave, campo]) => {
    campo.value = perfil[clave] ?? "";
  });
  edadPerfilDocente.value = perfil.edad === null ? "No disponible" : `${perfil.edad} años`;
  actualizarVisualFotoPerfil(perfil.foto_perfil);
}

function actualizarEdadPerfilDocente() {
  const fecha = camposPerfilDocente.fecha_nacimiento.value;
  if (!fecha) {
    edadPerfilDocente.value = "No disponible";
    return;
  }
  const nacimiento = new Date(`${fecha}T00:00:00`);
  const hoy = new Date();
  let edad = hoy.getFullYear() - nacimiento.getFullYear();
  if (
    hoy.getMonth() < nacimiento.getMonth() ||
    (hoy.getMonth() === nacimiento.getMonth() && hoy.getDate() < nacimiento.getDate())
  ) {
    edad -= 1;
  }
  edadPerfilDocente.value = `${edad} años`;
}

function cambiarEdicionPerfilDocente(editar) {
  Object.values(camposPerfilDocente).forEach((campo) => {
    campo.disabled = !editar;
  });
  campoNombreCompletoPerfil.classList.toggle("oculto", editar);
  document.querySelectorAll(".campos-nombres-edicion").forEach((campo) =>
    campo.classList.toggle("oculto", !editar)
  );
  archivoFotoPerfilDocente.disabled = !editar;
  botonEditarPerfilDocente.classList.toggle("oculto", editar);
  accionesPerfilDocente.classList.toggle("oculto", !editar);
  etiquetaSubirFoto.classList.toggle("oculto", !editar);
  estadoPerfilDocente.textContent = "";
}

camposPerfilDocente.fecha_nacimiento.addEventListener(
  "input",
  actualizarEdadPerfilDocente
);

async function cargarPerfilDocente() {
  estadoPerfilDocente.textContent = "Cargando información del perfil...";
  try {
    const respuesta = await fetchAuth(`${URL_PANEL_DOCENTE}/perfil`);
    const resultado = await respuesta.json();
    if (!respuesta.ok) throw new Error(resultado?.detail ?? "No se pudo cargar el perfil.");
    mostrarPerfilDocente(resultado);
    estadoPerfilDocente.textContent = "";
  } catch (error) {
    estadoPerfilDocente.textContent = `No se pudo cargar la información personal: ${error.message}`;
  }
}

botonEditarPerfilDocente.addEventListener("click", () => {
  if (!perfilDocenteActual) return;
  cambiarEdicionPerfilDocente(true);
});

botonCancelarPerfilDocente.addEventListener("click", () => {
  if (perfilDocenteActual) mostrarPerfilDocente(perfilDocenteActual);
  fotoPerfilPendiente = null;
  archivoFotoPerfilDocente.value = "";
  cambiarEdicionPerfilDocente(false);
});

archivoFotoPerfilDocente.addEventListener("change", () => {
  const archivo = archivoFotoPerfilDocente.files?.[0];
  if (!archivo) return;
  const tiposPermitidos = ["image/jpeg", "image/png", "image/webp"];
  if (!tiposPermitidos.includes(archivo.type) || archivo.size > 2 * 1024 * 1024) {
    estadoPerfilDocente.textContent = "Seleccione una imagen JPG, PNG o WEBP de máximo 2 MB.";
    archivoFotoPerfilDocente.value = "";
    return;
  }
  const lector = new FileReader();
  lector.addEventListener("load", () => {
    if (typeof lector.result !== "string") {
      estadoPerfilDocente.textContent = "No se pudo leer el archivo de imagen.";
      return;
    }
    fotoPerfilPendiente = lector.result;
    actualizarVisualFotoPerfil(fotoPerfilPendiente);
    estadoPerfilDocente.textContent = "";
  });
  lector.addEventListener("error", () => {
    estadoPerfilDocente.textContent = "No se pudo leer el archivo de imagen.";
  });
  lector.readAsDataURL(archivo);
});

formularioPerfilDocente.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  estadoPerfilDocente.textContent = "";
  if (!formularioPerfilDocente.reportValidity()) return;

  const datos = Object.fromEntries(
    Object.entries(camposPerfilDocente).map(([clave, campo]) => [
      clave,
      campo.value.trim() || null,
    ])
  );
  datos.foto_perfil = fotoPerfilPendiente ?? perfilDocenteActual?.foto_perfil ?? null;
  const botonGuardar = document.getElementById("boton-guardar-perfil-docente");
  botonGuardar.disabled = true;
  botonGuardar.textContent = "Guardando...";
  try {
    const respuesta = await fetchAuth(`${URL_PANEL_DOCENTE}/perfil`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(datos),
    });
    const resultado = await respuesta.json();
    if (!respuesta.ok) {
      const detalle = Array.isArray(resultado?.detail)
        ? resultado.detail.map((error) => error.msg).join(" ")
        : resultado?.detail;
      throw new Error(detalle ?? "No se pudo actualizar el perfil.");
    }
    mostrarPerfilDocente(resultado);
    fotoPerfilPendiente = null;
    archivoFotoPerfilDocente.value = "";
    tituloBienvenida.textContent = `Hola, ${resultado.nombre_completo}`;
    cambiarEdicionPerfilDocente(false);
    estadoPerfilDocente.textContent = "Información personal actualizada.";
  } catch (error) {
    estadoPerfilDocente.textContent = `No se pudo guardar el perfil: ${error.message}`;
  } finally {
    botonGuardar.disabled = false;
    botonGuardar.textContent = "Guardar cambios";
  }
});

function mostrarTextoEstado(nodo, texto) {
  nodo.textContent = texto;
  nodo.classList.toggle("oculto", !texto);
}

async function cargarResumenDocente() {
  try {
    const respuesta = await fetchAuth(`${URL_PANEL_DOCENTE}/resumen`);
    const resumen = await respuesta.json();
    if (!respuesta.ok) throw new Error(resumen?.detail ?? "error");

    TARJETAS_KPI_DOCENTE.forEach(({ clave }) => {
      const nodo = filaTarjetasDocente.querySelector(`[data-kpi="${clave}"]`);
      if (nodo) nodo.textContent = resumen[clave] ?? "—";
    });
    tituloBienvenida.textContent = `Hola, ${resumen.docente_nombre}`;
    const docente = `Docente: ${resumen.docente_nombre} (${resumen.especialidad})`;
    textoPeriodoDocente.textContent = resumen.periodo_activo
      ? `${docente} · Período académico activo: ${resumen.periodo_activo}`
      : `${docente} · No hay un período académico activo.`;
  } catch (error) {
    textoPeriodoDocente.textContent = `No se pudo cargar su resumen: ${error.message}`;
  }
}

async function cargarMisSecciones() {
  mostrarTextoEstado(textoMisSeccionesEstado, "Cargando sus secciones...");
  cuerpoTablaMisSecciones.replaceChildren();
  try {
    const respuesta = await fetchAuth(`${URL_PANEL_DOCENTE}/mis-secciones`);
    const secciones = await respuesta.json();
    if (!respuesta.ok) throw new Error(secciones?.detail ?? "error");
    seccionesDocente = secciones;

    contadorMisSecciones.textContent = `${secciones.length} sección(es) asignada(s)`;
    cuerpoTablaMisSecciones.replaceChildren();
    if (secciones.length === 0) {
      seccionDocenteSeleccionada = null;
      botonAbrirNotasSeccion.disabled = true;
      mostrarTextoEstado(textoMisSeccionesEstado, "No tiene secciones asignadas.");
      return;
    }
    mostrarTextoEstado(textoMisSeccionesEstado, "");
    const seleccionAnterior = seccionDocenteSeleccionada?.id;
    seccionDocenteSeleccionada =
      secciones.find((seccion) => seccion.id === seleccionAnterior) ?? null;
    secciones.forEach((seccion) => {
      const fila = document.createElement("tr");
      fila.classList.toggle(
        "fila-seccion-seleccionada",
        seccion.id === seccionDocenteSeleccionada?.id
      );
      const codigo = document.createElement("td");
      codigo.textContent = seccion.asignatura_codigo;
      fila.appendChild(codigo);

      const asignatura = document.createElement("td");
      asignatura.textContent = seccion.asignatura_nombre;
      fila.appendChild(asignatura);

      const celdaSeccion = document.createElement("td");
      celdaSeccion.textContent = seccion.codigo;
      fila.appendChild(celdaSeccion);

      [
        `${seccion.dias} ${seccion.hora_inicio}–${seccion.hora_fin}`,
        seccion.aula_codigo
          ? `${seccion.aula_codigo}${seccion.aula_edificio ? ` · ${seccion.aula_edificio}` : ""}`
          : "—",
        `${seccion.matriculados} / ${seccion.cupo_maximo}`,
        seccion.estado,
      ].forEach((valor) => {
        const celda = document.createElement("td");
        celda.textContent = valor;
        fila.appendChild(celda);
      });

      const celdaAcciones = document.createElement("td");
      const botonVerAlumnos = document.createElement("button");
      botonVerAlumnos.type = "button";
      botonVerAlumnos.className = "boton-icono";
      botonVerAlumnos.textContent = "Entrar al detalle";
      botonVerAlumnos.addEventListener("click", () =>
        abrirDetalleClase(seccion.id, "matricula")
      );
      celdaAcciones.appendChild(botonVerAlumnos);
      fila.appendChild(celdaAcciones);
      cuerpoTablaMisSecciones.appendChild(fila);
    });
    if (seccionDocenteSeleccionada &&
        !secciones.some((seccion) => seccion.id === seccionDocenteSeleccionada.id)) {
      seccionDocenteSeleccionada = null;
    }
  } catch (error) {
    mostrarTextoEstado(textoMisSeccionesEstado, `No se pudieron cargar sus secciones: ${error.message}`);
  }
}

async function cargarSeccionesSelectorDocente(seccionInicialId = null) {
  const seleccionActual =
    seccionInicialId ?? seccionDocenteSeleccionada?.id ?? selectorSeccionDocente.value;
  selectorSeccionDocente.replaceChildren();
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "Seleccione una sección";
  selectorSeccionDocente.appendChild(placeholder);

  botonAbrirNotasSeccion.disabled = true;
  mostrarTextoEstado(textoSeleccionNotas, "Seleccione una clase para abrir su matriz de notas.");
  try {
    const respuesta = await fetchAuth(`${URL_PANEL_DOCENTE}/mis-secciones`);
    const secciones = await respuesta.json();
    if (!respuesta.ok) throw new Error(secciones?.detail ?? "No se pudieron cargar las secciones.");
    seccionesDocente = secciones;
    secciones.forEach((seccion) => {
      const opcion = document.createElement("option");
      opcion.value = String(seccion.id);
      opcion.textContent =
        `${seccion.asignatura_codigo} ${seccion.asignatura_nombre} - ${seccion.codigo}`;
      selectorSeccionDocente.appendChild(opcion);
    });

    if (secciones.length === 0) {
      seccionDocenteSeleccionada = null;
      mostrarTextoEstado(textoSeleccionNotas, "No tiene secciones en el período activo.");
      return;
    }
    if (secciones.some((seccion) => String(seccion.id) === String(seleccionActual))) {
      selectorSeccionDocente.value = String(seleccionActual);
      seccionDocenteSeleccionada = secciones.find(
        (seccion) => String(seccion.id) === String(seleccionActual)
      );
      botonAbrirNotasSeccion.disabled = false;
      mostrarTextoEstado(
        textoSeleccionNotas,
        `Clase seleccionada: ${seccionDocenteSeleccionada.asignatura_codigo} — ${seccionDocenteSeleccionada.asignatura_nombre} · Sección ${seccionDocenteSeleccionada.codigo}.`
      );
    } else {
      seccionDocenteSeleccionada = null;
    }
  } catch (error) {
    mostrarTextoEstado(
      textoSeleccionNotas,
      `No se pudieron cargar las secciones: ${error.message}`
    );
  }
}

async function abrirDetalleClase(seccionId, pestana = "matricula") {
  await cargarSeccionesSelectorDocente(seccionId);
  if (seccionDocenteSeleccionada?.id !== seccionId) return;
  mostrarModulo("detalle-clase-docente");
  mostrarPestanaClase(pestana);
  await cargarEstudiantesSeccion(seccionId);
}

async function cargarSelectorEstudiantesDocente() {
  const seleccionActual = selectorEstudiantesDocente.value ||
    (seccionDocenteSeleccionada ? String(seccionDocenteSeleccionada.id) : "");
  selectorEstudiantesDocente.replaceChildren();
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "Seleccione una sección";
  selectorEstudiantesDocente.appendChild(placeholder);
  detalleEstudiantesDocente.classList.add("oculto");
  cuerpoEstudiantesDocente.replaceChildren();
  mostrarTextoEstado(estadoEstudiantesDocente, "Cargando sus secciones...");

  try {
    const respuesta = await fetchAuth(`${URL_PANEL_DOCENTE}/mis-secciones`);
    const secciones = await respuesta.json();
    if (!respuesta.ok) throw new Error(secciones?.detail ?? "No se pudieron cargar las secciones.");
    secciones.forEach((seccion) => {
      const opcion = document.createElement("option");
      opcion.value = String(seccion.id);
      opcion.textContent =
        `${seccion.asignatura_codigo} ${seccion.asignatura_nombre} - ${seccion.codigo}`;
      selectorEstudiantesDocente.appendChild(opcion);
    });

    if (!secciones.length) {
      mostrarTextoEstado(estadoEstudiantesDocente, "No tiene secciones en el período activo.");
      return;
    }
    mostrarTextoEstado(estadoEstudiantesDocente, "");
    if (secciones.some((seccion) => String(seccion.id) === seleccionActual)) {
      selectorEstudiantesDocente.value = seleccionActual;
      await cargarListadoEstudiantesDocente(Number(seleccionActual));
    }
  } catch (error) {
    mostrarTextoEstado(estadoEstudiantesDocente, `No se pudieron cargar sus secciones: ${error.message}`);
  }
}

async function cargarListadoEstudiantesDocente(seccionId) {
  detalleEstudiantesDocente.classList.remove("oculto");
  cuerpoEstudiantesDocente.replaceChildren();
  mostrarTextoEstado(estadoEstudiantesDocente, "Cargando estudiantes...");
  try {
    const respuesta = await fetchAuth(
      `${URL_PANEL_DOCENTE}/mis-secciones/${seccionId}/estudiantes`
    );
    const resultado = await respuesta.json();
    if (!respuesta.ok) throw new Error(resultado?.detail ?? "No se pudieron cargar los estudiantes.");
    if (Number(selectorEstudiantesDocente.value) !== seccionId) return;
    renderizarListadoEstudiantesDocente(resultado.seccion, resultado.estudiantes);
  } catch (error) {
    mostrarTextoEstado(estadoEstudiantesDocente, `No se pudieron cargar los estudiantes: ${error.message}`);
  }
}

function renderizarListadoEstudiantesDocente(seccion, estudiantes) {
  cuerpoEstudiantesDocente.replaceChildren();
  tituloListadoEstudiantesDocente.textContent =
    `${seccion.asignatura_codigo} — ${seccion.asignatura_nombre} · Sección ${seccion.codigo}`;
  contadorListadoEstudiantesDocente.textContent =
    `${estudiantes.length} estudiante(s) matriculado(s) · Período ${seccion.periodo}`;
  if (!estudiantes.length) {
    mostrarTextoEstado(estadoEstudiantesDocente, "No hay estudiantes matriculados en esta sección.");
    return;
  }
  mostrarTextoEstado(estadoEstudiantesDocente, "");
  estudiantes.forEach((estudiante) => {
    const fila = document.createElement("tr");
    [
      estudiante.cuenta,
      estudiante.estudiante_nombre,
      estudiante.correo,
      estudiante.carrera_nombre,
    ].forEach((valor) => {
      const celda = document.createElement("td");
      celda.textContent = valor ?? "—";
      fila.appendChild(celda);
    });
    cuerpoEstudiantesDocente.appendChild(fila);
  });
}

async function cargarEstudiantesSeccion(seccionId) {
  mostrarTextoEstado(textoMisEstudiantesEstado, "Cargando notas de la clase...");
  cuerpoTablaMisEstudiantes.replaceChildren();
  cuerpoMatriculaClase.replaceChildren();
  mostrarTextoEstado(mensajeMatriculaClase, "");
  try {
    const respuesta = await fetchAuth(
      `${URL_PANEL_DOCENTE}/mis-secciones/${seccionId}/estudiantes`
    );
    const resultado = await respuesta.json();
    if (!respuesta.ok) throw new Error(resultado?.detail ?? "error");
    if (seccionDocenteSeleccionada?.id !== seccionId) return;

    const { seccion, estudiantes } = resultado;
    tituloEstudiantesSeccion.textContent =
      `${seccion.asignatura_codigo} — ${seccion.asignatura_nombre} · Sección ${seccion.codigo}`;
    contadorMisEstudiantes.textContent =
      `${estudiantes.length} estudiante(s) matriculado(s) · Período ${seccion.periodo}`;
    estadoMatriculaClase.textContent =
      `${estudiantes.length} estudiante(s) con matrícula activa`;
    renderizarMatriculaClase(estudiantes);
    renderizarEstudiantesSeccion(estudiantes, seccionId);
    mostrarTextoEstado(
      textoMisEstudiantesEstado,
      estudiantes.length ? "" : "No hay estudiantes matriculados en esta sección."
    );
    if (Number(selectorEstudiantesDocente.value) === seccionId) {
      renderizarListadoEstudiantesDocente(seccion, estudiantes);
    }
  } catch (error) {
    mostrarTextoEstado(textoMisEstudiantesEstado, `No se pudieron cargar sus estudiantes: ${error.message}`);
    estadoMatriculaClase.textContent = `No se pudo cargar la matrícula: ${error.message}`;
    mostrarTextoEstado(mensajeMatriculaClase, `No se pudo cargar la matrícula: ${error.message}`);
  }
}

function renderizarMatriculaClase(estudiantes) {
  cuerpoMatriculaClase.replaceChildren();
  if (!estudiantes.length) {
    mostrarTextoEstado(mensajeMatriculaClase, "No hay estudiantes matriculados en esta sección.");
    return;
  }
  mostrarTextoEstado(mensajeMatriculaClase, "");
  estudiantes.forEach((estudiante) => {
    const fila = document.createElement("tr");
    [
      estudiante.cuenta,
      estudiante.estudiante_nombre,
      estudiante.correo,
      estudiante.carrera_nombre,
    ].forEach((valor) => {
      const celda = document.createElement("td");
      celda.textContent = valor ?? "—";
      fila.appendChild(celda);
    });
    cuerpoMatriculaClase.appendChild(fila);
  });
}

function mostrarPestanaClase(nombre) {
  pestanaClaseActiva = nombre;
  document.querySelectorAll("[data-pestana-clase]").forEach((boton) => {
    const activa = boton.dataset.pestanaClase === nombre;
    boton.classList.toggle("activa", activa);
    if (activa) boton.setAttribute("aria-current", "page");
    else boton.removeAttribute("aria-current");
  });
  document.querySelectorAll("[data-panel-clase]").forEach((panel) => {
    panel.classList.toggle("oculto", panel.dataset.panelClase !== nombre);
  });
  if (nombre === "asistencia") cargarAsistenciaSeccion();
}

document.querySelectorAll("[data-pestana-clase]").forEach((boton) => {
  boton.addEventListener("click", () => mostrarPestanaClase(boton.dataset.pestanaClase));
});

function fechaLocalISO() {
  const hoy = new Date();
  const desplazamiento = hoy.getTimezoneOffset() * 60000;
  return new Date(hoy.getTime() - desplazamiento).toISOString().slice(0, 10);
}

fechaSesionAsistencia.value = fechaLocalISO();

async function cargarAsistenciaSeccion(sesionInicialId = null) {
  const seccionId = seccionDocenteSeleccionada?.id;
  if (!seccionId) return;
  mostrarTextoEstado(mensajeAsistenciaClase, "Cargando sesiones de asistencia...");
  botonGuardarAsistencia.disabled = true;
  cuerpoAsistenciaClase.replaceChildren();
  try {
    const respuesta = await fetchAuth(
      `${URL_PANEL_DOCENTE}/mis-secciones/${seccionId}/asistencia`
    );
    const sesiones = await respuesta.json();
    if (!respuesta.ok) throw new Error(sesiones?.detail ?? "No se pudieron cargar las sesiones.");
    if (seccionDocenteSeleccionada?.id !== seccionId) return;

    const anterior = sesionInicialId ?? selectorSesionAsistencia.value;
    selectorSesionAsistencia.replaceChildren();
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "Seleccione una fecha";
    selectorSesionAsistencia.appendChild(placeholder);
    sesiones.forEach((sesion) => {
      const opcion = document.createElement("option");
      opcion.value = String(sesion.id);
      opcion.textContent = `${sesion.fecha} · ${sesion.registros_completados} registro(s)`;
      selectorSesionAsistencia.appendChild(opcion);
    });

    if (!sesiones.length) {
      mostrarTextoEstado(mensajeAsistenciaClase, "Todavía no hay sesiones. Cree una para registrar asistencia.");
      return;
    }
    const seleccionada = sesiones.find((sesion) => String(sesion.id) === String(anterior)) ?? sesiones[0];
    selectorSesionAsistencia.value = String(seleccionada.id);
    await cargarRegistrosAsistencia(seccionId, seleccionada.id);
  } catch (error) {
    mostrarTextoEstado(mensajeAsistenciaClase, `No se pudieron cargar las sesiones: ${error.message}`);
  }
}

async function cargarRegistrosAsistencia(seccionId, sesionId) {
  cuerpoAsistenciaClase.replaceChildren();
  botonGuardarAsistencia.disabled = true;
  mostrarTextoEstado(mensajeAsistenciaClase, "Cargando alumnos...");
  try {
    const respuesta = await fetchAuth(
      `${URL_PANEL_DOCENTE}/mis-secciones/${seccionId}/asistencia/${sesionId}`
    );
    const resultado = await respuesta.json();
    if (!respuesta.ok) throw new Error(resultado?.detail ?? "No se pudieron cargar los alumnos.");
    if (
      seccionDocenteSeleccionada?.id !== seccionId ||
      Number(selectorSesionAsistencia.value) !== sesionId
    ) return;

    resultado.registros.forEach((registro) => {
      const fila = document.createElement("tr");
      [registro.cuenta, registro.estudiante_nombre].forEach((valor) => {
        const celda = document.createElement("td");
        celda.textContent = valor;
        fila.appendChild(celda);
      });
      const celdaEstado = document.createElement("td");
      const selector = document.createElement("select");
      selector.className = "estado-asistencia";
      selector.setAttribute("aria-label", `Asistencia de ${registro.estudiante_nombre}`);
      const opciones = [
        ["", "Seleccione estado"],
        ["PRESENTE", "Presente"],
        ["AUSENTE", "Ausente"],
        ["TARDANZA", "Tardanza"],
        ["JUSTIFICADO", "Justificado"],
      ];
      opciones.forEach(([valor, etiqueta]) => {
        const opcion = document.createElement("option");
        opcion.value = valor;
        opcion.textContent = etiqueta;
        selector.appendChild(opcion);
      });
      selector.value = registro.estado ?? "";
      celdaEstado.appendChild(selector);
      fila.appendChild(celdaEstado);
      fila.dataset.matriculaId = String(registro.matricula_id);
      cuerpoAsistenciaClase.appendChild(fila);
    });
    botonGuardarAsistencia.disabled = resultado.registros.length === 0;
    mostrarTextoEstado(
      mensajeAsistenciaClase,
      resultado.registros.length
        ? `Sesión del ${resultado.sesion.fecha}. Marque el estado de todos los alumnos.`
        : "No hay alumnos con matrícula activa en esta sesión."
    );
  } catch (error) {
    mostrarTextoEstado(mensajeAsistenciaClase, `No se pudieron cargar los alumnos: ${error.message}`);
  }
}

formularioSesionAsistencia.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const seccionId = seccionDocenteSeleccionada?.id;
  if (!seccionId || !formularioSesionAsistencia.reportValidity()) return;
  const boton = document.getElementById("boton-crear-sesion-asistencia");
  boton.disabled = true;
  try {
    const respuesta = await fetchAuth(
      `${URL_PANEL_DOCENTE}/mis-secciones/${seccionId}/asistencia`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fecha: fechaSesionAsistencia.value }),
      }
    );
    const resultado = await respuesta.json();
    if (!respuesta.ok) throw new Error(resultado?.detail ?? "No se pudo crear la sesión.");
    await cargarAsistenciaSeccion(resultado.id);
  } catch (error) {
    mostrarTextoEstado(mensajeAsistenciaClase, `No se pudo crear la sesión: ${error.message}`);
  } finally {
    boton.disabled = false;
  }
});

selectorSesionAsistencia.addEventListener("change", () => {
  const seccionId = seccionDocenteSeleccionada?.id;
  const sesionId = Number(selectorSesionAsistencia.value);
  if (!seccionId || !sesionId) {
    cuerpoAsistenciaClase.replaceChildren();
    botonGuardarAsistencia.disabled = true;
    mostrarTextoEstado(mensajeAsistenciaClase, "Seleccione una sesión para consultar la asistencia.");
    return;
  }
  cargarRegistrosAsistencia(seccionId, sesionId);
});

botonGuardarAsistencia.addEventListener("click", async () => {
  const seccionId = seccionDocenteSeleccionada?.id;
  const sesionId = Number(selectorSesionAsistencia.value);
  if (!seccionId || !sesionId) return;
  const filas = [...cuerpoAsistenciaClase.querySelectorAll("tr")];
  if (filas.some((fila) => !fila.querySelector("select").value)) {
    mostrarTextoEstado(mensajeAsistenciaClase, "Seleccione un estado para cada alumno antes de guardar.");
    return;
  }
  botonGuardarAsistencia.disabled = true;
  try {
    const respuesta = await fetchAuth(
      `${URL_PANEL_DOCENTE}/mis-secciones/${seccionId}/asistencia/${sesionId}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          registros: filas.map((fila) => ({
            matricula_id: Number(fila.dataset.matriculaId),
            estado: fila.querySelector("select").value,
          })),
        }),
      }
    );
    const resultado = await respuesta.json();
    if (!respuesta.ok) throw new Error(resultado?.detail ?? "No se pudo guardar la asistencia.");
    mostrarTextoEstado(
      mensajeAsistenciaClase,
      `Asistencia guardada para ${resultado.registros_guardados} alumno(s).`
    );
    await cargarAsistenciaSeccion(sesionId);
    mostrarTextoEstado(mensajeAsistenciaClase, `Asistencia guardada para ${resultado.registros_guardados} alumno(s).`);
  } catch (error) {
    mostrarTextoEstado(mensajeAsistenciaClase, `No se pudo guardar la asistencia: ${error.message}`);
    botonGuardarAsistencia.disabled = false;
  }
});

function renderizarEstudiantesSeccion(estudiantes, seccionId) {
  cuerpoTablaMisEstudiantes.replaceChildren();
  const etiquetasColumnas = ["Cuenta", "Estudiante", "Correo"];
  estudiantes.forEach((estudiante) => {
    const fila = document.createElement("tr");
    [
      estudiante.cuenta,
      estudiante.estudiante_nombre,
      estudiante.correo,
    ].forEach((valor, indice) => {
      const celda = document.createElement("td");
      celda.dataset.label = etiquetasColumnas[indice];
      celda.textContent = valor ?? "—";
      fila.appendChild(celda);
    });

    ["primer_parcial", "segundo_parcial", "tercer_parcial"].forEach(
      (campo, indice) => {
        const celda = document.createElement("td");
        celda.dataset.label = `Parcial ${indice + 1}`;
        const controles = document.createElement("div");
        controles.className = "control-parcial";
        const entrada = document.createElement("input");
        entrada.type = "number";
        entrada.min = "0";
        entrada.max = "100";
        entrada.step = "0.01";
        entrada.value = estudiante[campo] ?? "";
        entrada.setAttribute(
          "aria-label",
          `Parcial ${indice + 1} de ${estudiante.estudiante_nombre}`
        );
        entrada.title = "Calificación entre 0 y 100";
        entrada.addEventListener("input", () => actualizarNotaFinalVista(fila));
        controles.appendChild(entrada);
        celda.appendChild(controles);
        fila.appendChild(celda);
      }
    );

    const celdaFinal = document.createElement("td");
    celdaFinal.dataset.label = "Nota Final";
    celdaFinal.dataset.notaFinal = "true";
    celdaFinal.textContent = estudiante.nota_final ?? "—";
    fila.appendChild(celdaFinal);

    const celdaEstado = document.createElement("td");
    celdaEstado.dataset.label = "Estado";
    const estado = document.createElement("span");
    estado.className = `estado-academico estado-${estudiante.estado_academico.toLowerCase()}`;
    estado.textContent = estudiante.estado_academico;
    celdaEstado.appendChild(estado);
    fila.appendChild(celdaEstado);

    const celdaAcciones = document.createElement("td");
    celdaAcciones.dataset.label = "Acciones";
    const botonGuardar = document.createElement("button");
    botonGuardar.type = "button";
    botonGuardar.className = "boton-icono";
    botonGuardar.textContent = "Guardar Notas";
    botonGuardar.addEventListener("click", () =>
      guardarCalificacionesDocente(estudiante, fila, botonGuardar, seccionId)
    );
    celdaAcciones.appendChild(botonGuardar);
    fila.appendChild(celdaAcciones);
    cuerpoTablaMisEstudiantes.appendChild(fila);
  });
}

function actualizarNotaFinalVista(fila) {
  const entradas = [...fila.querySelectorAll(".control-parcial input")];
  const final = fila.querySelector('[data-nota-final="true"]');
  if (entradas.some((entrada) => entrada.value === "")) {
    final.textContent = "—";
    return;
  }
  const notas = entradas.map((entrada) => Number(entrada.value));
  if (notas.some((nota) => !Number.isFinite(nota) || nota < 0 || nota > 100)) {
    final.textContent = "—";
    return;
  }
  final.textContent = (notas.reduce((suma, nota) => suma + nota, 0) / 3).toFixed(2);
}

async function guardarCalificacionesDocente(estudiante, fila, boton, seccionId) {
  const entradas = [...fila.querySelectorAll(".control-parcial input")];
  const notas = entradas.map((entrada) => Number(entrada.value));
  if (
    entradas.some((entrada) => entrada.value === "") ||
    notas.some((nota) => !Number.isFinite(nota) || nota < 0 || nota > 100)
  ) {
    mostrarTextoEstado(
      textoMisEstudiantesEstado,
      "Ingrese los tres parciales con calificaciones entre 0 y 100."
    );
    entradas.find((entrada) => entrada.value === "")?.focus();
    return;
  }
  boton.disabled = true;
  boton.textContent = "Guardando...";
  try {
    const respuesta = await fetchAuth(
      `${URL_PANEL_DOCENTE}/mis-estudiantes/${estudiante.matricula_id}/calificacion`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          primer_parcial: notas[0],
          segundo_parcial: notas[1],
          tercer_parcial: notas[2],
        }),
      }
    );
    const resultado = await respuesta.json();
    if (!respuesta.ok) throw new Error(resultado?.detail ?? "No se pudo guardar la calificación.");
    await cargarEstudiantesSeccion(seccionId);
    await cargarResumenDocente();
    mostrarTextoEstado(textoMisEstudiantesEstado, "Calificaciones guardadas correctamente.");
  } catch (error) {
    mostrarTextoEstado(textoMisEstudiantesEstado, `No se pudo guardar la calificación: ${error.message}`);
    boton.disabled = false;
    boton.textContent = "Guardar Notas";
  }
}

selectorSeccionDocente.addEventListener("change", () => {
  const seccionId = Number(selectorSeccionDocente.value);
  if (!seccionId) {
    seccionDocenteSeleccionada = null;
    botonAbrirNotasSeccion.disabled = true;
    mostrarTextoEstado(textoSeleccionNotas, "Seleccione una clase para abrir su matriz de notas.");
    return;
  }
  seccionDocenteSeleccionada =
    seccionesDocente.find((seccion) => seccion.id === seccionId) ?? { id: seccionId };
  botonAbrirNotasSeccion.disabled = false;
  mostrarTextoEstado(
    textoSeleccionNotas,
    `Clase seleccionada: ${seccionDocenteSeleccionada.asignatura_codigo ?? ""} ${seccionDocenteSeleccionada.asignatura_nombre ?? ""} · Sección ${seccionDocenteSeleccionada.codigo ?? ""}.`
  );
});

botonAbrirNotasSeccion.addEventListener("click", () => {
  if (seccionDocenteSeleccionada) abrirDetalleClase(seccionDocenteSeleccionada.id, "notas");
});

selectorEstudiantesDocente.addEventListener("change", () => {
  const seccionId = Number(selectorEstudiantesDocente.value);
  if (!seccionId) {
    detalleEstudiantesDocente.classList.add("oculto");
    cuerpoEstudiantesDocente.replaceChildren();
    mostrarTextoEstado(estadoEstudiantesDocente, "");
    return;
  }
  cargarListadoEstudiantesDocente(seccionId);
});

// Se ejecuta al final: ya existen todas las referencias que necesita.
// Decide la vista inicial (login o dashboard) y, si hay sesión, dispara
// la carga de datos (ver mostrarDashboard más arriba).
restaurarSesion();

botonSalir.addEventListener("click", cerrarSesion);