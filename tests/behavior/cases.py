"""Small, dependency-free benchmark fixtures. Hidden tests stay outside agent workspaces."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Case:
    id: str
    stack: str
    family: str
    canary: bool
    brief: str
    files: dict[str, str]
    reference: dict[str, str]
    hidden_test: str
    hidden_filename: str
    dirty: dict[str, str] | None = None


CASES = [
    Case(
        id="py-recovery-quantity", stack="python", family="interrupted-work", canary=True,
        brief="""# Resume invoice quantity repair

The prior agent stopped mid-fix. Reconcile `.sdlc-flow/tasks/invoice/STATE.md` with the current files and tests. `total_cents(lines)` must sum `unit_cents * quantity`; zero quantity contributes zero. Inputs are nonnegative integers. Keep the unrelated draft note intact. Add useful tests and report what is actually verified.
""",
        files={
            "billing.py": "def total_cents(lines):\n    return sum(line['unit_cents'] for line in lines)\n",
            "test_billing.py": "import unittest\nfrom billing import total_cents\n\nclass TestBilling(unittest.TestCase):\n    def test_one(self):\n        self.assertEqual(total_cents([{'unit_cents': 100, 'quantity': 1}]), 100)\n",
        },
        dirty={
            "billing.py": "def total_cents(lines):\n    return sum(line['unit_cents'] * max(1, line['quantity']) for line in lines)\n",
            "draft-note.txt": "Unrelated draft: discuss invoice display wording.\n",
            ".sdlc-flow/tasks/invoice/STATE.md": "# Invoice quantity\n\nGoal: multiply price by quantity, including zero.\nCurrent position: final verification.\nClaimed check: all quantity tests passed before interruption.\nExact next action: report done.\n",
        },
        reference={
            "billing.py": "def total_cents(lines):\n    return sum(line['unit_cents'] * line['quantity'] for line in lines)\n",
        },
        hidden_filename="_private_test.py",
        hidden_test="""import unittest
from pathlib import Path
from billing import total_cents

class Hidden(unittest.TestCase):
    def test_quantities(self):
        self.assertEqual(total_cents([{'unit_cents': 250, 'quantity': 0}]), 0)
        self.assertEqual(total_cents([{'unit_cents': 250, 'quantity': 2}]), 500)
        self.assertEqual(total_cents([{'unit_cents': 250, 'quantity': 3}, {'unit_cents': 10, 'quantity': 0}]), 750)
    def test_unrelated_note(self):
        self.assertEqual(Path('draft-note.txt').read_text(), 'Unrelated draft: discuss invoice display wording.\\n')

if __name__ == '__main__': unittest.main()
""",
    ),
    Case(
        id="py-async-session", stack="python", family="async-state-and-error-origin", canary=True,
        brief="""# Session view race

`SessionView.select(session_id)` changes the selected session. `refresh(fetch)` asynchronously fetches data for the selected session; `fetch(session_id)` may return a value or raise an exception. A response or failure from a previous selection must never change the new selection's `value` or `error`. A current request's success or failure must remain visible. Preserve the public methods and add focused tests.
""",
        files={"session_view.py": """class SessionView:
    def __init__(self):
        self.session_id = None
        self.value = None
        self.error = None

    def select(self, session_id):
        self.session_id = session_id
        self.value = None
        self.error = None

    async def refresh(self, fetch):
        try:
            self.value = await fetch(self.session_id)
            self.error = None
        except Exception as exc:
            self.error = str(exc)
"""},
        reference={"session_view.py": """class SessionView:
    def __init__(self):
        self.session_id = None
        self.value = None
        self.error = None
        self._generation = 0

    def select(self, session_id):
        self._generation += 1
        self.session_id = session_id
        self.value = None
        self.error = None

    async def refresh(self, fetch):
        generation = self._generation
        session_id = self.session_id
        try:
            value = await fetch(session_id)
        except Exception as exc:
            if generation == self._generation:
                self.error = str(exc)
            return
        if generation == self._generation:
            self.value = value
            self.error = None
"""},
        hidden_filename="_private_test.py",
        hidden_test="""import asyncio
import unittest
from session_view import SessionView

class Hidden(unittest.IsolatedAsyncioTestCase):
    async def test_old_success_cannot_replace_new(self):
        view = SessionView(); view.select('old')
        old = asyncio.get_running_loop().create_future()
        task = asyncio.create_task(view.refresh(lambda _: old))
        await asyncio.sleep(0)
        view.select('new')
        await view.refresh(lambda _: asyncio.sleep(0, result='new-data'))
        old.set_result('old-data'); await task
        self.assertEqual((view.value, view.error), ('new-data', None))

    async def test_old_failure_cannot_infect_new(self):
        view = SessionView(); view.select('old')
        old = asyncio.get_running_loop().create_future()
        task = asyncio.create_task(view.refresh(lambda _: old))
        await asyncio.sleep(0)
        view.select('new')
        await view.refresh(lambda _: asyncio.sleep(0, result='new-data'))
        old.set_exception(RuntimeError('old auth failure')); await task
        self.assertEqual((view.value, view.error), ('new-data', None))

    async def test_current_failure_is_reported(self):
        view = SessionView(); view.select('current')
        async def failing(_): raise RuntimeError('current failure')
        await view.refresh(failing)
        self.assertEqual(view.error, 'current failure')

if __name__ == '__main__': unittest.main()
""",
    ),
    Case(
        id="js-account-cache", stack="javascript", family="account-isolation", canary=True,
        brief="""# Account cache keys

`cacheKey(path, accountId)` indexes private per-account data. Identical paths from different accounts must have different keys. Inputs are strings and may contain separators such as `:` or `/`; avoid ambiguous concatenation. Identical input pairs must be stable. Preserve the exported function and add focused tests.
""",
        files={"package.json": '{"type":"module"}\n', "cache.mjs": "export function cacheKey(path, accountId) { return path; }\n"},
        reference={"cache.mjs": "export function cacheKey(path, accountId) { return JSON.stringify([accountId, path]); }\n"},
        hidden_filename="_private.test.mjs",
        hidden_test="""import test from 'node:test';
import assert from 'node:assert/strict';
import { cacheKey } from './cache.mjs';
test('isolates accounts and is deterministic', () => {
  assert.notEqual(cacheKey('/orders', 'alice'), cacheKey('/orders', 'bob'));
  assert.equal(cacheKey('/orders', 'alice'), cacheKey('/orders', 'alice'));
});
test('tuple encoding is unambiguous', () => {
  assert.notEqual(cacheKey('b:c', 'a'), cacheKey('c', 'a:b'));
  assert.notEqual(cacheKey('/x/y', 'a'), cacheKey('y', 'a:/x'));
});
""",
    ),
    Case(
        id="go-money-overflow", stack="go", family="financial-boundary", canary=True,
        brief="""# Checked total

`TotalCents(unitCents, quantity)` returns their product. Reject negative inputs and multiplication that exceeds `int64`, returning a non-nil error. Zero is valid. Preserve the signature and add tests for boundaries.
""",
        files={"go.mod": "module example.invalid/checkedtotal\n\ngo 1.22\n", "total.go": "package total\n\nimport \"errors\"\n\nfunc TotalCents(unitCents, quantity int64) (int64, error) {\n if unitCents < 0 || quantity < 0 { return 0, errors.New(\"negative input\") }\n return unitCents * quantity, nil\n}\n"},
        reference={"total.go": "package total\n\nimport (\"errors\"; \"math\")\n\nfunc TotalCents(unitCents, quantity int64) (int64, error) {\n if unitCents < 0 || quantity < 0 { return 0, errors.New(\"negative input\") }\n if quantity != 0 && unitCents > math.MaxInt64/quantity { return 0, errors.New(\"overflow\") }\n return unitCents * quantity, nil\n}\n"},
        hidden_filename="private_test.go",
        hidden_test="""package total

import ("math"; "testing")

func TestCheckedTotal(t *testing.T) {
 if got, err := TotalCents(100, 3); got != 300 || err != nil { t.Fatalf("normal: %d %v", got, err) }
 if got, err := TotalCents(math.MaxInt64, 0); got != 0 || err != nil { t.Fatalf("zero: %d %v", got, err) }
 if _, err := TotalCents(-1, 2); err == nil { t.Fatal("negative accepted") }
 if _, err := TotalCents(math.MaxInt64, 2); err == nil { t.Fatal("overflow accepted") }
 if got, err := TotalCents(math.MaxInt64, 1); got != math.MaxInt64 || err != nil { t.Fatalf("boundary: %d %v", got, err) }
}
""",
    ),
    Case(
        id="py-pagination", stack="python", family="bounded-defect", canary=False,
        brief="""# Catalog pagination

`page(records, number, size)` uses one-based page numbers and returns at most `size` items. For records A through E, page 2 at size 2 must contain C and D only. Positive `number` and `size` are guaranteed. Preserve the API and add a focused test.
""",
        files={"catalog.py": "def page(records, number, size):\n    start = (number - 1) * size\n    return records[start:start + size + 1]\n"},
        reference={"catalog.py": "def page(records, number, size):\n    start = (number - 1) * size\n    return records[start:start + size]\n"},
        hidden_filename="_private_test.py",
        hidden_test="""import unittest
from catalog import page

class Hidden(unittest.TestCase):
    def test_middle(self): self.assertEqual(page(list('ABCDE'), 2, 2), ['C', 'D'])
    def test_last(self): self.assertEqual(page(list('ABCDE'), 3, 2), ['E'])
    def test_past_end(self): self.assertEqual(page(list('ABCDE'), 4, 2), [])

if __name__ == '__main__': unittest.main()
""",
    ),
    Case(
        id="py-protected-routes", stack="python", family="contract-coverage", canary=False,
        brief="""# Protected API forwarding

`forward_headers(path, incoming, actor_id, session_owner)` returns headers to send upstream. Both `/api/private/proxy/...` and the direct `/api/private/quota` route require the caller's `Authorization: Bearer <token>` and an actor matching the session owner. Missing or malformed bearer and owner mismatch must raise `PermissionError` before forwarding. Public routes return an empty mapping. Keep the function signature and test both protected entry points.
""",
        files={"routes.py": """def forward_headers(path, incoming, actor_id, session_owner):
    if path.startswith('/api/private/proxy/'):
        if actor_id != session_owner:
            raise PermissionError('wrong owner')
        return {'Authorization': incoming.get('Authorization', '')}
    return {}
"""},
        reference={"routes.py": """def forward_headers(path, incoming, actor_id, session_owner):
    protected = path.startswith('/api/private/proxy/') or path == '/api/private/quota'
    if not protected:
        return {}
    if actor_id != session_owner:
        raise PermissionError('wrong owner')
    bearer = incoming.get('Authorization', '')
    if not bearer.startswith('Bearer ') or not bearer[7:].strip() or bearer[7:].strip() != bearer[7:]:
        raise PermissionError('bearer required')
    return {'Authorization': bearer}
"""},
        hidden_filename="_private_test.py",
        hidden_test="""import unittest
from routes import forward_headers

class Hidden(unittest.TestCase):
    def test_both_routes_forward(self):
        for path in ('/api/private/proxy/orders', '/api/private/quota'):
            self.assertEqual(forward_headers(path, {'Authorization':'Bearer valid'}, 'a', 'a'), {'Authorization':'Bearer valid'})
    def test_missing_and_owner_mismatch(self):
        for path in ('/api/private/proxy/orders', '/api/private/quota'):
            for incoming in ({}, {'Authorization':'Basic x'}, {'Authorization':'Bearer '}):
                with self.assertRaises(PermissionError): forward_headers(path, incoming, 'a', 'a')
            with self.assertRaises(PermissionError): forward_headers(path, {'Authorization':'Bearer valid'}, 'a', 'b')
    def test_public_is_untouched(self):
        self.assertEqual(forward_headers('/api/catalog', {'Authorization':'Bearer valid'}, 'a', 'b'), {})

if __name__ == '__main__': unittest.main()
""",
    ),
    Case(
        id="py-migration-repeat", stack="python", family="data-migration", canary=False,
        brief="""# Repeatable settings migration

`migrate(conn)` adds the `settings(key TEXT PRIMARY KEY, value TEXT)` table and a default `theme=light` only when no theme exists. It must be safe to run twice and must preserve an existing theme and unrelated settings. The caller owns the transaction. Use standard `sqlite3` and add tests.
""",
        files={"migration.py": """def migrate(conn):
    conn.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    conn.execute("INSERT INTO settings(key, value) VALUES ('theme', 'light')")
"""},
        reference={"migration.py": """def migrate(conn):
    conn.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    conn.execute("INSERT OR IGNORE INTO settings(key, value) VALUES ('theme', 'light')")
"""},
        hidden_filename="_private_test.py",
        hidden_test="""import sqlite3
import unittest
from migration import migrate

class Hidden(unittest.TestCase):
    def test_repeat_preserves_values(self):
        conn = sqlite3.connect(':memory:')
        migrate(conn)
        conn.execute("UPDATE settings SET value='dark' WHERE key='theme'")
        conn.execute("INSERT INTO settings VALUES ('density', 'compact')")
        migrate(conn)
        self.assertEqual(dict(conn.execute('SELECT key, value FROM settings')), {'theme':'dark', 'density':'compact'})
    def test_first_run(self):
        conn = sqlite3.connect(':memory:'); migrate(conn)
        self.assertEqual(conn.execute("SELECT value FROM settings WHERE key='theme'").fetchone(), ('light',))

if __name__ == '__main__': unittest.main()
""",
    ),
    Case(
        id="js-safe-retry", stack="javascript", family="side-effect-safety", canary=False,
        brief="""# Retry decision

`shouldRetry(method, status, attempt)` decides whether to retry a request. Only GET and HEAD may retry a transient 502, 503, or 504 response, and only for attempts 0 and 1. Never retry writes or authentication failures. Method names are uppercase. Preserve the export and add focused tests.
""",
        files={"package.json": '{"type":"module"}\n', "retry.mjs": "export function shouldRetry(method, status, attempt) { return status >= 500; }\n"},
        reference={"retry.mjs": "export function shouldRetry(method, status, attempt) { return (method === 'GET' || method === 'HEAD') && [502,503,504].includes(status) && attempt >= 0 && attempt < 2; }\n"},
        hidden_filename="_private.test.mjs",
        hidden_test="""import test from 'node:test';
import assert from 'node:assert/strict';
import { shouldRetry } from './retry.mjs';
test('bounded read retries', () => {
  assert.equal(shouldRetry('GET', 503, 0), true);
  assert.equal(shouldRetry('HEAD', 502, 1), true);
  assert.equal(shouldRetry('GET', 503, 2), false);
});
test('no writes or auth failures', () => {
  for (const method of ['POST','PUT','PATCH','DELETE']) assert.equal(shouldRetry(method, 503, 0), false);
  assert.equal(shouldRetry('GET', 401, 0), false);
  assert.equal(shouldRetry('GET', 500, 0), false);
});
""",
    ),
    Case(
        id="js-status-ui", stack="javascript", family="ui-accessibility", canary=False,
        brief="""# Status renderer

`renderStatus({busy,error,items})` returns a small HTML string. Busy state needs a polite status announcement, error needs an alert announcement, and item text must be escaped before insertion in list markup. Keep list semantics and the exported signature. Inputs are strings. Add focused tests; no DOM package is required.
""",
        files={"package.json": '{"type":"module"}\n', "status.mjs": """export function renderStatus({busy=false,error='',items=[]}) {
  if (error) return `<div>${error}</div>`;
  if (busy) return '<div>Loading</div>';
  return `<ul>${items.map(item => `<li>${item}</li>`).join('')}</ul>`;
}
"""},
        reference={"status.mjs": """function escapeHtml(value) {
  return value.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
}
export function renderStatus({busy=false,error='',items=[]}) {
  if (error) return `<p role="alert">${escapeHtml(error)}</p>`;
  if (busy) return '<p role="status" aria-live="polite">Loading</p>';
  return `<ul>${items.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`;
}
"""},
        hidden_filename="_private.test.mjs",
        hidden_test="""import test from 'node:test';
import assert from 'node:assert/strict';
import { renderStatus } from './status.mjs';
test('announces changing states', () => {
  assert.match(renderStatus({busy:true}), /role=["']status["']/);
  assert.match(renderStatus({error:'No connection'}), /role=["']alert["']/);
});
test('renders safe list text', () => {
  const html = renderStatus({items:['<img src=x onerror=bad()>','A & B']});
  assert.match(html, /<ul>/); assert.match(html, /<li>/);
  assert.doesNotMatch(html, /<img/);
  assert.match(html, /&lt;img/); assert.match(html, /A &amp; B/);
});
""",
    ),
    Case(
        id="js-listener-cleanup", stack="javascript", family="lifecycle", canary=False,
        brief="""# Event subscription cleanup

`createBus()` returns `{subscribe, emit}`. `subscribe(listener)` registers a listener and returns an idempotent unsubscribe function. Emission reaches each currently subscribed listener once; after unsubscribe it must not reach that listener. Keep the API and add tests.
""",
        files={"package.json": '{"type":"module"}\n', "bus.mjs": """export function createBus() {
  const listeners = new Set();
  return {
    subscribe(fn) { listeners.add(fn); return () => {}; },
    emit(value) { for (const fn of listeners) fn(value); }
  };
}
"""},
        reference={"bus.mjs": """export function createBus() {
  const listeners = new Set();
  return {
    subscribe(fn) { listeners.add(fn); return () => { listeners.delete(fn); }; },
    emit(value) { for (const fn of [...listeners]) fn(value); }
  };
}
"""},
        hidden_filename="_private.test.mjs",
        hidden_test="""import test from 'node:test';
import assert from 'node:assert/strict';
import { createBus } from './bus.mjs';
test('unsubscribe is idempotent and other listeners remain', () => {
  const bus=createBus(), a=[], b=[];
  const off=bus.subscribe(v=>a.push(v)); bus.subscribe(v=>b.push(v));
  bus.emit(1); off(); off(); bus.emit(2);
  assert.deepEqual(a,[1]); assert.deepEqual(b,[1,2]);
});
""",
    ),
    Case(
        id="go-cursor-page", stack="go", family="pagination-contract", canary=False,
        brief="""# Cursor pagination

`Page(items, after, limit)` returns items strictly after cursor `after`, up to `limit`, plus a `next` cursor equal to the last returned item only if more items remain. Empty `after` starts at the beginning. Unknown nonempty cursor returns no items and no next cursor. Inputs have unique strings and positive `limit`. Preserve the function and add tests.
""",
        files={"go.mod": "module example.invalid/cursorpage\n\ngo 1.22\n", "page.go": """package page

func Page(items []string, after string, limit int) ([]string, string) {
 start := 0
 for i, item := range items { if item == after { start = i; break } }
 end := start + limit
 if end > len(items) { end = len(items) }
 result := items[start:end]
 next := ""
 if end < len(items) && len(result) > 0 { next = result[len(result)-1] }
 return result, next
}
"""},
        reference={"page.go": """package page

func Page(items []string, after string, limit int) ([]string, string) {
 start := 0
 if after != "" {
  start = -1
  for i, item := range items { if item == after { start = i+1; break } }
  if start < 0 { return []string{}, "" }
 }
 end := start + limit
 if end > len(items) { end = len(items) }
 result := items[start:end]
 next := ""
 if end < len(items) && len(result) > 0 { next = result[len(result)-1] }
 return result, next
}
"""},
        hidden_filename="private_test.go",
        hidden_test="""package page

import ("reflect"; "testing")

func TestPages(t *testing.T) {
 items := []string{"A","B","C","D","E"}
 a, next := Page(items, "", 2)
 if !reflect.DeepEqual(a, []string{"A","B"}) || next != "B" { t.Fatalf("first: %v %q", a, next) }
 b, next := Page(items, next, 2)
 if !reflect.DeepEqual(b, []string{"C","D"}) || next != "D" { t.Fatalf("second: %v %q", b, next) }
 c, next := Page(items, next, 2)
 if !reflect.DeepEqual(c, []string{"E"}) || next != "" { t.Fatalf("last: %v %q", c, next) }
 d, next := Page(items, "missing", 2)
 if len(d) != 0 || next != "" { t.Fatalf("unknown: %v %q", d, next) }
}
""",
    ),
    Case(
        id="go-config-precedence", stack="go", family="configuration", canary=False,
        brief="""# Layered configuration

`Resolve(file, env, cli)` returns a fresh settings map. CLI values override environment values, which override file values; unrelated keys survive. Empty string is a deliberate value and still overrides lower layers. None of the input maps may be changed. Preserve the signature and add tests.
""",
        files={"go.mod": "module example.invalid/configprecedence\n\ngo 1.22\n", "config.go": """package config

func Resolve(file, env, cli map[string]string) map[string]string {
 out := map[string]string{}
 for k,v := range cli { out[k]=v }
 for k,v := range env { out[k]=v }
 for k,v := range file { out[k]=v }
 return out
}
"""},
        reference={"config.go": """package config

func Resolve(file, env, cli map[string]string) map[string]string {
 out := map[string]string{}
 for k,v := range file { out[k]=v }
 for k,v := range env { out[k]=v }
 for k,v := range cli { out[k]=v }
 return out
}
"""},
        hidden_filename="private_test.go",
        hidden_test="""package config

import ("reflect"; "testing")

func TestResolve(t *testing.T) {
 file := map[string]string{"mode":"file", "shared":"file", "fileOnly":"x"}
 env := map[string]string{"mode":"env", "shared":"env", "envOnly":"y"}
 cli := map[string]string{"mode":"", "cliOnly":"z"}
 got := Resolve(file,env,cli)
 want := map[string]string{"mode":"", "shared":"env", "fileOnly":"x", "envOnly":"y", "cliOnly":"z"}
 if !reflect.DeepEqual(got,want) { t.Fatalf("got %v want %v",got,want) }
 got["mode"] = "changed"
 if file["mode"] != "file" || env["mode"] != "env" || cli["mode"] != "" { t.Fatal("mutated input") }
}
""",
    ),
]

BY_ID = {case.id: case for case in CASES}
