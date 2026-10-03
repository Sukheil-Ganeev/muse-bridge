import os
import plistlib
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


if __name__ == "__main__":
    unittest.main()
