"use client";

import { NextRouter } from "next/navigation";
import { type BoardData } from "@/lib/kanban";

const AUTH_STORAGE_KEY = "kanban-auth-session";

const resolveApiBaseUrl = () => {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (configured) {
    return configured.replace(/\/$/, "");
  }

  // In production the frontend is served by backend, so same-origin keeps API simple.
  if (typeof window !== "undefined") {
    return window.location.origin;
  }

  return "http://localhost:8000";
};

const API_BASE_URL = resolveApiBaseUrl();

type AuthSession = {
  username: string;
  password: string;
};

const loadSession = (): AuthSession | null => {
  if (typeof window === "undefined") {
    return null;
  }

  const raw = localStorage.getItem(AUTH_STORAGE_KEY);
  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw) as AuthSession;
    if (typeof parsed.username === "string" && typeof parsed.password === "string") {
      return parsed;
    }
    return null;
  } catch {
    return null;
  }
};

const saveSession = (session: AuthSession) => {
  if (typeof window === "undefined") {
    return;
  }
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
};

const authPayload = () => {
  const session = loadSession();
  if (!session) {
    return null;
  }
  return {
    username: session.username,
    password: session.password,
  };
};

export const isAuthenticated = () =>
  typeof window !== "undefined" && loadSession() !== null;

export const registerUser = async (username: string, password: string) => {
  const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) {
    return false;
  }

  saveSession({ username, password });
  return true;
};

export const login = async (username: string, password: string) => {
  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) {
    return false;
  }

  saveSession({ username, password });
  return true;
};

export const loadBoard = async (): Promise<BoardData | null> => {
  const payload = authPayload();
  if (!payload) {
    return null;
  }

  const response = await fetch(`${API_BASE_URL}/api/board/load`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    return null;
  }

  const data = await response.json();
  return data.board as BoardData;
};

export const saveBoard = async (board: BoardData) => {
  const payload = authPayload();
  if (!payload) {
    return false;
  }

  const response = await fetch(`${API_BASE_URL}/api/board/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...payload, board }),
  });

  return response.ok;
};

export const logout = (router: NextRouter) => {
  if (typeof window !== "undefined") {
    localStorage.removeItem(AUTH_STORAGE_KEY);
  }
  router.push("/login");
};
