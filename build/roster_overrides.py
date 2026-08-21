"""Manual escape hatch for renames the automatic guard in `rename_guard.py`
can't safely catch. Add an entry here, with the reasoning and the
confirmed true launch date, whenever a spot-check finds one.

(Kharar/Panchkula, the original reason this file exists, are now caught
automatically by the exact-token-match rule in `_name_signature_match`
— left empty rather than removed so the mechanism is ready for the next
gap a spot-check turns up.)
"""

MANUAL_EXCLUDE_STORE_NAMES = set()
