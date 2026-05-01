"""End-to-end behavior of /shared/<group> directories.

Per-group RWX shared dirs at /shared/<group> are set up by the chart with:

  - ownership root:users (uid=0, gid=100), mode 2775 (setgid on 'users')
  - pod runs with fsGroup=100 + NB_UMASK=0002 so new files are 664/775,
    group-writable, and inherit gid=100 by setgid propagation
  - only the groups a user belongs to are mounted (no cross-group leakage)
  - shared dir is RWX across all members of a group (multi-pod, multi-user)

Test usernames encode group membership via the test DummyAuthenticator
(see tests/e2e/fixtures/test-values.yaml):

    "alice-data"     -> User('alice', groups=['data'])
    "alice-data-ml"  -> User('alice', groups=['data','ml'])
    "bob-ml"         -> User('bob',   groups=['ml'])
"""

import pytest

# Constants used in assertions across the suite. They read out as English
# next to `==` so a failing assertion explains itself.
USERS_GID = 100               # Linux 'users' group; nebari's fsGroup
ROOT_UID = 0                  # init container chown's dir to root for setgid
SHARED_DIR_MODE = 0o2775      # rwxrwsr-x — setgid + group-writable
EXPECTED_FILE_MODE = 0o664    # under umask 0002
EXPECTED_DIR_MODE = 0o2775    # umask 0002 + setgid propagated from parent


# --- Helpers ---------------------------------------------------------------


def _write_under_pod_umask(user, shell_cmd):
    """Run `shell_cmd` with umask taken from NB_UMASK.

    `kubectl exec` starts a fresh shell that does NOT inherit the umask
    z2jh's start.sh applied to the kernel process — so tests have to
    re-apply it explicitly to observe the documented behavior.
    """
    rc, out = user.exec("bash", "-c", f'umask "$NB_UMASK"; {shell_cmd}')
    assert rc == 0, f"setup command failed (rc={rc}): {out}"


# --- Directory attributes (chart-rendered, before any user write) ----------


@pytest.mark.parametrize("group", ["data", "ml"])
def test_group_dir_is_root_users_with_setgid_2775(spawn_user, group):
    """Per-group dir is owned root:users, mode 2775. Setgid forces gid=100
    on every new file regardless of the creator's primary gid — this is
    what makes shared collaboration work across users."""
    u = spawn_user(f"alice-{group}")
    s = u.stat(f"/shared/{group}")
    assert s.uid == ROOT_UID
    assert s.gid == USERS_GID
    assert s.mode == SHARED_DIR_MODE


# --- Pod identity (groups + umask the chart configured) --------------------


def test_pod_is_member_of_users_group(spawn_user):
    """fsGroup=100 — pod's effective gids include 100, which is what
    grants it write access to the group-writable shared dirs."""
    u = spawn_user("alice-data")
    rc, out = u.exec("id", "-G")
    assert rc == 0
    assert str(USERS_GID) in out.split()


def test_pod_environment_sets_nb_umask_to_0002(spawn_user):
    """NB_UMASK=0002 is the env var z2jh's start.sh applies before exec'ing
    the kernel. The umask effect is covered by the file-mode test below;
    here we just pin the configuration contract."""
    u = spawn_user("alice-data")
    rc, out = u.exec("printenv", "NB_UMASK")
    assert rc == 0
    assert out == "0002"


# --- File/dir creation inherits group + umask ------------------------------


def test_new_file_is_group_writable_and_owned_by_users(spawn_user):
    """A file created in /shared/<group> ends up mode 664, gid 100. This
    is the core multi-tenancy invariant: any teammate can edit any other
    teammate's files without explicit coordination."""
    u = spawn_user("alice-data")
    _write_under_pod_umask(u, "touch /shared/data/file_from_alice")

    s = u.stat("/shared/data/file_from_alice")
    assert s.gid == USERS_GID
    assert s.mode == EXPECTED_FILE_MODE


def test_new_subdir_inherits_setgid_and_users_group(spawn_user):
    """A subdir created under a setgid parent inherits the setgid bit and
    gid=100. Without this, nested files would silently fall back to the
    user's primary gid and become invisible to teammates."""
    u = spawn_user("alice-data")
    _write_under_pod_umask(u, "mkdir /shared/data/subdir_from_alice")

    s = u.stat("/shared/data/subdir_from_alice")
    assert s.gid == USERS_GID
    assert s.mode == EXPECTED_DIR_MODE


# --- Multi-tenancy across users and groups ---------------------------------


def test_user_in_multiple_groups_sees_each_groups_dir(spawn_user):
    """A user who belongs to N groups gets N per-group dirs mounted, each
    of them writable. Group membership composes — there is no max."""
    u = spawn_user("alice-data-ml")

    for group in ("data", "ml"):
        path = f"/shared/{group}"
        assert u.path_exists(path), f"{path} should be mounted for alice"
        rc, out = u.exec("touch", f"{path}/probe-{group}")
        assert rc == 0, f"write to {path} failed: {out}"


def test_user_does_not_see_groups_they_dont_belong_to(spawn_user):
    """Group isolation is enforced at mount time: a user not in group X
    does not get /shared/X mounted at all (as opposed to mounted-but-
    unreadable). Cleaner failure mode and one less attack surface."""
    u = spawn_user("bob-ml")
    assert u.path_exists("/shared/ml")
    assert not u.path_exists("/shared/data")


def test_files_are_visible_and_writable_to_groupmates(spawn_user):
    """alice and carol both belong to 'data'. alice writes a file from
    her pod; carol reads + appends to it from hers. Same RWX PVC, same
    subPath, same setgid'd gid=100 — the actual collaboration story."""
    alice = spawn_user("alice-data")
    _write_under_pod_umask(
        alice, "echo hello-from-alice > /shared/data/handoff.txt"
    )

    carol = spawn_user("carol-data")
    rc, out = carol.exec("cat", "/shared/data/handoff.txt")
    assert rc == 0
    assert out == "hello-from-alice"

    rc, out = carol.exec(
        "bash", "-c", "echo carol-was-here >> /shared/data/handoff.txt"
    )
    assert rc == 0, f"carol could not append to alice's file: {out}"
