-- 📦 go-file schema
CREATE TABLE files(id INTEGER PRIMARY KEY, name TEXT, size INTEGER, sha256 TEXT UNIQUE, storage TEXT DEFAULT 'local', path TEXT, created_at DATETIME);
CREATE TABLE share_links(id INTEGER PRIMARY KEY, file_id INTEGER REFERENCES files(id), token TEXT UNIQUE, password_hash TEXT, expires_at DATETIME, max_downloads INTEGER, downloads INTEGER DEFAULT 0, created_at DATETIME);
CREATE TABLE download_logs(id INTEGER PRIMARY KEY, link_id INTEGER REFERENCES share_links(id), ip TEXT, at DATETIME);
