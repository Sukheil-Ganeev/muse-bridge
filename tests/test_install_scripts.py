import os
import plistlib
import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MacOSInstallTests(unittest.TestCase):
    def test_plist_escapes_xml_special_characters_in_repo_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            project = temp / "project & <tools>"
            install_dir = project / "install"
            install_dir.mkdir(parents=True)
            shutil.copyfile(ROOT / "install" / "macos-install.sh",
                            install_dir / "macos-install.sh")

            fake_bin = temp / "bin"
            fake_bin.mkdir()
            launchctl = fake_bin / "launchctl"
            launchctl.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            launchctl.chmod(0o755)

            home = temp / "home"
            home.mkdir()
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")
            subprocess.run(
                ["bash", str(install_dir / "macos-install.sh")],
                check=True, capture_output=True, text=True, env=env)

            plist_path = home / "Library" / "LaunchAgents" / "com.muse-bridge.plist"
            config = plistlib.loads(plist_path.read_bytes())
            self.assertEqual(config["ProgramArguments"], [
                "/usr/bin/env", "python3", str(project / "muse_bridge.py")])


class LinuxInstallTests(unittest.TestCase):
    def test_autostart_rejects_control_character_in_repo_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            project = temp / "project\nmalicious"
            install_dir = project / "install"
            install_dir.mkdir(parents=True)
            shutil.copyfile(ROOT / "install" / "linux-install.sh",
                            install_dir / "linux-install.sh")

            fake_bin = temp / "bin"
            fake_bin.mkdir()
            python = fake_bin / "python3"
            python.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            python.chmod(0o755)

            home = temp / "home"
            home.mkdir()
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")
            result = subprocess.run(
                ["bash", str(install_dir / "linux-install.sh")],
                capture_output=True, text=True, env=env)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("control character", result.stderr + result.stdout)
            desktop = home / ".config" / "autostart" / "muse-bridge.desktop"
            self.assertFalse(desktop.exists())

    def test_autostart_exec_preserves_quotes_and_backslashes_in_repo_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            project = temp / 'project "quoted" \\ $cash `ticks` %f'
            install_dir = project / "install"
            install_dir.mkdir(parents=True)
            shutil.copyfile(ROOT / "install" / "linux-install.sh",
                            install_dir / "linux-install.sh")

            fake_bin = temp / "bin"
            fake_bin.mkdir()
            python = fake_bin / "python3"
            python.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            python.chmod(0o755)

            home = temp / "home"
            home.mkdir()
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")
            subprocess.run(
                ["bash", str(install_dir / "linux-install.sh")],
                check=True, capture_output=True, text=True, env=env)

            desktop = home / ".config" / "autostart" / "muse-bridge.desktop"
            exec_line = next(
                line for line in desktop.read_text(encoding="utf-8").splitlines()
                if line.startswith("Exec="))
            self.assertIn("%%f", exec_line)
            desktop_exec = exec_line[len("Exec="):].replace("\\\\", "\\")
            argv = shlex.split(desktop_exec)
            parsed_path = (argv[2].replace("\\$", "$")
                           .replace("\\`", "`").replace("%%", "%"))
            self.assertEqual(
                argv[:2] + [parsed_path],
                ["/usr/bin/env", "python3", str(project / "muse_bridge.py")])
            validator = shutil.which("desktop-file-validate")
            if validator:
                result = subprocess.run(
                    [validator, str(desktop)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0,
                                 result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
