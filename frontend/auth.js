const CLAVE_TOKEN = "sa_token";
const CLAVE_USUARIO = "sa_usuario";

function decodificarToken(token) {
  try {
    const payload = token.split(".")[1];
    const json = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(json);
  } catch (error) {
    return null;
  }
}

// `usuario`, si se recibe, es el objeto que ya devuelve la API en
// /api/v1/auth/login ({id, usuario, nombre_completo, rol}). Si no se pasa,
// se intenta reconstruir a partir de los claims del propio token.
function guardarSesion(token, usuario) {
  localStorage.setItem(CLAVE_TOKEN, token);
  const datos = usuario ?? decodificarToken(token) ?? {};
  localStorage.setItem(
    CLAVE_USUARIO,
    JSON.stringify({
      id: datos.id ?? null,
      docente_id: datos.docente_id ?? null,
      usuario: datos.usuario ?? "",
      nombre_completo: datos.nombre_completo ?? datos.sub ?? "",
      rol: datos.rol ?? "",
      debe_cambiar_password: Boolean(
        datos.debe_cambiar_password ?? datos.cambiar_password
      ),
    })
  );
}

function obtenerToken() {
  return localStorage.getItem(CLAVE_TOKEN);
}

function obtenerUsuario() {
  const usuario = JSON.parse(localStorage.getItem(CLAVE_USUARIO) || "null");
  if (!usuario) return null;
  usuario.debe_cambiar_password = Boolean(
    usuario.debe_cambiar_password ?? usuario.cambiar_password
  );
  return usuario;
}

function cerrarSesion() {
  localStorage.removeItem(CLAVE_TOKEN);
  localStorage.removeItem(CLAVE_USUARIO);
  window.location.href = "/index.html";
}

function requerirSesion() {
  if (!obtenerToken()) {
    window.location.href = "/index.html";
    return false;
  }
  return true;
}

async function fetchAuth(url, opciones = {}) {
  const token = obtenerToken();
  const cabeceras = { ...(opciones.headers || {}) };
  if (token) cabeceras["Authorization"] = `Bearer ${token}`;

  const respuesta = await fetch(url, { ...opciones, headers: cabeceras });

  if (respuesta.status === 401) {
    cerrarSesion();
    throw new Error("Sesión expirada");
  }
  return respuesta;
}