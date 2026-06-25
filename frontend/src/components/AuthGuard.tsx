"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated } from "@/lib/auth";

export const AuthGuard = ({ children }: { children: React.ReactNode }) => {
  const router = useRouter();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    let mounted = true;

    const checkAuth = async () => {
      try {
        if (!(await isAuthenticated())) {
          router.push("/login");
          return;
        }
      } catch {
        router.push("/login");
        return;
      }
      if (mounted) {
        setChecked(true);
      }
    };

    void checkAuth();

    return () => {
      mounted = false;
    };
  }, [router]);

  if (!checked) {
    return null;
  }

  return <>{children}</>;
};
