import { useState, useEffect } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  PieChart, Pie, Cell, Legend,
} from "recharts";
import "./App.css";

const CORE = "http://localhost:8001";
// Paleta para los gráficos de torta
const COLORS = ["#6c8cff", "#4fd1a5", "#f5a05a", "#e77ea0", "#a78bfa",
                "#5ac8e7", "#e7d06e", "#7bd88f", "#f07171", "#9ca3af"];

function App() {
  const [datasets, setDatasets] = useState([]);
  const [subiendo, setSubiendo] = useState(false);
  const [error, setError] = useState("");
  const [activo, setActivo] = useState(null);      // { id, tipo, nombre }
  const [analytics, setAnalytics] = useState(null); // para tablas
  const [contenido, setContenido] = useState(null); // para documentos
  const [insights, setInsights] = useState("");
  const [pensando, setPensando] = useState(false);
  const [pregunta, setPregunta] = useState("");
  const [respuesta, setRespuesta] = useState("");
  const [conocimiento, setConocimiento] = useState([]);
  const [urlScan, setUrlScan] = useState("");
  const [escaneando, setEscaneando] = useState(false);
  const [scan, setScan] = useState(null);

  useEffect(() => { cargar(); cargarConocimiento(); }, []);

  async function escanearSeguridad(e) {
    e.preventDefault();
    if (!urlScan.trim()) return;
    setEscaneando(true);
    setScan(null);
    try {
      const r = await fetch(`${CORE}/security/scan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: urlScan }),
      }).then((r) => r.json());
      setScan(r);
    } catch {
      setError("No se pudo escanear el sitio.");
    } finally {
      setEscaneando(false);
    }
  }

  async function cargar() {
    try {
      const ds = await fetch(`${CORE}/datasets`).then((r) => r.json());
      setDatasets(ds);
      setError("");
    } catch {
      setError("No se pudo conectar con el servicio core (¿está corriendo en :8001?)");
    }
  }

  async function cargarConocimiento() {
    try {
      setConocimiento(await fetch(`${CORE}/conocimiento`).then((r) => r.json()));
    } catch { /* silencioso */ }
  }

  async function guardarConocimiento(contenido) {
    try {
      await fetch(`${CORE}/conocimiento`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          dataset_id: activo?.id,
          titulo: activo?.nombre,
          contenido,
        }),
      });
      await cargarConocimiento();
    } catch {
      setError("No se pudo guardar en la base de conocimiento.");
    }
  }

  async function borrarConocimiento(id) {
    try {
      await fetch(`${CORE}/conocimiento/${id}`, { method: "DELETE" });
      await cargarConocimiento();
    } catch { /* silencioso */ }
  }

  async function subirArchivo(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setSubiendo(true);
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${CORE}/datasets/upload`, { method: "POST", body: form });
      if (!res.ok) throw new Error((await res.json()).detail || "Error");
      const nuevo = await res.json();
      await cargar();
      await abrir(nuevo);
    } catch (err) {
      setError("Error subiendo archivo: " + err.message);
    } finally {
      setSubiendo(false);
      e.target.value = "";
    }
  }

  // Abre un archivo: si es tabla carga analytics, si es texto carga el contenido
  async function abrir(ds) {
    setActivo({ id: ds.id, tipo: ds.tipo, nombre: ds.nombre_archivo });
    setAnalytics(null);
    setContenido(null);
    setInsights("");
    setRespuesta("");
    try {
      if (ds.tipo === "tabla") {
        setAnalytics(await fetch(`${CORE}/datasets/${ds.id}/analytics`).then((r) => r.json()));
      } else {
        setContenido(await fetch(`${CORE}/datasets/${ds.id}/content`).then((r) => r.json()));
      }
    } catch {
      setError("No se pudo abrir el archivo.");
    }
  }

  async function pedirInsights() {
    setPensando(true);
    setInsights("");
    try {
      const r = await fetch(`${CORE}/datasets/${activo.id}/insights`).then((r) => r.json());
      setInsights(r.insights);
    } catch {
      setError("ShaddAI no pudo razonar (¿Ollama está corriendo?).");
    } finally {
      setPensando(false);
    }
  }

  async function preguntar(e) {
    e.preventDefault();
    if (!pregunta.trim()) return;
    setPensando(true);
    setRespuesta("");
    try {
      const r = await fetch(`${CORE}/datasets/${activo.id}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pregunta }),
      }).then((r) => r.json());
      setRespuesta(r.respuesta);
    } catch {
      setError("ShaddAI no pudo responder.");
    } finally {
      setPensando(false);
    }
  }

  return (
    <div className="app">
      <header>
        <h1>🧠 ShaddAI</h1>
        <p>Sube cualquier archivo · ShaddAI lo razona por ti</p>
      </header>

      {error && <div className="error">{error}</div>}

      <section className="card">
        <h2>Subir archivo</h2>
        <input type="file" onChange={subirArchivo} disabled={subiendo} />
        <p className="hint">
          Datos: CSV, Excel, JSON · Documentos: PDF, TXT, código, SQL, logs
        </p>
        {subiendo && <span> Procesando…</span>}
      </section>

      <section className="card">
        <h2>Archivos ({datasets.length})</h2>
        <ul className="lista-datasets">
          {datasets.map((d) => (
            <li key={d.id}>
              <span>
                {d.tipo === "texto" ? "📄" : "📊"} {d.nombre_archivo}
                {d.tipo === "tabla" && d.filas != null ? ` — ${d.filas} filas` : ""}
              </span>
              <button onClick={() => abrir(d)}>Abrir</button>
            </li>
          ))}
        </ul>
      </section>

      {activo && (
        <section className="card">
          <h2>{activo.nombre}</h2>

          {/* Razonamiento de ShaddAI (funciona para tablas y documentos) */}
          <div className="ia">
            <button className="btn-ia" onClick={pedirInsights} disabled={pensando}>
              🧠 {pensando ? "ShaddAI está pensando…" : "Pedir análisis a ShaddAI"}
            </button>
            {insights && (
              <div className="ia-respuesta">
                {insights}
                <button className="btn-guardar" onClick={() => guardarConocimiento(insights)}>
                  💾 Guardar en base de conocimiento
                </button>
              </div>
            )}
            <form onSubmit={preguntar} className="ia-form">
              <input
                type="text"
                placeholder="Pregúntale a ShaddAI sobre este archivo…"
                value={pregunta}
                onChange={(e) => setPregunta(e.target.value)}
                disabled={pensando}
              />
              <button type="submit" disabled={pensando}>Preguntar</button>
            </form>
            {respuesta && (
              <div className="ia-respuesta">
                {respuesta}
                <button className="btn-guardar" onClick={() => guardarConocimiento(respuesta)}>
                  💾 Guardar en base de conocimiento
                </button>
              </div>
            )}
          </div>

          {/* Vista de TABLA: tarjetas + gráficos */}
          {analytics && (
            <>
              <p className="sub">{analytics.filas} filas · {analytics.columnas.length} columnas</p>
              {analytics.resumen_numerico.length > 0 && (
                <div className="tarjetas">
                  {analytics.resumen_numerico.map((r) => (
                    <div className="tarjeta" key={r.columna}>
                      <div className="tarjeta-titulo">{r.columna}</div>
                      <div className="tarjeta-valor">{r.promedio.toLocaleString()}</div>
                      <div className="tarjeta-sub">promedio</div>
                      <div className="tarjeta-mini">
                        min {r.minimo.toLocaleString()} · máx {r.maximo.toLocaleString()}
                      </div>
                    </div>
                  ))}
                </div>
              )}
              {/* Gráficos cruzados: métrica por categoría (lo más útil para decidir) */}
              {(analytics.agregaciones || []).map((a) => (
                <div className="grafico" key={a.categoria + a.metrica}>
                  <h3>{a.metrica} por {a.categoria} (top {a.datos.length})</h3>
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={a.datos}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                      <XAxis dataKey="nombre" tick={{ fill: "#aaa", fontSize: 12 }} />
                      <YAxis tick={{ fill: "#aaa", fontSize: 12 }} />
                      <Tooltip contentStyle={{ background: "#1a1a1a", border: "1px solid #444" }} />
                      <Bar dataKey="valor" fill="#4fd1a5" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ))}

              {/* Distribución por categoría como torta */}
              {analytics.resumen_categorico.map((c) => (
                <div className="grafico" key={c.columna}>
                  <h3>{c.columna} — distribución (top {c.datos.length})</h3>
                  <ResponsiveContainer width="100%" height={280}>
                    <PieChart>
                      <Pie data={c.datos} dataKey="valor" nameKey="nombre"
                           cx="50%" cy="50%" outerRadius={95} label>
                        {c.datos.map((_, i) => (
                          <Cell key={i} fill={COLORS[i % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={{ background: "#1a1a1a", border: "1px solid #444" }} />
                      <Legend wrapperStyle={{ fontSize: 12 }} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              ))}
            </>
          )}

          {/* Vista de DOCUMENTO: preview del texto */}
          {contenido && (
            <>
              <p className="sub">{contenido.longitud.toLocaleString()} caracteres</p>
              <pre className="doc-preview">{contenido.preview}
                {contenido.longitud > contenido.preview.length ? "\n\n… (recortado)" : ""}
              </pre>
            </>
          )}
        </section>
      )}

      <section className="card">
        <h2>🛡️ Inspector de seguridad</h2>
        <p className="hint">
          Analiza los encabezados de seguridad de un sitio (usá sitios propios o autorizados).
        </p>
        <form onSubmit={escanearSeguridad} className="ia-form">
          <input
            type="text"
            placeholder="ejemplo.com"
            value={urlScan}
            onChange={(e) => setUrlScan(e.target.value)}
            disabled={escaneando}
          />
          <button type="submit" disabled={escaneando}>
            {escaneando ? "Escaneando…" : "Escanear"}
          </button>
        </form>

        {scan?.reporte?.error && (
          <div className="error" style={{ marginTop: "0.8rem" }}>
            {scan.reporte.error}
          </div>
        )}

        {scan?.reporte && !scan.reporte.error && (
          <div className="scan-resultado">
            <div className="scan-head">
              <span className="scan-url">{scan.reporte.url}</span>
              <span className={`scan-puntaje ${scan.reporte.puntaje >= 70 ? "ok" : scan.reporte.puntaje >= 40 ? "medio" : "malo"}`}>
                {scan.reporte.puntaje}/100
              </span>
            </div>
            <div className="scan-cols">
              <div>
                <h4>✅ Presentes ({scan.reporte.headers_presentes.length})</h4>
                <ul>
                  {scan.reporte.headers_presentes.map((h) => (
                    <li key={h.header}>{h.header}</li>
                  ))}
                </ul>
              </div>
              <div>
                <h4>⚠️ Faltantes ({scan.reporte.headers_faltantes.length})</h4>
                <ul>
                  {scan.reporte.headers_faltantes.map((h) => (
                    <li key={h.header} title={h.descripcion}>{h.header}</li>
                  ))}
                </ul>
              </div>
            </div>
            {scan.analisis && (
              <div className="ia-respuesta">
                {scan.analisis}
                <button className="btn-guardar" onClick={() => guardarConocimiento(scan.analisis)}>
                  💾 Guardar en base de conocimiento
                </button>
              </div>
            )}
          </div>
        )}
      </section>

      <section className="card">
        <h2>🧠 Base de conocimiento ({conocimiento.length})</h2>
        <p className="hint">Análisis que ShaddAI recordó de tus proyectos.</p>
        {conocimiento.length === 0 && (
          <p className="sub">Todavía no guardaste ningún análisis.</p>
        )}
        {conocimiento.map((k) => (
          <div className="conocimiento-item" key={k.id}>
            <div className="conocimiento-head">
              <strong>
                {k.tipo_archivo === "texto" ? "📄" : k.tipo_archivo === "tabla" ? "📊" : "🧠"}{" "}
                {k.titulo || "Análisis"}
              </strong>
              <button className="btn-borrar" onClick={() => borrarConocimiento(k.id)}>
                Eliminar
              </button>
            </div>
            <div className="conocimiento-cuerpo">{k.contenido}</div>
          </div>
        ))}
      </section>
    </div>
  );
}

export default App;
