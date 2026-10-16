import asyncio
from typing import List, Dict, Any, Optional
from src.telemetry import tracer

# Entry point for Git operations boundary.
class Gitworker:
    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
    
def lookup_commit_by_hash(commit_hash: str, commit_index: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not commit_hash:
        return None
    return commit_index.get(commit_hash)

def filter_commits_by_filepath(file_path: str, commit_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not file_path:
        return []

    matches = []
    for commit in commit_history:
        changed_files = commit.get("files_changed", [])
        if any(file_path in f for f in changed_files):
            matches.append(commit)
        return matches
    
def parse_commit_payload(raw_commit: Dict[str, Any]) -> Dict[str, Any]:
    # Formats raw commit data into a clean verifiable structure.
    return {
        "sha": raw_commit.get("sha", "UNKNOWN"),
        "author": raw_commit.get("author", "UNKNOWN"),
        "timestamp": raw_commit.get("timestamp", ""),
        "message": raw_commit.get("message", ""),
        "files_changed": raw_commit.get("files_changed", []),
        "summary": raw_commit.get("summary", "")
    }

async def fetch_git_context_async(
    target_sha: Optional[str], 
    target_file: Optional[str], 
    commit_index: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
   
    tracer.log("GIT_WORKER", f"Executing Git lookup for SHA: '{target_sha}' / File: '{target_file}'")
    
    # Run hash lookup and path filter, offload in threadpool to prevent loop blocks.
    def _run_git_search():
        result = {
            "exact_commit": None,
            "path_matches": []
        }
        
        if target_sha:
            commit_data = lookup_commit_by_hash(target_sha, commit_index)
            if commit_data:
                result["exact_commit"] = parse_commit_payload(commit_data)

        if target_file:
            all_commits = list(commit_index.values())
            matched = filter_commits_by_filepath(target_file, all_commits)
            result["path_matches"] = [parse_commit_payload(c) for c in matched]

        return result

    git_data = await asyncio.to_thread(_run_git_search)
    
    has_exact = git_data["exact_commit"] is not None
    num_matches = len(git_data["path_matches"])
    tracer.log("GIT_WORKER", f"Git lookup complete. Exact match: {has_exact}, Path matches: {num_matches}")
    
    return git_data