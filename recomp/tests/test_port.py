"""Disc-free tests for migration tooling, patch ownership and launch arguments."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("sc3_port", Path(__file__).parents[1] / "port.py")
port = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(port)


class PortTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="sc3 port [test] ")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.engine = self.root / "work/native engine"
        self.config = self.root / "config"
        self.config.mkdir()

    def fixture(self):
        upstream = self.root / "upstream"
        upstream.mkdir()
        port.call(["git", "init", "-q", upstream])
        (upstream / "source.txt").write_text("base\n")
        (upstream / ".gitignore").write_text("/games/\n/build/\n")
        port.git(upstream, "add", ".")
        port.git(upstream, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "commit", "-qm", "fixture")
        commit = port.git(upstream, "rev-parse", "HEAD", capture=True)
        (self.config / "ps2-native-recomp.commit").write_text(commit + "\n")
        (upstream / "source.txt").write_text("patched\n")
        delta = port.git(upstream, "diff", capture=True)
        (self.config / "change.patch").write_text(delta + "\n")
        (self.config / "series").write_text("change.patch\n")
        port.git(upstream, "checkout", "--", "source.txt")
        return upstream

    def prepare(self, upstream):
        return port.prepare(self.engine, self.config, str(upstream))

    def test_iso_selection_and_explicit_override(self):
        with self.assertRaisesRegex(RuntimeError, "No disc"):
            port.find_iso(self.root, self.engine)
        first = self.root / "Disc (PAL) [v2].ISO"
        first.touch()
        self.assertEqual(port.find_iso(self.root, self.engine), first)
        (self.root / "second.iso").touch()
        with self.assertRaisesRegex(RuntimeError, "More than one"):
            port.find_iso(self.root, self.engine)
        self.assertEqual(port.find_iso(self.root, self.engine, str(first)), first)
        with self.assertRaisesRegex(RuntimeError, "not found"):
            port.find_iso(self.root, self.engine, str(self.root / "absent.iso"))
        cached = self.engine / "games/sc3/disc.iso"
        cached.parent.mkdir(parents=True)
        cached.symlink_to(first)
        self.assertEqual(port.find_iso(self.root, self.engine), first)

    def test_preparation_is_repeatable(self):
        upstream = self.fixture()
        first = self.prepare(upstream)
        self.assertEqual((self.engine / "source.txt").read_text(), "patched\n")
        self.assertEqual(self.prepare(upstream), first)
        self.assertEqual((self.engine / "source.txt").read_text(), "patched\n")

    def test_unstaged_edits_are_preserved(self):
        upstream = self.fixture()
        self.prepare(upstream)
        source = self.engine / "source.txt"
        source.write_text("user work\n")
        with self.assertRaisesRegex(RuntimeError, "Local source edits"):
            self.prepare(upstream)
        self.assertEqual(source.read_text(), "user work\n")

    def test_staged_edits_are_preserved(self):
        upstream = self.fixture()
        self.prepare(upstream)
        source = self.engine / "source.txt"
        source.write_text("staged user work\n")
        port.git(self.engine, "add", "source.txt")
        with self.assertRaisesRegex(RuntimeError, "Local source edits"):
            self.prepare(upstream)
        self.assertEqual(source.read_text(), "staged user work\n")

    def test_removing_merged_patch_keeps_local_game_data(self):
        upstream = self.fixture()
        self.prepare(upstream)
        card = self.engine / "games/sc3/card.ps2"
        card.parent.mkdir(parents=True)
        card.write_bytes(b"private card sentinel")
        (self.config / "series").write_text("# patch removed after a pin update\n")
        self.prepare(upstream)
        self.assertEqual((self.engine / "source.txt").read_text(), "base\n")
        self.assertEqual(card.read_bytes(), b"private card sentinel")

    def test_failed_series_rolls_back_partial_changes(self):
        upstream = self.fixture()
        self.prepare(upstream)
        (self.config / "bad.patch").write_text("not a patch\n")
        (self.config / "series").write_text("change.patch\nbad.patch\n")
        with self.assertRaises(subprocess.CalledProcessError):
            self.prepare(upstream)
        self.assertEqual((self.engine / "source.txt").read_text(), "base\n")
        self.assertEqual(port.git(self.engine, "status", "--porcelain", capture=True), "")
        (self.config / "series").write_text("change.patch\n")
        self.prepare(upstream)
        self.assertEqual((self.engine / "source.txt").read_text(), "patched\n")

    def test_series_cannot_escape_configuration_directory(self):
        self.fixture()
        (self.config / "series").write_text("../outside.patch\n")
        with self.assertRaisesRegex(RuntimeError, "Invalid patch"):
            port.configuration(self.config)

    def test_runner_needs_only_binary_and_iso_and_preserves_arguments(self):
        with self.assertRaisesRegex(RuntimeError, "make build"):
            port.runner_command(self.engine)
        for name in ["build/native-sc3/ps2run", "games/sc3/disc.iso"]:
            p = self.engine / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.touch()
        extra = ["--load-state", str(self.root / "State [a] with spaces.state")]
        args = port.runner_command(self.engine, extra)
        self.assertEqual(args[1:3], ["--disc", str(self.engine / "games/sc3/disc.iso")])
        self.assertEqual(args[3:5], ["--game-dir", str(self.engine / "games/sc3")])
        self.assertFalse((self.engine / "games/sc3/disc").exists())
        self.assertEqual(args[-2:], extra)
        self.assertNotIn("--patches", args)
        self.assertIn(str(self.engine / "games/sc3/play.ps2"), args)

    def test_invalid_exploration_limits_fail_before_preparation(self):
        for frames, rounds in [(0, 1), (1, -1)]:
            with self.assertRaisesRegex(RuntimeError, "must be positive"):
                port.build(self.root / "work", frames=frames, rounds=rounds)
        self.assertFalse(self.engine.exists())

    def test_different_image_does_not_replace_existing_elf(self):
        work = self.root / "work"
        engine = work / "ps2-native-recomp"
        game = engine / "games/sc3"
        (game / "disc").mkdir(parents=True)
        elf = game / "disc/SCES_533.12"
        elf.write_bytes(b"original ELF sentinel")
        (game / "disc.iso").touch()
        other = self.root / "other.iso"
        other.touch()
        with patch.dict(os.environ, {"ISO": str(other)}), \
             self.assertRaisesRegex(RuntimeError, "another image"):
            port.build(work)
        self.assertEqual(elf.read_bytes(), b"original ELF sentinel")

    def test_failed_build_invalidates_success_stamp(self):
        work = self.root / "work"
        engine = work / "ps2-native-recomp"
        stamp = engine / "build/sc3-port-build.json"
        port.write_json(stamp, {"fingerprint": "previous"})
        iso = self.root / "disc.iso"
        iso.touch()
        with patch.dict(os.environ, {"ISO": str(iso)}), \
             patch.object(port, "prepare", return_value="fingerprint"), \
             patch.object(port, "modern_bash", return_value="/bin/bash"), \
             patch.object(port.shutil, "which", return_value="tool"), \
             patch.object(port, "call", side_effect=RuntimeError("extract failed")), \
             self.assertRaisesRegex(RuntimeError, "extract failed"):
            port.build(work)
        self.assertFalse(stamp.exists())

    def test_build_forwards_native_only_without_instruction_overrides(self):
        work = self.root / "build work"
        engine = work / "ps2-native-recomp"
        iso = self.root / "own disc.iso"
        iso.touch()
        calls = []
        def fake_call(args, **kwargs):
            args = [str(a) for a in args]
            calls.append(args)
            if "SYSTEM.CNF" in args:
                (engine / "games/sc3/disc/SYSTEM.CNF").write_text("BOOT2 = cdrom0:\\SCES_533.12;1\n")
            return port.CRC if "crc" in args else None
        with patch.dict(os.environ, {"ISO": str(iso)}, clear=False), \
             patch.object(port, "prepare", return_value="fingerprint"), \
             patch.object(port, "modern_bash", return_value="/bin/bash"), \
             patch.object(port.shutil, "which", return_value="tool"), \
             patch.object(port, "call", side_effect=fake_call):
            port.build(work, no_explore=True)
        build_call = next(c for c in calls if str(engine / "scripts/port.sh") in c)
        self.assertIn("--native-only", build_call)
        self.assertNotIn("--embed-elf", build_call)
        self.assertIn("--no-explore", build_call)
        self.assertNotIn("--pnach", build_call)
        self.assertEqual(json.loads((engine / "build/sc3-port-build.json").read_text())["elf_crc"], port.CRC)


if __name__ == "__main__":
    unittest.main()
