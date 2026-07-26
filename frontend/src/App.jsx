import { useState, useEffect } from "react";
import "./App.css";

// URL del servicio core (FastAPI). En dev apunta al puerto 8001.
const CORE = "http://localhost:8001";

function App() {
  const [datasets, setDatasets] = useState([]);
  const [proyectos, setProyectos] = useState([]);
  const [subiendo, setSubiendo] = useState(false);
  const [error, setError] = useState("");
  const [ultimo, setUltimo] = useState(null);

  // Carga inicial de datos guardados
  useEffect(() => {
    cargar();
  }, []);

  async function cargar() {
    try {
      const [ds, ps] = await Promise.all([
        fetch(`${CORE}/datasets`).then((r) => r.json()),
        fetch(`${CORE}/proyectos`).then((r) => r.json()),
      ]);
      setDatasets(ds);
      setProyectos(ps);
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
      const res = await fetch(`${CORE}/datasets/upload`, {
        method: "POST",
        body: form,
      });
      if (!res.ok) throw new Error((await res.json()).detail || "Error");
      setUltimo(await res.json());
      await cargar();
    } catch (err) {
      setError("Error subiendo CSV: " + err.message);
    } finally {
      setSubiendo(false);
      e.target.value = "";
    }
  }

  return (
    <div className="app">
      <header>
        <h1>🧠 cerebrito</h1>
        <p>Base de conocimiento + análisis de datos</p>
      </header>

      {error && <div className="error">{error}</div>}

      <section className="card">
        <h2>Subir CSV</h2>
        <input type="file" accept=".csv" onChange={subirCsv} disabled={subiendo} />
        {subiendo && <span> Procesando…</span>}
        {ultimo && (
          <div className="preview">
            <strong>{ultimo.nombre_archivo}</strong> — {ultimo.filas} filas,{" "}
            {ultimo.columnas.length} columnas
            <div className="cols">{ultimo.columnas.join(", ")}</div>
          </div>
        )}
      </section>

      <section className="card">
        <h2>Datasets guardados ({datasets.length})</h2>
        <ul>
          {datasets.map((d) => (
            <li key={d.id}>
              {d.nombre_archivo} — {d.filas} filas
            </li>
          ))}
        </ul>
      </section>

      <section className="card">
        <h2>Proyectos / base de conocimiento ({proyectos.length})</h2>
        <ul>
          {proyectos.map((p) => (
            <li key={p.id}>
              <strong>{p.nombre}</strong> {p.tipo && `· ${p.tipo}`}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

export default App;
