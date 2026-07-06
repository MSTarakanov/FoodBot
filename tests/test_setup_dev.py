from __future__ import annotations

import os
import pty
import select
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SETUP_DEV = ROOT / "scripts" / "setup-dev"


def run_env_setup(
    tmp_path: Path,
    user_input: str,
    *extra_args: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SETUP_DEV), "--env-only", "--skip-token-check", *extra_args],
        cwd=tmp_path,
        input=user_input,
        text=True,
        capture_output=True,
        check=True,
    )


def read_env(tmp_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in (tmp_path / ".env").read_text(encoding="utf-8").splitlines():
        key, value = line.split("=", 1)
        values[key] = value
    return values


def clean_git_environment() -> dict[str, str]:
    env = os.environ.copy()
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_PREFIX"):
        env.pop(key, None)
    return env


def run_interactive_setup(
    command: list[str],
    cwd: Path,
    user_input: str,
) -> subprocess.CompletedProcess[str]:
    master_fd, slave_fd = pty.openpty()
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        close_fds=True,
        env=clean_git_environment(),
    )
    os.close(slave_fd)
    output_chunks: list[bytes] = []
    try:
        os.write(master_fd, user_input.encode())
        while True:
            ready_fds, _, _ = select.select([master_fd], [], [], 0.1)
            if ready_fds:
                try:
                    chunk = os.read(master_fd, 4096)
                except OSError:
                    break
                if not chunk:
                    break
                output_chunks.append(chunk)

            if process.poll() is not None:
                ready_fds, _, _ = select.select([master_fd], [], [], 0)
                if not ready_fds:
                    break

        return_code = process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        raise
    finally:
        os.close(master_fd)

    return subprocess.CompletedProcess(
        command,
        return_code,
        stdout=b"".join(output_chunks).decode(errors="replace"),
        stderr="",
    )


def run_git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=True,
        env=clean_git_environment(),
    )


def test_setup_dev_creates_env_with_admin_id(tmp_path: Path) -> None:
    result = run_env_setup(
        tmp_path,
        "123456:test-token\nfoodbot_dev\ny\n42\ndev-splitwise-key\n",
    )

    assert read_env(tmp_path) == {
        "FOODBOT_ENV": "development",
        "TELEGRAM_BOT_TOKEN": "123456:test-token",
        "TELEGRAM_BOT_USERNAME": "foodbot_dev",
        "DATABASE_PATH": "foodbot.local.sqlite3",
        "TELEGRAM_ADMIN_IDS": "42",
        "FOODBOT_TIMEZONE": "Europe/Belgrade",
        "SPLITWISE_API_KEY": "dev-splitwise-key",
        "SPLITWISE_GROUP_ID": "",
    }
    assert "123456:test-token" not in result.stdout
    assert "123456:test-token" not in result.stderr
    assert "dev-splitwise-key" not in result.stdout
    assert "dev-splitwise-key" not in result.stderr


def test_setup_dev_reuses_local_state_for_linked_worktree(tmp_path: Path) -> None:
    main_worktree = tmp_path / "FoodBot"
    main_worktree.mkdir()
    (main_worktree / "scripts").mkdir()
    setup_copy = main_worktree / "scripts" / "setup-dev"
    setup_copy.write_text(SETUP_DEV.read_text(encoding="utf-8"), encoding="utf-8")
    setup_copy.chmod(0o755)
    (main_worktree / ".gitignore").write_text(
        ".env\n.tools\n*.sqlite3\n",
        encoding="utf-8",
    )
    (main_worktree / ".env.defaults").write_text(
        "SPLITWISE_GROUP_ID=55\nPRODUCTION_TELEGRAM_BOT_ID=8490386710\n",
        encoding="utf-8",
    )

    run_git(main_worktree, "init")
    run_git(main_worktree, "config", "user.name", "Test User")
    run_git(main_worktree, "config", "user.email", "test@example.com")
    run_git(main_worktree, "add", "scripts/setup-dev", ".gitignore", ".env.defaults")
    run_git(main_worktree, "commit", "-m", "init")

    (main_worktree / ".env").write_text(
        "\n".join(
            [
                "FOODBOT_ENV=development",
                "TELEGRAM_BOT_TOKEN=123456:test-token",
                "TELEGRAM_BOT_USERNAME=foodbot_dev",
                "DATABASE_PATH=foodbot.local.sqlite3",
                "TELEGRAM_ADMIN_IDS=42",
                "FOODBOT_TIMEZONE=Europe/Belgrade",
                "SPLITWISE_API_KEY=dev-splitwise-key",
                "SPLITWISE_GROUP_ID=55",
            ]
        ),
        encoding="utf-8",
    )
    (main_worktree / ".tools" / "bin").mkdir(parents=True)
    (main_worktree / ".tools" / "bin" / "uv").write_text("", encoding="utf-8")
    (main_worktree / "foodbot.local.sqlite3").write_text("db", encoding="utf-8")

    linked_worktree = tmp_path / "FoodBot-feature"
    run_git(main_worktree, "worktree", "add", "-b", "feature/test", str(linked_worktree))

    result = run_interactive_setup(
        [
            "bash",
            str(linked_worktree / "scripts" / "setup-dev"),
            "--skip-tools",
            "--skip-token-check",
        ],
        linked_worktree,
        "\n\n\n\n\n\n\n\n",
    )

    assert result.returncode == 0
    assert "Imported local .env values" in result.stdout
    assert (linked_worktree / ".tools").is_symlink()
    assert (linked_worktree / "foodbot.local.sqlite3").is_symlink()
    assert read_env(linked_worktree) == {
        "FOODBOT_ENV": "development",
        "TELEGRAM_BOT_TOKEN": "123456:test-token",
        "TELEGRAM_BOT_USERNAME": "foodbot_dev",
        "DATABASE_PATH": "foodbot.local.sqlite3",
        "TELEGRAM_ADMIN_IDS": "42",
        "FOODBOT_TIMEZONE": "Europe/Belgrade",
        "SPLITWISE_API_KEY": "dev-splitwise-key",
        "SPLITWISE_GROUP_ID": "55",
    }


def test_setup_dev_keeps_existing_values_on_empty_answers(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "TELEGRAM_BOT_TOKEN=existing-token",
                "TELEGRAM_BOT_USERNAME=existing_dev_bot",
                "DATABASE_PATH=old.sqlite3",
                "TELEGRAM_ADMIN_IDS=42",
                "FOODBOT_TIMEZONE=UTC",
                "SPLITWISE_API_KEY=existing-splitwise-key",
                "SPLITWISE_GROUP_ID=1001",
            ]
        ),
        encoding="utf-8",
    )

    result = run_env_setup(tmp_path, "\n\n\n\n\n")

    assert read_env(tmp_path) == {
        "FOODBOT_ENV": "development",
        "TELEGRAM_BOT_TOKEN": "existing-token",
        "TELEGRAM_BOT_USERNAME": "existing_dev_bot",
        "DATABASE_PATH": "foodbot.local.sqlite3",
        "TELEGRAM_ADMIN_IDS": "42",
        "FOODBOT_TIMEZONE": "Europe/Belgrade",
        "SPLITWISE_API_KEY": "existing-splitwise-key",
        "SPLITWISE_GROUP_ID": "1001",
    }
    assert "existing-token" not in result.stdout
    assert "existing-token" not in result.stderr
    assert "Get the token from Telegram @BotFather" not in result.stdout
    assert "Use current TELEGRAM_BOT_USERNAME? [y/n]" in result.stdout
    assert "Use current TELEGRAM_ADMIN_IDS? [y/n]" in result.stdout
    assert "[Y/n]" not in result.stdout
    assert "[y/N]" not in result.stdout


def test_setup_dev_reads_existing_env_with_export_spaces_and_quotes(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                'export TELEGRAM_BOT_TOKEN = "existing-token"',
                'export TELEGRAM_BOT_USERNAME = "@existing_dev_bot"',
                "DATABASE_PATH=old.sqlite3",
                "TELEGRAM_ADMIN_IDS = '42'",
                "FOODBOT_TIMEZONE=UTC",
                'SPLITWISE_API_KEY = "existing-splitwise-key"',
                "SPLITWISE_GROUP_ID = '1001'",
            ]
        ),
        encoding="utf-8",
    )

    result = run_env_setup(tmp_path, "\n\n\n\n\n")

    assert read_env(tmp_path) == {
        "FOODBOT_ENV": "development",
        "TELEGRAM_BOT_TOKEN": "existing-token",
        "TELEGRAM_BOT_USERNAME": "existing_dev_bot",
        "DATABASE_PATH": "foodbot.local.sqlite3",
        "TELEGRAM_ADMIN_IDS": "42",
        "FOODBOT_TIMEZONE": "Europe/Belgrade",
        "SPLITWISE_API_KEY": "existing-splitwise-key",
        "SPLITWISE_GROUP_ID": "1001",
    }
    assert "existing-token" not in result.stdout
    assert "existing-token" not in result.stderr
    assert "Get the token from Telegram @BotFather" not in result.stdout
    assert "Use current TELEGRAM_BOT_USERNAME? [y/n]" in result.stdout
    assert "Use current TELEGRAM_ADMIN_IDS? [y/n]" in result.stdout


def test_setup_dev_replaces_token_and_clears_admin_ids(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "TELEGRAM_BOT_TOKEN=old-token",
                "TELEGRAM_BOT_USERNAME=old_dev_bot",
                "DATABASE_PATH=old.sqlite3",
                "TELEGRAM_ADMIN_IDS=42",
                "FOODBOT_TIMEZONE=UTC",
                "SPLITWISE_API_KEY=old-splitwise-key",
                "SPLITWISE_GROUP_ID=1001",
            ]
        ),
        encoding="utf-8",
    )

    result = run_env_setup(tmp_path, "new-token\nn\nnew_dev_bot\nn\nnew-splitwise-key\n")

    assert read_env(tmp_path) == {
        "FOODBOT_ENV": "development",
        "TELEGRAM_BOT_TOKEN": "new-token",
        "TELEGRAM_BOT_USERNAME": "new_dev_bot",
        "DATABASE_PATH": "foodbot.local.sqlite3",
        "TELEGRAM_ADMIN_IDS": "",
        "FOODBOT_TIMEZONE": "Europe/Belgrade",
        "SPLITWISE_API_KEY": "new-splitwise-key",
        "SPLITWISE_GROUP_ID": "1001",
    }
    assert "old-token" not in result.stdout
    assert "old-token" not in result.stderr
    assert "new-token" not in result.stdout
    assert "new-token" not in result.stderr
    assert "new-splitwise-key" not in result.stdout
    assert "new-splitwise-key" not in result.stderr


def test_setup_dev_keeps_existing_env_when_interrupted_before_replace(tmp_path: Path) -> None:
    existing_env = "\n".join(
        [
            "TELEGRAM_BOT_TOKEN=old-token",
            "TELEGRAM_BOT_USERNAME=old_dev_bot",
            "DATABASE_PATH=old.sqlite3",
            "TELEGRAM_ADMIN_IDS=42",
            "FOODBOT_TIMEZONE=UTC",
            "SPLITWISE_API_KEY=old-splitwise-key",
            "SPLITWISE_GROUP_ID=1001",
        ]
    )
    (tmp_path / ".env").write_text(existing_env, encoding="utf-8")

    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    fake_mv = fake_bin / "mv"
    fake_mv.write_text(
        "#!/usr/bin/env bash\n"
        'kill -INT "$PPID"\n'
        "sleep 1\n"
        "exit 130\n",
        encoding="utf-8",
    )
    fake_mv.chmod(0o755)

    result = subprocess.run(
        ["bash", str(SETUP_DEV), "--env-only", "--skip-token-check"],
        cwd=tmp_path,
        input="new-token\nn\nnew_dev_bot\nn\nnew-splitwise-key\n",
        text=True,
        capture_output=True,
        check=False,
        env={"PATH": f"{fake_bin}:{ROOT / '.venv' / 'bin'}:/usr/bin:/bin:/usr/sbin:/sbin"},
    )

    assert result.returncode == 130
    assert (tmp_path / ".env").read_text(encoding="utf-8") == existing_env
    assert not list(tmp_path.glob(".env.tmp.*"))
    assert "new-token" not in result.stdout
    assert "new-token" not in result.stderr
    assert "new-splitwise-key" not in result.stdout
    assert "new-splitwise-key" not in result.stderr


def test_setup_dev_reset_env_ignores_existing_values(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "TELEGRAM_BOT_TOKEN=old-token",
                "TELEGRAM_BOT_USERNAME=old_dev_bot",
                "DATABASE_PATH=old.sqlite3",
                "TELEGRAM_ADMIN_IDS=42",
                "FOODBOT_TIMEZONE=UTC",
                "SPLITWISE_API_KEY=old-splitwise-key",
                "SPLITWISE_GROUP_ID=1001",
            ]
        ),
        encoding="utf-8",
    )

    result = run_env_setup(
        tmp_path,
        "fresh-token\nfresh_dev_bot\nn\nfresh-splitwise-key\n",
        "--reset-env",
    )

    assert read_env(tmp_path) == {
        "FOODBOT_ENV": "development",
        "TELEGRAM_BOT_TOKEN": "fresh-token",
        "TELEGRAM_BOT_USERNAME": "fresh_dev_bot",
        "DATABASE_PATH": "foodbot.local.sqlite3",
        "TELEGRAM_ADMIN_IDS": "",
        "FOODBOT_TIMEZONE": "Europe/Belgrade",
        "SPLITWISE_API_KEY": "fresh-splitwise-key",
        "SPLITWISE_GROUP_ID": "",
    }
    assert "old-token" not in result.stdout
    assert "old-token" not in result.stderr
    assert "fresh-token" not in result.stdout
    assert "fresh-token" not in result.stderr
    assert "fresh-splitwise-key" not in result.stdout
    assert "fresh-splitwise-key" not in result.stderr


def test_setup_dev_requires_splitwise_api_key(tmp_path: Path) -> None:
    result = subprocess.run(
        ["bash", str(SETUP_DEV), "--env-only", "--skip-token-check"],
        cwd=tmp_path,
        input="123456:test-token\ndev_bot\nn\n\n",
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "SPLITWISE_API_KEY is required." in result.stderr
    assert not (tmp_path / ".env").exists()


def test_setup_dev_detects_bot_username_from_verified_token(tmp_path: Path) -> None:
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    fake_curl = fake_bin / "curl"
    fake_curl.write_text(
        "#!/usr/bin/env bash\n"
        "printf '%s\\n' "
        "'{\"ok\":true,\"result\":{\"id\":123456789,\"username\":\"foodbot_dev\"}}'\n",
        encoding="utf-8",
    )
    fake_curl.chmod(0o755)

    result = subprocess.run(
        ["bash", str(SETUP_DEV), "--env-only"],
        cwd=tmp_path,
        input="123456789:abcdefghijklmnopqrstuvwxyzABCDE\n\nn\ndev-splitwise-key\n",
        text=True,
        capture_output=True,
        check=True,
        env={"PATH": f"{fake_bin}:/usr/bin:/bin:/usr/sbin:/sbin"},
    )

    assert read_env(tmp_path) == {
        "FOODBOT_ENV": "development",
        "TELEGRAM_BOT_TOKEN": "123456789:abcdefghijklmnopqrstuvwxyzABCDE",
        "TELEGRAM_BOT_USERNAME": "foodbot_dev",
        "DATABASE_PATH": "foodbot.local.sqlite3",
        "TELEGRAM_ADMIN_IDS": "",
        "FOODBOT_TIMEZONE": "Europe/Belgrade",
        "SPLITWISE_API_KEY": "dev-splitwise-key",
        "SPLITWISE_GROUP_ID": "",
    }
    assert "Telegram bot username: @foodbot_dev" in result.stdout
    assert "123456789:abcdefghijklmnopqrstuvwxyzABCDE" not in result.stdout
    assert "dev-splitwise-key" not in result.stdout


def test_setup_dev_rejects_production_telegram_bot_token(tmp_path: Path) -> None:
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    fake_curl = fake_bin / "curl"
    fake_curl.write_text(
        "#!/usr/bin/env bash\n"
        "printf '%s\\n' "
        "'{\"ok\":true,\"result\":{\"id\":8490386710,\"username\":\"jos_jedan_bot\"}}'\n",
        encoding="utf-8",
    )
    fake_curl.chmod(0o755)

    result = subprocess.run(
        ["bash", str(SETUP_DEV), "--env-only"],
        cwd=tmp_path,
        input="123456789:abcdefghijklmnopqrstuvwxyzABCDE\n",
        text=True,
        capture_output=True,
        check=False,
        env={"PATH": f"{fake_bin}:/usr/bin:/bin:/usr/sbin:/sbin"},
    )

    assert result.returncode == 1
    assert "TELEGRAM_BOT_TOKEN belongs to the production bot" in result.stderr
    assert "Use a separate development bot token" in result.stderr
    assert not (tmp_path / ".env").exists()


def test_setup_dev_rejects_invalid_token_without_skip(tmp_path: Path) -> None:
    result = subprocess.run(
        ["bash", str(SETUP_DEV), "--env-only"],
        cwd=tmp_path,
        input="dummy-token\n",
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "does not look like a real BotFather token" in result.stderr
    assert not (tmp_path / ".env").exists()


def test_setup_dev_verifies_valid_shape_token_without_extra_prompt(tmp_path: Path) -> None:
    result = subprocess.run(
        ["bash", str(SETUP_DEV), "--env-only"],
        cwd=tmp_path,
        input="123456789:abcdefghijklmnopqrstuvwxyzABCDE\n",
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Verify this bot token with Telegram now?" not in result.stdout
    assert "Continue with an unverified bot token?" not in result.stdout
    assert "Checking Telegram bot token..." in result.stdout
    assert not (tmp_path / ".env").exists()
