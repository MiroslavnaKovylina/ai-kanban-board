"use client";

import { type BoardData } from "@/lib/kanban";

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

type RouterLike = {
  push: (href: string) => void;
};

export type ChatHistoryMessage = {
  role: "user" | "assistant";
  content: string;
};

export type AiBoardResponse = {
  success: boolean;
  message: string;
  board_updated: boolean;
  board: BoardData;
};

export type AuthMeResponse = {
  success: boolean;
  user_id: number;
  username: string;
  board_id: number;
};

export const getCurrentUser = async (): Promise<AuthMeResponse | null> => {
  const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
    method: "GET",
    credentials: "include",
  });

  if (!response.ok) {
    return null;
  }

  return (await response.json()) as AuthMeResponse;
};

export const isAuthenticated = async () => (await getCurrentUser()) !== null;

export const registerUser = async (username: string, password: string) => {
  const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ username, password }),
  });

  return response.ok;
};

export const login = async (username: string, password: string) => {
  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ username, password }),
  });

  return response.ok;
};

export const loadBoard = async (): Promise<BoardData | null> => {
  const response = await fetch(`${API_BASE_URL}/api/board/load`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
  });

  if (!response.ok) {
    return null;
  }

  const data = await response.json();
  return data.board as BoardData;
};

export const saveBoard = async (board: BoardData) => {
  const response = await fetch(`${API_BASE_URL}/api/board/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ board }),
  });

  return response.ok;
};

export const sendAiBoardPrompt = async (
  prompt: string,
  history: ChatHistoryMessage[] = []
): Promise<AiBoardResponse | null> => {
  const response = await fetch(`${API_BASE_URL}/api/ai/board`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({
      prompt,
      history,
    }),
  });

  if (!response.ok) {
    return null;
  }

  return (await response.json()) as AiBoardResponse;
};

export const logout = async (router: RouterLike) => {
  try {
    await fetch(`${API_BASE_URL}/api/auth/logout`, {
      method: "POST",
      credentials: "include",
    });
  } catch {
    // Proceed to redirect even if the server call fails.
  }
  router.push("/login");
};
