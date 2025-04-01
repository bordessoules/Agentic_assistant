# tools/github_tool.py
"""Tool for interacting with GitHub repositories and users."""

import requests
import base64
import json
from agentic_assistant.tools.registry import tool
from agentic_assistant.config import GITHUB_PAT, GITHUB_RESULTS_LIMIT, HTTP_TIMEOUT, USER_AGENT

# --- Helper Functions ---

def _make_github_request(url: str, headers: dict, params: dict = None):
    """Makes a request to the GitHub API and handles basic error checking."""
    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=HTTP_TIMEOUT
        )
        response.raise_for_status()
        if response.status_code == 204:
            return {}
        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type:
            return response.json()
        else:
            # Return non-JSON as an error or raw content if needed by caller
            print(f"[GitHub Tool Warning] Non-JSON response from {url}. Content-Type: {content_type}")
            return {"warning": f"Unexpected content type received: {content_type}", "content": response.text}
    except requests.exceptions.RequestException as e:
        status_code = e.response.status_code if e.response is not None else "N/A"
        error_message = f"GitHub API request failed (Status: {status_code}): {str(e)}"
        try:
            if e.response is not None and "application/json" in e.response.headers.get("Content-Type", ""):
                error_detail = e.response.json().get("message", "No additional details")
                error_message += f". Detail: {error_detail}"
            elif e.response is not None:
                 error_message += f". Response Text: {e.response.text[:200]}"
        except Exception as parse_err:
            print(f"Could not parse error response detail: {parse_err}")
        print(f"[GitHub Tool Error] Request URL: {e.request.url if e.request else 'N/A'}, Status: {status_code}, Message: {error_message}")
        return {"error": error_message}
    except Exception as e:
        error_message = f"An unexpected error occurred during GitHub API request: {str(e)}"
        print(f"[GitHub Tool Error] {error_message}")
        return {"error": error_message}


def _list_user_repositories(owner: str, headers: dict):
    """Lists repositories accessible to the authenticated user, preferentially using the /user/repos endpoint."""

    # Common parameters for listing repos
    params = {
        "affiliation": "owner,collaborator,organization_member", # Be explicit about relationships
        "sort": "updated", # Sort by most recently updated
        "per_page": 100 # Fetch max per page
        # 'type': 'all' is default for /user/repos, not needed explicitly here
    }

    # --- Attempt 1: Use the /user/repos endpoint (best for authenticated user's view) ---
    auth_user_url = "https://api.github.com/user/repos"
    print(f"Attempting to list repos for authenticated user via: {auth_user_url} with params: {params}")
    auth_user_data = _make_github_request(auth_user_url, headers, params=params)

    all_repos_data = []

    # Prioritize results from /user/repos if successful and seems relevant
    # Heuristic: If the owner requested is likely the authenticated user (can't know for sure without another API call)
    # Let's assume for now that if this call works, it's the primary source.
    if isinstance(auth_user_data, list):
        print(f"Successfully fetched {len(auth_user_data)} repos using /user/repos endpoint.")
        all_repos_data = auth_user_data # Use this list primarily
    elif isinstance(auth_user_data, dict) and "error" in auth_user_data:
        print(f"/user/repos endpoint failed (Error: {auth_user_data.get('error')}). Will try specific user/org endpoints for '{owner}'.")
        # Fall through to try specific user/org endpoints
    else:
        print(f"Unexpected response format from /user/repos: {type(auth_user_data)}. Response: {str(auth_user_data)[:200]}")
        # Fall through

    # --- Attempt 2: Fallback/Specific User/Org (if /user/repos failed or returned nothing) ---
    # Only run this if the authenticated user call failed or returned nothing.
    if not all_repos_data:
        print(f"Falling back to specific user/org endpoints for '{owner}'.")
        user_url = f"https://api.github.com/users/{owner}/repos"
        # Add type=all here, as it's not default for /users/{owner}/repos
        user_params = params.copy()
        user_params["type"] = "all"
        print(f"Attempting to list repos for user '{owner}' using url: {user_url} with params: {user_params}")
        user_data = _make_github_request(user_url, headers, params=user_params)

        if isinstance(user_data, list):
            print(f"Successfully fetched {len(user_data)} repos from user endpoint for '{owner}'.")
            all_repos_data.extend(user_data) # Add to potentially empty list
        elif isinstance(user_data, dict) and "error" in user_data:
            print(f"User endpoint failed for '{owner}' (Error: {user_data.get('error')}). Will try organization endpoint.")
        else:
            print(f"Unexpected response format from user endpoint for {owner}: {type(user_data)}. Response: {str(user_data)[:200]}")

        # Try organization endpoint
        org_url = f"https://api.github.com/orgs/{owner}/repos"
        # Add type=all here too
        org_params = params.copy()
        org_params["type"] = "all"
        print(f"Attempting to list repos for organization '{owner}' using url: {org_url} with params: {org_params}")
        org_data = _make_github_request(org_url, headers, params=org_params)

        if isinstance(org_data, list):
            print(f"Successfully fetched {len(org_data)} repos from organization endpoint for '{owner}'.")
            # Combine results, avoiding duplicates based on 'full_name'
            existing_full_names = {repo.get("full_name") for repo in all_repos_data if repo and isinstance(repo, dict)}
            for repo in org_data:
                if repo and isinstance(repo, dict) and repo.get("full_name") not in existing_full_names:
                    all_repos_data.append(repo)
        elif isinstance(org_data, dict) and "error" in org_data:
             print(f"Organization endpoint failed or returned error for '{owner}' (Error: {org_data.get('error')}).")
             if not all_repos_data: # If we got nothing from user AND org failed
                  return {"error": f"Could not list repositories for user or organization '{owner}'. All specific endpoints failed or returned errors. Check PAT scope ('repo') and existence of user/org."}
        else:
            print(f"Unexpected response format from org endpoint for {owner}: {type(org_data)}. Response: {str(org_data)[:200]}")
            # Proceed if we got user data earlier

    # --- Process final list ---
    if not all_repos_data:
         print(f"No repository data retrieved after checking all relevant endpoints for '{owner}'.")
         return {"error": f"No repositories found or accessible for '{owner}' via any relevant endpoint."}

    # Process the combined/retrieved list
    repos = []
    processed_full_names = set()
    for repo_raw in all_repos_data:
         if not repo_raw or not isinstance(repo_raw, dict): continue
         full_name_raw = repo_raw.get("full_name")
         if not full_name_raw or full_name_raw in processed_full_names: continue

         # Filter here: Only include repos actually owned by the requested 'owner'
         # This is needed because /user/repos returns ALL accessible repos (collaborator, org member etc)
         if full_name_raw.split('/')[0].lower() != owner.lower():
             print(f"  Skipping '{full_name_raw}' as owner does not match requested '{owner}'.")
             continue

         repos.append({
             "full_name": full_name_raw,
             "name": repo_raw.get("name"),
             "description": repo_raw.get("description", "No description") or "No description",
             "url": repo_raw.get("html_url"),
             "stars": repo_raw.get("stargazers_count", 0),
             "private": repo_raw.get("private", False),
             "last_updated": repo_raw.get("updated_at")
         })
         processed_full_names.add(full_name_raw)

    # Sort by last updated descending
    repos.sort(key=lambda x: x.get("last_updated", ""), reverse=True)

    # Limit the number of results shown
    limited_repos = repos[:GITHUB_RESULTS_LIMIT]
    print(f"Processed {len(repos)} unique repos owned by '{owner}', returning {len(limited_repos)} after sorting.")
    # Adjust total count reporting if needed, maybe report total OWNED found vs total accessible found
    return {"repositories": limited_repos, "total_owned_found_in_batch": len(repos)}


def _get_repo_structure(owner: str, repo: str, path: str, headers: dict):
    """Fetches the structure (files/dirs) of a path in a repository."""
    path = path.strip('/') if path else ''
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    print(f"Attempting to get structure for {owner}/{repo}/{path} using url: {url}") # Debug print
    data = _make_github_request(url, headers)

    if "error" in data:
        return data
    if isinstance(data, dict) and "warning" in data: # Pass warnings through
        print(f"Warning from _make_github_request: {data['warning']}")

    if isinstance(data, list):
        structure = [
            {"name": item["name"], "type": item["type"], "path": item["path"]}
            for item in data if isinstance(item, dict) # Ensure item is dict
        ]
        return {"structure": structure}
    elif isinstance(data, dict) and data.get("type") == "file":
         # If the path given was actually a file, return error specific to structure listing
         print(f"Path '{path}' in {owner}/{repo} is a file, not a directory.")
         return {"error": f"Path '{path}' is a file. Use 'get_file_content' to read its content."}
    else:
        print(f"Path '{path}' in {owner}/{repo} is not a directory or recognizable structure (response type: {type(data)}).") # Debug print
        return {"error": f"Path '{path}' does not appear to be a directory or structure could not be retrieved."}

def _get_file_content(owner: str, repo: str, path: str, headers: dict):
    """Fetches the content of a file in a repository."""
    path = path.strip('/')
    if not path:
        return {"error": "File path cannot be empty for 'get_file_content'."}

    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    print(f"Attempting to get content for {owner}/{repo}/{path} using url: {url}") # Debug print
    data = _make_github_request(url, headers)

    if "error" in data:
        return data
    if isinstance(data, dict) and "warning" in data:
        print(f"Warning from _make_github_request: {data['warning']}")
        # Continue if content might still be usable, or decide how to handle non-JSON


    if isinstance(data, dict) and data.get("type") == "file":
        content_encoded = data.get("content")
        encoding = data.get("encoding")

        if not content_encoded or encoding != "base64":
            print(f"Could not get base64 content for {owner}/{repo}/{path}. Encoding: {encoding}, Content available: {bool(content_encoded)}") # Debug print
            return {"error": f"Could not retrieve base64 encoded content for file: {path}"}

        try:
            content_decoded = base64.b64decode(content_encoded).decode("utf-8")

            # --- REMOVED TRUNCATION ---
            # max_len = 10000
            # if len(content_decoded) > max_len:
            #     content_decoded = content_decoded[:max_len] + "\n... [File Content Truncated]"
            #     print(f"Warning: Truncated content for file {path}")
            # --- END REMOVED TRUNCATION ---

            print(f"Successfully decoded content for {owner}/{repo}/{path}, length: {len(content_decoded)}") # Debug print
            return {
                "file_path": path,
                "content": content_decoded, # Return full decoded content
                "size": data.get("size")
            }
        except Exception as e:
            print(f"Error decoding content for {owner}/{repo}/{path}: {str(e)}") # Debug print
            return {"error": f"Failed to decode file content for {path}: {str(e)}"}
    elif isinstance(data, list):
         print(f"Path '{path}' in {owner}/{repo} appears to be a directory when getting content.") # Debug print
         return {"error": f"Path '{path}' appears to be a directory. Use 'get_repo_structure'."}
    else:
        print(f"Could not get file content for {owner}/{repo}/{path}. Response type: {type(data)}, Keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}") # Debug print
        return {"error": f"Could not retrieve file content for path: {path}. Is the path correct? Response: {str(data)[:200]}"}


def _search_code(owner: str, repo: str, query: str, headers: dict):
    """Searches for code within a specific repository."""
    if not query:
        return {"error": "Search query cannot be empty for 'search_code'."}

    search_url = "https://api.github.com/search/code"
    params = {
        "q": f"{query} repo:{owner}/{repo}",
        "per_page": GITHUB_RESULTS_LIMIT
    }
    print(f"Attempting to search code in {owner}/{repo} for '{query}' using url: {search_url} with params: {params}")
    data = _make_github_request(search_url, headers, params=params)

    if "error" in data:
        return data
    if isinstance(data, dict) and "warning" in data:
        print(f"Warning from _make_github_request: {data['warning']}")

    results = []
    total_count = 0
    if isinstance(data, dict) and "items" in data:
        total_count = data.get("total_count", 0)
        for item in data["items"]:
            snippets = []
            text_matches = item.get("text_matches")
            if isinstance(text_matches, list):
                snippets = [match["fragment"] for match in text_matches if isinstance(match, dict) and "fragment" in match]

            results.append({
                "path": item.get("path"),
                "score": item.get("score"),
                "url": item.get("html_url"),
                "snippets": snippets
            })
    print(f"Found {total_count} total results for query '{query}', returning {len(results)}")
    return {
        "query": query,
        "total_results": total_count,
        "showing_results": len(results),
        "results": results
    }

# --- Tool Definition ---
@tool(
    name="github_tool",
    description="Interacts with GitHub repositories and users. Allows listing user/org repositories (public and private accessible via PAT using the /user/repos endpoint when applicable), listing directory structures within a repo, reading file contents (returns full content), and searching code within a specific repository.", # Updated description
    parameters={
        "action": {
            "type": "string",
            "description": "The specific action to perform.",
            "enum": ["list_user_repositories", "get_repo_structure", "get_file_content", "search_code"],
        },
        "owner": {
            "type": "string",
            "description": "The owner (username or organization name) on GitHub whose repositories should be listed or interacted with." # Clarified owner purpose
        },
        "repo": {
            "type": "string",
            "description": "The name of the GitHub repository. Required for 'get_repo_structure', 'get_file_content', and 'search_code'. Not used for 'list_user_repositories'.",
            "optional": True
        },
        "path": {
            "type": "string",
            "description": "The path to a file or directory within the repository (used for 'get_repo_structure' and 'get_file_content'). Omit or use '/' for the root directory.",
            "optional": True
        },
        "query": {
            "type": "string",
            "description": "The code search query (used only for 'search_code'). Supports GitHub search syntax.",
            "optional": True
        }
    }
)
def execute(action: str, owner: str, repo: str = None, path: str = None, query: str = None, **kwargs):
    """Executes a specific action on GitHub."""

    if not GITHUB_PAT or GITHUB_PAT == "your_github_pat_here":
        return {
            "error": "GitHub Personal Access Token (GITHUB_PAT) is not configured.",
            "_tool_status": "❌ Error: GitHub PAT not configured."
        }

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Bearer {GITHUB_PAT}",
        "User-Agent": USER_AGENT
    }

    if not owner:
        return {"error": "GitHub owner (username or organization) is required.", "_tool_status": "❌ Error: Missing owner."}

    result = {}
    status_details = ""

    print(f"[GitHub Tool Execute] Action: {action}, Owner: {owner}, Repo: {repo}, Path: {path}, Query: {query}")

    # --- Action Dispatching ---
    if action == "list_user_repositories":
        result = _list_user_repositories(owner, headers)
        # Create status message based on results
        repo_count = 0
        total_found = 0
        if isinstance(result, dict):
             repo_count = len(result.get("repositories", []))
             total_found = result.get("total_owned_found_in_batch", 0) # Use the count of owned repos

        if "error" in result:
             status_details = f"Failed to list repositories for '{owner}'."
        elif repo_count > 0 :
             status_details = f"Listed {repo_count} repositories owned by '{owner}' (sorted by update, limited by GITHUB_RESULTS_LIMIT from {total_found} found)"
        else: # No error, but empty list
             status_details = f"No repositories found or accessible that are owned by '{owner}'."

    elif action == "get_repo_structure":
        if not repo:
            return {"error": f"Repository name ('repo') is required for action '{action}'.", "_tool_status": f"❌ Error: Missing repo for {action}."}
        result = _get_repo_structure(owner, repo, path, headers)
        if "error" not in result and "structure" in result:
             status_details = f"Listed structure for '{owner}/{repo}/{path or ''}' ({len(result['structure'])} items)"
        elif "error" not in result:
             status_details = f"Listed structure for '{owner}/{repo}/{path or ''}' (Empty or no structure data)"

    elif action == "get_file_content":
        if not repo:
            return {"error": f"Repository name ('repo') is required for action '{action}'.", "_tool_status": f"❌ Error: Missing repo for {action}."}
        if not path:
             return {"error": "File path is required for 'get_file_content'.", "_tool_status": "❌ Error: Missing path for get_file_content."}
        result = _get_file_content(owner, repo, path, headers)
        if "error" not in result and "content" in result:
             status_details = f"Read file content for '{owner}/{repo}/{path}' ({len(result['content'])} chars)"
        elif "error" not in result:
              status_details = f"Completed reading attempt for '{owner}/{repo}/{path}', but no content retrieved."


    elif action == "search_code":
        if not repo:
            return {"error": f"Repository name ('repo') is required for action '{action}'.", "_tool_status": f"❌ Error: Missing repo for {action}."}
        if not query:
            return {"error": "Search query is required for 'search_code'.", "_tool_status": "❌ Error: Missing query for search_code."}
        result = _search_code(owner, repo, query, headers)
        showing = result.get("showing_results", 0) if isinstance(result, dict) else 0
        total = result.get("total_results", 0) if isinstance(result, dict) else 0
        status_details = f"Searched code in '{owner}/{repo}' for query: '{query}'. Found {total} total matches, showing {showing}."
    else:
        result = {"error": f"Invalid action specified: {action}"}
        status_details = f"Invalid action: {action}"

    # --- Format Final Result ---
    if "error" in result:
        if "_tool_status" not in result: # Add status if not already set by validation
             result["_tool_status"] = f"❌ Error ({action}): {result.get('error', 'Unknown GitHub tool error')}"
    elif status_details: # Ensure we have details before setting success status
        result["_tool_status"] = f"✓ github_tool ({action}): {status_details}"
    else:
        # Fallback if no error and no status details were set (should happen less often now)
        print(f"Warning: No error and no status details generated for action '{action}'. Result: {str(result)[:200]}")
        result["_tool_status"] = f"✓ github_tool ({action}): Completed."

    return result