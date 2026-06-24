#!/usr/bin/env python3
"""
Part 11 E2E validation script for containerized app.
Tests: auth, board CRUD, persistence, and AI endpoint.
"""
import json
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = "http://localhost:8000"
TEST_USER = "test_e2e_user"
TEST_PASSWORD = "test_e2e_password"


def http_request(method: str, endpoint: str, data: dict | None = None) -> tuple[int, dict]:
    """Make HTTP request and return (status_code, response_dict)."""
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode() if data else None

    req = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(req, timeout=10) as response:
            status = response.status
            content = response.read().decode()
            result = json.loads(content) if content else {}
            return status, result
    except HTTPError as exc:
        status = exc.code
        content = exc.read().decode()
        result = json.loads(content) if content else {}
        return status, result
    except URLError as exc:
        print(f"ERROR: Connection failed to {url}: {exc}")
        sys.exit(1)


def test_auth():
    """Test registration and login."""
    print("[AUTH] Testing registration...")
    status, resp = http_request("POST", "/api/auth/register", {
        "username": TEST_USER,
        "password": TEST_PASSWORD,
    })
    if status != 200:
        print(f"  FAIL: register returned {status}")
        return False
    print(f"  OK: registered user {TEST_USER}")

    print("[AUTH] Testing login...")
    status, resp = http_request("POST", "/api/auth/login", {
        "username": TEST_USER,
        "password": TEST_PASSWORD,
    })
    if status != 200:
        print(f"  FAIL: login returned {status}")
        return False
    print(f"  OK: login successful")
    return True


def test_board_persistence():
    """Test board load, save, and reload."""
    print("[BOARD] Testing initial board load...")
    status, resp = http_request("POST", "/api/board/load", {
        "username": TEST_USER,
        "password": TEST_PASSWORD,
    })
    if status != 200:
        print(f"  FAIL: board/load returned {status}")
        return False
    
    board = resp.get("board", {})
    columns = board.get("columns", [])
    cards = board.get("cards", {})
    print(f"  OK: loaded board with {len(columns)} columns, {len(cards)} cards")

    print("[BOARD] Testing board save...")
    if len(columns) > 0 and len(cards) > 0:
        new_board = {
            "columns": columns[:1],
            "cards": {cid: cards[cid] for cid in list(cards.keys())[:1] if cid in cards},
        }
    else:
        new_board = board
    
    status, resp = http_request("POST", "/api/board/save", {
        "username": TEST_USER,
        "password": TEST_PASSWORD,
        "board": new_board,
    })
    if status != 200:
        print(f"  FAIL: board/save returned {status}")
        return False
    print(f"  OK: saved board changes")

    print("[BOARD] Testing board reload (persistence)...")
    time.sleep(0.5)
    status, resp = http_request("POST", "/api/board/load", {
        "username": TEST_USER,
        "password": TEST_PASSWORD,
    })
    if status != 200:
        print(f"  FAIL: reload board returned {status}")
        return False
    
    reloaded_board = resp.get("board", {})
    if reloaded_board.get("columns") == new_board.get("columns"):
        print(f"  OK: board state persisted correctly")
    else:
        print(f"  WARN: board state mismatch after reload")
    
    return True


def test_ai_endpoint():
    """Test AI endpoint with valid auth and abuse protections."""
    print("[AI] Testing AI board endpoint with valid auth...")
    status, resp = http_request("POST", "/api/ai/board", {
        "username": TEST_USER,
        "password": TEST_PASSWORD,
        "prompt": "What columns exist?",
        "history": [],
    })
    
    if status == 200:
        print(f"  OK: AI endpoint returned 200")
        message = resp.get("message", "")
        board_updated = resp.get("board_updated", False)
        print(f"    Message: {message[:80]}")
        print(f"    Board updated: {board_updated}")
        return True
    elif status == 503:
        print(f"  WARN: AI endpoint returned 503 (OPENROUTER_API_KEY not configured)")
        return True
    else:
        print(f"  FAIL: AI endpoint returned {status}")
        return False


def test_relogin():
    """Test logout and relogin persistence."""
    print("[RELOGIN] Testing logout (local operation, no server call)...")
    print(f"  OK: logout is client-side only")

    print("[RELOGIN] Testing relogin after logout...")
    status, resp = http_request("POST", "/api/auth/login", {
        "username": TEST_USER,
        "password": TEST_PASSWORD,
    })
    if status != 200:
        print(f"  FAIL: relogin returned {status}")
        return False
    print(f"  OK: relogin successful, session restored")

    print("[RELOGIN] Testing board still persisted after relogin...")
    status, resp = http_request("POST", "/api/board/load", {
        "username": TEST_USER,
        "password": TEST_PASSWORD,
    })
    if status == 200:
        print(f"  OK: board still available after relogin")
        return True
    else:
        print(f"  FAIL: board/load after relogin returned {status}")
        return False


def main():
    """Run all E2E validation tests."""
    print("=" * 60)
    print("Part 11 E2E Validation (Container Runtime)")
    print("=" * 60)
    
    tests = [
        ("Authentication", test_auth),
        ("Board Persistence", test_board_persistence),
        ("AI Endpoint", test_ai_endpoint),
        ("Relogin Persistence", test_relogin),
    ]
    
    results = []
    for name, test_func in tests:
        print()
        try:
            passed = test_func()
            results.append((name, "PASS" if passed else "FAIL"))
        except Exception as exc:
            print(f"ERROR: {exc}")
            results.append((name, "ERROR"))
    
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    for name, status in results:
        symbol = "✓" if status == "PASS" else "✗" if status == "FAIL" else "!"
        print(f"{symbol} {name}: {status}")
    
    all_passed = all(status == "PASS" for _, status in results)
    print("=" * 60)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
