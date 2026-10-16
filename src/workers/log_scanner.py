import asyncio
from typing import List, Dict, Any
from src.telemetry import tracer

# Entry point pass this, object. The rest of the file is functional to one task.
class LogScannerWorker:
    def __init__(self, max_line_length: int = 4096):
        self.max_line_length = max_line_length



def build_bad_char_table(pattern: str) -> Dict[str, int]:
  # Pre-computes the bad chars, jumps table for a target pattern. Time complexity is equal to O(m) where m = length of pattern
    table = {}
    pattern_len = len(pattern)
    for i in range(pattern_len - 1):
        table[pattern[i]] = pattern_len - 1 - i
    return table

def boyer_moore_search(text: str, pattern: str, bad_char_table: Dict[str, int]) -> List[int]:
    # The main algorithm, return indices where pattern starts.
    pattern_len = len(pattern)
    text_len = len(text)
    
    if pattern_len == 0 or text_len < pattern_len:
        return []

    matches = []
    shift = 0

    while shift <= (text_len - pattern_len):
        j = pattern_len - 1

        # Match from right to left (Bijective)
        while j >= 0 and pattern[j] == text[shift + j]:
            j -= 1

        if j < 0:
            matches.append(shift)
            # Shift pattern past this match, based on bad character or 1
            next_char = text[shift + pattern_len] if (shift + pattern_len) < text_len else ''
            shift += bad_char_table.get(next_char, pattern_len)
        else:
            bad_char = text[shift + j]
            # Pre-computed bad character skip or it defaults to pattern length
            skip = bad_char_table.get(bad_char, pattern_len)
            shift += max(1, skip)

    return matches

def scan_file_stream(file_path: str, pattern: str) -> List[Dict[str, Any]]:
    # Reads line by line, without loading the entire thing into RAM. Applies Booyer-Moore matching on each line.
    bad_char_table = build_bad_char_table(pattern)
    hits = []

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for line_num, line in enumerate(f, start=1):
                matches = boyer_moore_search(line, pattern, bad_char_table)
                if matches:
                    hits.append({
                        "line": line_num,
                        "match_count": len(matches),
                        "content": line.strip()
                    })
    except Exception as e:
        tracer.log("LOG_WORKER", f"Error opening the log file {file_path}: {str(e)}")

    return hits

async def scan_log_async(file_path: str, pattern: str) -> List[Dict[str, Any]]:
    """
    Async function offloading file I/O to worker thread to keep the main loop unblocked.
    """
    tracer.log("LOG_WORKER", f"Initiating Boyer-Moore scan on '{file_path}' for pattern: '{pattern}'")
    
    # Run blocking file |read| in threadpool
    results = await asyncio.to_thread(scan_file_stream, file_path, pattern)
    
    tracer.log("LOG_WORKER", f"Scan complete for '{file_path}'. Hits found: {len(results)}")
    return results