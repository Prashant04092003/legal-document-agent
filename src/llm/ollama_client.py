import subprocess


def generate(prompt: str, model: str = "qwen2.5:7b") -> str:
    """
    Send a prompt to a local Ollama model and return its raw response.
    """

    result = subprocess.run(
        [
            "ollama",
            "run",
            model,
            "--format",
            "json",
            prompt,
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    return result.stdout.strip()