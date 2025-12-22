"""
DoD Confirmer - Interactive CLI confirmation for Definition of Done

Provides interactive prompts for users to:
- Review extracted/generated DoD
- Confirm, modify, or add items
- Skip DoD validation entirely
"""

import logging
import sys
from typing import List, Optional, Tuple

from ..models import (
    DefinitionOfDone,
    DoDItem,
    DoDSource,
    DoDFormat,
    DoDCriterionType,
)

logger = logging.getLogger(__name__)


class DoDConfirmer:
    """
    Interactive CLI confirmation for Definition of Done.

    Allows users to review, modify, and confirm DoD items
    before the review process continues.
    """

    # Criterion type shortcuts for user input
    TYPE_SHORTCUTS = {
        'f': DoDCriterionType.FUNCTIONAL,
        's': DoDCriterionType.SECURITY,
        't': DoDCriterionType.TEST,
        'd': DoDCriterionType.DOCUMENTATION,
        'p': DoDCriterionType.PERFORMANCE,
        'q': DoDCriterionType.CODE_QUALITY,
    }

    def __init__(self, input_func=None, output_func=None):
        """
        Initialize DoD confirmer.

        Args:
            input_func: Custom input function (default: built-in input)
            output_func: Custom output function (default: print)
        """
        self.input_func = input_func or input
        self.output_func = output_func or print

    def confirm(
        self,
        dod: Optional[DefinitionOfDone],
        source_description: str = "",
    ) -> Tuple[Optional[DefinitionOfDone], bool]:
        """
        Interactively confirm DoD with user.

        Args:
            dod: Current DoD (may be None if not found/generated)
            source_description: Description of where DoD came from

        Returns:
            Tuple of (confirmed DoD, should_skip)
            - If user confirms, returns (dod, False)
            - If user skips, returns (None, True)
        """
        self._print_header()

        if dod and dod.items:
            self._print_current_dod(dod, source_description)
            return self._confirm_existing(dod)
        else:
            self._output("\n  No Definition of Done found.\n")
            return self._prompt_create_new()

    def _print_header(self):
        """Print the confirmation header."""
        self._output("\n" + "=" * 60)
        self._output("DEFINITION OF DONE - CONFIRMATION")
        self._output("=" * 60)

    def _print_current_dod(
        self,
        dod: DefinitionOfDone,
        source_description: str,
    ):
        """Print the current DoD for review."""
        source_info = f" (from {dod.source.value})" if dod.source else ""
        self._output(f"\nCurrent DoD{source_info}:")
        self._output("-" * 40)

        for i, item in enumerate(dod.items, 1):
            type_label = f"[{item.criterion_type.value[:4].upper()}]"
            self._output(f"  {i}. {type_label} {item.description}")

        self._output("-" * 40)
        self._output(f"Total: {len(dod.items)} items\n")

    def _confirm_existing(
        self,
        dod: DefinitionOfDone,
    ) -> Tuple[Optional[DefinitionOfDone], bool]:
        """Confirm or modify existing DoD."""
        self._output("Options:")
        self._output("  [c] Confirm and continue")
        self._output("  [e] Edit items")
        self._output("  [a] Add new item")
        self._output("  [r] Remove item")
        self._output("  [s] Skip DoD validation")
        self._output("  [q] Quit review")

        while True:
            choice = self._input("\nChoice [c/e/a/r/s/q]: ").strip().lower()

            if choice == 'c':
                # Confirm
                confirmed_dod = DefinitionOfDone(
                    items=dod.items,
                    source=dod.source,
                    format=dod.format,
                    confirmed=True,
                    generated_from=dod.generated_from,
                    raw_text=dod.raw_text,
                )
                self._output("\n[OK] DoD confirmed.\n")
                return confirmed_dod, False

            elif choice == 'e':
                # Edit
                dod = self._edit_items(dod)
                self._print_current_dod(dod, "")

            elif choice == 'a':
                # Add
                new_item = self._prompt_new_item()
                if new_item:
                    dod.items.append(new_item)
                    self._output(f"  Added: {new_item.description}")
                self._print_current_dod(dod, "")

            elif choice == 'r':
                # Remove
                dod = self._remove_item(dod)
                self._print_current_dod(dod, "")

            elif choice == 's':
                # Skip
                self._output("\n[SKIP] DoD validation will be skipped.\n")
                return None, True

            elif choice == 'q':
                # Quit
                self._output("\n[ABORT] Review cancelled.\n")
                raise KeyboardInterrupt("User cancelled review")

            else:
                self._output("  Invalid choice. Please try again.")

    def _prompt_create_new(self) -> Tuple[Optional[DefinitionOfDone], bool]:
        """Prompt user to create new DoD or skip."""
        self._output("Options:")
        self._output("  [c] Create DoD manually")
        self._output("  [s] Skip DoD validation")
        self._output("  [q] Quit review")

        while True:
            choice = self._input("\nChoice [c/s/q]: ").strip().lower()

            if choice == 'c':
                items = self._prompt_multiple_items()
                if items:
                    dod = DefinitionOfDone(
                        items=items,
                        source=DoDSource.MANUAL,
                        format=DoDFormat.CHECKLIST,
                        confirmed=True,
                    )
                    self._output(f"\n[OK] Created DoD with {len(items)} items.\n")
                    return dod, False
                else:
                    self._output("  No items added.")

            elif choice == 's':
                self._output("\n[SKIP] DoD validation will be skipped.\n")
                return None, True

            elif choice == 'q':
                self._output("\n[ABORT] Review cancelled.\n")
                raise KeyboardInterrupt("User cancelled review")

            else:
                self._output("  Invalid choice. Please try again.")

    def _edit_items(self, dod: DefinitionOfDone) -> DefinitionOfDone:
        """Edit existing DoD items."""
        self._output("\nEdit items (press Enter to keep current):")

        new_items = []
        for i, item in enumerate(dod.items, 1):
            self._output(f"\n  Item {i}: {item.description}")
            self._output(f"  Type: {item.criterion_type.value}")

            new_desc = self._input("  New description (Enter=keep): ").strip()
            if new_desc:
                item = DoDItem(
                    description=new_desc,
                    criterion_type=item.criterion_type,
                )

            type_input = self._input("  New type [f/s/t/d/p/q] (Enter=keep): ").strip().lower()
            if type_input in self.TYPE_SHORTCUTS:
                item = DoDItem(
                    description=item.description,
                    criterion_type=self.TYPE_SHORTCUTS[type_input],
                )

            new_items.append(item)

        return DefinitionOfDone(
            items=new_items,
            source=dod.source,
            format=dod.format,
            confirmed=False,
            generated_from=dod.generated_from,
            raw_text=dod.raw_text,
        )

    def _remove_item(self, dod: DefinitionOfDone) -> DefinitionOfDone:
        """Remove an item from DoD."""
        if not dod.items:
            self._output("  No items to remove.")
            return dod

        try:
            idx_str = self._input(f"  Item number to remove (1-{len(dod.items)}): ").strip()
            idx = int(idx_str) - 1
            if 0 <= idx < len(dod.items):
                removed = dod.items.pop(idx)
                self._output(f"  Removed: {removed.description}")
            else:
                self._output("  Invalid item number.")
        except ValueError:
            self._output("  Invalid input.")

        return dod

    def _prompt_new_item(self) -> Optional[DoDItem]:
        """Prompt user for a new DoD item."""
        self._output("\nAdd new DoD item:")
        self._output("  Types: [f]unctional, [s]ecurity, [t]est, [d]ocs, [p]erf, [q]uality")

        desc = self._input("  Description: ").strip()
        if not desc:
            return None

        type_input = self._input("  Type [f/s/t/d/p/q]: ").strip().lower()
        criterion_type = self.TYPE_SHORTCUTS.get(type_input, DoDCriterionType.FUNCTIONAL)

        return DoDItem(
            description=desc,
            criterion_type=criterion_type,
        )

    def _prompt_multiple_items(self) -> List[DoDItem]:
        """Prompt user for multiple DoD items."""
        self._output("\nEnter DoD items (empty line to finish):")
        self._output("  Types: [f]unctional, [s]ecurity, [t]est, [d]ocs, [p]erf, [q]uality")

        items = []
        item_num = 1

        while True:
            desc = self._input(f"\n  Item {item_num} description (Enter=done): ").strip()
            if not desc:
                break

            type_input = self._input("  Type [f/s/t/d/p/q]: ").strip().lower()
            criterion_type = self.TYPE_SHORTCUTS.get(type_input, DoDCriterionType.FUNCTIONAL)

            items.append(DoDItem(
                description=desc,
                criterion_type=criterion_type,
            ))
            item_num += 1

        return items

    def _input(self, prompt: str) -> str:
        """Get input from user."""
        try:
            return self.input_func(prompt)
        except EOFError:
            return ""

    def _output(self, message: str):
        """Output message to user."""
        self.output_func(message)
