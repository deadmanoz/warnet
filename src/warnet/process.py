import subprocess


def run_command(command: str) -> str:
    """
    Run a command and return the output.

    Args:
        command: Command to run

    Returns:
        str: Output of the command

    Raises:
        Exception: If the command fails
    """
    result = subprocess.run(command, shell=True, capture_output=True, text=True, executable="bash")
    if result.returncode != 0:
        raise Exception(result.stderr)
    return result.stdout


def stream_command(command: str) -> bool:
    """
    Stream the output of a command.

    Args:
        command: Command to run

    Raises:
        Exception: If the command fails

    Returns:
        bool: True if the command was executed successfully
    """
    process = subprocess.Popen(
        ["bash", "-c", command],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )

    message = ""
    for line in iter(process.stdout.readline, ""):
        message += line
        print(line, end="")

    process.stdout.close()
    return_code = process.wait()

    if return_code != 0:
        raise Exception(message)
    return True
