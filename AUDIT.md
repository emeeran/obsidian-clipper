# Production Readiness Audit — 2026-08-07

Scope: full codebase on branch `cleanup/pipeline-2026-08-07` after the cleanup
pipeline (Phases 0–3). Findings are from six parallel dimension reviews
(correctness, security, config/env, observability, testing/CI, ops), each
verified against the code with `file:line` references. The two blockers and the
highest-impact highs were independently re-confirmed by the main thread.

## Summary

**Verdict: ready with fixes.** The fundamentals are strong — arg-list subprocess
calls everywhere (no shell injection), robust path-traversal validation, a
typed `ClipperError` hierarchy, 394 tests at ~85% coverage, and ruff / mypy /
bandit all clean. **Two blockers must be fixed before any shared release:**

1. A **live Obsidian API key is compromised in git history** (verified) and must
   be rotated and scrubbed.
2. **`--daily -s` silently drops screenshots and leaks temp files** (verified) —
   a real data-loss path.

Beyond those, the high-severity cluster is about **failure visibility**
(failures can be silent on a hotkey-launched process), **test gaps on critical
runtime paths**, and **CI that doesn't actually gate merges**. None of those are
data-loss or RCE, but together they mean "things go wrong and nobody finds out."

---

## Blockers (must fix before prod)

- [ ] **B1 — Live API key compromised in git history.** The key in the working-tree
  `.env` is recoverable from commits `4c372c6` and `80f31f1` (it was carried by
  `lcaude_conv030526.md`, a committed conversation export; `git rm` removed it
  from HEAD but did not rewrite history). Verified via `git log --all -S <key>`.
  Anyone with repo read access can fully read/write the vault via the Local REST
  API. **Fix:** (1) regenerate the key in Obsidian → Settings → Local REST API;
  (2) scrub history with `git filter-repo --invert-paths --path lcaude_conv030526.md`
  (or BFG `--delete-files`); (3) force-push; (4) audit other `*_conv*.md` / dumps.

- [ ] **B2 — `--daily` drops screenshots and leaks temp files.**
  `obsidian_clipper/cli/main.py:327-338` calls `session.to_markdown()` +
  `client.append_periodic_note("daily", ...)` directly, **bypassing
  `process_and_save_content`** (the only caller of `client.upload_image`,
  `main.py:191`). Consequence for `obsidian-clipper -s --daily`: the screenshot
  PNG is never uploaded, so the `![[file.png]]` embed is a broken link; the temp
  PNG leaks in `/tmp` (no `_cleanup_session`); and `_validate_session` is
  skipped. **Fix:** in the `--daily` branch, upload the image first (if
  `session.screenshot_path`), then append the resulting markdown to the periodic
  note, and clean up the temp file on failure.

---

## High priority

- [ ] **H1 — `notify()` catches the wrong exception type.**
  `obsidian_clipper/utils/notification.py:28` catches `subprocess.CalledProcessError`
  / `FileNotFoundError`, but `run_command_safely(check=True)` raises its own
  `CommandError`. So `notify-send` exiting non-zero (no D-Bus, headless, daemon
  disabled) raises `CommandError` uncaught → propagates to `main`'s catch-all,
  turning a **successful** capture into a reported failure. **Fix:** catch
  `CommandError` (+ `OSError`) here.

- [ ] **H2 — `_known_notes` cache can silently lose appended data.**
  `obsidian_clipper/obsidian/api.py:108-127` caches "note exists" after the first
  GET/PUT. If the note is later deleted in Obsidian, `ensure_note_exists` returns
  `True` from cache and the subsequent `append_to_note` POST can 404 → returns
  `False` → content lost, with no cache invalidation. **Fix:** evict from
  `_known_notes` when a write returns 404/`False` for a cached-existing path.

- [ ] **H3 — Default log level `WARNING` hides all `logger.error` output.**
  `obsidian_clipper/cli/args.py:19-23` defaults to WARNING, so every
  `logger.error("Failed to …")` across `api.py`/`capture.py`/`screenshot.py` is
  invisible unless `-v`/`--debug` is passed. For a hotkey-launched tool this
  means failures leave no diagnostic trail. **Fix:** default to `INFO`; add
  `--quiet` if a lower level is wanted.

- [ ] **H4 — Notification fallback degrades to `print(stdout)`, silently.**
  `obsidian_clipper/utils/notification.py:28-29`: when `notify-send` is missing,
  errors `print(...)` to **stdout** (not the logger, not stderr) — invisible on a
  detached hotkey process and not captured by `LOG_FILE`. Combined with H3, a
  capture failure with no `notify-send` is completely silent. **Fix:** route the
  fallback through `logger.error(...)` (and `file=sys.stderr`).

- [ ] **H5 — No branch protection on `main`; CI does not gate merges.** GitHub
  reports `main` is unprotected, so the `test`/`security` jobs don't block a bad
  PR from merging. **Fix:** require the `test` (all 3 Pythons) and `security`
  checks to pass on `main`, plus PR review.

- [ ] **H6 — Integration tests turn CI red the moment `OBSIDIAN_API_KEY` is set.**
  `tests/integration/test_api_integration.py:19` uses
  `skipif(not os.getenv("OBSIDIAN_API_KEY"))`, so they skip today (CI green by
  accident). Add `OBSIDIAN_API_KEY` to CI secrets (a natural step) and 4 of 5
  fail against a non-running Obsidian. `.github/workflows/ci.yml:35` has no
  `-m "not integration"` filter. **Fix:** add `-m "not integration"` to the CI
  pytest step (and/or require an explicit `RUN_INTEGRATION=1` opt-in).

- [ ] **H7 — `retry_with_backoff` has 0% test coverage** despite being production
  code on the citation-detection path (`capture/citation.py:589`). The
  exception-retry and `should_retry` branches are entirely untested.
  `obsidian_clipper/utils/retry.py:15-72`. **Fix:** add `tests/test_retry.py`.

- [ ] **H8 — `.ocr.png` temp file leaks on every successful OCR.**
  `obsidian_clipper/capture/screenshot.py:298` writes a preprocessed
  `img_path.with_suffix(".ocr.png")`; `ocr_image` only unlinks it in the
  `except` branches, not on the success `return` (line ~348). Every OCR run
  drops a file in `/tmp`. **Fix:** unlink `ocr_path` in a `finally`.

- [ ] **H9 — `KeyboardInterrupt` leaks the screenshot temp file.**
  `obsidian_clipper/cli/main.py:368` returns 130 without calling
  `_cleanup_session`. The session (with temp PNG) is captured at line 319 before
  any cleanup-aware block. **Fix:** call `_cleanup_session(session)` in the
  `except KeyboardInterrupt` branch.

- [ ] **H10 — `--vault` config is not validated.** `config.py:216-239`
  `get_vault_config` returns a `Config(_loaded=True)` with no `validate()` call,
  and `cli/main.py`'s vault branch doesn't validate either, so a misconfigured
  named vault produces cryptic `requests` errors instead of the friendly
  "API key is required" / "must start with http(s)" messages. **Fix:** call
  `vault_config.validate()` and surface errors like the default path.

- [ ] **H11 — `.deb` doesn't declare `fzf`/`rofi` needed by `--pick`.**
  `scripts/build-deb.sh:70` lists Recommends/Suggests but omits the pickers that
  `--pick` requires (`cli/main.py:68`). **Fix:** add `fzf | rofi` to `Suggests`.

---

## Medium / Low

### Medium
- **M1 — `_validate_session` is too strict for image-only screenshots.**
  `main.py:102` aborts (exit 1) when `-s` (OCR on) yields no OCR text, even for a
  legitimate screenshot of a diagram/image. Warn and proceed with image-only.
- **M2 — `upload_image` joins dir+name without a slash if `dest_dir` lacks a
  trailing slash.** `api.py:210` → `"Attachmentsfoo.png"`. Use
  `f"{dest_dir.rstrip('/')}/{dest_filename}"`.
- **M3 — `list_directory` returns dict keys on unexpected shapes.** `api.py:305`
  `list(data)` on a dict returns its keys as fake file paths. Guard with
  `isinstance(data, list)`.
- **M4 — `get_profile` env-override bool parsing is broken** for any value other
  than literal `true`/`false` (`yes`, `1` → stored as string → ignored).
  `config.py:212`.
- **M5 — `search`/`search_simple` can violate their return type** if the server
  returns non-list JSON. `api.py:243,263`. Coerce with `isinstance`.
- **M6 — Screenshot failure isn't surfaced to the user** during capture
  (`capture.py:121` logs a warning but the final notification still says
  "Captured …"). Use the (currently unused) `notify_warning`.
- **M7 — OCR failure is suppressed with no log.** `screenshot.py:417`
  `contextlib.suppress(OCRError)`. Log at warning.
- **M8 — Full note body logged at DEBUG.** `capture.py:201` dumps the entire
  capture (possibly sensitive) to `LOG_FILE` under `--debug`. Log length + short
  preview instead.
- **M9 — Non-200 API responses return empty with no logging** across
  `api.py` (`list_vault_files`, `search`, `get_tags`, …). A 401 is
  indistinguishable from an empty vault in the logs.
- **M10 — POST is not retried** (urllib3 default `allowed_methods` excludes POST),
  so `append_to_note`/`append_periodic_note` fail on the first 5xx/429 while PUTs
  retry. `api.py:77`. Be explicit about the policy.
- **M11 — `flameshot` fallback cascade can block ~180s** on a broken flameshot
  (raw → gui → gui-no-flag, each `timeout=60`). `screenshot.py:142`. Lower or skip.
- **M12 — `.deb` builds from `pyproject` lower bounds, not `uv.lock`**
  (`build-deb.sh:43` uses `uv pip install --target`), so the shipped deb can pull
  an untested `textual`/`Pillow` major. Build from the lock for reproducibility.
- **M13 — `.env` precedence: the XDG config can never win** over a cwd `.env`
  (`config.py:38-48`, both loaded with `override=False`). Document or fix.
- **M14 — OCR language packs not declared** in the deb/docs (`OBSIDIAN_OCR_LANGUAGE=eng,tam`
  needs `tesseract-ocr-tam`). Document lang-pack install.
- **M15 — `process_and_save_content` has no direct tests** (`capture.py:160-202`),
  incl. the upload-fail and temp-cleanup branches.
- **M16 — `main()` top-level exception handler is untested**
  (`main.py:356-374`) — the user-facing error boundary.
- **M17 — Test fixtures leak real env secrets** when `Config(...)` is built
  without `_loaded=True` (`test_api.py:113,738,788,821`) — a dev `.env`/exported
  key silently substitutes. Pass `_loaded=True` or add an autouse env-clearing
  fixture.
- **M18 — No coverage gate** (`--cov-fail-under`). Coverage can drop silently.

### Low (condensed — see linked lines)
- `validate_path` doesn't reject NUL bytes (`api.py:47`) — latent footgun.
- TUI `.env` write has a TOCTOU window before `chmod 0o600` (`tui.py:151`).
- `OBSIDIAN_VERIFY_SSL` parsing inverts on typos (`yes`/`1` → disabled); no
  warning when verification is off (`config.py:54`).
- `_pick_note_with_fzf` swallows all picker errors silently (`main.py:77`).
- `_save_via_uri` swallows `xdg-open` failure with no log (`main.py:154`).
- `notify_warning` / `get_logger` exported but never called (dead surface).
- `text.py` `except (CommandError, TimeoutExpired)` branches are silent.
- `_optimize_screenshot` catches bare `Exception` (`capture.py:72`).
- `.env.example` defaults differ from the `Config` dataclass defaults.
- `validate()` could assert the key is 64-char hex (`config.py:85`).
- `Dockerfile` pins `setup-uv:latest` (moving tag) (`Dockerfile:5`).
- `unlink()` without `missing_ok=True` in the screenshot cleanup
  (`capture.py:184`).
- `run_command_safely` doesn't catch `TimeoutExpired` → surfaces as a generic
  error (`command.py:69`).
- Docker healthcheck (`obsidian-clipper --help`) doesn't validate capture
  capability (`docker-compose.yml:30`).
- `retry_with_backoff`'s terminal `return None` (`retry.py:72`) is unreachable.

---

## Explicitly out of scope / accepted risk

- **SSRF via `base_url`** (`api.py`, `config.py:90`): the URL is operator-
  controlled and the bearer token is sent to whatever host is configured. For a
  local single-user CLI this is accepted, but it should be documented, and
  non-loopback targets should at least warn. Match the project's precedent of
  *flagging* known-fragile-but-low-priority items rather than silently fixing.
- **Docker `network_mode: host`** (`docker-compose.yml`): removes the container
  network boundary. Accepted because the compose file is explicitly EXPERIMENTAL
  and both endpoints are loopback on the same host; documented in-file.
- **Repeated try/except/log/default pattern across ~13 API methods** (`api.py`):
  considered for extraction in Phase 2 (F3) and deliberately left — the methods
  return different types and a generic helper adds abstraction for little gain.
- **Vestigial `-o`/`--ocr` flag** (`args.py:61`): always `True` via
  `store_true`+`default=True`; the attribute is still written by profile
  application. Flagged in Phase 2 (F1) — fixing changes the public CLI surface,
  so it's the owner's call.
- **`get_vault_config` duplication of `Config.load`** (`config.py:216`): Phase 2
  (F4) — consolidating risks subtle precedence changes; left as-is.
- **Phase 3 (style)** found the code already consistent (ruff/black clean,
  professional tone, coherent two-tier error philosophy). No changes warranted;
  recorded here so the pass isn't silently skipped.

---

## Verification status of this audit

- Gates at audit time: `ruff check .` clean · `mypy obsidian_clipper` clean ·
  `pytest -m "not integration"` → 394 passed · `bandit -r obsidian_clipper/ -ll`
  → 0 Medium/High.
- Blockers B1 and B2 were re-confirmed by the main thread (not just the subagent)
  before being recorded as blockers.
- This audit shares context with the cleanup pipeline that preceded it; an
  independent, context-blind review follows in Phase 5 (`.pipeline/blind-review.md`).

## Blind review reconciliation (Phase 5)

A context-blind reviewer was dispatched (sanitized prompt, no pipeline context).
Full output and reconciliation are in `.pipeline/blind-review.md`.

- **Agreement (higher confidence):** the blind review independently surfaced the
  same two blockers (key-in-history, `--daily` screenshot loss) and the same
  high cluster (`notify()` exception mismatch, WARNING-default + print-fallback
  observability, `_known_notes` staleness, `.ocr.png` leak, `KeyboardInterrupt`
  cleanup, `--vault` validation, CI/integration gating, `retry_with_backoff`
  coverage). Its trace of the `notify()` "phantom failure" propagation is the
  sharper framing and is recommended reading for whoever fixes H1.
- **Missed by pipeline, caught by blind review:** none substantive. The blind
  review corroborated rather than diverged. (Caveat below.)
- **Contamination caveat (honest):** this was **not** a fully clean blind pass.
  The reviewer located and read the in-repo `AUDIT.md` despite the sanitized
  prompt, so convergence on the same list is partly expected. For a truly
  independent read, review a checkout without `AUDIT.md`/`.pipeline/`/
  `trash2review/` — ideally in a fresh session with a different reviewer.
- **Model limit:** the blind reviewer shares this session's underlying model.
  Sanitization removes self-grading and framing bias, not model blind spots.
  Treat Phase 5 as bias reduction, not a substitute for external review.

## Resolution status (post-fix pass)

A follow-up pass addressed the findings. Gates after fixes: 413 tests pass
(+19), coverage 86% (gate 85%), ruff / mypy / `bandit -ll` clean.

**Fixed (code):**
- B2 — `--daily` now uploads the screenshot and cleans up the temp file
  (`upload_screenshot` helper shared with `process_and_save_content`).
- H1 — `notify()` catches `CommandError` (+`OSError`), so a flaky `notify-send`
  no longer turns a success into a reported failure.
- H2 — `_known_notes` is evicted on a 404 append, preventing silent data loss.
- H3 — default log level is now `INFO` (failures visible on the hotkey path);
  added `--quiet`.
- H4 — notification fallback routes to `logger.error` + stderr, not stdout.
- H6 — CI runs `pytest -m "not integration"`.
- H7 — added `tests/test_retry.py` (retry was 0% covered).
- H8 — `.ocr.png` preprocessed file is removed in a `finally` (no more `/tmp` leak).
- H9 — `KeyboardInterrupt` cleans up the screenshot temp file.
- H11 — `.deb` `Suggests` now includes `fzf | rofi` (for `--pick`).
- M1 — image-only screenshots (no OCR text) now save instead of aborting.
- M2 — `upload_image` joins dir/name with a slash even without a trailing slash.
- M3 — `list_directory` guards against unexpected response shapes.
- M4 — profile env-override bool parsing accepts `true/1/yes/on`.
- M5 — `search`/`search_simple` coerce to `list` regardless of response shape.
- M7 — OCR failures are logged at warning (no longer silent `suppress`).
- M8 — debug log no longer dumps the full note body (length only).
- M9 — non-200 API responses are logged across the client methods.
- M10 — `Retry.allowed_methods` is explicit (POST excluded by design).
- M12 — `.deb` builds from `uv.lock` (reproducible), verified by rebuild.
- M14 — `.deb` post-build message documents OCR language packs.
- M15/M16 — added tests for `upload_screenshot`/`process_and_save_content` and
  the `main()` top-level exception handlers; fixed a stale patch target.
- M17 — test `Config(...)` fixtures pass `_loaded=True` (no more real-key leak).
- M18 — added `--cov-fail-under=85`.
- NUL-byte rejection in `validate_path`; picker/URI failures now logged;
  TUI `.env` written with atomic `0600`; screenshot temp cleanup uses
  `missing_ok`.

**Verified false positive:**
- H10 — `--vault` config **is** validated (`cli/main.py:254-261`).

**Deferred (flagged, not auto-fixed — needs a human or a behavior call):**
- **B1 — history scrubbed + force-pushed (2026-08-07).** `git filter-repo` removed
  `lcaude_conv030526.md` (the only file containing the key) from all history;
  verified no reachable object contains the key; force-pushed `main` to origin
  (`4c372c6` → `b86101a`); local dangling objects gc'd. **Still required (cannot
  be done for you): rotate the key in Obsidian (Settings → Local REST API →
  Regenerate) — the old key remains compromised regardless of the scrub.** GitHub
  may also retain the orphaned `4c372c6` commit briefly until its GC (contact
  GitHub support for immediate purge), and any existing forks/clones still
  contain the key.
- **H5 — GitHub branch protection on `main`.** Outward-facing repo-setting
  change; not applied without authorization.
- M6 — screenshot failure is logged but not yet surfaced in the success
  notification (UX enhancement).
- M11 — flameshot fallback timing left as-is (lowering timeouts risks cutting
  off legitimate user area-selection).
- M13 — `.env` precedence (XDG can't override a cwd `.env`) documented, not
  changed (behavior change).
- Dockerfile `setup-uv:latest` pin and `run_command_safely` `TimeoutExpired`
  conversion left flagged (risk of breaking the build / rippling through
  callers' `except` clauses).
