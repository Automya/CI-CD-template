"""Módulo de clientes para APIs externas."""

from .github_client import GitHubClient, IGitHubClient

__all__ = ["GitHubClient", "IGitHubClient"]
