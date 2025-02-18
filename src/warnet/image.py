import sys

import click

from .image_build import build_image


@click.group(name="image")
def image():
    """Build a custom Warnet Bitcoin Core image"""


@image.command()
@click.option("--repo", required=True, type=str)
@click.option("--commit-sha", required=True, type=str)
@click.option("--registry", required=True, type=str)
@click.option(
    "--tags",
    required=True,
    type=str,
    help="Comma-separated list of full tags including image names",
)
@click.option("--build-args", required=False, type=str)
@click.option("--arches", required=False, type=str)
@click.option("--action", required=False, type=str, default="load")
def build(repo: str, commit_sha: str, registry: str, tags: str, build_args: str, arches: str, action: str) -> None:
    """
    Build bitcoind and bitcoin-cli from <repo> at <commit_sha> with the specified <tags>.
    Optionally deploy to remote registry using --action=push, otherwise image is loaded to local registry.

    Args:
        repo: Git repository URL
        commit_sha: Git commit hash to build
        registry: Docker registry to push to
        tags: Comma-separated list of full tags including image names
        build_args: Additional build arguments for Bitcoin Core compilation
        arches: Comma-separated list of target architectures (e.g. amd64, arm64, armhf)
        action: Build action (e.g. 'load' for local, 'push' for registry)
    """
    res = build_image(repo, commit_sha, registry, tags, build_args, arches, action)
    if not res:
        sys.exit(1)
