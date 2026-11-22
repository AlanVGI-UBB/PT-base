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
    puede_capturar INTEGER NOT NULL DEFAULT 0,
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
    titulo TEXT,
    cierre TEXT,
    condiciones_confirmadas INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS evento_clase (
    id INTEGER PRIMARY KEY,
    clase_id INTEGER NOT NULL REFERENCES clase(id),
    timestamp_ms INTEGER NOT NULL,
    texto TEXT,
    estable INTEGER DEFAULT 0,
    senas_json TEXT,
    abstenciones_json TEXT,
    tipo TEXT NOT NULL DEFAULT 'segmento'
);

CREATE TABLE IF NOT EXISTS metrica_segmento (
    id INTEGER PRIMARY KEY,
    clase_id INTEGER NOT NULL REFERENCES clase(id),
    segmento_id INTEGER NOT NULL,
    audio_inicio_ms INTEGER NOT NULL,
    audio_fin_ms INTEGER NOT NULL,
    llegada_fin_ms INTEGER NOT NULL,
    asr_ms INTEGER NOT NULL,
    nlp_ms INTEGER NOT NULL,
    emitido_ms INTEGER NOT NULL,
    receptores INTEGER NOT NULL
);
