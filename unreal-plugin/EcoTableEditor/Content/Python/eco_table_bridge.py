"""Eco Table Editor bridge.

Serves the UE DataTable Editor web app and a small JSON API that reads/writes
Aziel Ecosystem DataTables (species + ecosystem) directly in the open editor.

Inside Unreal (started from init_unreal.py):
    http://127.0.0.1:8765/            -> the editor web app
    GET  /api/ping
    GET  /api/tables?struct=species|ecosystem|all
    GET  /api/table?path=/Game/.../SDT_X
    POST /api/table      {path, csv, baseCsv?, force?}
    POST /api/regenerate {}
    GET  /api/selection
    GET  /api/hidden     -> {hidden: {table: {row: saved StemsPerHectare}}}  (species switched off)
    POST /api/hidden     {hidden}   stored in Saved/EcoTableEditor/hidden_species.json
    GET  /api/thumb?mesh=/Game/.../SM_X[&refresh=1]  -> PNG (rendered once via the editor's MCP
                                                       CaptureAssetImage, cached in Saved/EcoThumbs)

Outside Unreal (for testing the web app without the editor):
    python -I eco_table_bridge.py --mock <folder of DataTable CSVs> [--html <editor.html>]
"""
import base64
import json
import os
import queue
import re
import sys
import threading
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:
    import unreal  # noqa: F401
    IN_UNREAL = True
except ImportError:
    IN_UNREAL = False

HOST = '127.0.0.1'
PORT = 8765
SPECIES_STRUCT = '/AzielEcosystems/Assets/Data/ST_SpeciesDefinition.ST_SpeciesDefinition'
ECOSYSTEM_STRUCT = '/AzielEcosystems/Assets/Data/ST_EcosytemDefinition.ST_EcosytemDefinition'
SEARCH_ROOTS = ['/Game', '/AzielEcosystems']
# Aziel's event is "\u26a1\ud83d\udd04\ufe0fForceUpdate" (note U+FE0F after the arrows); keep the other spellings as fallbacks.
FORCE_UPDATE_EVENTS = ('\u26a1\U0001f504\ufe0fForceUpdate', '\u26a1\U0001f504ForceUpdate', 'ForceUpdate')
ALLOWED_ORIGINS = {'https://markleyboyer.github.io', 'http://127.0.0.1:%d' % PORT, 'http://localhost:%d' % PORT, 'null'}

_HERE = os.path.dirname(os.path.abspath(__file__))
HTML_CANDIDATES = [
    os.environ.get('ECO_EDITOR_HTML', ''),
    r'C:\Users\mail\projects\EcosystemEDTEditor\ue-datatable-editor.html',
    os.path.join(_HERE, '..', '..', 'Resources', 'ue-datatable-editor.html'),
]


def log(msg):
    if IN_UNREAL:
        unreal.log('[EcoTableBridge] ' + msg)
    else:
        print('[EcoTableBridge] ' + msg, flush=True)


def _norm(csv_text):
    return (csv_text or '').replace('\r\n', '\n').rstrip('\n')


# ─── Thumbnails (rendered by the editor's MCP server, cached as PNG files) ──

MCP_URL = os.environ.get('ECO_MCP_URL', 'http://127.0.0.1:8000/mcp')
THUMB_DIR = os.path.join(_HERE, '..', '..', '..', '..', 'Saved', 'EcoThumbs')  # <Project>/Saved/EcoThumbs


def _mesh_package(mesh):
    """'/Script/Engine.StaticMesh'/Game/X/SM_A.SM_A'' or '/Game/X/SM_A.SM_A' -> '/Game/X/SM_A'."""
    for m in re.finditer(r"(/[A-Za-z0-9_\-]+(?:/[^'\"./]+)+)", mesh or ''):
        if not m.group(1).startswith('/Script/'):
            return m.group(1)
    raise ValueError('Not an asset path: %r' % mesh)


class _McpThumbs:
    """Minimal MCP (streamable HTTP) client for EditorAppToolset.CaptureAssetImage.

    Must be called from an HTTP thread, never the game thread: the MCP server
    renders on the game thread and would deadlock waiting for itself."""

    def __init__(self):
        self.sid = None
        self.lock = threading.Lock()  # one render at a time; also guards the cache

    def _rpc(self, method, params=None, notify=False):
        body = {'jsonrpc': '2.0', 'method': method}
        if params is not None:
            body['params'] = params
        if not notify:
            body['id'] = 1
        h = {'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream'}
        if self.sid:
            h['Mcp-Session-Id'] = self.sid
        req = urllib.request.Request(MCP_URL, json.dumps(body).encode('utf-8'), h)
        with urllib.request.urlopen(req, timeout=60) as r:
            self.sid = r.headers.get('Mcp-Session-Id') or self.sid
            ctype = r.headers.get('Content-Type', '')
            raw = r.read().decode('utf-8')
        if notify:
            return None
        if 'event-stream' in ctype:  # take the last SSE data line
            raw = [ln[5:].strip() for ln in raw.splitlines() if ln.startswith('data:')][-1]
        res = json.loads(raw)
        if 'error' in res:
            raise RuntimeError('MCP %s: %s' % (method, res['error'].get('message')))
        return res['result']

    def _connect(self):
        self.sid = None
        self._rpc('initialize', {'protocolVersion': '2025-06-18', 'capabilities': {},
                                 'clientInfo': {'name': 'EcoTableBridge', 'version': '1.0'}})
        self._rpc('notifications/initialized', notify=True)

    def _capture(self, pkg):
        args = {'toolset_name': 'EditorToolset.EditorAppToolset', 'tool_name': 'CaptureAssetImage',
                'arguments': {'assetPath': pkg}}
        if not self.sid:
            self._connect()
        try:
            res = self._rpc('tools/call', {'name': 'call_tool', 'arguments': args})
        except urllib.error.HTTPError:  # stale session (editor/MCP restarted)
            self._connect()
            res = self._rpc('tools/call', {'name': 'call_tool', 'arguments': args})
        for c in res.get('content', []):
            if c.get('type') == 'image':
                return base64.b64decode(c['data'])
            if c.get('type') == 'text':
                try:
                    rv = json.loads(c['text']).get('returnValue') or {}
                except ValueError:
                    rv = {}
                if rv.get('data'):
                    return base64.b64decode(rv['data'])
                raise RuntimeError(c['text'][:300])
        raise RuntimeError('No image returned for ' + pkg)

    def get(self, mesh, refresh=False):
        pkg = _mesh_package(mesh)
        f = os.path.join(THUMB_DIR, pkg.strip('/').replace('/', '__') + '.png')
        with self.lock:
            if refresh or not os.path.isfile(f):
                # The first render only kicks off texture streaming (foliage comes out as grey,
                # unmasked cards), so render once to warm up, give streaming a moment, then keep the second.
                self._capture(pkg)
                time.sleep(0.75)
                png = self._capture(pkg)
                os.makedirs(THUMB_DIR, exist_ok=True)
                with open(f, 'wb') as fh:
                    fh.write(png)
            with open(f, 'rb') as fh:
                return fh.read()


_thumbs = _McpThumbs()


# ─── Backends ──────────────────────────────────────────────────────────────

class UnrealBackend:
    """All methods run on the game thread (see _GameThread)."""

    def info(self):
        return {'mode': 'unreal', 'project': unreal.Paths.get_base_filename(unreal.Paths.get_project_file_path()),
                'engine': unreal.SystemLibrary.get_engine_version()}

    def list_tables(self, kind):
        ar = unreal.AssetRegistryHelpers.get_asset_registry()
        flt = unreal.ARFilter(class_paths=[unreal.TopLevelAssetPath('/Script/Engine', 'DataTable')],
                              package_paths=SEARCH_ROOTS, recursive_paths=True)
        out = []
        for ad in ar.get_assets(flt):
            rs = str(ad.get_tag_value('RowStructure') or '')
            t = 'species' if rs == SPECIES_STRUCT else 'ecosystem' if rs == ECOSYSTEM_STRUCT else None
            if t is None or (kind not in ('all', t)):
                continue
            out.append({'path': str(ad.package_name), 'name': str(ad.asset_name), 'type': t})
        return sorted(out, key=lambda r: (r['type'], r['path']))

    def _load(self, path):
        dt = unreal.EditorAssetLibrary.load_asset(path)
        if not isinstance(dt, unreal.DataTable):
            raise ValueError('Not a DataTable: ' + path)
        return dt

    def read_csv(self, path):
        dt = self._load(path)
        r = unreal.DataTableFunctionLibrary.export_data_table_to_csv_string(dt)
        if isinstance(r, tuple):
            ok, csv = (r[0], r[1]) if len(r) > 1 else (True, r[0])
        elif isinstance(r, str):
            ok, csv = True, r
        else:
            ok, csv = bool(r), ''
        if not ok:
            raise RuntimeError('Export failed for ' + path)
        return csv

    def write_csv(self, path, csv):
        dt = self._load(path)
        if not unreal.DataTableFunctionLibrary.fill_data_table_from_csv_string(dt, csv):
            raise RuntimeError('FillDataTableFromCSVString failed (see Output Log) for ' + path)
        unreal.EditorAssetLibrary.save_loaded_asset(dt, False)
        return self.read_csv(path)

    def regenerate(self):
        eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        done = []
        for a in eas.get_all_level_actors():
            if a.get_class().get_name() != 'BP_Aziel_Ecosystem_C':
                continue
            fired, errors = None, []
            # The construction script rebuilds the cached plant lists from the DataTables
            # (ForceUpdate isn't reachable via call_method). Re-setting a property with
            # notify reruns it, exactly like editing the actor in the Details panel.
            try:
                eco = a.get_editor_property('EcosystemList')
                a.set_editor_property('EcosystemList', eco, unreal.PropertyAccessChangeNotifyMode.ALWAYS)
                fired = 'construction rerun'
            except Exception as e:
                errors.append('EcosystemList touch: %s' % e)
            for ev in FORCE_UPDATE_EVENTS if fired is None else ():
                try:
                    a.call_method(ev)
                    fired = ev
                    break
                except Exception as e:
                    errors.append('%r: %s' % (ev, e))
            # ForceUpdate disables runtime PCG, then re-enables and generates after a
            # DelayUntilNextFrame that never resumes in the editor world. Finish that half here.
            unreal.SystemLibrary.execute_console_command(None, 'pcg.RuntimeGeneration.Enable 1')
            gens = []
            for comp in a.get_components_by_class(unreal.PCGComponent):
                try:
                    if comp.get_editor_property('activated'):
                        comp.generate(True)
                        gens.append(comp.get_name())
                except Exception as e:
                    errors.append('%s.generate: %s' % (comp.get_name(), e))
            log('Regenerate %s: event=%s generated=%s%s' % (
                a.get_actor_label(), fired, gens, (' errors=' + '; '.join(errors)) if errors else ''))
            done.append({'actor': a.get_actor_label(), 'event': fired, 'generated': gens, 'errors': errors})
        return done

    def selection(self):
        out = []
        for a in unreal.EditorUtilityLibrary.get_selected_assets():
            if isinstance(a, unreal.DataTable):
                out.append(a.get_path_name().split('.')[0])
        return out


class MockBackend:
    """Serves a folder of CSVs as if they were DataTables (path = /Mock/<name>)."""

    def __init__(self, folder):
        self.folder = os.path.abspath(folder)

    def info(self):
        return {'mode': 'mock', 'project': 'mock:' + self.folder, 'engine': 'none'}

    def _file(self, path):
        name = path.rstrip('/').split('/')[-1]
        f = os.path.join(self.folder, name + '.csv')
        if not os.path.isfile(f):
            raise ValueError('No such table: ' + path)
        return f

    def list_tables(self, kind):
        out = []
        for fn in sorted(os.listdir(self.folder)):
            if not fn.lower().endswith('.csv'):
                continue
            with open(os.path.join(self.folder, fn), encoding='utf-8-sig') as fh:
                head = fh.readline()
            t = 'species' if 'MeshVariants' in head else 'ecosystem' if 'SpeciesList' in head else None
            if t and kind in ('all', t):
                out.append({'path': '/Mock/' + fn[:-4], 'name': fn[:-4], 'type': t})
        return out

    def read_csv(self, path):
        with open(self._file(path), encoding='utf-8-sig', newline='') as fh:
            return fh.read()

    def write_csv(self, path, csv):
        with open(self._file(path), 'w', encoding='utf-8', newline='') as fh:
            fh.write(csv)
        return self.read_csv(path)

    def regenerate(self):
        return [{'actor': 'mock', 'event': 'none'}]

    def selection(self):
        return []


# ─── Game-thread marshalling (Unreal API must run on the game thread) ──────

class _GameThread:
    def __init__(self):
        self.jobs = queue.Queue()
        self.handle = None

    def install(self):
        if IN_UNREAL and self.handle is None:
            self.handle = unreal.register_slate_post_tick_callback(self._tick)

    def uninstall(self):
        if IN_UNREAL and self.handle is not None:
            unreal.unregister_slate_post_tick_callback(self.handle)
            self.handle = None

    def _tick(self, _dt):
        while True:
            try:
                fn, args, box, ev = self.jobs.get_nowait()
            except queue.Empty:
                return
            try:
                box['r'] = fn(*args)
            except Exception as e:  # report to the HTTP thread
                box['e'] = e
                box['tb'] = traceback.format_exc()
            ev.set()

    def call(self, fn, *args, timeout=60):
        if not IN_UNREAL:
            return fn(*args)
        box, ev = {}, threading.Event()
        self.jobs.put((fn, args, box, ev))
        if not ev.wait(timeout):
            raise TimeoutError('Unreal did not respond (is the editor busy or minimised?)')
        if 'e' in box:
            log(box.get('tb', ''))
            raise box['e']
        return box['r']


_gt = _GameThread()
_backend = None
_server = None


# ─── HTTP layer ────────────────────────────────────────────────────────────

class _Handler(BaseHTTPRequestHandler):
    server_version = 'EcoTableBridge/1.0'

    def log_message(self, fmt, *args):  # keep the Output Log quiet
        pass

    def _cors(self):
        origin = self.headers.get('Origin')
        if origin in ALLOWED_ORIGINS:
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Vary', 'Origin')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Private-Network', 'true')

    def _send(self, code, body, ctype='application/json; charset=utf-8', cache='no-store'):
        data = body if isinstance(body, bytes) else json.dumps(body).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', cache)
        self._cors()
        self.end_headers()
        self.wfile.write(data)

    def _origin_ok(self):
        origin = self.headers.get('Origin')
        return origin is None or origin in ALLOWED_ORIGINS

    def do_OPTIONS(self):
        self.send_response(204 if self._origin_ok() else 403)
        self._cors()
        self.end_headers()

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        try:
            if u.path in ('/', '/index.html', '/ue-datatable-editor.html'):
                for p in HTML_CANDIDATES:
                    if p and os.path.isfile(p):
                        with open(p, 'rb') as fh:
                            return self._send(200, fh.read(), 'text/html; charset=utf-8')
                return self._send(404, {'error': 'editor HTML not found', 'searched': HTML_CANDIDATES})
            if not self._origin_ok():
                return self._send(403, {'error': 'origin not allowed'})
            if u.path == '/api/ping':
                return self._send(200, dict(_gt.call(_backend.info), ok=True))
            if u.path == '/api/tables':
                kind = (q.get('struct') or ['all'])[0]
                return self._send(200, {'tables': _gt.call(_backend.list_tables, kind)})
            if u.path == '/api/table':
                path = (q.get('path') or [''])[0]
                return self._send(200, {'path': path, 'csv': _gt.call(_backend.read_csv, path)})
            if u.path == '/api/selection':
                return self._send(200, {'paths': _gt.call(_backend.selection)})
            if u.path == '/api/hidden':
                return self._send(200, {'hidden': _hidden.read()})
            if u.path == '/api/thumb':  # runs on this HTTP thread, not the game thread (see _McpThumbs)
                mesh = (q.get('mesh') or [''])[0]
                png = _thumbs.get(mesh, refresh=(q.get('refresh') or [''])[0] == '1')
                return self._send(200, png, 'image/png', 'max-age=86400')
            return self._send(404, {'error': 'not found'})
        except Exception as e:
            return self._send(500, {'error': str(e)})

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        if not self._origin_ok():
            return self._send(403, {'error': 'origin not allowed'})
        try:
            n = int(self.headers.get('Content-Length') or 0)
            body = json.loads(self.rfile.read(n) or b'{}')
            if u.path == '/api/table':
                path, csv = body['path'], body['csv']
                if not body.get('force') and body.get('baseCsv') is not None:
                    current = _gt.call(_backend.read_csv, path)
                    if _norm(current) != _norm(body['baseCsv']):
                        return self._send(409, {'error': 'conflict', 'csv': current})
                return self._send(200, {'path': path, 'csv': _gt.call(_backend.write_csv, path, csv)})
            if u.path == '/api/regenerate':
                return self._send(200, {'regenerated': _gt.call(_backend.regenerate)})
            if u.path == '/api/hidden':
                return self._send(200, {'hidden': _hidden.write(body.get('hidden') or {})})
            return self._send(404, {'error': 'not found'})
        except Exception as e:
            return self._send(500, {'error': str(e)})


class _HiddenStore:
    """Species rows switched off in the web editor: {table: {row: saved StemsPerHectare}}.
    Plain file I/O, so it runs on the HTTP thread."""

    def __init__(self):
        self.path = None
        self.lock = threading.Lock()

    def read(self):
        with self.lock:
            if not self.path or not os.path.isfile(self.path):
                return {}
            with open(self.path, encoding='utf-8') as fh:
                return json.load(fh)

    def write(self, hidden):
        clean = {t: {r: str(v) for r, v in rows.items()} for t, rows in hidden.items() if rows}
        with self.lock:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, 'w', encoding='utf-8') as fh:
                json.dump(clean, fh, indent=1, sort_keys=True)
        return clean


_hidden = _HiddenStore()


def start(backend=None, port=PORT):
    """Start the server (idempotent). Called from init_unreal.py inside the editor."""
    global _backend, _server
    if _server is not None:
        return _server
    _backend = backend or (UnrealBackend() if IN_UNREAL else None)
    if _backend is None:
        raise RuntimeError('No backend: run inside Unreal or pass --mock <folder>')
    saved = unreal.Paths.project_saved_dir() if IN_UNREAL else getattr(_backend, 'folder', _HERE)
    _hidden.path = os.path.join(os.path.abspath(saved), 'EcoTableEditor', 'hidden_species.json')
    _gt.install()
    try:
        _server = ThreadingHTTPServer((HOST, port), _Handler)
    except OSError as e:
        log('Could not bind %s:%d (%s). Is another editor already serving it?' % (HOST, port, e))
        _gt.uninstall()
        return None
    _server.daemon_threads = True
    threading.Thread(target=_server.serve_forever, name='EcoTableBridge', daemon=True).start()
    log('Serving http://%s:%d/ (%s mode)' % (HOST, port, 'unreal' if IN_UNREAL else 'mock'))
    return _server


def stop():
    global _server
    if _server is not None:
        _server.shutdown()
        _server.server_close()
        _server = None
    _gt.uninstall()
    log('Stopped')


if __name__ == '__main__' and not IN_UNREAL:
    import argparse
    ap = argparse.ArgumentParser(description='Eco Table Editor bridge (mock mode)')
    ap.add_argument('--mock', required=True, help='folder of DataTable CSV files')
    ap.add_argument('--html', help='path to ue-datatable-editor.html')
    ap.add_argument('--port', type=int, default=PORT)
    a = ap.parse_args()
    if a.html:
        HTML_CANDIDATES.insert(0, a.html)
    ALLOWED_ORIGINS.add('http://127.0.0.1:%d' % a.port)
    start(MockBackend(a.mock), a.port)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        stop()
        sys.exit(0)
