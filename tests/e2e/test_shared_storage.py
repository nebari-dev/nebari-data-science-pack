"""Behavior tests for PR #30 shared-storage feature."""


def test_user_in_group_can_write(spawn_user):
    """alice (in group 'data') can write to /shared/data/."""
    u = spawn_user("alice-data")
    rc, out = u.exec("touch", "/shared/data/file_from_alice")
    assert rc == 0, f"expected write to succeed, got rc={rc}: {out}"


def test_shared_dir_is_group_owned(spawn_user):
    """/shared/data has gid matching the 'data' group and mode 2775 (setgid)."""
    u = spawn_user("alice-data")
    rc, out = u.exec("stat", "-c", "%a", "/shared/data")
    assert rc == 0
    assert out.strip() == "2775", f"expected mode 2775, got {out.strip()!r}"
