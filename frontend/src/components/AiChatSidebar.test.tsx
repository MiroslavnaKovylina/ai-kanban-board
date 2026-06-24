import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { AiChatSidebar } from "@/components/AiChatSidebar";

describe("AiChatSidebar", () => {
  it("sends prompt when pressing Enter", async () => {
    const onSend = vi.fn().mockResolvedValue({ message: "Done." });

    render(<AiChatSidebar onSend={onSend} />);

    await userEvent.type(screen.getByLabelText(/ai prompt/i), "Create testing task{enter}");

    expect(onSend).toHaveBeenCalledTimes(1);
    expect(await screen.findByText("Done.")).toBeInTheDocument();
  });

  it("sends prompt and renders assistant response", async () => {
    const onSend = vi.fn().mockResolvedValue({ message: "Created a new card in To Do." });

    render(<AiChatSidebar onSend={onSend} />);

    await userEvent.type(screen.getByLabelText(/ai prompt/i), "Add a task for release notes");
    await userEvent.click(screen.getByRole("button", { name: /send to ai/i }));

    expect(onSend).toHaveBeenCalled();
    expect(await screen.findByText(/created a new card in to do/i)).toBeInTheDocument();
  });

  it("shows error when AI call fails", async () => {
    const onSend = vi.fn().mockResolvedValue(null);

    render(<AiChatSidebar onSend={onSend} />);

    await userEvent.type(screen.getByLabelText(/ai prompt/i), "Move review cards to done");
    await userEvent.click(screen.getByRole("button", { name: /send to ai/i }));

    expect(await screen.findByText(/ai request failed/i)).toBeInTheDocument();
  });
});
