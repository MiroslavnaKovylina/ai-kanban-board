import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { KanbanBoard } from "@/components/KanbanBoard";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/lib/auth", () => ({
  loadBoard: vi.fn().mockResolvedValue({
    columns: [
      { id: "col-backlog", title: "Backlog", cardIds: ["card-1", "card-2"] },
      { id: "col-discovery", title: "Discovery", cardIds: ["card-3"] },
      { id: "col-progress", title: "In Progress", cardIds: ["card-4", "card-5"] },
      { id: "col-review", title: "Review", cardIds: ["card-6"] },
      { id: "col-done", title: "Done", cardIds: ["card-7", "card-8"] },
    ],
    cards: {
      "card-1": { id: "card-1", title: "Align roadmap themes", details: "Draft quarterly themes." },
      "card-2": { id: "card-2", title: "Gather customer signals", details: "Review feedback." },
      "card-3": { id: "card-3", title: "Prototype analytics view", details: "Sketch dashboard." },
      "card-4": { id: "card-4", title: "Refine status language", details: "Standardize labels." },
      "card-5": { id: "card-5", title: "Design card layout", details: "Add spacing." },
      "card-6": { id: "card-6", title: "QA micro-interactions", details: "Verify states." },
      "card-7": { id: "card-7", title: "Ship marketing page", details: "Copy approved." },
      "card-8": { id: "card-8", title: "Close onboarding sprint", details: "Document notes." },
    },
  }),
  logout: vi.fn(),
  saveBoard: vi.fn().mockResolvedValue(true),
  sendAiBoardPrompt: vi.fn().mockResolvedValue({
    success: true,
    message: "No changes needed.",
    board_updated: false,
    board: null,
  }),
}));

const getFirstColumn = async () => (await screen.findAllByTestId(/column-/i))[0];

describe("KanbanBoard", () => {
  it("renders five columns", async () => {
    render(<KanbanBoard />);
    expect(await screen.findAllByTestId(/column-/i)).toHaveLength(5);
  });

  it("renames a column", async () => {
    render(<KanbanBoard />);
    const column = await getFirstColumn();
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "New Name");
    expect(input).toHaveValue("New Name");
  });

  it("adds and removes a card", async () => {
    render(<KanbanBoard />);
    const column = await getFirstColumn();
    const addButton = within(column).getByRole("button", {
      name: /add a card/i,
    });
    await userEvent.click(addButton);

    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await userEvent.type(titleInput, "New card");
    const detailsInput = within(column).getByPlaceholderText(/details/i);
    await userEvent.type(detailsInput, "Notes");

    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    expect(within(column).getByText("New card")).toBeInTheDocument();

    const deleteButton = within(column).getByRole("button", {
      name: /delete new card/i,
    });
    await userEvent.click(deleteButton);

    expect(within(column).queryByText("New card")).not.toBeInTheDocument();
  });
});
