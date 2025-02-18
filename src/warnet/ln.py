import json
from typing import Optional

import click

from .k8s import (
    get_default_namespace_or,
    get_pod,
)
from .process import run_command


@click.group(name="ln")
def ln() -> None:
    """Control running lightning nodes"""


@ln.command(context_settings={"ignore_unknown_options": True})
@click.argument("pod", type=str)
@click.argument("method", type=str)
@click.argument("params", type=str, nargs=-1)  # this will capture all remaining arguments
@click.option("--namespace", default=None, show_default=True)
def rpc(pod: str, method: str, params: str, namespace: Optional[str]) -> None:
    """
    Call lightning cli rpc <command> on <ln pod name>

    Args:
        pod: Name of the lightning node pod
        method: RPC method to call
        params: Additional parameters for the RPC call
        namespace: Kubernetes namespace, uses default if None
    """
    print(_rpc(pod, method, params, namespace))


def _rpc(
    pod_name: str,
    method: str,
    params: str = "",
    namespace: Optional[str] = None
) -> str:
    """
    Execute an RPC command on a lightning node.

    Args:
        pod_name: Name of the lightning node pod
        method: RPC method to call
        params: Additional parameters for the RPC call
        namespace: Kubernetes namespace, uses default if None

    Returns:
        str: Output from the RPC command
    """
    pod = get_pod(pod_name)
    namespace = get_default_namespace_or(namespace)
    chain = pod.metadata.labels["chain"]
    cmd = f"kubectl -n {namespace} exec {pod_name} -- lncli --network {chain} {method} {' '.join(map(str, params))}"
    return run_command(cmd)


@ln.command()
@click.argument("pod", type=str)
def pubkey(pod: str) -> None:
    """
    Get lightning node pub key from <ln pod name>

    Args:
        pod: Name of the lightning node pod
    """
    print(_pubkey(pod))


def _pubkey(pod: str) -> str:
    """
    Get the public key of a lightning node.

    Args:
        pod: Name of the lightning node pod

    Returns:
        str: Node's public key
    """
    info = _rpc(pod, "getinfo")
    return json.loads(info)["identity_pubkey"]


@ln.command()
@click.argument("pod", type=str)
def host(pod: str) -> None:
    """
    Get lightning node host from <ln pod name>

    Args:
        pod: Name of the lightning node pod
    """
    print(_host(pod))


def _host(pod: str) -> str:
    """
    Get the host address of a lightning node.

    Args:
        pod: Name of the lightning node pod

    Returns:
        str: Node's host address or empty string if not found
    """
    info = _rpc(pod, "getinfo")
    uris = json.loads(info)["uris"]
    if uris and len(uris) >= 0:
        return uris[0].split("@")[1]
    else:
        return ""
