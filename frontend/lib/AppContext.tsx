"use client";

import React, { createContext, useContext, useState, useEffect } from "react";

interface AppContextType {
  selectedActivityId: string | null;
  setSelectedActivityId: (id: string | null) => void;
  commandPaletteOpen: boolean;
  setCommandPaletteOpen: (open: boolean) => void;
  openActivityDetail: (activityId: string) => void;
  closeActivityDetail: () => void;
  reviewCount: number;
  setReviewCount: (count: number) => void;
  updateCount: number;
  setUpdateCount: (count: number) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [selectedActivityId, setSelectedActivityId] = useState<string | null>(null);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [reviewCount, setReviewCount] = useState<number>(0);
  const [updateCount, setUpdateCount] = useState<number>(0);

  // Global keyboard shortcut for Command Palette: Cmd+K or Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCommandPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const openActivityDetail = (id: string) => setSelectedActivityId(id);
  const closeActivityDetail = () => setSelectedActivityId(null);

  return (
    <AppContext.Provider
      value={{
        selectedActivityId,
        setSelectedActivityId,
        commandPaletteOpen,
        setCommandPaletteOpen,
        openActivityDetail,
        closeActivityDetail,
        reviewCount,
        setReviewCount,
        updateCount,
        setUpdateCount,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) {
    throw new Error("useApp must be used within an AppProvider");
  }
  return ctx;
}

export const useAppContext = useApp;
