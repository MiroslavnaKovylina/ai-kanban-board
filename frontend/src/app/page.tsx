import { AuthGuard } from "@/components/AuthGuard";
import { KanbanBoard } from "@/components/KanbanBoard";

export default function Home() {
  return (
    <AuthGuard>
      <KanbanBoard />
    </AuthGuard>
  );
}
