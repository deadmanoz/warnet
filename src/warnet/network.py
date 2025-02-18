import json
import shutil
from pathlib import Path

from rich import print

from .bitcoin import _rpc
from .constants import (
    NETWORK_DIR,
    PLUGINS_DIR,
    SCENARIOS_DIR,
)
from .k8s import get_mission


def copy_defaults(
    directory: Path,
    target_subdir: str,
    source_path: Path,
    exclude_list: list[str]
) -> None:
    """
    Generic function to copy default files and directories.

    Args:
        directory: Base directory to copy to
        target_subdir: Name of target subdirectory
        source_path: Source path to copy from
        exclude_list: List of patterns to exclude from copying
    """
    target_dir = directory / target_subdir
    target_dir.mkdir(parents=True, exist_ok=True)
    print(f"Creating directory: {target_dir}")

    shutil.copytree(
        src=source_path,
        dst=target_dir,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(*exclude_list),
    )

    print(f"Finished copying files to {target_dir}")


def copy_network_defaults(directory: Path) -> None:
    """
    Create the project structure for a warnet project's network.

    Args:
        directory: Base directory for the warnet project
    """
    copy_defaults(
        directory,
        NETWORK_DIR.name,
        NETWORK_DIR,
        ["__pycache__", "__init__.py"],
    )


def copy_scenario_defaults(directory: Path) -> None:
    """
    Create the project structure for a warnet project's scenarios.

    Args:
        directory: Base directory for the warnet project
    """
    copy_defaults(
        directory,
        SCENARIOS_DIR.name,
        SCENARIOS_DIR,
        ["__pycache__", "test_scenarios"],
    )


def copy_plugins_defaults(directory: Path) -> None:
    """
    Create the project structure for a warnet project's plugins.

    Args:
        directory: Base directory for the warnet project
    """
    copy_defaults(
        directory,
        PLUGINS_DIR.name,
        PLUGINS_DIR,
        ["__pycache__", "__init__"],
    )


def is_connection_manual(peer: dict) -> bool:
    """
    Check if a peer connection is manual.

    Args:
        peer: Peer information dictionary

    Returns:
        bool: True if connection is manual, False otherwise
    """
    # newer nodes specify a "connection_type"
    return bool(peer.get("connection_type") == "manual" or peer.get("addnode") is True)


def _connected(end: str = "\n") -> bool:
    """
    Check if all tanks in the network are properly connected.

    Args:
        end: String to append at end of print statements

    Returns:
        bool: True if all tanks are connected with expected peers, False otherwise
    """
    tanks = get_mission("tank")
    for tank in tanks:
        # Get actual
        try:
            peerinfo = json.loads(
                _rpc(tank.metadata.name, "getpeerinfo", "", namespace=tank.metadata.namespace)
            )
            actual = 0
            for peer in peerinfo:
                if is_connection_manual(peer):
                    actual += 1
            expected = int(tank.metadata.annotations["init_peers"])
            print(
                f"Tank {tank.metadata.name} peers expected: {expected}, actual: {actual}", end=end
            )
            # Even if more edges are specified, bitcoind only allows
            # 8 manual outbound connections
            if min(8, expected) > actual:
                print("\nNetwork not connected")
                return False
        except Exception:
            return False
    print("Network connected                                                           ")
    return True
