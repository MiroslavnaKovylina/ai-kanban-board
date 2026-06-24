import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getCurrentUser, login, isAuthenticated, registerUser } from "@/lib/auth";

describe("auth utility", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("authenticates valid credentials", async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: true } as Response);

    expect(await login("user", "password")).toBe(true);
    expect(localStorage.length).toBe(0);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/auth/login"),
      expect.objectContaining({
        credentials: "include",
        body: JSON.stringify({ username: "user", password: "password" }),
      })
    );
  });

  it("rejects invalid credentials", async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: false } as Response);

    expect(await login("user", "wrong")).toBe(false);
    expect(localStorage.length).toBe(0);
  });

  it("registers a new user", async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: true } as Response);

    expect(await registerUser("new-user", "password")).toBe(true);
    expect(localStorage.length).toBe(0);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/auth/register"),
      expect.objectContaining({ credentials: "include" })
    );
  });

  it("loads the current user from the session cookie", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true,
        user_id: 1,
        username: "user",
        board_id: 1,
      }),
    } as Response);

    await expect(getCurrentUser()).resolves.toMatchObject({ username: "user" });
    await expect(isAuthenticated()).resolves.toBe(true);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/auth/me"),
      expect.objectContaining({ credentials: "include" })
    );
  });

  it("reports unauthenticated when /me fails", async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: false } as Response);

    await expect(getCurrentUser()).resolves.toBeNull();
    await expect(isAuthenticated()).resolves.toBe(false);
  });
});
