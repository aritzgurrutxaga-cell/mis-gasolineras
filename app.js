const TRAD = {
  eu: {
    subtitulo: "Konparatu prezioak eta aurreztu depositua betetzean.",
    btn_inicio: "📍 Erakutsi gasolindegiak",
    btn_inicio_sub: "Gomendagarria da kokapena onartzea bilatzeko",
    localizando: "⏳ Kokapena bilatzen...",
    localizando_countdown: "⏳ Kokapena bilatzen... {s} segundo",
    localizando_countdown_plural: "⏳ Kokapena bilatzen... {s} segundo",
    escribe_muni: "📍 Idatzi zure udalerria:",
    placeholder: "Bilatu...",
    btn_confirmar: "🔍 Bilatu",
    ajustes_tit: "⚙️ Bilaketa ezarpenak",
    cambiar_muni: "Aldatu udalerria:",
    radio: "Bilaketa-erradioa:",
    ordenar: "Prezioaren arabera ordenatu:",
    btn_buscar: "🔍 Bilatu",
    error_con: "Konexio errorea.",
    navegar: "Nabigatu",
    distancia_fmt: "📍 {d} km-ra",
    label_muni: "Udalerria:",
    sin_resultados: "Ez da gasolindegirik aurkitu hautatutako erradioan."
  },
  es: {
    subtitulo: "Compara precios en tiempo real y ahorra en cada repostaje.",
    btn_inicio: "📍 Mostrar gasolineras",
    btn_inicio_sub: "Es recomendable la ubicación para buscar",
    localizando: "⏳ Localizando...",
    localizando_countdown: "⏳ Localizando... {s} segundo",
    localizando_countdown_plural: "⏳ Localizando... {s} segundos",
    escribe_muni: "📍 Escribe tu municipio:",
    placeholder: "Buscar...",
    btn_confirmar: "✅ Confirmar selección",
    ajustes_tit: "⚙️ Ajustes de búsqueda",
    cambiar_muni: "Cambiar municipio:",
    radio: "Radio de búsqueda:",
    ordenar: "Ordenar por precio de:",
    btn_buscar: "🔍 Buscar",
    error_con: "Error de conexión.",
    navegar: "Navegar",
    distancia_fmt: "📍 A {d} km",
    label_muni: "Municipio:",
    sin_resultados: "No se han encontrado gasolineras en el radio seleccionado."
  }
};

let datos = [];
let lang = localStorage.getItem("lang_gasolineras") || "eu";
let municipioGuardado = localStorage.getItem("muni_gasolineras") || null;
let tipoCombustible = localStorage.getItem("comb_gasolineras") || "Diésel";
let radioKm = Number(localStorage.getItem("radio_gasolineras") || 5);
let latRef = null;
let lonRef = null;
let muniRef = null;

const pantallaInicio = document.getElementById("pantalla-inicio");
const pantallaLocalizando = document.getElementById("pantalla-localizando");
const pantallaManual = document.getElementById("pantalla-manual");
const pantallaResultados = document.getElementById("pantalla-resultados");

const btnEu = document.getElementById("btn-eu");
const btnEs = document.getElementById("btn-es");
const subtitulo = document.getElementById("subtitulo");
const btnUbicacion = document.getElementById("btn-ubicacion");
const btnUbicacionText = document.getElementById("btn-ubicacion-text");
const btnUbicacionSub = document.getElementById("btn-ubicacion-sub");
const textoLocalizando = document.getElementById("texto-localizando");
const textoMunicipio = document.getElementById("texto-municipio");
const selectMunicipio = document.getElementById("select-municipio");
const btnConfirmar = document.getElementById("btn-confirmar");

const tituloAjustes = document.getElementById("titulo-ajustes");
const labelCambiarMuni = document.getElementById("label-cambiar-muni");
const selectMunicipioAjustes = document.getElementById("select-municipio-ajustes");
const labelRadio = document.getElementById("label-radio");
const labelCombustible = document.getElementById("label-combustible");
const btnBuscarAjustes = document.getElementById("btn-buscar-ajustes");
const resumenFiltros = document.getElementById("resumen-filtros");
const resultados = document.getElementById("resultados");

function t() {
  return TRAD[lang];
}

function mostrarPantalla(nombre) {
  pantallaInicio.classList.add("hidden");
  pantallaLocalizando.classList.add("hidden");
  pantallaManual.classList.add("hidden");
  pantallaResultados.classList.add("hidden");

  if (nombre === "inicio") pantallaInicio.classList.remove("hidden");
  if (nombre === "localizando") pantallaLocalizando.classList.remove("hidden");
  if (nombre === "manual") pantallaManual.classList.remove("hidden");
  if (nombre === "resultados") pantallaResultados.classList.remove("hidden");
}

function aplicarIdioma() {
  document.documentElement.lang = lang;

  btnEu.classList.toggle("active", lang === "eu");
  btnEs.classList.toggle("active", lang === "es");

  subtitulo.textContent = t().subtitulo;
  btnUbicacionText.textContent = t().btn_inicio;
  btnUbicacionSub.textContent = t().btn_inicio_sub;
  textoLocalizando.textContent = t().localizando;
  textoMunicipio.textContent = t().escribe_muni;
  btnConfirmar.textContent = t().btn_confirmar;

  tituloAjustes.textContent = t().ajustes_tit;
  labelCambiarMuni.textContent = t().cambiar_muni;
  labelRadio.textContent = t().radio;
  labelCombustible.textContent = t().ordenar;
  btnBuscarAjustes.textContent = t().btn_buscar;

  const placeholder = selectMunicipio.querySelector("option[value='']");
  if (placeholder) placeholder.textContent = t().placeholder;

  if (!pantallaResultados.classList.contains("hidden") && muniRef) {
    pintarResultados();
  }
}

function normalizarNumero(valor) {
  if (valor === null || valor === undefined) return NaN;
  return Number(String(valor).replace(",", "."));
}

function calcularDistancia(lat1, lon1, lat2, lon2) {
  const R = 6371.0;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const rLat1 = lat1 * Math.PI / 180;
  const rLat2 = lat2 * Math.PI / 180;

  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(rLat1) * Math.cos(rLat2) * Math.sin(dLon / 2) ** 2;

  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function prepararDatos(raw) {
  return raw.map(g => ({
    ...g,
    lat_num: normalizarNumero(g["Latitud"]),
    lon_num: normalizarNumero(g["Longitud (WGS84)"]),
    precio_diesel_num: normalizarNumero(g["Precio Gasoleo A"]),
    precio_g95_num: normalizarNumero(g["Precio Gasolina 95 E5"])
  }));
}

function municipiosUnicos() {
  return [...new Set(datos.map(g => String(g["Municipio"])).filter(Boolean))].sort();
}

function rellenarMunicipios() {
  const municipios = municipiosUnicos();

  selectMunicipio.innerHTML = `<option value="">${t().placeholder}</option>`;
  selectMunicipioAjustes.innerHTML = "";

  municipios.forEach(muni => {
    const opt1 = document.createElement("option");
    opt1.value = muni;
    opt1.textContent = muni;
    selectMunicipio.appendChild(opt1);

    const opt2 = document.createElement("option");
    opt2.value = muni;
    opt2.textContent = muni;
    selectMunicipioAjustes.appendChild(opt2);
  });
}

function municipioMasCercano(lat, lon) {
  let mejor = null;
  let mejorDistancia = Infinity;

  datos.forEach(g => {
    if (Number.isNaN(g.lat_num) || Number.isNaN(g.lon_num)) return;

    const d = calcularDistancia(lat, lon, g.lat_num, g.lon_num);
    if (d < mejorDistancia) {
      mejorDistancia = d;
      mejor = g["Municipio"];
    }
  });

  return mejor;
}

function obtenerCoordenadasMunicipio(municipio) {
  const fila = datos.find(g => String(g["Municipio"]) === String(municipio));
  if (!fila) return null;

  return {
    lat: fila.lat_num,
    lon: fila.lon_num
  };
}

function guardarEstado() {
  if (muniRef) localStorage.setItem("muni_gasolineras", muniRef);
  localStorage.setItem("comb_gasolineras", tipoCombustible);
  localStorage.setItem("radio_gasolineras", String(radioKm));
  localStorage.setItem("lang_gasolineras", lang);
}

function actualizarBotonesFiltros() {
  document.querySelectorAll(".radio-btn").forEach(btn => {
    btn.classList.toggle("active", Number(btn.dataset.radio) === radioKm);
  });

  document.querySelectorAll(".fuel-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.fuel === tipoCombustible);
  });
}

function pintarResultados() {
  guardarEstado();
  actualizarBotonesFiltros();

  selectMunicipioAjustes.value = muniRef || "";

  const colPrecio = tipoCombustible === "Diésel" ? "precio_diesel_num" : "precio_g95_num";

  const filtradas = datos
    .map(g => ({
      ...g,
      distancia: calcularDistancia(latRef, lonRef, g.lat_num, g.lon_num)
    }))
    .filter(g => !Number.isNaN(g.distancia) && g.distancia <= radioKm)
    .sort((a, b) => {
      const pa = Number.isNaN(a[colPrecio]) ? Infinity : a[colPrecio];
      const pb = Number.isNaN(b[colPrecio]) ? Infinity : b[colPrecio];
      return pa - pb;
    })
    .slice(0, 20);

  resumenFiltros.innerHTML = `📍 <b>${muniRef}</b> | 🚗 <b>${radioKm} km</b> | ⛽ <b>${tipoCombustible}</b>`;

  if (filtradas.length === 0) {
    resultados.innerHTML = `<div class="mensaje">${t().sin_resultados}</div>`;
    return;
  }

  resultados.innerHTML = filtradas.map(g => {
    const diesel = !Number.isNaN(g.precio_diesel_num) && g["Precio Gasoleo A"]
      ? `${g["Precio Gasoleo A"]}€`
      : "N/A";

    const g95 = !Number.isNaN(g.precio_g95_num) && g["Precio Gasolina 95 E5"]
      ? `${g["Precio Gasolina 95 E5"]}€`
      : "N/A";

    const distancia = t().distancia_fmt.replace("{d}", g.distancia.toFixed(2));

    const mapsUrl = `https://www.google.com/maps/search/?api=1&query=${g.lat_num},${g.lon_num}`;

    return `
      <article class="gasolinera-card">
        <div>
          <h3>${g["Rótulo"] || ""} - ${g["Municipio"] || ""}</h3>
          <p>⛽ <b>Diesel:</b> ${diesel} | <b>G95:</b> ${g95}</p>
          <p class="distancia">${distancia}</p>
        </div>
        <div>
          <a class="btn-navegar" href="${mapsUrl}" target="_blank" rel="noopener noreferrer">${t().navegar}</a>
        </div>
      </article>
    `;
  }).join("");
}

function buscarPorMunicipio(municipio) {
  if (!municipio) return;

  const coords = obtenerCoordenadasMunicipio(municipio);
  if (!coords) return;

  muniRef = municipio;
  latRef = coords.lat;
  lonRef = coords.lon;

  mostrarPantalla("resultados");
  pintarResultados();
}

function iniciarGeolocalizacion() {
  mostrarPantalla("localizando");

  if (!navigator.geolocation) {
    mostrarPantalla("manual");
    return;
  }

  let segundos = 5;
  textoLocalizando.textContent = t().localizando_countdown_plural.replace("{s}", segundos);

  const intervalo = setInterval(() => {
    segundos -= 1;

    if (segundos <= 0) {
      clearInterval(intervalo);
      return;
    }

    const key = segundos === 1 ? "localizando_countdown" : "localizando_countdown_plural";
    textoLocalizando.textContent = t()[key].replace("{s}", segundos);
  }, 1000);

  navigator.geolocation.getCurrentPosition(
    pos => {
      clearInterval(intervalo);

      latRef = pos.coords.latitude;
      lonRef = pos.coords.longitude;
      muniRef = municipioMasCercano(latRef, lonRef);

      if (!muniRef) {
        mostrarPantalla("manual");
        return;
      }

      mostrarPantalla("resultados");
      pintarResultados();
    },
    () => {
      clearInterval(intervalo);
      mostrarPantalla("manual");
    },
    {
      enableHighAccuracy: true,
      timeout: 5000,
      maximumAge: 300000
    }
  );
}

async function cargarDatos() {
  try {
    const res = await fetch("precios_gasolineras.json", { cache: "no-store" });
    if (!res.ok) throw new Error("Error cargando JSON");

    const payload = await res.json();

    if (!payload.datos || !Array.isArray(payload.datos)) {
      throw new Error("Formato JSON inválido");
    }

    datos = prepararDatos(payload.datos);
    rellenarMunicipios();

    if (municipioGuardado) {
      buscarPorMunicipio(municipioGuardado);
    } else {
      mostrarPantalla("inicio");
    }
  } catch (e) {
    pantallaInicio.innerHTML = `<h1 class="titulo">gasolina<span>.eus</span></h1><div class="mensaje">${t().error_con}</div>`;
    mostrarPantalla("inicio");
  }
}

btnEu.addEventListener("click", () => {
  lang = "eu";
  aplicarIdioma();
  guardarEstado();
});

btnEs.addEventListener("click", () => {
  lang = "es";
  aplicarIdioma();
  guardarEstado();
});

btnUbicacion.addEventListener("click", iniciarGeolocalizacion);

btnConfirmar.addEventListener("click", () => {
  buscarPorMunicipio(selectMunicipio.value);
});

btnBuscarAjustes.addEventListener("click", () => {
  const nuevoMuni = selectMunicipioAjustes.value;
  buscarPorMunicipio(nuevoMuni);
});

document.querySelectorAll(".radio-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    radioKm = Number(btn.dataset.radio);
    pintarResultados();
  });
});

document.querySelectorAll(".fuel-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    tipoCombustible = btn.dataset.fuel;
    pintarResultados();
  });
});

aplicarIdioma();
cargarDatos();
