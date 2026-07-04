"""
===========================================================================
MailCleaner

Module:
    Console Output

Purpose:
    Standardized console output helpers.

Author:
    Shrinidhi D C

Version:
    0.2.0
===========================================================================
"""

from __future__ import annotations


class Console:
    """Simple console output helper."""

    @staticmethod
    def separator() -> None:
        print("=" * 60)

    @staticmethod
    def title(text: str) -> None:
        Console.separator()
        print(text)
        Console.separator()

    @staticmethod
    def info(message: str) -> None:
        print(f"[INFO]    {message}")

    @staticmethod
    def success(message: str) -> None:
        print(f"[SUCCESS] {message}")

    @staticmethod
    def warning(message: str) -> None:
        print(f"[WARNING] {message}")

    @staticmethod
    def error(message: str) -> None:
        print(f"[ERROR]   {message}")


console = Console()