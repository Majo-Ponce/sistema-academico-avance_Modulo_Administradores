const opcionesMenuAdmin = [
  {
    modulo: "estudiantes",
    etiqueta: "Estudiantes",
    icono: '<path d="M22 10 12 5 2 10l10 5 10-5z"/><path d="M6 12v5c3 2 9 2 12 0v-5"/>',
  },
  {
    modulo: "docentes",
    etiqueta: "Docentes",
    icono: '<circle cx="9" cy="8" r="4"/><path d="M2 21v-1a6 6 0 0 1 6-6h2a6 6 0 0 1 6 6v1"/><path d="m17 11 2 2 4-4"/>',
  },
  {
    modulo: "asignaturas",
    etiqueta: "Asignaturas",
    icono: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
  },
  {
    modulo: "carreras",
    etiqueta: "Carreras",
    icono: '<path d="M3 21h18M5 21V7l7-4 7 4v14M9 21v-8h6v8M9 8h.01M15 8h.01"/>',
  },
  {
    modulo: "periodos",
    etiqueta: "Períodos",
    icono: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  },
  {
    modulo: "aulas",
    etiqueta: "Aulas",
    icono: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 20V8h6v12M3 12h6m6 0h6M3 16h6m6 0h6"/>',
  },
  {
    modulo: "secciones",
    etiqueta: "Secciones",
    icono: '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
    pagina: "/secciones.html",
  },
  {
    modulo: "matriculas",
    etiqueta: "Matrículas",
    icono: '<path d="m9 11 3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>',
    pagina: "/matriculas.html",
  },
];

function crearEnlaceMenu({ modulo, etiqueta, icono, pagina }) {
  const enlace = document.createElement("a");
  enlace.className = "boton-menu solo-admin";
  enlace.dataset.modulo = modulo;
  enlace.href = pagina ?? `/index.html#${modulo}`;
  const paginaInicio =
    window.location.pathname === "/" ||
    window.location.pathname.endsWith("/index.html");
  if (
    (pagina && window.location.pathname === pagina) ||
    (!pagina &&
      paginaInicio &&
      (window.location.hash === `#${modulo}` ||
        (!window.location.hash && modulo === "estudiantes")))
  ) {
    enlace.classList.add("activo");
    enlace.setAttribute("aria-current", "page");
  }

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("width", "18");
  svg.setAttribute("height", "18");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "2");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  svg.setAttribute("aria-hidden", "true");
  svg.innerHTML = icono;

  const texto = document.createElement("span");
  texto.textContent = etiqueta;
  enlace.append(svg, texto);
  return enlace;
}

function crearEnlaceMenuDocente(modulo, etiqueta, icono) {
  const boton = document.createElement("button");
  boton.type = "button";
  boton.className = "boton-menu solo-docente oculto";
  boton.dataset.modulo = modulo;
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("width", "18");
  svg.setAttribute("height", "18");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "2");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  svg.setAttribute("aria-hidden", "true");
  svg.innerHTML = icono;
  const texto = document.createElement("span");
  texto.textContent = etiqueta;
  boton.append(svg, texto);
  return boton;
}

const menuLateral = document.querySelector(".menu-principal");
const marcaMenu = document.createElement("div");
marcaMenu.className = "marca-menu";
marcaMenu.innerHTML =
  '<span class="logo-menu">SA</span><span class="nombre-menu">Sistema Académico</span>';
const tituloMenu = document.createElement("p");
tituloMenu.className = "titulo-menu";
tituloMenu.id = "titulo-menu-rol";

const usuarioMenu = obtenerUsuario();
const esAdminMenu = usuarioMenu?.rol === "ADMIN";
tituloMenu.textContent = esAdminMenu
  ? "ADMINISTRACIÓN GLOBAL"
  : "PANEL DEL DOCENTE";

menuLateral.replaceChildren(marcaMenu, tituloMenu);
opcionesMenuAdmin.forEach((opcion) => {
  menuLateral.appendChild(crearEnlaceMenu(opcion));
});
const enlaceInicioDocente = crearEnlaceMenuDocente(
  "inicio",
  "Inicio",
  '<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-6v-6h-4v6H4a1 1 0 0 1-1-1z"/>'
);
const grupoClasesDocente = document.createElement("section");
grupoClasesDocente.className = "grupo-menu-docente solo-docente oculto";
const botonClasesDocente = document.createElement("button");
botonClasesDocente.type = "button";
botonClasesDocente.className = "boton-menu-toggle-clases";
botonClasesDocente.setAttribute("aria-expanded", "true");
botonClasesDocente.setAttribute("aria-controls", "submenu-clases-docente");
botonClasesDocente.innerHTML =
  '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg><span>Clases</span><span class="flecha-menu-clases" aria-hidden="true">⌄</span>';
const submenuClasesDocente = document.createElement("div");
submenuClasesDocente.className = "submenu-menu-docente";
submenuClasesDocente.id = "submenu-clases-docente";
[
  ["mis-secciones", "Lista de Clases"],
  ["estudiantes-docente", "Listados de Alumnos"],
  ["calificaciones-docente", "Notas de Alumnos"],
].forEach(([modulo, etiqueta]) => {
  submenuClasesDocente.appendChild(
    crearEnlaceMenuDocente(
      modulo,
      etiqueta,
      modulo === "mis-secciones"
        ? '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>'
        : modulo === "estudiantes-docente"
          ? '<circle cx="9" cy="8" r="4"/><path d="M2 21v-1a6 6 0 0 1 6-6h2a6 6 0 0 1 6 6v1"/><path d="M16 4.5a4 4 0 0 1 0 7.5"/>'
          : '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/><path d="m9 10 2 2 4-4"/>'
    )
  );
});
grupoClasesDocente.append(botonClasesDocente, submenuClasesDocente);
menuLateral.append(enlaceInicioDocente, grupoClasesDocente);
botonClasesDocente.addEventListener("click", () => {
  const expandido = botonClasesDocente.getAttribute("aria-expanded") === "true";
  botonClasesDocente.setAttribute("aria-expanded", String(!expandido));
  submenuClasesDocente.classList.toggle("oculto", expandido);
});
menuLateral.querySelectorAll(".solo-admin").forEach((enlace) => {
  enlace.classList.toggle("oculto", !esAdminMenu);
});
menuLateral.querySelectorAll(".solo-docente").forEach((enlace) => {
  enlace.classList.toggle("oculto", esAdminMenu);
});
