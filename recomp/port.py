#!/usr/bin/env python3
"""Source-only SC3 port: pinned upstream, owned patch state, build and launch."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
UPSTREAM = "https://github.com/exoteric33/ps2-native-recomp.git"
BOOT = "SCES_533.12"
CRC = "3BA95B70"


def call(args, cwd=None, capture=False, env=None):
    result = subprocess.run([str(a) for a in args], cwd=cwd, env=env, text=True,
                            check=True, stdout=subprocess.PIPE if capture else None)
    return result.stdout.strip() if capture else None


def git(engine, *args, capture=False):
    return call(["git", "-C", engine, *args], capture=capture)


def configuration(here=HERE):
    commit = (here / "ps2-native-recomp.commit").read_text().strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise RuntimeError("ps2-native-recomp.commit must contain one full commit SHA")
    patches = []
    for line in (here / "series").read_text().splitlines():
        name = line.split("#", 1)[0].strip()
        if name:
            path = (here / name).resolve()
            if not path.is_relative_to(here.resolve()) or not path.is_file():
                raise RuntimeError(f"Invalid patch in series: {name}")
            patches.append(path)
    digest = hashlib.sha256(commit.encode())
    for path in patches:
        digest.update(str(path.relative_to(here.resolve())).encode())
        digest.update(path.read_bytes())
    return commit, patches, digest.hexdigest()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n")
    temporary.replace(path)


def prepare(engine, here=HERE, upstream=UPSTREAM):
    commit, patches, fingerprint = configuration(here)
    if not engine.exists():
        engine.parent.mkdir(parents=True, exist_ok=True)
        call(["git", "clone", upstream, engine])
    if not (engine / ".git").exists():
        raise RuntimeError(f"Not a managed Git checkout: {engine}")
    stamp = engine / "build/sc3-port-source.json"
    previous = json.loads(stamp.read_text()) if stamp.exists() else None
    head = git(engine, "rev-parse", "HEAD", capture=True)
    tree = git(engine, "write-tree", capture=True)
    clean = subprocess.run(["git", "-C", str(engine), "diff", "--quiet"]).returncode == 0
    if previous:
        if not clean or head != previous["commit"] or tree != previous["tree"]:
            raise RuntimeError(f"Local source edits in {engine}; preserve them in a worktree before rebuilding")
        if previous["fingerprint"] == fingerprint:
            return fingerprint
        # Reset only the exact patch state this wrapper previously installed.
        # Ignored games, cards, recordings and build outputs are preserved.
        git(engine, "reset", "--hard", previous["commit"])
        stamp.unlink()
    elif not clean or tree != git(engine, "rev-parse", "HEAD^{tree}", capture=True):
        raise RuntimeError(f"Unmanaged source edits in {engine}; use a clean checkout")
    exists = subprocess.run(["git", "-C", str(engine), "cat-file", "-e", commit + "^{commit}"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    if not exists:
        git(engine, "fetch", "origin", commit)
    git(engine, "checkout", "--detach", commit)
    try:
        for patch in patches:
            git(engine, "apply", "--index", patch)
    except subprocess.CalledProcessError:
        git(engine, "reset", "--hard", commit)
        raise
    write_json(stamp, {"commit": commit, "fingerprint": fingerprint,
                       "tree": git(engine, "write-tree", capture=True)})
    return fingerprint


def find_iso(root, engine, explicit=None):
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.is_file():
            raise RuntimeError(f"Disc image not found: {path}")
        return path
    cached = engine / "games/sc3/disc.iso"
    if cached.is_file():
        return cached.resolve()
    images = sorted(p for p in root.iterdir() if p.is_file() and p.suffix.lower() == ".iso")
    if len(images) != 1:
        raise RuntimeError("No disc image found" if not images else "More than one .iso: set ISO=/path/to/disc.iso")
    return images[0].resolve()


def modern_bash():
    candidates = [os.environ["BASH_BIN"]] if os.environ.get("BASH_BIN") else [
        "/opt/homebrew/bin/bash", "/usr/local/bin/bash", shutil.which("bash")]
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and subprocess.run(
                [candidate, "-c", 'test "${BASH_VERSINFO[0]}" -ge 4'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            return candidate
    raise RuntimeError("Bash 4+ is required by upstream: brew install bash (or set BASH_BIN)")


def environment(work):
    env = os.environ.copy()
    env.setdefault("CCACHE_DIR", str(work / ".ccache"))
    if not env.get("PS2_JOBS"):
        env["PS2_JOBS"] = str(min(8, os.cpu_count() or 1))
    return env


def build(work, no_explore=False, frames=3600, rounds=8):
    if frames < 1 or rounds < 1:
        raise RuntimeError("Exploration frames and rounds must be positive")
    engine = work / "ps2-native-recomp"
    iso = find_iso(ROOT, engine, os.environ.get("ISO"))
    cached = engine / "games/sc3/disc.iso"
    if cached.exists() and not cached.samefile(iso):
        raise RuntimeError(f"{cached} already names another image; use a separate WORK directory")
    bash = modern_bash()
    for command in ("git", "cmake", "ninja"):
        if not shutil.which(command):
            raise RuntimeError(f"Missing build tool: {command}")
    fingerprint = prepare(engine)
    build_stamp = engine / "build/sc3-port-build.json"
    # A failed build must not leave a successful stamp for a replaced ELF.
    build_stamp.unlink(missing_ok=True)
    env = environment(work)
    game = engine / "games/sc3"
    disc = game / "disc"
    disc.mkdir(parents=True, exist_ok=True)
    call([sys.executable, "-I", engine / "scripts/disc.py", "extract", iso, disc, "SYSTEM.CNF"])
    cnf = (disc / "SYSTEM.CNF").read_text()
    if not re.search(r"BOOT2\s*=\s*cdrom0:\\SCES_533\.12;1", cnf, re.IGNORECASE):
        raise RuntimeError(f"Only the tested PAL disc booting {BOOT} is supported")
    call([sys.executable, "-I", engine / "scripts/disc.py", "extract", iso, disc, BOOT])
    crc = call([sys.executable, "-I", engine / "scripts/pnach.py", "crc", disc / BOOT], capture=True)
    if crc != CRC:
        raise RuntimeError(f"Unsupported ELF CRC {crc}; the tested PAL revision is {CRC}")
    if cached.is_symlink() and not cached.exists():
        cached.unlink()
    call([bash, engine / "scripts/setup.sh", "--native-only"], env=env)
    install_default_keys(engine)
    args = [bash, engine / "scripts/port.sh", "sc3", iso, "--native-only",
            "--frames", frames, "--rounds", rounds]
    if no_explore or os.environ.get("EXPLORE") == "0":
        args.append("--no-explore")
    call(args, env=env)
    write_json(engine / "build/sc3-port-build.json", {"fingerprint": fingerprint, "elf_crc": crc})
    print("Built SC3. Run: make run", flush=True)


def runner_command(engine, extra=()):
    binary = engine / "build/native-sc3/ps2run"
    elf = engine / "games/sc3/disc" / BOOT
    iso = engine / "games/sc3/disc.iso"
    if not binary.is_file() or not elf.is_file() or not iso.is_file():
        raise RuntimeError("Runner or disc missing: run make build first")
    return [str(binary), str(elf), "--disc", str(iso), "--window", "--memcard",
            str(engine / "games/sc3/play.ps2"), *extra]


def install_default_keys(engine):
    destination = engine / "games/sc3/keys.ini"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        shutil.copyfile(HERE / "keys.ini", destination)


def run(work, extra):
    engine = work / "ps2-native-recomp"
    args = runner_command(engine, extra)
    stamp = engine / "build/sc3-port-build.json"
    if not stamp.is_file() or json.loads(stamp.read_text())["fingerprint"] != configuration()[2]:
        raise RuntimeError("Build does not match the current pin/patches: run make build")
    install_default_keys(engine)
    env = environment(work)
    env.setdefault("PS2_WINDOW_TITLE", "Soulcalibur III")
    env.setdefault("PS2_HITCH_LOG", "30")
    env.setdefault("PS2_VU0_RECORD", str(engine / "games/sc3/vu0"))
    env.setdefault("PS2_VU_RECORD", str(engine / "games/sc3/vu1"))
    os.chdir(engine)
    os.execvpe(args[0], args, env)


def test_runtime(work):
    engine = work / "ps2-native-recomp"
    prepare(engine)
    output = engine / "build/port-tests"
    output.mkdir(parents=True, exist_ok=True)
    cxx = os.environ.get("CXX", "clang++")
    for name, sources in [("stretch", ["tests/stretch_test.cpp", "host/stretch.cpp"]),
                          ("poll-watchdog", ["tests/poll_watchdog_test.cpp"])]:
        binary = output / name
        call([cxx, "-std=c++20", "-O2", "-I.", *sources, "-o", binary], cwd=engine)
        call([binary], cwd=engine)
    call([sys.executable, "scripts/test_vu0_codegen.py"], cwd=engine)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("build", "run", "test-runtime", "prepare"):
        command = commands.add_parser(name)
        command.add_argument("--work", type=Path, default=HERE / "work")
        if name == "build":
            command.add_argument("--no-explore", action="store_true")
            command.add_argument("--frames", type=int, default=3600)
            command.add_argument("--rounds", type=int, default=8)
        if name == "run":
            command.add_argument("args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    work = args.work.expanduser().resolve()
    if args.command == "build":
        build(work, args.no_explore, args.frames, args.rounds)
    elif args.command == "run":
        run(work, args.args[1:] if args.args[:1] == ["--"] else args.args)
    elif args.command == "prepare":
        prepare(work / "ps2-native-recomp")
    else:
        test_runtime(work)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError, OSError) as error:
        sys.exit(str(error))
