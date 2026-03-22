from __future__ import annotations

import atexit
import shlex
import socket
import subprocess
import time
from threading import Lock

from .config import RAGConfig


class AutoDLTunnelManager:
    def __init__(self, config: RAGConfig):
        self.config = config
        self._lock = Lock()
        self._process: subprocess.Popen[str] | None = None
        self._last_error: str | None = None
        atexit.register(self.close)

    @property
    def last_error(self) -> str | None:
        return self._last_error

    def should_manage_tunnel(self, base_url: str) -> bool:
        if not self.config.autodl_tunnel_enabled:
            return False
        host_port = f"{self.config.autodl_tunnel_local_host}:{self.config.autodl_tunnel_local_port}"
        return host_port in base_url

    def ensure_tunnel(self) -> bool:
        if not self.should_manage_tunnel(
            f"http://{self.config.autodl_tunnel_local_host}:{self.config.autodl_tunnel_local_port}"
        ):
            return False

        if self._is_local_port_open():
            self._last_error = None
            return True

        with self._lock:
            if self._is_local_port_open():
                self._last_error = None
                return True

            self._cleanup_dead_process()
            if not self.config.ssh_command or not self.config.ssh_password:
                self._last_error = "缺少 SSH 或 PASSWORD 配置，无法建立 AutoDL 隧道。"
                return False

            expect_script = self._build_expect_script()
            self._process = subprocess.Popen(
                ["expect", "-c", expect_script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
            )

            deadline = time.time() + self.config.autodl_tunnel_startup_timeout_seconds
            while time.time() < deadline:
                if self._is_local_port_open():
                    self._last_error = None
                    return True
                time.sleep(0.2)

            self._last_error = "SSH 隧道启动超时。"
            return False

    def close(self) -> None:
        with self._lock:
            if self._process and self._process.poll() is None:
                self._process.terminate()
                try:
                    self._process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self._process.kill()
            tunnel_pattern = (
                f"ssh .*{self.config.autodl_tunnel_local_host}:{self.config.autodl_tunnel_local_port}:"
                f"{self.config.autodl_tunnel_remote_host}:{self.config.autodl_tunnel_remote_port}"
            )
            subprocess.run(
                ["pkill", "-f", tunnel_pattern],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            self._process = None

    def _build_expect_script(self) -> str:
        ssh_parts = shlex.split(self.config.ssh_command)
        if not ssh_parts or ssh_parts[0] != "ssh":
            raise ValueError("SSH 配置格式无效，必须以 ssh 开头。")

        tunnel_arg = (
            f"{self.config.autodl_tunnel_local_host}:{self.config.autodl_tunnel_local_port}:"
            f"{self.config.autodl_tunnel_remote_host}:{self.config.autodl_tunnel_remote_port}"
        )
        cmd = [
            ssh_parts[0],
            "-f",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "ExitOnForwardFailure=yes",
            "-o",
            "ServerAliveInterval=30",
            "-o",
            "ServerAliveCountMax=3",
            "-N",
            "-L",
            tunnel_arg,
            *ssh_parts[1:],
        ]
        joined = shlex.join(cmd)
        password = self.config.ssh_password.replace("\\", "\\\\").replace('"', '\\"')
        return "\n".join(
            [
                "set timeout 20",
                f"spawn {joined}",
                "expect {",
                '    "password:" {',
                f'        send -- "{password}\\r"',
                "        exp_continue",
                "    }",
                '    "Permission denied" { exit 2 }',
                "    eof { exit 0 }",
                "    timeout { exit 3 }",
                "}",
            ]
        )

    def _cleanup_dead_process(self) -> None:
        if self._process and self._process.poll() is not None:
            self._process = None

    def _is_local_port_open(self) -> bool:
        try:
            with socket.create_connection(
                (self.config.autodl_tunnel_local_host, self.config.autodl_tunnel_local_port),
                timeout=1.0,
            ):
                return True
        except OSError:
            return False
