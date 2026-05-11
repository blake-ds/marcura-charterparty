"""Deterministic PDF clause extractor — PyMuPDF + bbox geometry.

Public API:

```python
from extractor import extract_clauses

clauses = extract_clauses("voyage-charter-example.pdf")
```
"""

from extractor.models import Clause, Section
from extractor.pipeline import extract_clauses

__all__ = ["Clause", "Section", "__version__", "extract_clauses"]
__version__ = "0.1.0"
