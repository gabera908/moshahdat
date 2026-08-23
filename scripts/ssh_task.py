# -*- coding: utf-8 -*-
"""Run a local bash script on the server via SSH+SFTP."""
import sys
import pathlib

import paramiko

HOST = "100.84.254.18"
USER = "root"
KEY = str(pathlib.Path.home() / ".ssh" / "id_ed25519")


def main(script_path: str) -> int:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, key_filename=KEY, timeout=20,
                   look_for_keys=False, allow_agent=False)
    try:
        sftp = client.open_sftp()
        remote = "/tmp/_vp_task.sh"
        sftp.put(script_path, remote)
        sftp.chmod(remote, 0o755)
        sftp.close()
        stdin, stdout, stderr = client.exec_command(f"bash {remote}", timeout=1800, get_pty=True)
        out = stdout.read().decode("utf-8", "replace")
        code = stdout.channel.recv_exit_status()
        print(out)
        return code
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
