const DEFINICIONES_CATALOGO = {
  carreras: {
    url: "/api/v1/carreras",
    nombre: "carrera",
    columnas: [
      { titulo: "Código", valor: (fila) => fila.codigo },
      { titulo: "Nombre", valor: (fila) => fila.nombre },
      { titulo: "Duración", valor: (fila) => `${fila.duracion_anios} años` },
    ],
    campos: ["codigo", "nombre", "duracion_anios", "activo"],
    etiquetaGuardar: "Guardar carrera",
    estado: "Activa",
  },
  periodos: {
    url: "/api/v1/periodos",
    nombre: "período",
    columnas: [
      { titulo: "Período", valor: (fila) => fila.nombre },
      { titulo: "Inicio", valor: (fila) => fila.fecha_inicio },
      { titulo: "Fin", valor: (fila) => fila.fecha_fin },
    ],
    campos: ["anio", "numero", "fecha_inicio", "fecha_fin", "activo"],
    etiquetaGuardar: "Guardar período",
    estado: "Activo",
  },
  aulas: {
    url: "/api/v1/aulas",
    nombre: "aula",
    columnas: [
      { titulo: "Código", valor: (fila) => fila.codigo },
      { titulo: "Edificio", valor: (fila) => fila.edificio },
      { titulo: "Capacidad", valor: (fila) => `${fila.capacidad} personas` },
    ],
    campos: ["codigo", "edificio", "capacidad", "activo"],
    etiquetaGuardar: "Guardar aula",
    estado: "Activa",
  },
};

function mostrarMensajeCatalogo(modulo, texto, tipo = "error") {
  const mensaje = document.querySelector(
    `#modulo-${modulo} .mensaje-catalogo`
  );
  mensaje.textContent = texto;
  mensaje.className = `mensaje-catalogo mensaje-${tipo}`;
}

function limpiarFormularioCatalogo(modulo) {
  const definicion = DEFINICIONES_CATALOGO[modulo];
  const formulario = document.querySelector(
    `#modulo-${modulo} .formulario-catalogo`
  );
  formulario.reset();
  formulario.elements.id.value = "";
  formulario.querySelector(".boton-guardar-catalogo").textContent =
    definicion.etiquetaGuardar;
  formulario.querySelector(".boton-cancelar-catalogo").classList.add("oculto");
  document.getElementById(`titulo-formulario-${modulo}`).textContent =
    modulo === "periodos" ? "Nuevo período" : `Nueva ${definicion.nombre}`;
}

function obtenerDatosFormulario(formulario, definicion) {
  const datos = {};
  definicion.campos.forEach((campo) => {
    const entrada = formulario.elements.namedItem(campo);
    if (campo === "activo") {
      datos[campo] = entrada.checked;
    } else if (entrada.type === "number") {
      datos[campo] = Number(entrada.value);
    } else {
      datos[campo] = entrada.value.trim();
    }
  });
  return datos;
}

function editarFilaCatalogo(modulo, fila) {
  const definicion = DEFINICIONES_CATALOGO[modulo];
  const formulario = document.querySelector(
    `#modulo-${modulo} .formulario-catalogo`
  );
  formulario.reset();
  formulario.elements.id.value = fila.id;
  definicion.campos.forEach((campo) => {
    const entrada = formulario.elements.namedItem(campo);
    if (campo === "activo") {
      entrada.checked = Boolean(fila[campo]);
    } else {
      entrada.value = fila[campo];
    }
  });
  document.getElementById(`titulo-formulario-${modulo}`).textContent =
    `Editar ${definicion.nombre} — ${fila.nombre ?? fila.codigo}`;
  formulario.querySelector(".boton-guardar-catalogo").textContent =
    `Guardar cambios`;
  formulario.querySelector(".boton-cancelar-catalogo").classList.remove("oculto");
  mostrarMensajeCatalogo(modulo, "");
  formulario.scrollIntoView({ behavior: "smooth", block: "start" });
}

function crearCelda(texto) {
  const celda = document.createElement("td");
  celda.textContent = texto ?? "";
  return celda;
}

function renderizarCatalogo(modulo, filas) {
  const definicion = DEFINICIONES_CATALOGO[modulo];
  const contenedor = document.querySelector(`#modulo-${modulo}`);
  const cuerpo = contenedor.querySelector(".cuerpo-catalogo");
  const textoVacio = contenedor.querySelector(".texto-vacio");
  cuerpo.replaceChildren();

  if (filas.length === 0) {
    textoVacio.textContent = `No hay ${definicion.nombre}s registrados.`;
    textoVacio.classList.remove("oculto");
    return;
  }
  textoVacio.classList.add("oculto");

  filas.forEach((fila) => {
    const tr = document.createElement("tr");
    definicion.columnas.forEach(({ valor }) => {
      tr.appendChild(crearCelda(valor(fila)));
    });

    const celdaEstado = document.createElement("td");
    const estado = document.createElement("span");
    estado.className = fila.activo
      ? "pastilla-estado pastilla-activo"
      : "pastilla-estado pastilla-neutral";
    estado.textContent = fila.activo ? definicion.estado : "Inactivo";
    celdaEstado.appendChild(estado);
    tr.appendChild(celdaEstado);

    const acciones = document.createElement("td");
    acciones.className = "acciones-fila";
    const botonEditar = document.createElement("button");
    botonEditar.type = "button";
    botonEditar.className = "boton-icono";
    botonEditar.textContent = "Editar";
    botonEditar.addEventListener("click", () => editarFilaCatalogo(modulo, fila));
    acciones.appendChild(botonEditar);

    const botonEstado = document.createElement("button");
    botonEstado.type = "button";
    botonEstado.className = fila.activo ? "boton-icono peligro" : "boton-icono";
    botonEstado.textContent = fila.activo ? "Desactivar" : "Activar";
    botonEstado.addEventListener("click", () =>
      cambiarEstadoCatalogo(modulo, fila, botonEstado)
    );
    acciones.appendChild(botonEstado);
    tr.appendChild(acciones);
    cuerpo.appendChild(tr);
  });
}

async function cargarCatalogoAdmin(modulo) {
  const definicion = DEFINICIONES_CATALOGO[modulo];
  if (!definicion) return;

  const contenedor = document.querySelector(`#modulo-${modulo}`);
  const cuerpo = contenedor.querySelector(".cuerpo-catalogo");
  try {
    const respuesta = await fetchAuth(definicion.url);
    if (!respuesta.ok) {
      throw new Error(`No se pudo cargar el catálogo (${respuesta.status}).`);
    }
    renderizarCatalogo(modulo, await respuesta.json());
  } catch (error) {
    cuerpo.replaceChildren();
    mostrarMensajeCatalogo(
      modulo,
      `No se pudo cargar ${definicion.nombre}: ${error.message}`
    );
  }
}

async function guardarCatalogo(modulo, evento) {
  evento.preventDefault();
  const definicion = DEFINICIONES_CATALOGO[modulo];
  const formulario = evento.currentTarget;
  const id = formulario.elements.id.value;
  const botonGuardar = formulario.querySelector(".boton-guardar-catalogo");
  botonGuardar.disabled = true;
  botonGuardar.textContent = "Guardando...";
  mostrarMensajeCatalogo(modulo, "");

  try {
    const respuesta = await fetchAuth(
      `${definicion.url}${id ? `/${id}` : ""}`,
      {
        method: id ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(obtenerDatosFormulario(formulario, definicion)),
      }
    );
    const resultado = await respuesta.json().catch(() => null);
    if (!respuesta.ok) {
      const detalle =
        typeof resultado?.detail === "string"
          ? resultado.detail
          : `La API rechazó los datos (${respuesta.status}).`;
      throw new Error(detalle);
    }

    mostrarMensajeCatalogo(
      modulo,
      `${definicion.nombre[0].toUpperCase()}${definicion.nombre.slice(1)} ${
        id ? "actualizado" : "creado"
      } correctamente.`,
      "exito"
    );
    limpiarFormularioCatalogo(modulo);
    await cargarCatalogoAdmin(modulo);
  } catch (error) {
    mostrarMensajeCatalogo(modulo, error.message);
  } finally {
    botonGuardar.disabled = false;
    botonGuardar.textContent = formulario.elements.id.value
      ? "Guardar cambios"
      : definicion.etiquetaGuardar;
  }
}

async function cambiarEstadoCatalogo(modulo, fila, boton) {
  const definicion = DEFINICIONES_CATALOGO[modulo];
  const accion = fila.activo ? "desactivar" : "activar";
  if (
    !window.confirm(`¿Desea ${accion} ${definicion.nombre} ${fila.codigo ?? fila.nombre}?`)
  ) {
    return;
  }

  boton.disabled = true;
  try {
    const respuesta = await fetchAuth(`${definicion.url}/${fila.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...fila, activo: !fila.activo }),
    });
    const resultado = await respuesta.json().catch(() => null);
    if (!respuesta.ok) {
      throw new Error(
        resultado?.detail ?? `No se pudo ${accion} el ${definicion.nombre}.`
      );
    }
    await cargarCatalogoAdmin(modulo);
  } catch (error) {
    mostrarMensajeCatalogo(modulo, error.message);
    boton.disabled = false;
  }
}

Object.keys(DEFINICIONES_CATALOGO).forEach((modulo) => {
  const formulario = document.querySelector(
    `#modulo-${modulo} .formulario-catalogo`
  );
  formulario.addEventListener("submit", (evento) => guardarCatalogo(modulo, evento));
  formulario
    .querySelector(".boton-cancelar-catalogo")
    .addEventListener("click", () => {
      limpiarFormularioCatalogo(modulo);
      mostrarMensajeCatalogo(modulo, "");
    });
});

window.cargarCatalogoAdmin = cargarCatalogoAdmin;
