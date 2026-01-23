
import sys
from pathlib import Path
import traceback

# Add src to path
src_path = Path(__file__).parent.parent / "src"
print(f"Adding to path: {src_path.absolute()}")
sys.path.insert(0, str(src_path))

try:
    print("Importing PhoneticLine...")
    from core.models import PhoneticLine, PhonemeType
    print("Import successful.")

    print("Importing ReclistParser...")
    from core.reclist_parser import ReclistParser
    print("Import successful.")

    print("Creating parser...")
    parser = ReclistParser()
    print("Parser created.")

    print("Parsing sample content...")
    lines = parser.parse_content("ba_be_bi_bo_bu_ba_b")
    print(f"Parsed {len(lines)} lines.")
    print(f"First line: {lines[0]}")
    
    print("SUCCESS: Basic parsing works.")

except Exception as e:
    print("ERROR OCCURRED:")
    traceback.print_exc()
