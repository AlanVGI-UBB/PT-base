CREATE TABLE IF NOT EXISTS curso (
    id INTEGER PRIMARY KEY,
    cod_ramo TEXT NOT NULL,
    nombre TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS termino (
    id INTEGER PRIMARY KEY,
    curso_id INTEGER NOT NULL REFERENCES curso(id),
    texto_visible TEXT NOT NULL,
    formas_json TEXT NOT NULL,
    bloqueos_json TEXT NOT NULL DEFAULT '[]',
    video_url TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'ensayo' CHECK (estado IN ('ensayo', 'publicado', 'retirado'))
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

CREATE TABLE IF NOT EXISTS usuario (
    rut TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    nombre TEXT NOT NULL,
    apellido TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inscripcion (
    rut TEXT NOT NULL REFERENCES usuario(rut),
    curso_id INTEGER NOT NULL REFERENCES curso(id),
    seccion TEXT NOT NULL,
    PRIMARY KEY (rut, curso_id, seccion)
);

CREATE TABLE IF NOT EXISTS clase (
    id INTEGER PRIMARY KEY,
    room_id TEXT NOT NULL,
    curso_id INTEGER NOT NULL REFERENCES curso(id),
    seccion TEXT NOT NULL,
    rut_emisor TEXT NOT NULL REFERENCES usuario(rut),
    fecha_inicio TEXT NOT NULL,
    fecha_fin TEXT,
    duracion_ms INTEGER DEFAULT 0,
    titulo TEXT
);

CREATE TABLE IF NOT EXISTS evento_clase (
    id INTEGER PRIMARY KEY,
    clase_id INTEGER NOT NULL REFERENCES clase(id),
    timestamp_ms INTEGER NOT NULL,
    texto TEXT,
    estable INTEGER DEFAULT 0,
    senas_json TEXT,
    abstenciones_json TEXT
);
