import { useRef, useState } from "react";
import { analyzeImage } from "../services/api";
import type { ImageAnalysis } from "../types/image";

const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];
const MAX_BYTES = 10 * 1024 * 1024;

function BrandMark() {
  return <span className="brand-mark" aria-hidden="true"><i /><i /><i /><i /></span>;
}

function ImageWorkspace() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [result, setResult] = useState<ImageAnalysis | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function selectFile(next?: File) {
    setError("");
    setResult(null);
    if (!next) return;
    if (!ACCEPTED_TYPES.includes(next.type)) return setError("Choose a JPEG, PNG, or WebP image.");
    if (next.size > MAX_BYTES) return setError("The image must be 10 MB or smaller.");
    if (preview) URL.revokeObjectURL(preview);
    setFile(next);
    setPreview(URL.createObjectURL(next));
  }

  async function runAnalysis() {
    if (!file) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      setResult(await analyzeImage(file));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Analysis failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  function reset() {
    if (preview) URL.revokeObjectURL(preview);
    setFile(null); setPreview(null); setResult(null); setError("");
    if (inputRef.current) inputRef.current.value = "";
  }

  return <section className="workspace" aria-label="Image analysis workspace">
    <div className="section-heading">
      <div><p className="eyebrow">IMAGE ENGINE / 01</p><h2>See beyond the image.</h2>
        <p className="muted">Turn visual input into a structured understanding of the scene.</p></div>
      <span className="status"><i /> ENGINE INTERFACE</span>
    </div>
    <div className="workspace-grid">
      <article className="panel">
        <div className="panel-label"><span>01</span> INPUT IMAGE</div>
        <input ref={inputRef} className="hidden-input" type="file" accept="image/jpeg,image/png,image/webp"
          aria-label="Choose an image" onChange={e => selectFile(e.target.files?.[0])} />
        {preview ? <div className="preview"><img src={preview} alt="Selected image preview" />
          <button className="remove" onClick={reset} aria-label="Remove selected image">×</button></div> :
          <button className="dropzone" onClick={() => inputRef.current?.click()}>
            <span className="upload-symbol">↑</span><strong>Drop an image here</strong>
            <span className="muted">or click to browse files</span><small>JPG · PNG · WEBP · MAX 10 MB</small>
          </button>}
        {file && <div className="file-row"><span className="file-badge">IMG</span>
          <span className="file-name"><strong>{file.name}</strong><small>{(file.size / 1048576).toFixed(2)} MB</small></span>
          <span className="ready">READY</span></div>}
        <div className="panel-footer"><p className="privacy">◇ Images are not stored by this application.</p>
          <button className="primary" disabled={!file || loading} onClick={runAnalysis}>
            {loading ? <><span className="spinner" /> Analyzing…</> : <>Analyze image <span>↗</span></>}
          </button>
        </div>
      </article>
      <article className="panel result-panel" aria-live="polite">
        <div className="panel-label"><span>02</span> INTELLIGENCE REPORT {result && <b className="complete">COMPLETE</b>}</div>
        {!result && !loading && !error && <div className="empty-state">
          <div className="visual-orbit"><div>✳</div></div><h3>Your report starts here</h3>
          <p>Scene description and visible-object observations will appear here after analysis.</p>
          <div className="capabilities"><span>SCENE</span><span>OBJECTS</span><span>CONTEXT</span></div>
        </div>}
        {loading && <div className="empty-state"><span className="spinner big" /><h3>Reading the visual world</h3>
          <p>Analyzing scene details and visible objects. This may take a few seconds.</p></div>}
        {error && <div className="empty-state error" role="alert"><h3>Analysis could not complete</h3><p>{error}</p>
          <button className="secondary" disabled={!file || loading} onClick={runAnalysis}>Try again</button></div>}
        {result && <div className="report">
          <div className="report-section"><label>SCENE DESCRIPTION</label><p>{result.description}</p></div>
          <div className="report-section"><label>VISIBLE OBJECTS <span className="count">{result.objects.length}</span></label>
            <div className="chips">{result.objects.map((item, index) => <span key={`${item}-${index}`}>{item}</span>)}</div></div>
          <div className="meta"><span>PROVIDER <b>{result.provider}</b></span><span>MODEL <b>{result.model}</b></span></div>
          {result.caveats.map(c => <p className="caveat" key={c}>ⓘ {c}</p>)}
          <button className="secondary" onClick={reset}>Analyze another image</button>
        </div>}
      </article>
    </div>
    <p className="footnote">MAYACHITRAM INTELLIGENCE SYSTEMS <span>•</span> IMAGE ENGINE V1.0 <span>•</span> MODEL OUTPUTS MAY BE INACCURATE</p>
  </section>;
}

export default function App() {
  return <div className="app-shell">
    <header className="topbar"><a className="brand" href="/"><BrandMark /><strong>Maya<span>Chitram</span></strong>
      <i className="divider" /><small>INTELLIGENCE PLATFORM</small></a>
      <div className="top-actions"><span className="environment"><i /> V1.0 PREVIEW</span>
        <a className="api-docs" href="http://localhost:8000/docs" target="_blank" rel="noreferrer">API DOCS ↗</a></div>
    </header>
    <main>
      <section className="hero"><div className="hero-copy"><p className="eyebrow"><i /> ONE PLATFORM. MANY ENGINES.</p>
        <h1>Intelligence for<br /><span>the visual world.</span></h1>
        <p>MayaChitram turns visual input into structured understanding. The Image Engine is the first building block in a growing system of specialized AI engines.</p>
        <div className="metrics"><div><strong>01</strong><small>ACTIVE ENGINE</small></div><i /><div><strong>∞</strong><small>ROOM TO EXPAND</small></div></div>
      </div><div className="hero-art" aria-hidden="true"><div className="grid-lines" /><div className="ring ring-a" /><div className="ring ring-b" /><div className="ring ring-c" />
        <div className="scanline" /><div className="art-core"><BrandMark /><small>MC / 001</small></div>
        <small className="coordinate top-left">VISUAL<br />PERCEPTION</small><small className="coordinate bottom-right">IMAGE ENGINE<br />V1.0.0</small><b className="cross">+</b></div></section>
      <section className="engine-directory"><span className="directory-label">ENGINE DIRECTORY</span>
        <div className="engine active"><span className="engine-glyph">◈</span><span><b>Image Engine</b><small>ACTIVE · V1.0</small></span><span className="arrow">↗</span></div>
        <div className="engine planned"><span className="engine-glyph">◌</span><span><b>Similarity Engine</b><small>PLANNED</small></span></div>
        <div className="engine planned"><span className="engine-glyph">⌘</span><span><b>Future Engines</b><small>EXTENSIBLE</small></span></div>
      </section>
      <ImageWorkspace />
    </main>
    <footer><span className="footer-brand"><BrandMark /> MAYACHITRAM</span><span>BUILT FOR CLARITY. DESIGNED TO SCALE.</span><span>V1.0.0 <i>●</i> DEVELOPMENT</span></footer>
  </div>;
}
