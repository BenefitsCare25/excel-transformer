# Upload Errors Analysis - December 2025

## Summary
Two critical errors preventing file uploads:
1. **Legacy Excel Format (.xls) Not Supported** - Income IHP file
2. **Index Mismatch in Termination Filtering** - Singlife PCP file

---

## Error 1: Income - IHP - December 2025.xls

### Error Message
```
BadZipFile: File is not a zip file
```

### Root Cause
- **Location**: `backend/app.py` line 1251
- **Issue**: Code uses `openpyxl.load_workbook()` unconditionally to check for Alliance-Tokio format
- **Problem**: `.xls` files (legacy Excel 97-2003 format) are NOT zip-based
  - `.xls` uses BIFF (Binary Interchange File Format)
  - `.xlsx` uses Office Open XML (zip-based)
  - `openpyxl` only supports `.xlsx` files

### Code Analysis
```python
# Line 1250-1251
import openpyxl
wb = openpyxl.load_workbook(input_path)  # FAILS for .xls files
```

### Solution
**Option 1: Skip Alliance-Tokio check for .xls files**
```python
import openpyxl

# Check file extension first
file_extension = os.path.splitext(input_path)[1].lower()

if file_extension == '.xlsx':
    # Only try openpyxl for .xlsx files
    wb = openpyxl.load_workbook(input_path)
    ws = wb[sheet_name]
    is_alliance_tokio = ExcelTransformer.detect_alliance_tokio_format(ws)
else:
    # .xls files don't support Alliance-Tokio format (which uses merged cells)
    is_alliance_tokio = False
```

**Option 2: Install xlrd for .xls support**
- Add `xlrd` to requirements.txt
- Use pandas engine parameter: `pd.read_excel(file, engine='xlrd')`

### Recommendation
Use **Option 1** - it's simpler and doesn't require additional dependencies. Alliance-Tokio format uses merged cells which is a modern Excel feature unlikely to appear in legacy .xls files.

---

## Error 2: Singlife PCP Panel Specialist DECEMBER 2025 - error.xlsx

### Error Message
```
IndexError: single positional indexer is out-of-bounds
```

### Root Cause
- **Location**: `backend/app.py` line 1461
- **Issue**: Index mismatch between `df_transformed` and `df_source`
- **Problem**: Iterating over `df_transformed.iterrows()` but accessing `df_source.iloc[idx]`

### Code Analysis
```python
# Line 1459-1461
for idx, row in df_transformed.iterrows():  # idx comes from df_transformed
    # Normalize provider code and postal code for consistent matching
    provider_code = ExcelTransformer.normalize_code(df_source.iloc[idx][clinic_id_col])  # FAILS - idx out of bounds
```

### Why This Fails
1. `df_transformed.iterrows()` returns the **DataFrame's index values**, not sequential integers
2. If `df_transformed` has been filtered/reset, its index might be: `[0, 1, 5, 10, 15]` (non-sequential)
3. `df_source.iloc[15]` might not exist if `df_source` only has 10 rows
4. `df_transformed` and `df_source` may have different row counts

### File-Specific Analysis
**Singlife file structure:**
- Panel sheet: 1,331 rows (including headers)
- Terminated sheet: 167 rows
- Header at row 1, data starts at row 2
- After processing, `df_source` might have ~1,325 rows
- But `df_transformed` indices could be non-sequential if any filtering occurred

### Solution
**Use `.loc[]` with index values instead of `.iloc[]` with positions:**

```python
# BEFORE (BROKEN):
for idx, row in df_transformed.iterrows():
    provider_code = ExcelTransformer.normalize_code(df_source.iloc[idx][clinic_id_col])
    # idx might be 1500, but df_source only has 1000 rows

# AFTER (FIXED):
for idx, row in df_transformed.iterrows():
    # Use .loc[] to access by index label, not position
    provider_code = ExcelTransformer.normalize_code(df_source.loc[idx][clinic_id_col])
    # Now idx=1500 will correctly access the row with index label 1500
```

### Why This Works
- `.iloc[idx]`: Position-based indexing (0, 1, 2, 3...)
- `.loc[idx]`: Label-based indexing (uses actual index values)
- When iterating with `.iterrows()`, `idx` is the **index label**, not the position

---

## Implementation Priority

### High Priority (Blocking uploads)
1. **Fix #2 first** - Changes one line, fixes Singlife files
   - File: `backend/app.py` line 1461
   - Change: `df_source.iloc[idx]` → `df_source.loc[idx]`

2. **Fix #1 second** - Add file extension check, fixes .xls files
   - File: `backend/app.py` line 1250-1251
   - Change: Wrap openpyxl code in file extension check

### Testing Steps
1. Apply Fix #2, test Singlife file upload
2. Apply Fix #1, test Income IHP file upload
3. Verify both files process successfully
4. Check other .xls files in sample data

---

## Additional Observations

### Income IHP File Structure
- 6 sheets: Singapore GP, JB GP PANEL, SP PANEL, TCM, PHYSIO, DENTAL
- Headers at varying rows (0, 4, 5, 7) depending on sheet
- PHYSIO sheet has header at row 0 (no disclaimer rows)
- All sheets follow standard IHP format (backend should handle them once .xls is supported)

### Singlife File Structure
- 2 sheets: Panel, Terminated
- Column names: PROVIDER CODE, SPECIALTY, CLINIC NAME, DOCTOR NAME, BLK, STREET NAME, UNIT NO, BUILDING NAME, POSTCODE, TELEPHONE
- Different from IHP format but has 'provider code' in column mapping (line 787)
- Termination logic should work once index mismatch is fixed

---

## Recommended Changes

### Change 1: Fix index mismatch (backend/app.py:1461)
```python
# OLD:
provider_code = ExcelTransformer.normalize_code(df_source.iloc[idx][clinic_id_col])

# NEW:
provider_code = ExcelTransformer.normalize_code(df_source.loc[idx][clinic_id_col])
```

### Change 2: Support .xls files (backend/app.py:1250-1254)
```python
# OLD:
import openpyxl
wb = openpyxl.load_workbook(input_path)
ws = wb[sheet_name]
is_alliance_tokio = ExcelTransformer.detect_alliance_tokio_format(ws)

# NEW:
import openpyxl
file_extension = os.path.splitext(input_path)[1].lower()

if file_extension == '.xlsx':
    # Only check for Alliance-Tokio format in .xlsx files
    wb = openpyxl.load_workbook(input_path)
    ws = wb[sheet_name]
    is_alliance_tokio = ExcelTransformer.detect_alliance_tokio_format(ws)
else:
    # Legacy .xls files don't support Alliance-Tokio merged cell format
    is_alliance_tokio = False
```

---

## Expected Outcomes

After applying both fixes:
- ✓ Income IHP file (.xls) should upload successfully
- ✓ All 6 sheets should be processed
- ✓ Singlife PCP file (.xlsx) should upload successfully
- ✓ Both Panel and Terminated sheets should be processed
- ✓ Termination filtering should work correctly
