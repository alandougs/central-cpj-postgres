# Leaflet 1.9.4 (cópia local)

Biblioteca de mapas usada pela aba Mapa (modo "Mapa real"). Servida localmente: a política de segurança da Central mantém `script-src 'self'`, sem CDN.

- Origem: pacote npm `leaflet@1.9.4` (https://leafletjs.com), arquivos de `dist/` e `LICENSE`, sem alteração.
- Licença: BSD-2-Clause (arquivo `LICENSE`).
- Integridade (SRI oficial da versão 1.9.4, conferida contra o download e contra o pacote npm):
  - `leaflet.js`  `sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=`
  - `leaflet.css` `sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=`
- Para atualizar: substituir os arquivos por uma versão nova do mesmo pacote e refazer a conferência de integridade.

Os tiles do mapa vêm de `tile.openstreetmap.org` (© OpenStreetMap contributors). Esse é o único host externo liberado, e só em `img-src` da política de segurança (`web_seguro.py`).
