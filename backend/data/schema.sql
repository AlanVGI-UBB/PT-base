CREATE TABLE IF NOT EXISTS curso (
    id INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS termino (
    id INTEGER PRIMARY KEY,
    curso_id INTEGER NOT NULL REFERENCES curso(id),
    lema TEXT NOT NULL,
    texto_visible TEXT NOT NULL,
    video_url TEXT NOT NULL,
    n_palabras INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS sesion (
    id INTEGER PRIMARY KEY,
    curso_id INTEGER NOT NULL REFERENCES curso(id),
    inicio TEXT NOT NULL,
    fin TEXT
);

CREATE TABLE IF NOT EXISTS segmento (
    id INTEGER PRIMARY KEY,
    sesion_id INTEGER NOT NULL REFERENCES sesion(id),
    texto TEXT,
    recibido_at TEXT,
    emitido_at TEXT,
    estable INTEGER DEFAULT 0,
    senas_json TEXT
);