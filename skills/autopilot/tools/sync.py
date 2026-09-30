#!/usr/bin/env python3
"""Зеркалит state.js в саму страницу дашборда и держит сервер живым.

Вызывается после каждой правки .autopilot/state.js — одной строкой, без аргументов:

    python3 .autopilot/sync.py

Делает ровно три вещи, в этом порядке:

  1. Проверяет, что state.js разбирается. Битый файл не идёт дальше: снимок на
     странице остаётся прежним, а не затирается мусором.
  2. Вписывает состояние внутрь dashboard.html между маркерами — атомарно, через
     временный файл рядом. Оборвётся на середине — на месте останется целая
     прежняя страница. Отсюда дашборд показывает данные, даже когда его открыли
     файлом, из панели через data:, с мёртвым сервером или через месяц после
     прогона.
  3. Смотрит, жив ли статический сервер этого прогона, и поднимает на прежнем
     порту, если нет. Прежний порт — чтобы ссылка, которую пользователь уже
     скопировал, продолжала работать.

Флаги:
  --check-update   ещё и сверить версию навыка с GitHub (раз за прогон, в фазе 0)
  --no-serve       не трогать сервер
  --stop           погасить сервер этого прогона через 12 секунд, не блокируя
                   вызов: страница успевает забрать финальное состояние

Работает на macOS, Linux и Windows (в том числе из Git Bash).
Ничего не печатает в чат сама по себе: одна строка на stdout, её видит агент.
"""

import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

for _s in (sys.stdout, sys.stderr):                       # cp1251-консоль Windows
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

A = os.path.dirname(os.path.abspath(__file__))          # .autopilot этого прогона
STATE = os.path.join(A, "state.js")
PAGE = os.path.join(A, "dashboard.html")
PIDF = os.path.join(A, "serve.pid")
LOG = os.path.join(A, "serve.log")
BEGIN, END = "/*STATE-BEGIN*/", "/*STATE-END*/"
WIN = os.name == "nt"
REPO = "nick-vels/skills"
REMOTE_SKILL = "https://raw.githubusercontent.com/%s/main/skills/autopilot/SKILL.md" % REPO
STOP_DELAY = 12


def fail(msg):
    print(msg)
    sys.exit(1)


def read_state():
    try:
        raw = open(STATE, encoding="utf-8").read()
    except FileNotFoundError:
        fail("state.js ещё нет — снимок не вписан, сервер не тронут")
    body = raw.split("=", 1)[1] if "=" in raw.split("\n", 1)[0] else raw
    try:
        return json.loads(body.strip().rstrip(";"))
    except json.JSONDecodeError as e:
        fail("state.js не разбирается (строка %d: %s) — снимок оставлен прежним" % (e.lineno, e.msg))


def write_snapshot(state):
    """Снимок внутрь страницы. Возвращает текст для отчёта."""
    try:
        page = open(PAGE, encoding="utf-8").read()
    except FileNotFoundError:
        return "страницы нет — перекопируй dashboard.html из навыка"
    i, j = page.find(BEGIN), page.find(END)
    if i < 0 or j < 0:
        return "страница без маркеров снимка — перекопируй dashboard.html из навыка"
    # </ внутри <script> закрыл бы тег и порвал страницу; < безопасен в JSON.
    payload = "window.STATE=" + json.dumps(state, ensure_ascii=False).replace("</", "<\\/") + ";"
    new = page[: i + len(BEGIN)] + payload + page[j:]
    if new == page:
        return "снимок уже совпадал"
    tmp = PAGE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(new)
    os.replace(tmp, PAGE)                                # атомарно: битой страницы не бывает
    return "снимок вписан"


# ── процессы ────────────────────────────────────────────────────────────────
# На Windows нет ps (а ps из Git Bash не видит Windows-процессов), поэтому
# командные строки берутся из CIM. Без этого живой сервер не узнавался своим,
# и каждый вызов поднимал ещё один (issues #8, #9, #10).

def _run(args):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=10,
                              encoding="utf-8", errors="replace").stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def _ps(script):
    return _run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script])


def cmdline(pid):
    if WIN:
        return _ps("(Get-CimInstance Win32_Process -Filter 'ProcessId=%d').CommandLine" % int(pid)).strip()
    return _run(["ps", "-p", str(pid), "-o", "command="]).strip()


def processes():
    """[(pid, командная строка)] всех python-процессов (на POSIX — всех)."""
    out = []
    if WIN:
        text = _ps("Get-CimInstance Win32_Process -Filter \"Name LIKE 'python%'\" | "
                   "ForEach-Object { \"$($_.ProcessId)`t$($_.CommandLine)\" }")
        for line in text.splitlines():
            num, _, cmd = line.partition("\t")
            if num.strip().isdigit():
                out.append((int(num), cmd))
    else:
        for line in _run(["ps", "-Ao", "pid=,command="]).splitlines():
            num, _, cmd = line.strip().partition(" ")
            if num.isdigit():
                out.append((int(num), cmd))
    return out


def _norm(path):
    return os.path.normcase(os.path.normpath(path)).replace("\\", "/")


_OURS = re.compile(r"--directory\s+\"?" + re.escape(_norm(A)) + r"\"?(?=\s|$)")


def is_ours(cmd):
    """Наш ли это процесс. Узкая проверка намеренно: широкая уже убивала чужое.

    Сервер этого прогона — и только он: `-m http.server` и ровно наш --directory
    (регистр и вид слэшей на Windows не важны, чужой префикс не совпадёт).
    """
    c = cmd.replace("\\", "/")
    c = c.lower() if WIN else c
    return bool(re.search(r"-m\s+http\.server\b", c)) and bool(_OURS.search(c))


def kill(pid):
    try:
        os.kill(int(pid), 15)                            # на Windows — TerminateProcess
    except (OSError, ValueError):
        pass


def recorded():
    try:
        port, pid = open(PIDF, encoding="utf-8").read().split()
        return int(port), int(pid)
    except (OSError, ValueError):
        return None, None


def http_ok(port, path="/dashboard.html"):
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d%s" % (port, path), timeout=2) as r:
            return r.status == 200
    except (urllib.error.URLError, OSError, ValueError):
        return False


def free_port(prefer):
    """Прежний порт, если свободен, иначе любой. Стабильный адрес важнее случайного."""
    for p in ([prefer] if prefer else []) + [0]:
        s = socket.socket()
        try:
            s.bind(("127.0.0.1", p))
            return s.getsockname()[1]
        except OSError:
            continue
        finally:
            s.close()
    return None


def kill_orphans(keep=None):
    """Серверы этого каталога, кроме записанного. Только по полному --directory,
    никогда по «все http.server, кроме...»."""
    n = 0
    for pid, cmd in processes():
        if pid != keep and pid != os.getpid() and is_ours(cmd):
            kill(pid)
            n += 1
    return n


def serve(state):
    port, pid = recorded()
    if state.get("finishedAt"):
        n = kill_orphans(keep=pid)                     # живой остаётся до --stop
        return "прогон закрыт — сервер не поднимаю" + (" · сирот погашено: %d" % n if n else "")
    if os.environ.get("SSH_CONNECTION") or os.environ.get("CI"):
        return "удалённая сессия — без сервера"

    if port and pid and http_ok(port) and is_ours(cmdline(pid)):
        return "сервер жив: http://localhost:%d/dashboard.html" % port

    kill_orphans()
    port = free_port(port)
    if not port:
        return "порт не нашёлся — дашборд открывается файлом: %s" % PAGE
    detach = {}
    if WIN:
        detach["creationflags"] = (getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                                   | getattr(subprocess, "CREATE_NO_WINDOW", 0))
    else:
        detach["start_new_session"] = True             # переживает конец сессии агента
    try:
        with open(LOG, "a", encoding="utf-8") as log:
            srv = subprocess.Popen([sys.executable, "-m", "http.server", str(port),
                                    "--bind", "127.0.0.1", "--directory", A],
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                   stderr=log, **detach)
    except OSError as e:
        return "сервер не запустился (%s) — дашборд открывается файлом: %s" % (e, PAGE)
    for _ in range(10):
        if http_ok(port):
            with open(PIDF, "w", encoding="utf-8") as f:
                f.write("%d %d\n" % (port, srv.pid))
            return "сервер поднят: http://localhost:%d/dashboard.html" % port
        try:
            srv.wait(timeout=0.5)
            break
        except subprocess.TimeoutExpired:
            continue
    srv.terminate()
    return "сервер не ответил — дашборд открывается файлом: %s" % PAGE


def stop_now(delay):
    time.sleep(delay)
    port, pid = recorded()
    if pid and is_ours(cmdline(pid)):
        kill(pid)
    kill_orphans()
    for f in (PIDF, LOG):
        try:
            os.remove(f)
        except OSError:
            pass


def stop_later():
    """Гасит сервер через STOP_DELAY секунд в отдельном процессе и сразу возвращает
    управление: страница опрашивает state.js раз в 10 секунд, и убийство в тот же
    ход оставило бы на экране «в работе» навсегда."""
    detach = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)} if WIN \
        else {"start_new_session": True}
    subprocess.Popen([sys.executable, os.path.abspath(__file__), "--stop-now"],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, **detach)
    return "сервер погаснет через %d с — после того, как страница заберёт финал" % STOP_DELAY


# ── версия навыка ───────────────────────────────────────────────────────────

_VER = re.compile(r"^\s*version:\s*[\"']?(\d+(?:\.\d+)*)", re.M)


def _version(text):
    m = _VER.search(text.split("\n---", 1)[0] if text.startswith("---") else "")
    return tuple(int(x) for x in m.group(1).split(".")) if m else None


def check_update(state):
    """Одна строка, если на GitHub навык новее установленного. Без сети — молчит.
    Отключается переменной AUTOPILOT_NO_UPDATE_CHECK=1."""
    if os.environ.get("AUTOPILOT_NO_UPDATE_CHECK"):
        return None
    skill = state.get("skillDir") or ""
    try:
        local = _version(open(os.path.join(skill, "SKILL.md"), encoding="utf-8").read())
    except OSError:
        return None
    try:
        with urllib.request.urlopen(REMOTE_SKILL, timeout=3) as r:
            remote = _version(r.read(65536).decode("utf-8", "replace"))
    except (urllib.error.URLError, OSError, ValueError):
        return None
    if not remote or (local and remote <= local):
        return None
    home = _norm(os.path.expanduser("~"))
    glob_flag = " -g" if _norm(skill).startswith(home + "/.") else ""
    v = lambda t: ".".join(map(str, t))
    return ("вышла версия Autopilot %s (у тебя %s): npx skills update autopilot%s · "
            "что нового — github.com/%s/blob/main/CHANGELOG.md"
            % (v(remote), v(local) if local else "без номера", glob_flag, REPO))


# ── этапы ───────────────────────────────────────────────────────────────────

ORDER = ["preflight", "manifest", "briefing", "spec", "plan", "build", "review", "final"]
# Этап, чей результат лежит на диске, пройден — даже если его забыли отметить.
ARTIFACT = {"manifest": "manifest.md", "spec": "spec.md", "plan": "tickets"}


def close_passed(state):
    """Закрывает этапы, которые прогон уже прошёл. Возвращает список закрытых.

    Инвариант, а не событие: раньше активного этапа не может быть другого
    активного. Поэтому агент только открывает следующий — предыдущий
    закрывается здесь, временем открытия нового.

    Одно исключение, и оно в самой модели работы: ревью идёт по таскам внутри
    сборки, поэтому review не закрывает build. Всё, что позже review, закрывает
    обоих.

    Этап, который прогон проскочил, не отметив (pending позади активного), тоже
    закрывается — если его результат лежит на диске. Без этого агент видел
    противоречие и шёл его расследовать (issue #5).

    Не трогает skipped и failed: это осознанные состояния.
    """
    rank = {v: i for i, v in enumerate(ORDER)}
    stages = [s for s in state.get("stages") or [] if s.get("id") in rank]
    live = [s for s in stages if s.get("status") == "active"]
    closed = []
    for s in live:
        # Ревью не считается «следующим» для сборки: оно живёт внутри неё.
        later = [o for o in live if rank[o["id"]] > rank[s["id"]]
                 and not (s["id"] == "build" and o["id"] == "review")]
        if not later:
            continue
        # Закрываем открытием ближайшего следующего этапа, а не самого дальнего.
        marks = sorted(o["startedAt"] for o in later if o.get("startedAt"))
        when = marks[0] if marks else state.get("updatedAt")
        if not when:
            continue
        s["status"] = "done"
        s["finishedAt"] = when
        closed.append("%s закрыт автоматически (%s)" % (s["id"], when[11:19]))

    if not live:
        return closed
    edge = max(rank[s["id"]] for s in stages if s.get("status") in ("active", "done")) \
        if any(s.get("status") in ("active", "done") for s in stages) else -1
    run_dir = os.path.join(A, state.get("dir") or "")
    for s in stages:
        art = ARTIFACT.get(s["id"])
        if s.get("status") != "pending" or rank[s["id"]] >= edge or not art:
            continue
        if not state.get("dir") or not os.path.exists(os.path.join(run_dir, art)):
            continue
        nxt = [o.get("startedAt") for o in stages
               if rank[o["id"]] > rank[s["id"]] and o.get("startedAt")]
        when = min(nxt) if nxt else state.get("updatedAt")
        s["status"], s["startedAt"], s["finishedAt"] = "done", s.get("startedAt") or when, when
        closed.append("%s отмечен пройденным по файлу %s" % (s["id"], art))
    return closed


def save(state):
    raw = open(STATE, encoding="utf-8").read()
    head = raw.split("=", 1)[0]
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(head + "=\n" + json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    os.replace(tmp, STATE)


def audit(state):
    """Молчит, пока состояние сходится само с собой. Не чинит: называет."""
    out = []
    stages = state.get("stages") or []
    rank = {v: i for i, v in enumerate(ORDER)}
    live = [s["id"] for s in stages if s.get("status") == "active" and s.get("id") in rank]
    if live:
        edge = max(rank[i] for i in live)
        for s in stages:
            if s.get("status") == "pending" and rank.get(s.get("id"), 99) < edge:
                out.append("этап %s пропущен в учёте: был — отметь done, не было — skipped с "
                           "причиной. Это бухгалтерия, не расследуй" % s.get("id"))
    for s in stages:
        if s.get("status") == "done" and not s.get("finishedAt"):
            out.append("этап %s закрыт без finishedAt" % s.get("id"))
    for t in state.get("tickets") or []:
        if t.get("status") in ("in-progress", "review", "repair") and not t.get("startedAt"):
            out.append("таск %s в работе без startedAt" % t.get("id"))
        if t.get("status") == "done" and not t.get("finishedAt"):
            out.append("таск %s закрыт без finishedAt" % t.get("id"))
    return out


def main():
    if "--stop-now" in sys.argv:
        stop_now(STOP_DELAY)
        return
    state = read_state()
    passed = close_passed(state)
    if passed:
        save(state)                    # updatedAt не двигаем: пульс принадлежит агенту
    snap = write_snapshot(state)
    if "--stop" in sys.argv:
        srv = stop_later()
    elif "--no-serve" in sys.argv:
        srv = "сервер не проверялся"
    else:
        srv = serve(state)
    print("%s · %s · обновлено %s" % (snap, srv, (state.get("updatedAt") or "?")[11:19]))
    for line in passed:
        print("  · " + line)
    for line in audit(state)[:5]:
        print("  ! " + line)
    if "--check-update" in sys.argv:
        note = check_update(state)
        if note:
            print("  ↑ " + note)


if __name__ == "__main__":
    main()
