import { useState, useEffect } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";
import "./App.css";

// URL del servicio core (FastAPI).
const CORE = "http://localhost:8001";

function App() {
  const [datasets, setDatasets] = useState([]);
  const [subiendo, setSubiendo] = useState(false);
  const [error, setError] = useState("");
  const [analytics, setAnalytics] = useState(null);
  const [datasetActivo, setDatasetActivo] = useState(null);
  const [insights, setInsights] = useState("");
  const [pensando, setPensando] = useState(false);
  const [pregunta, setPregunta] = useState("");
  const [respuesta, setRespuesta] = useState("");

  useEffect(() => {
    cargar();
  }, []);

  async function cargar() {
    try {
      const ds = await fetch(`${CORE}/datasets`).then((r) => r.json());
      setDatasets(ds);
      setError("");
    } catch {
      setError("No se pudo conectar con el servicio core (¿está corriendo en :8001?)");
    }
  }

  async function subirCsv(e) {
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
      await verAnalytics(nuevo.id); // grafica automáticamente el recién subido
    } catch (err) {
      setError("Error subiendo CSV: " + err.message);
    } finally {
      setSubiendo(false);
      e.target.value = "";
    }
  }

  async function verAnalytics(id) {
    setDatasetActivo(id);
    setAnalytics(null);
    setInsights("");
    setRespuesta("");
    try {
      const a = await fetch(`${CORE}/datasets/${id}/analytics`).then((r) => r.json());
      setAnalytics(a);
    } catch {
      setError("No se pudo analizar el dataset.");
    }
  }

  async function pedirInsights() {
    setPensando(true);
    setInsights("");
    try {
      const r = await fetch(`${CORE}/datasets/${datasetActivo}/insights`).then((r) => r.json());
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
      const r = await fetch(`${CORE}/datasets/${datasetActivo}/ask`, {
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
        <p>Sube tus datos · obtén análisis visual para decidir</p>
      </header>

      {error && <div className="error">{error}</div>}

      <section className="card">
        <h2>Subir CSV</h2>
        <input type="file" accept=".csv" onChange={subirCsv} disabled={subiendo} />
        {subiendo && <span> Procesando y analizando…</span>}
      </section>

      <section className="card">
        <h2>Datasets guardados ({datasets.length})</h2>
        <ul className="lista-datasets">
          {datasets.map((d) => (
            <li key={d.id}>
              <span>{d.nombre_archivo} — {d.filas} filas</span>
              <button onClick={() => verAnalytics(d.id)}>Analizar</button>
            </li>
          ))}
        </ul>
      </section>

      {analytics && (
        <section className="card">
          <h2>Análisis del dataset #{datasetActivo}</h2>
          <p className="sub">
            {analytics.filas} filas · {analytics.columnas.length} columnas
          </p>

          {/* Razonamiento de ShaddAI */}
          <div className="ia">
            <button className="btn-ia" onClick={pedirInsights} disabled={pensando}>
              🧠 {pensando ? "ShaddAI está pensando…" : "Pedir análisis a ShaddAI"}
            </button>
            {insights && <div className="ia-respuesta">{insights}</div>}

            <form onSubmit={preguntar} className="ia-form">
              <input
                type="text"
                placeholder="Pregúntale a ShaddAI sobre estos datos…"
                value={pregunta}
                onChange={(e) => setPregunta(e.target.value)}
                disabled={pensando}
              />
              <button type="submit" disabled={pensando}>Preguntar</button>
            </form>
            {respuesta && <div className="ia-respuesta">{respuesta}</div>}
          </div>

          {/* Tarjetas de resumen numérico */}
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

          {/* Gráficos de barras por columna categórica */}
          {analytics.resumen_categorico.map((c) => (
            <div className="grafico" key={c.columna}>
              <h3>{c.columna} (top {c.datos.length})</h3>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={c.datos}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                  <XAxis dataKey="nombre" tick={{ fill: "#aaa", fontSize: 12 }} />
                  <YAxis tick={{ fill: "#aaa", fontSize: 12 }} />
                  <Tooltip contentStyle={{ background: "#1a1a1a", border: "1px solid #444" }} />
                  <Bar dataKey="valor" fill="#6c8cff" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ))}

          {analytics.resumen_numerico.length === 0 &&
            analytics.resumen_categorico.length === 0 && (
              <p>No se detectaron columnas analizables en este CSV.</p>
            )}
        </section>
      )}
    </div>
  );
}

export default App;
