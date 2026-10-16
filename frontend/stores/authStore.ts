import { create } from "zustand";
import {
  UserProfile,
  loginUser,
  registerUser,
  logoutUser,
  getCurrentUser,
  setApiSessionToken,
} from "../lib/api";

const USER_SESSION_KEY = "garuda_auth_user";
const TOKEN_SESSION_KEY = "garuda_session_token";
const AUTH_COOKIE_FLAG = "garuda_auth_active";

function setAuthStatusCookie(active: boolean, rememberMe = true) {
  if (typeof document === "undefined") return;
  if (active) {
    const maxAge = rememberMe ? `; Max-Age=${7 * 24 * 3600}` : "";
    document.cookie = `${AUTH_COOKIE_FLAG}=1; Path=/; SameSite=Lax${maxAge}`;
  } else {
    document.cookie = `${AUTH_COOKIE_FLAG}=; Path=/; Max-Age=0; SameSite=Lax`;
  }
}

export interface AuthState {
  user: UserProfile | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isCheckingAuth: boolean;
  hasInitialized: boolean;
  error: string | null;

  login: (email: string, password: string, rememberMe?: boolean) => Promise<boolean>;
  register: (
    fullName: string,
    email: string,
    password: string,
    confirmPassword: string
  ) => Promise<boolean>;
  logout: () => Promise<void>;
  initAuth: () => Promise<boolean>;
  clearError: () => void;
  setUser: (user: UserProfile | null) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: false,
  isCheckingAuth: true,
  hasInitialized: false,
  error: null,

  initAuth: async () => {
    if (typeof window === "undefined") return false;
    set({ isCheckingAuth: true });

    try {
      const sessionToken = sessionStorage.getItem(TOKEN_SESSION_KEY);
      if (sessionToken) {
        setApiSessionToken(sessionToken);
      }

      // Verify active session with backend (via HttpOnly cookie or session token)
      const freshUser = await getCurrentUser(sessionToken || undefined);
      sessionStorage.setItem(USER_SESSION_KEY, JSON.stringify(freshUser));
      setAuthStatusCookie(true, true);
      set({
        user: freshUser,
        token: sessionToken,
        isAuthenticated: true,
        isCheckingAuth: false,
        hasInitialized: true,
        error: null,
      });
      return true;
    } catch {
      sessionStorage.removeItem(TOKEN_SESSION_KEY);
      sessionStorage.removeItem(USER_SESSION_KEY);
      setApiSessionToken(null);
      setAuthStatusCookie(false);
      set({
        user: null,
        token: null,
        isAuthenticated: false,
        isCheckingAuth: false,
        hasInitialized: true,
      });
      return false;
    }
  },

  login: async (email: string, password: string, rememberMe = true) => {
    set({ isLoading: true, error: null });
    try {
      const res = await loginUser(email, password, rememberMe);

      sessionStorage.setItem(TOKEN_SESSION_KEY, res.access_token);
      sessionStorage.setItem(USER_SESSION_KEY, JSON.stringify(res.user));
      setApiSessionToken(res.access_token);
      setAuthStatusCookie(true, rememberMe);

      set({
        token: res.access_token,
        user: res.user,
        isAuthenticated: true,
        isLoading: false,
        isCheckingAuth: false,
        hasInitialized: true,
        error: null,
      });
      return true;
    } catch (err: any) {
      const errorMsg =
        err?.message || "Invalid email or password. Please verify your credentials.";
      setAuthStatusCookie(false);
      set({
        isLoading: false,
        error: errorMsg,
        isAuthenticated: false,
      });
      return false;
    }
  },

  register: async (
    fullName: string,
    email: string,
    password: string,
    confirmPassword: string
  ) => {
    set({ isLoading: true, error: null });
    try {
      const res = await registerUser({
        full_name: fullName,
        email,
        password,
        confirm_password: confirmPassword,
      });

      sessionStorage.setItem(TOKEN_SESSION_KEY, res.access_token);
      sessionStorage.setItem(USER_SESSION_KEY, JSON.stringify(res.user));
      setApiSessionToken(res.access_token);
      setAuthStatusCookie(true, true);

      set({
        token: res.access_token,
        user: res.user,
        isAuthenticated: true,
        isLoading: false,
        isCheckingAuth: false,
        hasInitialized: true,
        error: null,
      });
      return true;
    } catch (err: any) {
      const errorMsg =
        err?.message || "Failed to create account. Please check your details and try again.";
      setAuthStatusCookie(false);
      set({
        isLoading: false,
        error: errorMsg,
        isAuthenticated: false,
      });
      return false;
    }
  },

  logout: async () => {
    set({ isLoading: true });
    try {
      await logoutUser();
    } catch {}
    if (typeof window !== "undefined") {
      sessionStorage.removeItem(TOKEN_SESSION_KEY);
      sessionStorage.removeItem(USER_SESSION_KEY);
      localStorage.removeItem("garuda_auth_token");
      localStorage.removeItem("garuda_auth_user");
    }
    setApiSessionToken(null);
    setAuthStatusCookie(false);
    set({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
      isCheckingAuth: false,
      hasInitialized: true,
      error: null,
    });
  },

  clearError: () => set({ error: null }),
  setUser: (user: UserProfile | null) =>
    set({ user, isAuthenticated: !!user, isCheckingAuth: false, hasInitialized: true }),
}));
