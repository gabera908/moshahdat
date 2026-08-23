# -*- coding: utf-8 -*-
"""Remote helper: run a command on the docker server via SSH (password auth)."""
import sys

import paramiko

HOST = "100.84.254.18"
USER = "root"
PASSWORD = "311211"


def run(cmd: str, timeout: int = 900) -> tuple[int, str, str]:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, timeout=20,
                   look_for_keys=True, allow_agent=False)
    try:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout, get_pty=True)
        out = stdout.read().decode("utf-8", "replace")
        code = stdout.channel.recv_exit_status()
        return code, out, ""
    finally:
        client.close()


if __name__ == "__main__":
    command = sys.argv[1]
    code, out, err = run(command)
    print(out)
    sys.exit(code)
